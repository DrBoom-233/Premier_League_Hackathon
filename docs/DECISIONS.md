# Decision log

Record decisions that affect product scope, data, architecture, or submission. Newest decisions go at the top.

| Date | Decision | Reason | Owner |
|---|---|---|---|
| 2026-10-24 | Keep the current working demo and frozen v2 snapshot on main; preserve the teammate's seven original commits through de2c530 on codex/teammate-model. | User explicitly requested separating the experimental model/data branch from current demo development. | User |
| 2026-10-23 | Implement the reviewed local MVP with the existing Foundry GPT-4.1 mini deployment and pre-rendered media. | User authorized implementation after real text/image connection tests. | User / implementation |
| 2026-10-23 | Keep null injury probability, cutoff-safe history and per-claim evidence; fan requests exclude internal history. | Synthetic observations are not a calibrated health predictor. | Implementation plan |
| 2026-10-23 | Agent Framework custom executors with a tool-driven, single-window recheck and one model deployment. | Real handoffs with bounded calls/images and preserved failures. | Implementation plan |
| 2026-10-23 | Local SQLite; optional Blob-leased snapshot and finite CPU Job. Media remains immutable in the image for now. | Cloud validation and separately versioned Blob media remain pending. | Implementation choice |
| 2026-10-21 | Repository initialized for shared hackathon planning and implementation. | Keep code, project docs, and submission prep together. | Team |
