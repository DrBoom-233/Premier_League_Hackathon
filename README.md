# PitchGuard AI — Premier League Hackathon

中文开发记录及伤病概率后续路线（2026-10-24）：[development.md](development.md)。

**Teammates: start with the [deployment and setup guide](docs/DEPLOYMENT.md).**
`main` contains the current demo. The teammate's XGBoost training experiment and v3
datasets are preserved separately on `codex/teammate-model`.

Minimum-cost paired probability demonstration: **Analyst → Paired probability demo**
(`/?view=paired`). Four scripted what-if cases combine two synthetic history profiles
with measured movement from existing videos. Percentages follow a declared stochastic
simulator, not a trained or clinically validated injury model. This separate panel needs
no new paid inference. Rebuild and limitations: [paired demo data](data/demo/README.md).

Evidence-grounded intelligence for synthetic football replays. Compare a player's sampled movement with a reference, inspect cutoff-safe historical context and switch between analyst and fan explanations. This qualitative prototype does not provide a calibrated injury probability. Model claims require human review.

## Run locally

Requires Python 3.12+, Node 22.12+ and the rendered animation assets. In PowerShell from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Only for a NEW checkout: copy .env.example to .env and fill the Azure API key.
# Preserve the existing .env in this configured local checkout.
cd src/frontend
npm ci
npm run build
cd ../..
.\scripts\run_demo.ps1
```

Open **http://127.0.0.1:8000**. Select a replay, analyze it, click evidence to seek the
current/reference video, and switch audience. Reopened case URLs and cached inference
are disclosed. A clean clone must first rebuild the media using the
[animation guide](data/animation/README.md); full videos/PNG sequences are Git-ignored.

Implemented: FastAPI/React, strict evidence contracts, cutoff-safe history adapter,
real Azure image inference, Agent Framework specialist/investigator/publication flow,
one tool-driven recheck, analyst/fan filtering, durable local cases and bounded caching.
The analyst brief reuses investigator rationale. Only public visual facts enter the
fan narration request. One Foundry deployment serves all roles.

Offline checks (no model charge):

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m unittest discover -s scripts/animation -v
.\.venv\Scripts\python.exe scripts/prepare_data.py
```

Real integration runs (billable unless cached):

```powershell
.\.venv\Scripts\python.exe scripts/evaluate.py --run
.\.venv\Scripts\python.exe scripts/evaluate.py --run --mode single --scenario S002
```

All successful, degraded and failed cases remain in `.state/pitchguard.sqlite3`.
Unknown model rates are shown as unknown cost, never zero. `.env`, state and raw
inference outputs are Git-ignored. Defaults bound daily calls/tokens and six invocations
per case. See the [runbook](docs/RUNBOOK.md), [runtime dictionary](data/DATA_DICTIONARY.md)
and [implementation status](docs/IMPLEMENTATION_STATUS.md).

Cloud adapter, Docker and Bicep assets are provided but not deployed. Run
`scripts/deploy.ps1` without `-Apply` to print the resource plan only. Human visual
acceptance, held-out evaluation, cloud checks, external demo URL and submission video
remain explicit release tasks.

## Hackathon at a glance

- Challenge: turn synthetic football events into explainable match intelligence, live narratives, and personalized match experiences.
- Team limit: up to four people.
- Submission deadline: October 27, 2026 at 11:59 p.m. Pacific Time.
- Submission requires an English project description, a working demo or testing link, a public GitHub repository, and a public demo video under two minutes.
- Use synthetic, football-realistic data. Any footage or third-party data must be properly licensed.

See [docs/HACKATHON_BRIEF.md](docs/HACKATHON_BRIEF.md) and the [official rules](https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md).

## Start here

1. Read [CONTRIBUTING.md](CONTRIBUTING.md) for the team workflow.
2. Read the project brief at [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md).
3. Add decisions to [docs/DECISIONS.md](docs/DECISIONS.md).
4. Track work in GitHub Issues and deliver changes through pull requests.

Planning documents: [Agent architecture](docs/ARCHITECTURE.md), [synthetic animation production plan](docs/SYNTHETIC_ANIMATION_PLAN.md), and [scoring/demo strategy](docs/SCORING_STRATEGY.md). Current implemented behavior and remaining gaps are recorded separately in the implementation status.

Latest internal review: [Implementation plan and document review (2026-10-23)](docs/IMPLEMENTATION_PLAN.md), including the current animation/application status, verified CSV snapshot, data issues, build order and submission schedule. Dataset provenance is recorded in [data/source/README.md](data/source/README.md).

## Repository layout

```text
docs/          Hackathon brief, project brief, architecture, decisions, demo and submission notes
src/           FastAPI backend and React replay UI
data/          Synthetic fixtures and schemas; do not commit licensed or private data
```

## Current status

The local application and real model pipeline are implemented. Visual correctness
is not established by schema/citation checks: slowdown and occlusion interpretation
remain imperfect. The three related clips form a development set, not held-out accuracy
evidence. Team roster, submission owner and public hosting are still pending.
