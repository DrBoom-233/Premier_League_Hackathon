# PitchGuard AI: judging and demonstration strategy

Status: revised proposal, 2026-10-22. The MVP uses pretrained VLM inference and programmatic history summaries, with no custom model training. Official rules were checked earlier on this date. No score, model quality, cost or deployment result is claimed.

## Theme and category fit

Section 6.1 has an initial pass/fail screen for theme and relevant technology. Section 4.1 describes synthetic football events flowing through ingestion, interpretation, explanation, rendering and personalization. A standalone injury dashboard risks weak theme fit.

Recommended positioning: **player-focused match intelligence connecting synthetic live movement changes with workload context and explaining their significance for analysts and fans.** Injury-risk estimation is a specialist capability inside that experience.

Primary target: **Best Multi-Agent System**. The category values distinct roles, shared state, effective handoffs, failure recovery and an outcome handled more effectively than by one agent. A graph alone does not prove this: include a fair single-agent comparison. Secondary strength: substantive Foundry use through inference, tracing, evaluation and management. Using named products does not guarantee points. Rules allow up to one Grand Prize and one Category Prize per entrant; check the entry form's category selection.

## Score-to-evidence map

The five criteria in section 6.2 each carry 20%.

| Criterion | Proposed approach | Judge-visible evidence |
|---|---|---|
| Technological Implementation | Coherent synthetic history/events/animation, actual frame-to-VLM inference, typed evidence and Agent Framework | Reproduction instructions, dataset/asset provenance, held-out observation checks, cutoff/failure checks and a real trace |
| Agentic Design & Innovation | Two specialists, evidence investigation, bounded recheck and audience narrative | Occlusion changes the next tool call and published evidence; equivalent single-agent baseline |
| Real-World Impact & Applicability | Useful review evidence and honest uncertainty | Review flow, unavailable/stale states, false-alert burden and real-data validation plan |
| User Experience & Presentation | Synchronized player overlay, analyst/fan toggle and evidence clip | Judge can replay and understand why the moment matters; functioning video under two minutes |
| Adherence to Hackathon Category | Complete football-event pipeline and purposeful multi-agent outcome | Shared state, handoffs, recovery and personalized explanations in one working scenario |

This mapping is our interpretation of the published criteria, not an organizer-provided scoring formula.

## Synthetic animation decision

The user chose synthetic animation. Section 4.7 requires synthetic football-realistic data and all necessary permissions for footage. It does not categorically prohibit outside video, but internet availability alone does not establish permission. Section 4.4 restricts copyrighted material/trademarks in the demo without permission. Avoid unlicensed downloaded broadcast clips. Keep a source/license manifest for rigs, motion, backgrounds, audio and other assets.

Use GPT-authored Blender Python scripts to create a simplified solid humanoid, joint keyframes and a short video with synchronized football events and history for the same fictional player. No external character or motion library is required for MVP. Reuse one tested script and scenario configurations. Include normal, persistent deviation, occlusion and missing-stream variants. Keep generation parameters, renderer ground truth and expected labels separately for evaluation, inaccessible to inference. Disclose precomputed stages and synthetic status. Verify procedural motion readability and frame-to-VLM inference early; success on animation does not establish broadcast or medical validity.

## Demo evidence and 115-second storyboard

The demonstration should show what happened, why it matters, which evidence supports it, why specialist collaboration helps, and how analyst/fan outputs differ. Show qualitative historical concerns and visible movement observations with evidence. Injury probability stays unavailable until a predictor is independently validated.

| Time | Working action | Message |
|---|---|---|
| 0-12 s | Synthetic player-focused replay | Problem and product in one sentence |
| 12-32 s | Movement overlay changes during sustained deviation | Actual timestamped-frame VLM analysis and synchronized events |
| 32-52 s | Historical context, snapshot cutoff and evidence frames | What is observed, inferred and unavailable |
| 52-76 s | Trace plus occluded interval and targeted recheck | Purposeful handoff and evidence rejection/acceptance |
| 76-94 s | Analyst/fan toggle | Different useful experiences from the same verified evidence |
| 94-108 s | Actual evaluation and working replay link | Measured quality, recovery, latency and cost |
| 108-115 s | Project link and value statement | Synthetic prototype scope and next validation step |

Record functioning software, not scripted success for missing features. Foundry trace ingestion can lag: a captured completed real trace can accompany a live application trace view; label the capture where applicable.

## Evaluation packet

Publish versions, test counts, held-out scenario definitions and reproduction commands. Assess visible-observation correctness, frame-reference grounding, wrong-player failures and abstention on insufficient views; measure agent completion, recovery, latency, frame/token count and cost. Compare against human-reviewed annotations. Do not claim injury-prediction accuracy or calibrated probability for this qualitative MVP.

Start with 10-15 held-out end-to-end scenarios: normal play, visible movement change, benign asymmetry, occlusion, wrong identity, missing/stale history, missing video and model timeout. Expand if time permits. Keep annotations/future labels out of runtime prompts and tune prompts on a separate set.

Compare history-only reasoning, motion-only observations and both combined as a qualitative assessment. Reserve calibrated joint prediction for a later validated model. Compare single versus multi-agent using equivalent tools, inputs and budgets. Report added latency and cases with no gain. Test unseen seeds, players and camera configurations.

## Microsoft stack and spending

Use Agent Framework for concurrent specialists and bounded reconciliation; one configurable Foundry model deployment; Foundry/Application Insights tracing/evaluation where supported; compact frontend/backend on Container Apps Consumption; Blob Storage for durable artifacts. Check region/model/SDK compatibility. Workflow/external-agent tracing includes preview surfaces at review time; retain standard OpenTelemetry and an in-app trace view. Scale-to-zero can reduce idle compute but introduces cold starts; measure both warm and cold latency.

Backend controls:

- Compute historical statistics without LLM calls; reuse history snapshots. Analyze selected or periodic short video windows with VLM rather than every frame; no separate CV trigger is needed.
- Short evidence summaries; one recheck; explicit token/tool/retry/deadline budgets; at most eight LLM calls per investigated case including retry/recheck.
- Cache by input revision, player/window, model/prompt version and audience/language; coalesce duplicates.
- Enforce session/concurrency and daily application-spend limits; use factual templates after the limit.
- Limit log retention/sampling and begin with one focused player; no model training or self-hosted GPU is needed for MVP.

Azure Budgets alerts do not stop resource consumption. Application-level model limits do not cap all compute/storage/log charges. Configure those separately and publish measured cost breakdowns after testing, not invented dollar totals.

## Proposed schedule and submission gates

Official deadline: October 27, 2026, 11:59 p.m. Pacific Time, equivalent to October 28, 2:59 a.m. Toronto time. Finish earlier.

| Toronto date | Proposed milestone |
|---|---|
| Oct 22 | Prove animation-frames-to-VLM, define evidence contracts and history summaries |
| Oct 23 | Historical summary agent and synchronized replay |
| Oct 24 | Agent tools, shared state, targeted recheck and fallbacks |
| Oct 25 | Analyst/fan UI, traces and held-out/baseline evaluation |
| Oct 26 | Hosted test link, documentation, real metrics and first recording |
| Oct 27 | Final verification and buffered submission |

If visual observations are unreliable, narrow camera/activity scope and improve frame selection. Keep probability unavailable and expose evidence/uncertainty. Prioritize a repeatable end-to-end outcome.

- Confirm registration, eligibility, team size at most four and team representative; registration and submission deadlines differ.
- Verify public repository visibility at submission; do not assume or change visibility as part of this design task.
- Supply English pitch and testing instructions, or required translations.
- Provide a public video strictly shorter than two minutes and functioning free test access.
- Maintain working judge access through the listed judging end: November 10, 2026, 11:59 p.m. Pacific Time.
- Record asset rights, synthetic assumptions, technologies actually used and reproduction steps.

## Sources

- [Official rules](https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md), sections 1, 3, 4 and 6, checked 2026-10-22.
- [Agent Framework orchestration](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/).
- [Foundry tracing and preview caveats](https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/trace-agent-framework) and [evaluation](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/evaluate-generative-ai-app?pivots=ai-studio).
- [Container Apps overview](https://learn.microsoft.com/en-us/azure/container-apps/overview).
- [Azure Budgets does not stop consumption](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets).
- [Detailed architecture](ARCHITECTURE.md).
