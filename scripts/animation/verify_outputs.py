"""Verify complete PNG sequences, MP4 sample count/timing and runtime contracts."""
import argparse
import json
from pathlib import Path
import struct

from motion import manifest, sample_frames


def boxes(data, start=0, end=None):
    end = len(data) if end is None else end
    while start + 8 <= end:
        size, kind = struct.unpack_from(">I4s", data, start)
        header = 8
        if size == 1:
            size, = struct.unpack_from(">Q", data, start + 8)
            header = 16
        elif size == 0:
            size = end - start
        if size < header or start + size > end:
            raise ValueError("Invalid MP4 box")
        yield kind, start + header, start + size
        start += size


def video_info(path):
    data = path.read_bytes()
    found = {}

    def visit(start, end):
        for kind, body, stop in boxes(data, start, end):
            if kind in (b"moov", b"trak", b"mdia", b"minf", b"stbl"):
                visit(body, stop)
            elif kind == b"mdhd":
                if data[body] == 1:
                    timescale, duration = struct.unpack_from(">IQ", data, body + 20)
                else:
                    timescale, duration = struct.unpack_from(">II", data, body + 12)
                found["duration_seconds"] = duration / timescale
            elif kind == b"stsz":
                found["frame_count"], = struct.unpack_from(">I", data, body + 8)
            elif kind == b"stsd":
                for codec, sample, _ in boxes(data, body + 8, stop):
                    if codec == b"avc1":
                        found["codec"] = "H.264"
                        found["resolution"] = list(struct.unpack_from(">HH", data, sample + 24))
    visit(0, len(data))
    if set(found) != {"duration_seconds", "frame_count", "codec", "resolution"}:
        raise ValueError("Missing H.264 video metadata")
    found["fps"] = found["frame_count"] / found["duration_seconds"]
    return found


def verify(root):
    results = []
    for clip in ("S001", "S002", "S003", "R001"):
        config = json.loads((root / "configs" / f"{clip}.json").read_text())
        runtime = root / "runtime" / clip
        value = json.loads((runtime / "input_manifest.json").read_text())
        if value != manifest(config):
            raise ValueError(f"{clip}: manifest/config mismatch")
        expected = {f["path"] for f in value["frames"]}
        actual = {"frames/" + p.name for p in (runtime / "frames").glob("*.png")}
        if actual != expected:
            raise ValueError(f"{clip}: missing or extra frames")
        for frame in value["frames"]:
            with (runtime / frame["path"]).open("rb") as source:
                header = source.read(24)
            if header[:8] != b"\x89PNG\r\n\x1a\n" or list(struct.unpack(">II", header[16:24])) != config["resolution"]:
                raise ValueError(f"Invalid PNG: {frame['frame_id']}")
        video = video_info(runtime / "video.mp4")
        if (video["frame_count"] != len(value["frames"]) or video["resolution"] != config["resolution"]
                or abs(video["fps"] - config["fps"]) > 0.001
                or abs(video["duration_seconds"] * 1000 - value["duration_ms"]) > 0.1):
            raise ValueError(f"{clip}: video timing/resolution mismatch")
        if not (root / "scenes" / f"{clip}.blend").is_file():
            raise ValueError(f"{clip}: missing editable scene")
        results.append({"scenario_id": clip, **video, "png_frames": len(expected),
                        "initial_sample_count": len(sample_frames(value["frames"]))})
    return {"status": "passed", "clips": results,
            "visual_review": "Agent inspected representative frames; human acceptance pending",
            "vlm_status": "not_run"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("data/animation"))
    args = parser.parse_args()
    result = verify(args.root)
    output = args.root / "evaluation" / "results" / "verification.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
