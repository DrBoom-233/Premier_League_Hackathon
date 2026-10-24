# Minimal paired history/video demo

Scope fixed by the user on 2026-10-24: prioritize a working demo and minimum data/video generation cost.

This is **four scripted what-if worlds**, two 28-day history profiles (56 unique daily rows), two existing 10-second current animations and one shared 3-second reference. The same avatar and camera are reused. These are not four independent action instances or four personal longitudinal baselines. Original CSVs and animation assets are unchanged.

## Rebuild

First rebuild the original S001/S002/R001 media if it is missing; see `data/animation/README.md`. Then, from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts/prepare_multimodal_demo.py
$env:BLENDER_USER_RESOURCES = Join-Path (Get-Location) '.tools\blender-user'
& '.\.tools\blender-4.5.9-windows-x64\blender.exe' -b -t 4 --python-exit-code 1 --python scripts/animation/measure_demo_video.py
npm.cmd --prefix src/frontend run build
.\scripts\run_demo.ps1
```

Open `http://127.0.0.1:8000/?view=paired` or select **Paired probability demo** in Analyst mode. Hosted mode requires the existing analyst token. Fan mode does not expose the panel or this private API. No Analyze replay POST is required for this demo.

The Blender measurement script decodes 18 frames from the three existing MP4s at 640×360. It does not perform a new 3D animation render. Its bundled NumPy measures the known blue jersey's centroid. Late-window displacement relative to the reference distinguishes steady and stopping movement. It reads no Blender production configuration, future events or generator label. Only these fixed-camera, single-avatar videos are supported; an unmeasurable or unsupported input does not become a zero-risk observation.

## Defined probability, not an estimated medical rate

For this toy world, the daily conditional Non-contact time-loss event rate is stipulated as:

```text
q = 0.004 + 0.008 * (mean_fatigue_7d - 1) / 4 + 0.016 * motion_state
motion_state = 0 for measured steady movement, 1 for measured stopping movement
P(event within 168h) = 1 - (1 - q)^7
```

The world uses seven independent 24-hour event opportunities, initially uninjured players and no competing event causes. An event lasts seven days. These coefficients are illustrative design parameters with no medical claim. Slowing is not evidence of real injury. This is an exact conditional probability under the specified toy process, not a fitted score renamed as calibrated probability.

The history-only value averages the two motion-conditioned probabilities with a stipulated 50/50 motion prior; it does not pretend missing video is normal motion. The joint value conditions on the actual measured clip. Sleep and workload are context, not extra predictors in this minimal version. Missing visual measurement returns an unavailable joint value.

| World | Fatigue / 5 | Observed replay | History only | Joint simulator probability |
|---|---|---|---|---|
| DEMO01 | 2 | Steady | 9.27% | 4.13% |
| DEMO02 | 2 | Slowing | 9.27% | 14.42% |
| DEMO03 | 4 | Steady | 11.82% | 6.79% |
| DEMO04 | 4 | Slowing | 11.82% | 16.84% |

Runtime clinical fields remain `injury_probability: null` and `probability_status: not_validated`. The original Foundry Agent workflow is still qualitative; it does not produce these percentages. No new Foundry calls, deployment, training or calibration are needed for this separate demonstration.

## Files and separation

- `runtime/episodes.json`: whitelisted case identity, historical summaries and explicit synthetic observation/reference timestamps.
- `runtime/video_features.json`: measured positions, frame times, extractor version and MP4/decoded-frame hashes. MP4 hashes are checked before serving; changed source videos require remeasurement.
- `offline/history.csv`: the two reproducible history profiles, seeded independently of future outcomes.
- `offline/future_events.json`: four seeded future event draws, labels and the generator's true conditional probabilities. All four initial draws happened to have no event; they are retained, not resampled to improve the story.
- `offline/generation.json`: declared event law, source reuse and limits.

The API reads only `runtime/`. Docker copies only `runtime/`, and `.dockerignore` excludes `offline/`. Labels and oracle probabilities never enter runtime prediction inputs, prompts or fan output. Predictions originate at 2026-01-25 16:10:10 UTC; history ends on January 24; the follow-up ends February 1 at the same time. These are newly stipulated what-if times, not recovered original observation times.

## Verification and cost

On 2026-10-24, actual video measurements gave late-speed ratios S001=0.9918, S002=0.0009, reference=1.0. Backend tests check probability arithmetic, future-data isolation, repeated generation, timestamps, stale-media rejection, unavailable/invalid measurements and hosted authorization. Browser checks cover all four cases, matching displayed values, real MP4 metadata, pixel measurements, mobile layout and fan hiding. The original replay browser regression also passes.

This delivery made zero new paid inference calls, created zero cloud resources and rendered zero new 3D frames. There is local CPU work for decoding and data generation. No independent predictive-accuracy, calibration, player-generalization or medical-validation result is claimed. A trained multimodal predictor remains a separate future task if the demo later requires it.
