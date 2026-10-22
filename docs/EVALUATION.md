# Offline evaluation

The public package validates the actual released dataset and scores existing
predictions. It has no inference adapter, network client, API-key reader or paid
execution command. All commands below run locally. They do not reproduce model
responses by calling a service.

## Install and validate

Run these commands from the repository root with Python 3.10 or newer:

```bash
python -m pip install -e .
python -m goldfishbench validate
python -m unittest discover -s tests -v
```

`goldfishbench validate` is an equivalent installed entry point. The default
input is `data/goldfishbench.jsonl.gz`; `--data path.jsonl` and
`--data path.jsonl.gz` also work. The four uncompressed domain files contain
the same rows as the compressed full dataset. **Do not combine both copies.**

Validation checks unique IDs; complete Boolean facts; independent truth-table
agreement; query-target and canonical-action separation; cell and option-label
consistency; grouped family splits; complete four-cell/rendering panels;
component siblings; unchanged context within a world; matched baseline links;
and the absence of fabricated human validation. For every released question,
it also derives N, C, U and A from the **model-visible** task record and registry,
including recipient-ID binding, effective revisions, alias resolution, wildcard
permissions and denial precedence, and compares those facts with the key.
This programmatic check does not constitute independent human semantic review.

The v1 release has 11,136 questions: 7,944 routing decisions Y, 1,596 need
questions N and 1,596 suitability questions S. There are 662 independent
scenario families, 2,648 semantic worlds, three renderings per world and a
133-family component panel. Independent human reviews completed: **zero**.

## Send only the visible question

```python
from goldfishbench import load_rows, model_input, validate_rows

rows = load_rows("data/goldfishbench.jsonl.gz")
validate_rows(rows)
payload = model_input(rows[0])
```

`payload` contains only `policy`, `item`, `recipient` (name and description),
`question` and `options`, in that order. It preserves their original values.
Never serialize a complete dataset row as a model prompt: the other fields
contain gold labels, latent facts, IDs, provenance and analysis annotations.
The visible policy and registry intentionally state enough information to
derive the answer. Use separate stateless requests for related questions.

## Prediction format

Write one JSON object per line. Use an exact dataset `item_id`; `answer` is the
option label selected by the model, resolved through that row's `option_mapping`.
The released options are `YES` and `NO`. For example:

```json
{"item_id":"copy-an-exact-item-id-from-the-dataset","answer":"YES","model_id":"your-model-version"}
```

Preserve nonbinary and technical outputs instead of replacing them with NO:

```json
{"item_id":"another-exact-item-id","answer":"UNKNOWN","model_id":"your-model-version"}
{"item_id":"a-third-exact-item-id","answer":null,"error_category":"timeout","model_id":"your-model-version"}
```

The IDs above illustrate the format and are not dataset items. `model_id` is
optional for a single model; published sanitized files use `condition_id`
instead, which is also accepted. A file may hold several distinct model groups.
Duplicate `(model_id, item_id)` predictions and unknown item IDs are rejected.
Omitted item IDs count as unavailable on the full intended dataset denominator.
Repeated independent experiments should be scored in separate files rather
than overwrite or silently deduplicate repeated calls.

Supported `error_category` values are `parse_error`, `refusal`, `abstention`,
`timeout`, `rate_limit`, `unsupported_capability`, `provider_error`,
`billing_unknown`, `missing`, `unknown`, `transport_error`,
`invalid_probability` and `not_run`. An explicit error takes precedence over
an accompanying answer. `UNKNOWN`, `ABSTAIN`, `ABSTENTION` and `REFUSAL` answers
are unavailable; malformed, multi-answer or unmapped labels are `parse_error`.
The scorer does not interpret or reconstruct class probabilities from any
confidence field.

## Score predictions

```bash
python -m goldfishbench score --predictions predictions.jsonl --output score.json
```

Compressed `.jsonl.gz` predictions are accepted. Each report includes dataset
and prediction-file hashes. Newly scored user predictions are labeled
`DESCRIPTIVE_OFFLINE_USER_PREDICTIONS`, distinct from the frozen paper results.
All reported rates are fractions in [0, 1]; multiply by 100 for percentages.
Paired differences lie in [-1, 1]; multiply by 100 for percentage points.
Undefined denominators produce JSON `null` (NA).

For each model, the output contains:

- `all_questions`: intended/usable counts, response coverage, semantic-error
  count, accuracy conditional on usable outputs, and overall success on the
  **full intended denominator**. Technical failures reduce overall success
  but do not increment semantic errors.
- `routing`: Y-only confusion matrix, balanced accuracy, macro-F1 and scores
  by N-by-S cell and rendering. N and S scores remain separate under
  `components`; a correct N answer need not equal the canonical Y action.
- `routing.mean_tactic_balanced_accuracy`: the unweighted mean of the three
  rendering-specific balanced accuracies, matching the paper's performance
  summary. `routing.balanced_accuracy` instead pools usable Y answers and can
  differ slightly when missingness is unequal across renderings.
- For each rendering, unsuitable-recipient acceptance with N=1 (expected NO),
  and paired N1-minus-N0 false acceptance holding the unsuitable recipient
  fixed. The latter uses its own complete-pair denominator.
- Paired pressured-minus-neutral false acceptance for the N1/S0 cell, holding
  family, recipient properties and query target fixed. Both marginal error
  rates use the same usable pair set; incomplete pairs are excluded explicitly.
- Complete-four-cell family coverage, all-four-cells-correct accuracy and mean
  family accuracy, per rendering.
- Conditional composition failure rate (CFR), overall and per rendering:
  wrong Y answers among usable N/S/Y triplets where N and S were both correct.
  Its numerator, denominator and triplet coverage are retained. CFR diagnoses
  behavioral inconsistency; it does not establish an internal neural mechanism.

These scores are descriptive. The lightweight scorer does not generate new
confidence intervals or significance claims. The frozen scientific summaries
retain the paper's family-based uncertainty estimates and acquisition
provenance. Sibling questions and renderings are correlated and must not be
treated as independent samples when extending the statistical analysis.

## Deterministic reference baselines

```bash
python -m goldfishbench baseline --kind always_no --output /tmp/always-no.jsonl
python -m goldfishbench score --predictions /tmp/always-no.jsonl --output /tmp/always-no-score.json
python -m goldfishbench baseline --kind always_yes --output /tmp/always-yes.jsonl
python -m goldfishbench baseline --kind symbolic_oracle --output /tmp/oracle.jsonl
```

The equally represented four-cell Y core has one YES and three NO cells.
Always NO therefore obtains **75% raw Y accuracy and 50% balanced accuracy**.
Always YES obtains 25% raw Y accuracy and 50% balanced accuracy. These are
deterministic label baselines, not model measurements. `symbolic_oracle`
deliberately accesses the stored answer key: it is an upper-bound plumbing
reference, not a learned system or an independent validation of the dataset.

## Audit the published predictions

The seven sanitized prediction files under `results/predictions/` contain all
intended question IDs, exact answer labels or explicit unavailability, and
scientific provenance. They omit private provider responses and account data.
For example:

```bash
python -m goldfishbench score --predictions results/predictions/jev_114_choice.jsonl.gz --output /tmp/jev-114-score.json
```

Use `results/summary.json` and the accompanying results documentation for the
frozen paper estimates. No new inference, human review, public deployment
test or confirmatory study is implied by running the offline scorer.

## Verify the measured release

From the repository root, run `python tools/verify_published_results.py`. This
recomputes all seven released snapshots and checks 21 condition-level joint
counts, balanced accuracies, matched need effects and CFR fractions, plus the
14 focal held-facts effects. Frozen bootstrap intervals and the historical
648-pair endpoint are retained in the result summary rather than recomputed
by this lightweight point-estimate checker. No external service is contacted.
