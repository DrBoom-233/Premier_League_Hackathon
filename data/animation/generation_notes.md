# Generation and inspection record

Date: 2026-10-22. Author: Codex, following `docs/SYNTHETIC_ANIMATION_PLAN.md`.

## Implementation

- Downloaded official portable Blender 4.5.9 LTS into the ignored `.tools` folder;
  verified SHA256 `41da973b9bf95bb312cbeff4d1982feb13259b43c821686b9bafea4dfe5477cf`.
- Created one procedural player with solid torso/head/limbs, hip/knee/ankle and
  shoulder/elbow parent pivots. Generated dense linear location/rotation keys.
- Used integrated root distance to drive gait phase, world-planted stance feet,
  eased foot swing and analytic two-segment leg IK. Slowdown changes both spatial
  motion and limb cadence/amplitude. The figure settles before 8 s and holds.
- Reused the exact S002 motion for S003. A plain foreground equipment screen
  obscures lower-body evidence around 4–6 s; entry/exit introduces some partial
  occlusion outside that core interval. The independent R001 clip uses a different
  initial gait phase, with the same visual template.
- Saved editable scenes before rendering; encoded H.264 from the exact PNG
  sequence with Blender's bundled FFmpeg. Runtime manifests appear only after
  successful full render/encoding, and never contain production motion labels.
- Motion is entirely deterministic. `seed` is recorded for provenance; no random
  variation is currently applied. Identical scripts/configs recreate the same
  motion, though bit-identical rendering across GPUs/drivers is not guaranteed.

## Iterations

1. Factory-empty Blender scenes have no World object: added explicit daylight
   world creation instead of assuming one exists.
2. Initial three-second preview: Cycles CPU, 640x360, 72 frames; total 57.7 s.
   Inspected limb connections, ground contact and composition.
3. Switched to locally tested EEVEE, 16 samples. First complete S001 rendered
   240 frames at 1280x720 in 45.1 s, mean 0.176 s/frame (encoding included in total).
4. Inspected representative S002 transition/end frames and S003 at 5 s. The
   equipment visibly blocks the legs. The first standing pose was too crouched;
   raised the pelvis and reduced swing lift during slowdown, then rebuilt all
   final scenes/videos from the revised script. These are agent visual checks,
   not a completed human annotation pass.

Per-clip final measured timings, Blender version, exact config and script hashes
are saved in `evaluation/results/*_generation.json`. Complete media verification
is saved in `evaluation/results/verification.json` after the final batch.

Final revised batch measurements (seconds; includes scene build and encoding):

| Clip | PNG frames | Mean render/frame | Total |
| --- | --- | --- | --- |
| S001 | 240 | 0.171 | 43.9 |
| S002 | 240 | 0.171 | 43.9 |
| S003 | 240 | 0.173 | 44.4 |
| R001 | 72 | 0.289 | 21.8 |

Total: 792 PNG frames, 154.0 seconds. All final reports match the delivered
`build_scene.py` and `motion.py` source hashes. The six standard-library checks
passed. Media verification passed for all four clips: complete PNG sequences,
1280x720 resolution, H.264 video, 24 fps and exact 10/3-second durations.
Additionally decoded the first, middle and last MP4 frames of every clip through
Blender's movie sequencer; all twelve frame decodes passed. Actual decode records
are in `evaluation/results/decode_verification.json`.

The local `preview.html` plays each full MP4. `previews/comparison.gif` is a
four-fps, downscaled side-by-side review copy of the three core clips; it is not
an input to the model. Three local model-input dry runs each selected ten current
and three reference images and explicitly recorded `not_run`.

## Remaining acceptance work

- Human review of full videos and real interval annotations remain pending.
- This is a stylized jogging/walking approximation with no flight-phase model,
  biomechanics, realistic muscles, skinning or injury simulation. It is suitable
  for checking visible activity/occlusion, subject to human and VLM readability
  checks. Walking transition quality is not validated against real motion data.
- On the user's instruction, this delivery stops at animation assets. No Foundry
  model was configured or called. Local VLM dry runs only validate input handling;
  they do not demonstrate recognition, grounding, abstention, latency or cost.
- Generated media remain local and ignored by Git; no shared upload, commit,
  push, deployment or external publication was performed.

## 2026-10-26: asymmetric gait and matched control

Added S004 and S006 following the user's request for a visible fictional limping
gait. Both clips run for 10 seconds at 1280x720/24 fps, with identical horizontal
root positions, speed, camera, lighting and character. S004/S006 form evaluation
group G004; S005 remains reserved for a camera experiment.

- 0–3 s: identical normal jogging in both clips.
- 3–5 s: speed smoothly decreases from 0.8 to 0.4 m/s. Asymmetric motion is
  introduced over planned steps in S004; S006 remains symmetric.
- After 5 s: both continue walking instead of stopping. S004 settles into shorter
  near-side forward steps, a shorter near-side support phase, longer opposite-side
  support, lower near-side foot lift, and a small pelvis dip/torso roll. These are
  authored visual features, not an anatomical diagnosis or validated injury model.

`gait_track` schedules world-space touchdown/liftoff anchors and eases each swing
between them. Changing step parameters does not move a planted foot. Fully
established steps have support fractions 0.40/0.75 and alternating forward step
lengths approximately 0.185/0.515 m at the common 0.70 m cycle distance. Both feet
retain ground support across the cycle; leg IK targets remain reachable.

Inspected a 6–9 s, 640x360 preview before the final renders. Added `-PreviewStart`
to select that actual motion window; preview frames use a local zero-based clock,
with the source start offset and shifted match clock recorded in their manifest.
Inspected representative final frames and generated an enlarged, cropped,
side-by-side 5–10 s GIF for human review only. Runtime images keep the original
fixed full-frame camera and contain no gait labels or risk overlays.

Final measured generation:

| Clip | PNG frames | Mean render/frame | Total |
| --- | --- | --- | --- |
| S004 | 240 | 0.173 s | 44.3 s |
| S006 | 240 | 0.175 s | 44.8 s |

Seven unit checks passed, including equal paths/speeds, identical first three
seconds, world-planted stance feet, continuous reachability, unequal late step
lengths and support durations, and neutral runtime manifests. Output verification
passed for all six delivered clips. Separately decoded the first/middle/final
MP4 frames for both new clips; all six decoded successfully. Generation reports
record the exact script hashes and configs used for this pair.

Original S001–S003/R001 assets were preserved; their older generation reports
retain the source hashes from their original render. No new VLM calls were made
in this extension. Human review/annotations for S004/S006 remain pending, and
the live demo's history/scenario mappings were not changed. Local media are still
ignored by Git; use `preview.html` to play the full clips.
