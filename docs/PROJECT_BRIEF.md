# PitchGuard AI — project brief

Current implementation: [status](IMPLEMENTATION_STATUS.md), [startup and operation](RUNBOOK.md).

## One-line idea

Evidence-grounded intelligence from synthetic football replays, with different analyst and fan explanations.

## Problem and target users

- Problem: keep visible evidence, historical context and uncertainty together without inventing a health conclusion.
- Primary user: a match analyst reviewing a short player-focused replay; a fan is the secondary audience.
- Need: inspect which frame or dated record supports an observation, and know what remains hidden or unverified.

## Experience

- Select replay → compare reference → analyze → inspect citations → acknowledge viewing.
- Example: a ten-second synthetic window at 68:00 for P001, with a separate 67:00 reference.
- Each observation includes evidence IDs and limitations. A recheck is bounded and is not independent verification.
- Analyst receives internal synthetic history; fan receives accepted visual facts only.

## Event data

- Frozen CSV provenance: `data/source_manifest.json`; pre-rendered Blender media has neutral input manifests.
- Neutral replay start/end events and timestamped frame IDs; no pre-scripted AI findings.
- Sampled-frame replay analysis, not full-match live tracking. Actual call latencies are recorded; no latency guarantee.

## MVP scope

- Real image calls, cutoff-safe history, investigator/recheck trace, source seeking and audience filtering.
- No training, pose service, GPU host, diagnosis, calibrated injury probabilities or full-match real-time analysis.

## Technical approach

- Azure GPT-4.1 mini and Microsoft Agent Framework custom executors; one model deployment shared by roles.
- FastAPI + React, local SQLite/cache, optional Blob-backed state and finite Container Apps Job.
- Architecture diagram: [architecture](ARCHITECTURE.md).

## Demo plan

- Local: [README](../README.md). External test URL remains pending.
- Video: show replay, real analysis, cited evidence, audience change and honest visibility limits; final recording pending.
- Submission owner: TBD.

## Team

| Member | GitHub username | Focus |
|---|---|---|
| [TBD] | [TBD] | [TBD] |

## Open questions

- [ ] Complete human visual/claim review and independent held-out evaluation.
- [ ] Verify Azure deployment, cold starts, managed identities and cost limits.
- [ ] Confirm team membership, registration, submission owner, public repo and video.
