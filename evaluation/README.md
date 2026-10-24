# Development integration audit

`development_runs.json` records all 14 initial development cases, including nine
completed executions, four degraded executions and one failed single-analyst case.
These counts describe software execution, not visual correctness or predictive accuracy.
The cases use three related development clips and multiple prompt/code revisions.
They are not 14 independent action instances or a held-out benchmark.

Each record includes the immutable input revision, actual case ID, branch errors,
call usage, image counts, cache status and latency. The source records remain in the
local state database. Original JSON-only schema failures and the failed recheck/baseline
are retained. Some history calls are cached; do not sum cached source usage as new paid
tokens or describe these case latencies as entirely cold inference.

The latest outputs still miss movement/occlusion details. Human labels and acceptance
are pending. A valid JSON schema and valid evidence IDs do not establish the statement
is true. No medical or injury-prediction accuracy result is reported.

Case `fbc66f9dc4034e4a869b6fe117033006` contains a real completed targeted visual
recheck. The single-analyst S002 run requested an invalid interval and was rejected;
a complete fair baseline comparison is still outstanding. Dollar cost remains unknown
because verified billing rates have not been configured.

Offline failure-injection outputs exist only in `tests/`; they are not included as
real inference in this audit and are never served as application fallback answers.
