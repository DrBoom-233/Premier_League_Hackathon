# PitchGuard demo: teammate setup and deployment

This guide deploys the current demo from **main**. Start with the local route. Azure
deployment is optional and creates billable resources. No model training is needed.

## Branches

- `main`: FastAPI/React application, Foundry Agent workflow, frozen v2 history snapshot,
  and the four-case paired probability simulation.
- `codex/teammate-model`: the teammate's original seven commits through `de2c530`,
  including `train_model.py`, generator 3.0 and its changed CSVs. These files remain
  available there; that experimental predictor is not wired into the main application.

The main history was reorganized on 2026-10-24 at the repository owner's request.
An existing clone based on the old main should not blindly merge it back. Save any
local work first. For deployment, the simplest route is a fresh clone of main:

```powershell
git clone --branch main https://github.com/DrBoom-233/Premier_League_Hackathon.git
cd Premier_League_Hackathon
```

The repository is private; the teammate needs GitHub access. To inspect the training
experiment separately, fetch and check out `codex/teammate-model` in a separate clone.

## 1. Requirements

- Python 3.12+ and Node.js 22.12+ / npm.
- Windows PowerShell for the provided scripts.
- Rendered runtime media, obtained as described below.
- For new Agent analyses: access to an existing compatible Azure OpenAI/Foundry image
  deployment. The configured implementation uses GPT-4.1 mini.
- For the paired simulation alone: no Azure credentials, GPU service or paid model
  calls are required once the media is available.

## 2. Install and configure

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd --prefix src/frontend ci

# Do not overwrite an existing configured .env.
if (!(Test-Path -LiteralPath '.env')) { Copy-Item .env.example .env }
```

For paid Agent analysis, edit `.env` locally:

```dotenv
AZURE_OPENAI_ENDPOINT=https://YOUR-RESOURCE.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=YOUR-DEPLOYMENT-NAME
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_API_KEY=YOUR-KEY
PITCHGUARD_LOCAL_ONLY=true
```

Use a resource-root endpoint, not a full API route. Leave credentials blank if only
demonstrating the paired simulator. Never commit `.env`, `.gh-config`, `.state`, or
Azure keys. Existing call/token caps apply; unknown unit prices are not reported as $0.

## 3. Obtain media without unnecessary rendering

The generated `data/animation/runtime/` directory is intentionally not in Git. A clean
clone therefore needs this step before the full demo or Docker image will work.

**Lowest additional compute cost:** copy the pre-rendered `data/animation/runtime/`
directory from a teammate's working checkout. Keep its structure: S001, S002, S003 and
R001 each have `video.mp4`, `input_manifest.json` and `frames/*.png`. Videos total about
1.42 MiB, while the 792 full-resolution PNG frames total about 583 MiB. Keep those
generated files outside normal Git commits. The full Agent workflow needs the frames;
copying MP4s alone is not sufficient for it.

If no pre-rendered bundle is available, rebuild locally with the pinned Blender helper:

```powershell
.\.venv\Scripts\python.exe scripts/animation/setup_blender.py
.\scripts\animation\render.ps1 -Scenario all
```

The helper downloads a roughly 399 MB portable Blender archive once. Rendering needs
a compatible local graphics device/driver; it does not create Azure resources or call
a model. See [animation instructions](../data/animation/README.md) for using an
existing Blender installation. Do not rerender an existing directory just for setup.

Refresh the paired demo artifacts against the exact received/rebuilt MP4 bytes:

```powershell
.\.venv\Scripts\python.exe scripts/prepare_data.py
.\.venv\Scripts\python.exe scripts/prepare_multimodal_demo.py
$env:BLENDER_USER_RESOURCES = Join-Path (Get-Location) '.tools\blender-user'
& '.\.tools\blender-4.5.9-windows-x64\blender.exe' -b -t 4 --python-exit-code 1 --python scripts/animation/measure_demo_video.py
```

If you copied media but do not have portable Blender yet, run the setup helper before
the measurement command, or use the path to an installed compatible Blender. Measuring
only decodes 18 small images; it does not rerender the animation or call Foundry.

## 4. Build, start and demonstrate

```powershell
npm.cmd --prefix src/frontend run build
.\scripts\run_demo.ps1
```

Open [the local application](http://127.0.0.1:8000).

- **No-paid-call path:** Analyst → **Paired probability demo**, or
  [open it directly](http://127.0.0.1:8000/?view=paired). Switch between steady/slowing
  cases with the same history to show the video's numerical contribution.
- **Real Foundry path:** Replay analysis → choose replay → **Analyze replay**. This
  can incur model charges unless cached. Inspect history, image citations and the fan
  view. Model observations still need human review.

The paired percentages follow a deliberately specified stochastic simulator. They
are not trained/calibrated real-player injury predictions, and the independent Agent
workflow does not generate them. See [the event law and limits](../data/demo/README.md).

If port 8000 is in use, run `.\scripts\run_demo.ps1 -Port 8001` and use that port.

## 5. Offline verification

Run after the media and paired artifacts are ready:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m unittest discover -s scripts/animation -v
npm.cmd --prefix src/frontend run build
```

These checks do not call a model. The recorded local baseline has 20 backend checks,
six animation checks and passing frontend/browser checks. A stored-case browser
regression also needs the local, uncommitted case database; a fresh clone should not
expect the original author's saved cases to be present.

## 6. Optional local Docker container

Requires a working Docker engine and populated runtime media from step 3:

```powershell
docker build -t pitchguard-demo .
docker run --rm --name pitchguard-demo -p 127.0.0.1:8000:8000 --env-file .env -e PITCHGUARD_LOCAL_ONLY=true pitchguard-demo
```

This example binds only to the local machine. It is a disposable container: its local
analysis state is removed with the container. Use the normal local checkout for
persistent local state, or the Blob-backed Azure route for the prepared hosted design.
The Docker recipe exists, but local image build has not been verified in the original
development environment. It is not evidence that cloud deployment has passed.

## 7. Optional Azure deployment

Use this only if an external hosted demo is required. Requirements include Azure CLI
login, the intended subscription, resource-deployment rights and permission to create
RBAC assignments/custom roles. The existing Foundry deployment/key must be accessible.
Do not expose `PITCHGUARD_LOCAL_ONLY=true` to a public network.

```powershell
az login
az account set --subscription YOUR-SUBSCRIPTION-ID

# The deployment script expects an existing resource group.
az group create --name rg-pitchguard-v2 --location francecentral

# Print the resource plan without deploying:
.\scripts\deploy.ps1

# Only after reviewing the plan and intended subscription:
.\scripts\deploy.ps1 -SubscriptionId YOUR-SUBSCRIPTION-ID -ResourceGroup rg-pitchguard-v2 -Location francecentral -Apply
```

The script creates registry/storage/telemetry and Container Apps web/CPU Job resources,
using the existing Foundry model. Azure ACR performs the image build; no local Docker
daemon is required for that build path. Registry, storage, logs and model usage may
cost money even when the app scales to zero. No extra GPU/model training service is
needed. The script saves the hosted analyst token in `.state/analyst-token.txt`; share
it privately with the tester, never in the repository or a public URL.

On the printed HTTPS URL, verify health, media, token-gated analyst access, fan
filtering, API→Job execution, persistence, cold start and failure recovery. Cloud
deployment and these checks remain unverified. The hosted demo currently requires
operator reconciliation for lost/crashed jobs; see [RUNBOOK.md](RUNBOOK.md).

## Troubleshooting

| Symptom | Action |
|---|---|
| Blank replay / runtime assets unavailable | Obtain/rebuild the full runtime media, not only CSVs. |
| Paired demo returns 503 | Check MP4 presence and rerun the two demo preparation/measurement commands. Source hashes must match. |
| Model configuration missing / 401 / 403 | Check resource-root endpoint, deployment, key and resource access; do not replace an error with a fabricated result. |
| Hosted analyst access denied | Enter the generated analyst token; do not enable local-only mode publicly. |
| Docker COPY fails for runtime media | Complete media setup before building; Git does not include rendered assets. |
| Trying to train XGBoost on main | Use the separate experimental branch; training is not part of main deployment. |
