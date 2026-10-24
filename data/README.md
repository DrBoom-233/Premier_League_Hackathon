# Training data

Store model training data for this project here. Keep large or generated datasets organized by source and split, for example:

```text
data/
  raw/          Original synthetic event files
  processed/    Cleaned and normalized datasets
  splits/       train, validation, and test data
```

Document each dataset's source, schema, generation steps, and license before using it. Do not add credentials, personal data, or data/footage without permission. Use Git LFS or an approved dataset store for files that are too large for regular Git.

## Current synthetic snapshot

The downloaded `daily_records.csv` and `injury_history.csv` are immutable source
inputs for the qualitative MVP. Training a predictor is not an MVP requirement.
See [source provenance and runtime restrictions](source/README.md),
[checksums](source_manifest.json), [CSV audit](data_profile.json), and the
[internal implementation plan](../docs/IMPLEMENTATION_PLAN.md). Keep processed
features separate, enforce historical cutoffs, and exclude future labels from
all runtime agent inputs.
