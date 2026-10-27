# PitchGuard judge testing instructions

[Live Azure demo](https://pgdemo-web.purpleground-33ee8913.francecentral.azurecontainerapps.io/) · [Demo video (1:46)](https://www.youtube.com/watch?v=ezsUFydyIyI)

## Public walkthrough

1. Open the live demo. No account or analysis code is needed to browse.
2. In **Movement evidence**, the default S006 case loads a previously generated analysis. Use **Play both from 5s**, then **Pause both**, to inspect the matched S006/S004 animations.
3. Select S004 to load its saved case. Read **History Analyst** and select a date citation to inspect a historical record.
4. In **Evidence Desk**, select a frame citation to open the source image and seek to its timestamp. Saved analyses are real prior Azure calls, not new inference on each visit. Machine claims retain their pending-human-review status.
5. Open **Paired probability demo**. Select S006, then S004: history remains the same, while the displayed joint simulator probability changes from 4.1% to 14.4%. **Inspect video measurements** shows the pixel-derived input. This is a separate synthetic simulator, not a clinically validated predictor or an Agent-generated percentage.
6. Switch to **Fan view** to see public visual facts without internal wellness history.

## Optional new Agent analysis

Use the analysis code supplied privately with the submission. Enter it in **Analysis code**, select **Unlock analysis**, choose a replay, and select **Analyze replay**. Do not put the code in the URL or public repository. If no code was supplied, contact [Charlie](mailto:cys620999@gmail.com).

Each code currently permits up to ten new analyses, subject to whole-site daily budgets and one active hosted workflow. Existing or cached results do not consume the allowance. An attempted model call can consume one use even if the workflow later fails. These limits remain an outstanding review-access consideration under official rule 4.8; unlimited judge testing is not claimed here. Do not wait until judging to arrange any additional access needed.

The selected replay is compared with R001, not automatically with the adjacent human comparison video. The system examines sampled frames, not a continuous live match feed. Playback, sources, and the paired simulator remain available without starting a paid inference request.

## What the demonstration establishes

The demo shows historical context, real Azure multi-agent inference, source navigation, audience filtering, and a separate probability simulation. It does not establish reliable gait-abnormality recognition, clinical accuracy, calibration on real player outcomes, or superiority over a single-agent baseline.
