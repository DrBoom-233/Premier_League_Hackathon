# Synthetic football animation

Procedural Blender assets for PitchGuard. All geometry, materials and motion are
created by our scripts; no third-party character or motion assets are used.

## Deliverables

| Clip | Content | Duration | Frames |
| --- | --- | --- | --- |
| S001 | Steady stylized jogging | 10 s | 240 |
| S002 | Jog, slow toward walking, settle, stand from 8 s | 10 s | 240 |
| S003 | Same motion as S002, foreground equipment obscures legs around 4–6 s | 10 s | 240 |
| S004 | Jog 0–3 s, slow 3–5 s, then sustained fictional limping gait | 10 s | 240 |
| S006 | Same speed/path as S004, symmetric gait throughout | 10 s | 240 |
| R001 | Separately generated reference, different initial gait phase | 3 s | 72 |

All clips use 1280 × 720, 24 fps, the same character, fixed orthographic camera,
lighting and clothing. These are stylized motion approximations, not biomechanical
or medically validated injury simulations. S002/S003 belong to one evaluation
group; S004/S006 belong to another. Keep each pair in the same data split.
S005 remains reserved for the optional camera-change experiment.

The new pair uses event-planned foot contacts. During the asymmetric section,
the near-camera leg takes the shorter forward step and spends less of the cycle
in support; the other leg has a longer support phase. The pelvis dips and the
torso rolls slightly. Both clips have exactly the same root x trajectory and
speed; asymmetry does not change clothing, lighting or camera. Step parameters
are fixed before each swing to preserve planted feet, so the gait changes over
successive steps during/after the 3–5 s transition. Body/foot geometry is unchanged.

Local output layout:

```text
configs/                         Production parameters (never model input)
scenes/S001.blend                Editable character, hierarchy and animation
runtime/S001/video.mp4           H.264 playback
runtime/S001/frames/*.png        Complete original render sequence
runtime/S001/input_manifest.json Full frame IDs and clip/match timestamps
previews/                       Separate low-resolution/still previews
evaluation/annotations.json     Empty until a person reviews the complete videos
evaluation/results/             Actual generation, verification and model records
generation_notes.md             Implementation and QA record
```

Large generated assets and portable tools are gitignored. Preserve/copy the
`runtime`, `scenes`, and `evaluation/results` directories for team handoff, or
rebuild them from the scripts/configs. A fresh clone does not contain the videos.

## Rebuild on Windows

Tested with **Blender 4.5.9 LTS** and external Python 3.12.4. Blender runs the
generator in its own bundled Python. External Python 3.11+ only runs the download,
self-check and manifest/model tools. Those tools use the standard library.
An EEVEE-compatible graphics device/driver is required; the tested GPU is an
NVIDIA RTX 4070 Ti. No Azure resources or paid model calls are needed for rendering.

From the repository root in PowerShell (adjust `$Python` to your interpreter):

```powershell
$Python = 'C:\Users\Charlie\anaconda3\python.exe'
& $Python scripts/animation/setup_blender.py
& $Python -m unittest discover -s scripts/animation -v

# 3-second, 640x360 preview, separate from full outputs
./scripts/animation/render.ps1 -Scenario S001 -Preview

# Ten evenly spaced 1280x720 stills across the complete action
./scripts/animation/render.ps1 -Scenario S002 -Stills

# Inspect the actual limping section in a 3-second low-resolution preview
./scripts/animation/render.ps1 -Scenario S004 -Preview -PreviewStart 6

# Rebuild just the new pair
./scripts/animation/render.ps1 -Scenario S004
./scripts/animation/render.ps1 -Scenario S006

# All five current clips plus the independent reference
./scripts/animation/render.ps1 -Scenario all *> data/animation/batch.log
& $Python scripts/animation/verify_outputs.py
```

Use `-Overwrite` to regenerate an existing clip. This deletes only generated
`frame_*.png`, the old video and manifest for that explicit output clip; it does
not remove configs or annotations. Blender may retain `.blend1` scene backups.
To use an existing Blender installation:

```powershell
./scripts/animation/render.ps1 -Scenario S001 -Blender 'C:\path\to\blender.exe'
```

The portable download is pinned to an official Blender archive and SHA256 in
`setup_blender.py`; it remains inside `.tools`. Blender's user resource/cache path
is also redirected there by `render.ps1`. Nothing is installed globally.

## Frame interface

The action tool should receive **only `runtime/`**, not the repository, configs,
Blender scenes or evaluation files. Manifests use neutral clip/player/frame IDs
and contain all frames in chronological order. Each path is relative to its clip
directory. All clips have a single target, `P001`.

```text
clip_time_ms = (frame_number - 1) * 1000 / fps
match_time_ms = match_start_ms + clip_time_ms
```

The first frame represents 0 ms; the last of 240 frames represents 9958.333 ms.
Each image is displayed for 1/24 second, so the video duration is exactly 10 s.
The independent reference starts at synthetic match time 67:00; current clips
start at 68:00. These are synthetic clock values, not real match records.

`motion.sample_frames` selects ten uniformly spaced initial images without
reading labels. The full PNG sequence supports time-bounded resampling. Reference
images count toward the request budget. Never use `generation_notes.md` or
`annotations.json` as model context.

## Optional later VLM test

S004/S006 now participate in the dashboard and separate synthetic probability
demo. A real S006 Agent run completed on 2026-10-26; comparative model evaluation
of the pair and human annotation remain pending. The following dry run checks image inputs locally and
records `not_run`; it makes no network request:

```powershell
& $Python scripts/animation/run_vlm.py --scenario S001
```

For a later real call, set `AZURE_OPENAI_ENDPOINT` (resource root),
`AZURE_OPENAI_DEPLOYMENT`, and `AZURE_OPENAI_API_KEY` in the local environment,
then append `--run`. `AZURE_OPENAI_API_VERSION` defaults to `2024-10-21`.
This adapter targets Azure OpenAI vision chat completions with JSON output;
Foundry models using other APIs need a different adapter. Deployment compatibility
was tested against the configured GPT-4.1 mini deployment on 2026-10-23. Put credentials only in Git-ignored `.env`; the adapter loads it.

Initial input: 7 current + 3 reference images, up to 900 completion tokens.
Optional `--allow-recheck` permits one additional request with up to eight
interval images plus two reference images over at most three seconds; previous images
are not accumulated. Each call has a 60-second transport
timeout and no automatic retries. Responses, actual model/usage, latency and frame
IDs are saved; malformed/unsupported citations are rejected and retained as
failures. JSON/citation checks cannot establish visual correctness or rule out
medical claims: review the actual output. No inference has been claimed from a
dry run, and no API prices or costs are assumed.

S004/S006 are also available in the live dashboard as the featured matched pair.
The same independent synthetic P001 history and R001 reference are linked for
qualitative analysis; these are not measured longitudinal records. The probability
simulator features S006/S004 shoe-span measurements, with S001/S002 speed cases
available as secondary examples. No new model call is needed to use that simulator,
and model recognition of the new gait pair remains unvalidated.

## Acceptance

`verify_outputs.py` checks all PNG names/dimensions, exact manifest time mapping,
editable scene existence, H.264 metadata, frame counts, duration and fps.
`test_animation.py` checks planted feet, inverse kinematics, continuous slowing,
paired motion, unequal step lengths/support durations, neutral runtime metadata
and bounded frame/citation handling.

A person must still watch each full video, assess motion artifacts/readability,
and fill `evaluation/annotations.json` with actual observations and reviewed
times. Production parameters are not human ground truth. See
[generation notes](generation_notes.md) for the measured run and remaining limits.

Official API references: [keyframes](https://docs.blender.org/api/4.5/bpy.types.bpy_struct.html#bpy.types.bpy_struct.keyframe_insert),
[image strips](https://docs.blender.org/api/4.5/bpy.types.SequenceEditor.html),
[render settings](https://docs.blender.org/api/4.5/bpy.types.RenderSettings.html).
