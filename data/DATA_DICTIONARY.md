# Runtime data dictionary (v1)

The source CSV snapshot is unchanged. `src/backend/history.py` is the only runtime CSV reader.
`data/scenario_mapping.json` binds independent synthetic assets to P001, match 2026-01-25,
reference 67:00 and current clip 68:00. This is a demo binding, not a measured alignment.

| Field | Unit / definition | Runtime handling |
|---|---|---|
| `match_minutes`, `training_minutes` | Completed calendar-day minutes | Sum over 7, prior non-overlapping 7, and 28 days |
| `srpe_load` | Minutes × session RPE, arbitrary units | Same windows; incomplete windows are null |
| `sleep_duration` | Hours | Seven complete days, mean |
| `sleep_quality` | 1–5, higher better | Seven complete days, mean |
| `fatigue_score`, `muscle_soreness` | 1–5, higher worse | Seven complete days, mean |
| `stress_level`, `resting_hr`, `hrv_rmssd` | 1–5 / bpm / ms | Source evidence only; no health inference |
| `actual_appearances_14d` | Count of completed days with match_minutes > 0 | Recomputed; not the source calendar-fixture count |
| `days_since_last_appearance` | Days between cutoff and latest actual appearance | Uses past rows only |
| `load_change_fraction` | (recent 7-day load − preceding 7-day load) / preceding load | Null with missing/zero denominator and an explicit availability reason |
| Past injury | Occurred on/before cutoff | Final end date/days lost included only if end <= cutoff; training-return dates withheld |
| Distances / rolling distances | Source definitions unresolved | Excluded from summaries; HSR > total recorded as a quality flag |
| Source ACWR, z-score, rolling counts, load_change_pct | Different/unstable definitions | Excluded; no blanket zero fill |
| `injury_next_7d`, `exclude_from_training` | Offline labels and eligibility | Never projected into runtime context |

Daily evidence IDs are `daily:P001:YYYY-MM-DD`; injury IDs retain source IDs.
Each source reference records CSV line and source SHA-256. Frame evidence records
PNG hash, neutral clip ID, player ID, clip/match milliseconds and input revision.
No labels, Blender configs, generator formulas or future rows are sent to the models.

Analyst evidence is gated separately from public frame evidence. A fan narration request
receives accepted visual claims and their visibility limitations only. Its API response
omits all historical outputs, investigator rationale, wellness metrics and case concern.
