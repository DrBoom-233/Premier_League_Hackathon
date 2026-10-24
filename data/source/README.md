# Source snapshot

Fetched on 2026-10-23 from the team repository
[`DrBoom-233/Premier_League_Hackathon`](https://github.com/DrBoom-233/Premier_League_Hackathon/tree/6c2d27bf0d64bdbfa0299989bcc64bcad876b058).

The pinned commit is `6c2d27bf0d64bdbfa0299989bcc64bcad876b058`.
The CSV files retain their original repository paths and exact bytes:

- [`../daily_records.csv`](../daily_records.csv): 7,000 rows, 37 columns, 25 fictional players, daily dates from 2025-08-01 to 2026-05-07.
- [`../injury_history.csv`](../injury_history.csv): 30 injury events, 9 columns.
- [`hackathon_injury2.0.py`](hackathon_injury2.0.py): a copy of the generator at the repository root, retained for source inspection. It was not executed during this review.

[`../source_manifest.json`](../source_manifest.json) records paths, byte lengths,
Git blob SHA-1 and SHA-256 checksums. The files were downloaded through the
read-only GitHub blob API using GitHub CLI and checked against the pinned tree.
This did not merge the remote branch into the local working branch. The generator
and CSVs coexist at that commit; exact regeneration has not been verified.

These are synthetic prototype inputs, not observed Premier League monitoring
records or validated injury-risk estimates. The generator's stated position
norms and risk coefficients are simulation assumptions without supporting
citations in this snapshot. No LICENSE file was present in the inspected remote
tree; record team ownership and redistribution permissions before publication.

## Audit and runtime boundary

[`../data_profile.json`](../data_profile.json) contains the CSV checks from this
review. The internal [implementation plan](../../docs/IMPLEMENTATION_PLAN.md)
explains the findings, priorities, proposed field definitions and next work.
The audit is not a medical validation or proof of observation quality.

Keep the downloaded CSVs immutable. Future cleaning and scenario mapping belong
in separately versioned processed artifacts. Do not pass the full CSV or generator
to an agent. Runtime tools must select a player, a historical cutoff and allowed
fields; future injury outcomes, `injury_next_7d` and `exclude_from_training` are
offline evaluation fields. Past injury records also need field-level as-of
filtering: a future return date or final time-loss total is not known at onset.

Daily records cannot establish which measurements were available at a particular
match minute. The initial implementation should use completed days before the
synthetic match date. Any alignment with animation is an explicit synthetic
scenario mapping, not an observed relationship between these datasets.
