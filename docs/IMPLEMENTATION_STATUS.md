# PitchGuard implementation status — 2026-10-23

Demo-scope update, 2026-10-24: a separate Analyst **Paired probability demo** now
combines two 28-day synthetic history profiles and actual pixel measurements from
S001/S002/R001 into four scripted what-if worlds. Displayed percentages are exact
conditional probabilities of a stipulated Bernoulli simulator, not a trained or
calibrated injury predictor. No new paid calls or 3D renders. Five additional backend
tests pass (20 total), as do the six animation tests, frontend build and both browser
regressions. Clinical fields remain null; original Agent analysis remains qualitative.
See [minimal paired demo](../data/demo/README.md) for the event law, rebuild steps,
video reuse, offline outcome separation and limits. Bulk data/video expansion is deferred.

UI clarification, 2026-10-24: analyst mode now independently displays the Historical
Agent assessment, completion/cache/error state, history cutoff, accepted historical
source count, source citations, all computed metrics and prior events. It no longer
relies on the final brief to expose specialist history. Fan mode still excludes these
fields; empty states explain that an analysis must be loaded. No new model call was
needed to display the existing saved historical assessment.

Local first version implemented following user authorization. This is a delivery/status
record, not a claim that every work package or quality target is complete.

| Work package | Implemented | Remaining |
|---|---|---|
| W0 | Immutable raw CSVs; dated mapping; whitelist/cutoff adapter; non-overlapping load windows, actual appearances, quality flags and provenance; processed P001 summary | Source distance/return-date semantics remain unresolved and excluded |
| W1 | Real text/image connections, three real multi-role scenario runs; request budget 7+3 / recheck 8+2; strict JSON Schema; usage/latency/failure records | Model movement/occlusion judgments are imperfect; human acceptance pending |
| W2 | Pydantic contracts, per-claim citations, player/time/path/version checks, scoped historical and frame tools, publication/audience filters | Automated checks do not establish claim truth |
| W3 | Agent Framework custom executors, concurrent specialists, investigator function tool, one recheck, publication and bounded failures | Latest prompts do not reliably request a recheck; Foundry external-agent trace export unverified |
| W4 | FastAPI/React replay, reference video, case polling, source seeking, audience switch, real call/caching display and acknowledgement | External judge access and final product acceptance pending |
| W5 | Offline leakage/contract/failure tests; durable real-case logs including failures; experimental single analyst path with bounded recheck | Full reviewed/fair baseline set, independent clips, price rates and accuracy scoring pending |
| W6 | Docker recipe, Bicep, deploy plan/apply script, Blob state adapter, finite Job entrypoint and optional telemetry | No cloud deployment or container build; Azure CLI/RBAC/capacity and crash-reconciliation checks required |

## Verification

15 backend checks and six original animation checks pass. Tests cover future-poisoned
CSV input, ongoing-injury outcomes, missing/zero-denominator windows, forged citations,
wrong identity, paths, image/recheck limits, timeout, malformed JSON, missing branches,
durable deduplication, budget reservation and Blob snapshot/lease rollback via a fake.
Fake model outputs are isolated to tests and are never used by the application.

React production build passes and npm reports zero known vulnerabilities for the
installed dependency tree. Both Bicep templates compile. Browser checks cover desktop,
mobile, actual stored model output, source seeking and fan filtering; see local QA
screenshots under `.tools` and development-run audit under `evaluation/`.

## Real inference limitations

All three multi-role scenarios have reached completed execution with real Foundry
inference. An earlier structured run contains an actual investigator tool call and
completed visual recheck (case `fbc66f9dc4034e4a869b6fe117033006`). Initial JSON-only runs failed schema validation and
are retained. Schema-level output constraints subsequently stabilized the structure.

Execution completion is not visual success. Different prompt revisions missed the
S002 slowdown or the S003 occluder and sometimes invented changes in facing direction.
The latest development outputs still require human review. No held-out motion accuracy
or injury-prediction metric is reported. The three related clips were used for prompt
iteration and cannot be claimed as independent held-out data.

The single-analyst S002 integration run failed because its requested recheck interval
exceeded the allowed window. The system rejected it instead of silently expanding the
budget. A valid complete baseline comparison remains outstanding.

Cached history is reused across scenarios; reported case elapsed times include this
reuse. They are not all-cold end-to-end timing. Usage and cache hits are recorded per
call. USD rates are unconfigured, so monetary cost is unknown; no $0 claim is made.

## Deliberate implementation choices

- Investigator rationale directly forms the analyst brief. One separate fan narration
  receives only public accepted visual facts, keeping the six-call worst-case budget.
- Four roles use local framework executors and one deployed model; no Foundry-hosted
  Agent creation permission is required for this local route.
- Local state is SQLite. Hosted mode serializes a small SQLite snapshot in Blob under
  leases and dispatches a finite Job; this is for low-volume demonstrations.
- Hosted media currently ships in the image rather than being independently fetched
  from Blob. Crash/lost-dispatch reconciliation is manual and must be verified before
  opening any public paid-analysis route.
- No new cloud resources, public deployment, commit, push, repo-visibility change,
  team messages or submission were performed during this implementation.

## Next acceptance steps

1. Review complete videos and actual claims, especially the missed slowdown/occlusion.
   Freeze acceptance labels independently. Improve image framing or model choice only
   against a stated quality/cost target; do not substitute production labels as inference.
2. Run a reviewed comparison on independent action instances with identical input and
   budget access. Record failed, extra-call and no-benefit results.
3. Authenticate Azure CLI under the authorized account, confirm resource/RBAC rights,
   then validate/apply the prepared infrastructure and perform external restart/cold-start checks.
4. Complete English submission narrative, public test link/repository, team ownership
   and <120-second video. The core demo currently runs locally.
