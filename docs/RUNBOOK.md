> Latest release update, 2026-10-27: the Azure demo was deployed on October 26. See [deployment overview](DEPLOYMENT.md) for the hosted version. Older statements below about pending cloud deployment are historical.

# PitchGuard runbook

## Local

Use Python 3.12+, `requirements.txt`, Node and the frontend package lock. The backend
loads `.env`. Set a resource-root Azure endpoint, not the full Responses route.
Start with `scripts/run_demo.ps1`: it binds to loopback and uses one worker. Vite
development mode proxies `/api` to port 8000; production React assets are served by FastAPI.

SQLite in `.state` persists cases, request mappings, cache, usage reservations and
acknowledgements. Do not publish it: it contains internal synthetic history. Restarted
unfinished local cases become failed, without automatic paid replay. Run only one local
backend/evaluation worker against that file at a time.

Defaults: concurrency 1; 16 new cases, 60 new model calls and 300,000 reserved/actual
tokens per UTC day; six invocations/case; ten images/request; 900 output tokens/call;
60s network timeout; 180s workflow deadline. Failed calls retain reservations when
actual usage is unknown. Budget-blocked calls are not sent; caches are distinct from
new paid inference. Optional verified USD-per-million-token rates populate estimates.
Storage, registry, logging and compute charges are separate. Alerts do not stop spend.

## Quality and access

Shape/citation checks do not prove visual correctness. Human-check every claim,
especially anatomy, movement changes and occlusion boundaries. Acknowledgement records
viewing, not correctness. Model judgments remain unvalidated. Partial/obscured views
retain an insufficient-evidence concern. Injury probability remains null.

Fan narration receives accepted visual facts only. Fan API reads omit historical
outputs, wellness, investigator rationale and case concern. Hosted writes/analyst
reads require `X-Analyst-Token`. This shared-token demo is not enterprise authorization.
Never expose local-only mode to the public network.

## Azure prerequisites still outstanding

No authenticated Azure CLI deployment session is configured on this machine. Local
development does not create additional paid Azure resources.

The authorized teammate identity needs resource deployment and RBAC/custom-role rights
on the intended subscription/RG. Contributor alone does not grant role assignments.
Check registration of Microsoft.App, Microsoft.Storage, Microsoft.ContainerRegistry,
Microsoft.OperationalInsights, Microsoft.Insights and Microsoft.ManagedIdentity.

France Central succeeded for Foundry. Allowed subscription regions are francecentral,
canadacentral, denmarkeast, belgiumcentral and norwayeast; service capacity/quotas still
require verification. Install Azure CLI, `az login`, select the intended subscription,
then review the resource plan before applying:

```powershell
.\scripts\deploy.ps1
.\scripts\deploy.ps1 -SubscriptionId YOUR-SUBSCRIPTION-ID -ResourceGroup rg-pitchguard-v2 -Location francecentral -Apply
```

The apply script creates ACR Basic, private Blob state, Log Analytics (0.1GB/day cap),
Application Insights, Consumption environment, web app (0–1 replicas) and a manual CPU
Job (parallelism 1, no retries, timeout 300s). ACR/logs can add charges; verify actual
subscription rates. It neither creates another Foundry account nor deletes the RG.
ACR builds the image; no local Docker daemon is required for that path.

Separate API/worker managed identities receive Blob Data Contributor on the container
and AcrPull on the registry. The API receives read/start rights on the specific Job,
without a listSecrets wildcard. Job-start permission is still trusted because execution
overrides can use Job secrets/identity. The model key is a secure parameter stored as
a Container Apps secret. Temporary parameter JSON is deleted; the generated analyst
token is saved to Git-ignored `.state/analyst-token.txt` and is not printed.

## Hosted lifecycle

`PITCHGUARD_STORAGE_ACCOUNT_URL` selects the Blob adapter. A small SQLite snapshot is
serialized under a 60s Blob lease and uploaded atomically. This is a low-volume demo
store, not a scalable database. A separate renewed inference lease and persisted case
check prevent concurrent/duplicate Job model work. The API persists the case before
calling Job Start; hosted analysis does not depend on the API process surviving.

Immutable runtime media currently ships in the image; moving independently versioned
media to Blob remains a refinement. Labels/configs/generator code are excluded from
the runtime image. Do not reuse image tags for changed assets.

Dispatch failures become durable failed cases. Job crashes, lost starts and stale
queued/running cases require operator reconciliation with Job execution history;
automatic crash recovery/retry is not implemented. Resolve or operationally check
this before exposing a public paid-analysis button. Hosted API restarts do not mark
a live Job failed.

Application Insights exports HTTP telemetry and role spans without prompt/image/key
contents. Local structured case traces work without it. Foundry external-agent trace
registration/export is a separate unverified integration.

## Release checks

Bicep compilation is necessary but not a live deployment test. Verify Azure what-if,
identity image pulls, API→Job dispatch, Blob contention, persistence across restarts,
cold starts, fan privacy, limits and excluded secrets in the image. The local Docker
engine was unavailable during implementation; image build and cloud checks remain pending.
Complete human review, held-out comparison, external browser access, team registration,
public repo and the under-two-minute public demo video.

Technical references checked: [Agent Framework executors](https://learn.microsoft.com/en-us/agent-framework/concepts/workflows/executors),
[Azure structured outputs](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs),
[finite Container Apps Jobs](https://learn.microsoft.com/en-us/azure/container-apps/jobs).
