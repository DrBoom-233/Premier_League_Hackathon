"""Bounded Azure OpenAI vision request; reads runtime manifests/images only."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    from .motion import CLIP_IDS, SCENARIO_IDS, sample_frames
except ImportError:
    from motion import CLIP_IDS, SCENARIO_IDS, sample_frames

PROMPT_VERSION = "motion-observer-v1"
PROMPT = """Observe the target player P001 in these ordered synthetic football frames.
Compare current movement with the separate reference clip. Describe only visible
activity and changes, cite supplied frame IDs, and identify obscured body parts.
Do not diagnose injury, infer hidden motion, or report injury probabilities.
Return a JSON object with exactly these fields:
observations: array of strings; evidence_frame_ids: array of supplied frame IDs;
view_status: clear, partial, or obscured; limitations: array of strings;
review_status: reviewed, needs_recheck, or insufficient_evidence;
requested_recheck: null or {start_ms: number, end_ms: number, reason: string}.
A recheck interval must be within the current clip and no longer than 3000ms.
No detected change is a valid result. Do not treat confidence as probability.
"""


def safe_file(base, relative):
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError("Runtime path escapes clip directory")
    if not path.is_file():
        raise ValueError(f"Missing runtime file: {relative}")
    return path


def load_clip(runtime, clip):
    if clip not in CLIP_IDS:
        raise ValueError("Unknown clip ID")
    base = runtime / clip
    value = json.loads(safe_file(base, "input_manifest.json").read_text())
    return base, value


def image_content(base, frames, role):
    content = []
    for frame in frames:
        path = safe_file(base, frame["path"])
        if path.suffix.lower() != ".png" or path.stat().st_size > 10_000_000:
            raise ValueError("Expected PNG under 10 MB")
        content.append({"type": "text", "text": f"{role} {frame['frame_id']} clip_time_ms={frame['clip_time_ms']}"})
        content.append({"type": "image_url", "image_url": {
            "url": "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode(),
            "detail": "high"}})
    return content


def validate_output(value, frame_ids, duration):
    required = {"observations", "evidence_frame_ids", "view_status", "limitations",
                "review_status", "requested_recheck"}
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("Unexpected model output fields")
    for field in ("observations", "evidence_frame_ids", "limitations"):
        if not isinstance(value[field], list) or not all(isinstance(v, str) for v in value[field]):
            raise ValueError(f"Invalid {field}")
    if not set(value["evidence_frame_ids"]).issubset(frame_ids):
        raise ValueError("Model cited frames it did not receive")
    if value["observations"] and not value["evidence_frame_ids"]:
        raise ValueError("Observations need supporting frame IDs")
    if value["view_status"] not in {"clear", "partial", "obscured"}:
        raise ValueError("Invalid view_status")
    if value["review_status"] not in {"reviewed", "needs_recheck", "insufficient_evidence"}:
        raise ValueError("Invalid review_status")
    window = value["requested_recheck"]
    if window is not None:
        if not isinstance(window, dict) or set(window) != {"start_ms", "end_ms", "reason"}:
            raise ValueError("Invalid recheck structure")
        start, end = window["start_ms"], window["end_ms"]
        if (type(start) not in (int, float) or type(end) not in (int, float)
                or not 0 <= start < end <= duration or end - start > 3000
                or not isinstance(window["reason"], str) or not window["reason"].strip()):
            raise ValueError("Invalid recheck interval")
    # Shape/citation validation cannot prove visual or medical correctness: review outputs.


def call_model(content):
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
    parsed = urllib.parse.urlsplit(endpoint)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("AZURE_OPENAI_ENDPOINT must be an HTTPS resource URL")
    deployment = os.environ["AZURE_OPENAI_DEPLOYMENT"]
    version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21")
    url = (endpoint + "/openai/deployments/" + urllib.parse.quote(deployment, safe="")
           + "/chat/completions?api-version=" + urllib.parse.quote(version, safe=""))
    payload = {"messages": [{"role": "system", "content": PROMPT},
                             {"role": "user", "content": content}],
               "max_completion_tokens": 900, "response_format": {"type": "json_object"}}
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={
        "Content-Type": "application/json", "api-key": os.environ["AZURE_OPENAI_API_KEY"]})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIO_IDS, required=True)
    parser.add_argument("--runtime", type=Path, default=Path("data/animation/runtime"))
    parser.add_argument("--results", type=Path, default=Path("data/animation/evaluation/results"))
    parser.add_argument("--run", action="store_true", help="Send images to configured model (billable)")
    parser.add_argument("--allow-recheck", action="store_true", help="Allow at most one additional call")
    args = parser.parse_args()
    base, clip = load_clip(args.runtime, args.scenario)
    reference_base, reference = load_clip(args.runtime, clip["reference_clip_id"])
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / '.env')
    current = sample_frames(clip["frames"], 7)
    refs = sample_frames(reference["frames"], 3)
    content = image_content(reference_base, refs, "reference") + image_content(base, current, "current")
    record = {"scenario_id": args.scenario, "prompt_version": PROMPT_VERSION,
              "prompt_sha256": hashlib.sha256(PROMPT.encode()).hexdigest(),
              "manifest_sha256": hashlib.sha256((base / "input_manifest.json").read_bytes()).hexdigest(),
              "deployment": os.environ.get("AZURE_OPENAI_DEPLOYMENT"),
              "status": "not_run", "calls": [], "human_review_status": "pending"}
    frame_ids = {f["frame_id"] for f in current + refs}
    record["initial_frame_ids"] = sorted(frame_ids)
    args.results.mkdir(parents=True, exist_ok=True)
    path = args.results / f"{args.scenario}_vlm_{time.time_ns()}.json"
    try:
        if args.run:
            missing = [key for key in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT",
                                       "AZURE_OPENAI_API_KEY") if not os.environ.get(key)]
            if missing:
                raise ValueError("Missing environment variables: " + ", ".join(missing))
            for attempt in range(2 if args.allow_recheck else 1):
                started = time.perf_counter()
                raw = call_model(content)
                call = {"latency_seconds": time.perf_counter() - started,
                        "input_frame_ids": sorted(frame_ids), "response": raw}
                record["calls"].append(call)
                value = json.loads(raw["choices"][0]["message"]["content"])
                validate_output(value, frame_ids, clip["duration_ms"])
                call["validated_output"] = value
                window = value["requested_recheck"]
                if window is None or attempt == 1 or not args.allow_recheck:
                    break
                extra = sample_frames(clip["frames"], 8, window["start_ms"], window["end_ms"])
                recheck_refs = sample_frames(reference["frames"], 2)
                content = [{"type": "text", "text": "One requested recheck. Reassess only the supplied frames. No further calls are available."}]
                content += image_content(reference_base, recheck_refs, "reference")
                content += image_content(base, extra, "current recheck")
                frame_ids = {f["frame_id"] for f in extra + recheck_refs}
            record["status"] = "completed"
            record["review_status"] = value["review_status"]
        else:
            record["reason"] = "Dry run: images validated locally; no model call made."
    except (ValueError, KeyError, TypeError, urllib.error.URLError, TimeoutError) as error:
        record["status"] = "failed"
        # Do not persist URLs/headers or credentials from transport errors.
        record["error"] = str(error) if isinstance(error, ValueError) else type(error).__name__
        raise SystemExit(record["error"])
    finally:
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(f"{record['status']}: {path}")


if __name__ == "__main__":
    main()
