# PitchGuard deployment and setup

[Live Azure demo](https://pgdemo-web.purpleground-33ee8913.francecentral.azurecontainerapps.io/) · [Demo video](https://www.youtube.com/watch?v=ezsUFydyIyI) · [Judge testing instructions](JUDGE_TESTING.md)

## Deployed release

The application was deployed on October 26, 2026, in France Central, in the isolated resource group `rg-pitchguard-demo-20261026`. The release uses a versioned image in Azure Container Registry, a Container App for React/FastAPI, a finite Container Apps Job for new Agent analyses, private Blob-backed state, Application Insights, and Log Analytics. One GPT-4.1 mini deployment in Azure OpenAI / Foundry serves the four Agent roles.

Public visitors can play videos, inspect five saved real analyses and citations, switch Analyst/Fan views, and use the six-case paired simulator. New analyses require a private code. See [access and operational limits](AZURE_ISOLATED_RELEASE.md).

Verification recorded 29 backend checks, seven animation checks, a production frontend build, Bicep compilation, local Docker packaging, and desktop/mobile browser checks. An end-to-end cloud analysis completed; a duplicate request returned the existing case without a second allowance charge. The completed case and quota persisted after a web revision restart. Stress testing and independent medical or visual validation remain separate work.

## Fresh local checkout

Requires Python 3.12+, Node.js 22.12+, and the rendered runtime assets.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd --prefix src/frontend ci
# Do not overwrite a configured .env.
if (!(Test-Path -LiteralPath '.env')) { Copy-Item .env.example .env }
```

For new Agent runs, configure `.env` with a resource-root Azure OpenAI endpoint, compatible image-capable deployment, API version and key. Never put credentials in the frontend, commit them, or distribute them with screenshots. The separate paired simulator needs no model credential once its media is available.

Generated videos and frame sequences are Git-ignored. Copy the team's pre-rendered `data/animation/runtime/` bundle, including S001/S002/S003/S004/S006/R001 manifests and frames, or rebuild using the [animation guide](../data/animation/README.md). MP4 files alone are insufficient for Agent frame analysis.

If the video bytes differ from the distributed measured artifacts, refresh the [paired simulator measurements](../data/demo/README.md), including `measure_gait_video.py`. Saved featured cases are tied to frame hashes: changed frames require a new explicit reviewed export, not relabeling an old case.

```powershell
npm.cmd --prefix src/frontend run build
.\scripts\run_demo.ps1
```

Open `http://127.0.0.1:8000`. Keep local-only mode bound to loopback. Public hosting requires server-side access checks.

## Offline verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m unittest discover -s scripts/animation -v
npm.cmd --prefix src/frontend run build
```

These commands do not request paid model inference. Media-dependent checks require the runtime bundle. The historical model experiment on `codex/teammate-model` is separate and not needed for application deployment.

## Container and Azure operations

With Docker running and runtime media present:

```powershell
docker build -t pitchguard-demo .
docker run --rm -p 127.0.0.1:8000:8000 --env-file .env -e PITCHGUARD_LOCAL_ONLY=true pitchguard-demo
```

The deployed release used local Docker build/push, not ACR Tasks. The checked-in `scripts/deploy.ps1` is the isolated release updater: its `-Apply` route requires the original prepared private sibling layout (CLI, Docker auth, foundation outputs, fallback Python environment and access state). Those files are deliberately excluded from Git. It is not a generic fresh-subscription bootstrap. Without `-Apply`, it prints the plan only.

The Bicep templates document the infrastructure. A new deployment needs the intended subscription, resource group, supported region and service capacity, scoped identities/RBAC, model access, immutable media and image, and private runtime parameters. Do not copy the original private release directory into a public checkout. Confirm the Azure preview scope before applying any changes. This README update does not redeploy the running service.

The web app keeps one small replica; a Job stops after finite execution. Compute, registry, Blob, logs, network and Foundry usage may incur charges. Defaults limit daily cases/calls/tokens and hosted concurrency. Access-code allowance is not reserved global capacity. Lost jobs need operator reconciliation; automatic paid retries and unlimited judge access are not claimed.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Missing video or frames | Obtain the full runtime media bundle or rebuild it. |
| Paired simulator rejects stale media | Remeasure against the exact MP4 bytes. |
| No saved featured case | Verify exported case/frame hashes; do not fabricate a result. |
| Azure inference fails | Check resource endpoint, deployment, server credentials and remaining budgets. |
| New analysis is disabled | Supply the privately issued code and unlock analysis. Public browsing remains available. |
| Hosted task stays queued or fails | Inspect the Job execution and durable case; no automatic paid replay is performed. |

Do not publish `.env`, `.state`, CLI sessions, generated access codes, or private release backups.
