> Public source snapshot: this document describes the original isolated release layout. The adjacent private fallback, CLI sessions, foundation outputs, and access files are not included in Git. `scripts/deploy.ps1 -Apply` is an updater for that prepared layout, not a fresh-subscription bootstrap.

# Isolated Azure demo release — 2026-10-26

The original checkout and its existing `.env`, Python environment, media and SQLite
database are preserved. All hosting changes live in this `azure-candidate` directory.
The adjacent `local-fallback` contains the exact pre-deployment source, built frontend,
media, a consistent database backup and a copied Python environment.

## Local fallback

From `../local-fallback` run `./scripts/run_demo.ps1 -Port 8011`, then open
http://127.0.0.1:8011. This path does not depend on Azure hosting resources. Fresh
Agent analyses still require the existing Foundry service; video playback and the
paired simulator do not. The original project also retains its normal local launcher.

The release directory is private: it contains `.env`, CLI authentication and generated
access codes. Do not upload the entire release directory or fallback folder.

## Cloud scope

- Subscription: the verified Azure for Students subscription.
- Resource group: `rg-pitchguard-demo-20261026`, France Central.
- Existing model: `foundry-pitchguard-v3` / `gpt-4.1-mini` in `rg-pitchguard-v2`.
  No changes to that model or resource group are part of this release.
- Registry: Basic ACR; images built by local Docker, without ACR Tasks.
- Web: React and FastAPI in one container, HTTPS, 0.5 vCPU / 1 GiB, one replica.
- Worker: finite manual Container Apps Job, 300 seconds, no automatic retry.
- State: private Blob-backed SQLite snapshot, a Blob lease and a local thread lock.
- Environment: explicitly `WorkloadProfiles` with only the `Consumption` profile.
  Express environments cannot run Jobs. The initial Express attempt failed before
  a web app or analysis Job was deployed. Its unused environment was removed after
  verifying that both the app and Job use the standard environment.

## Public experience

The public homepage loads a saved real S006 analysis. Five selected real synthetic
cases are exported in `data/demo/runtime/featured_cases.json`. Exports omit private
diagnostics and verify every cited frame against the included media bytes. Saved
machine output retains its pending-human-review disclosure. It is not a validated
clinical assessment. Analyst and fan views retain their separate projections.

Video playback, selected analyses, citations and the paired simulator need no code.
The page includes exactly: “Please contact email: cys620999@gmail.com if you need test code”.
The address links to `mailto:cys620999@gmail.com`.

## Judge access and limits

Private codes are in `.state/access-secrets.json`; they are not committed, baked into
the image, placed in URLs, or printed by deployment scripts. Three judge codes each
allow at most ten analyses, plus a separate one-use deployment test code. The server
stores configured code hashes. Removing a hash from the runtime configuration revokes
that code. Keep this JSON file across updates to preserve the codes.

A new case reserves a slot. The first uncached model request consumes it; further
Agent calls in that case do not. Saved results, request-ID replays, cached case reads,
all-cached workflows and failures before model invocation consume no allowance.
An attempted model call still counts if it fails. Concurrent reservations and use
are transactional and persist across restarts. Inputs and cases are shared synthetic
demo material, not private per-judge workspaces.

Whole-site budgets still apply: one active hosted analysis, 16 new cases/day,
60 model calls/day, 300,000 tokens/day, six calls/case. Daily reset is UTC. A code's
allowance is an upper bound, not a reservation of global model quota. A lost hosted
case expires after 15 minutes without automatically retrying paid work.

## Updates and rollback

`scripts/deploy.ps1` without `-Apply` prints the plan. With the explicit verified
subscription ID and `-Apply`, it checks the group's isolation tag, builds and pushes
a new image, preserves access codes, checks the ARM preview scope and updates the
web/Job. It never deletes resources or upgrades a subscription. CLI and Docker auth
are stored in adjacent isolated directories. Temporary ARM model-key parameters are
removed after the runtime deployment attempt.

Keep immutable image tags. The image with the corrected Job-start contract is
`demo-20261026205355`; its manifest digest is recorded in the release status.
Do not roll back to `20261026-v1`, which can display saved cases but has a Job-start bug.
For a cloud rollback, redeploy the verified corrected image
to both web and Job, retaining Blob state and code configuration. A cloud failure
does not require any source rollback in the original checkout: use the local launcher.

## Verification

Baseline: 22 backend checks and 7 animation checks passed in the copied fallback;
desktop/mobile presentation browser checks made no analysis POST.

Candidate: 29 backend checks, production frontend build, Bicep compilation, scoped
Azure what-if, local Docker build, credential/state exclusion check, and hosted-mode
desktop/mobile browser acceptance passed. Two new saved S006/S004 workflows completed
with three new model calls each. Public cloud and Job acceptance is recorded in the
[deployment overview](DEPLOYMENT.md).

Charges are separate for web/Job compute, Basic registry, Blob, logs, egress and
Foundry. One small replica and log caps bound configuration; budget alerts alone are
not a spending stop. Do not remove the model resource group when retiring hosting.
