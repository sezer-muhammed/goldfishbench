# GoldfishBench dataset card

Version **1.0.0** is the exact Goldfish question inventory used in the paper's
seven-system comparison. It contains original fictional, controlled English
scenarios. It is not a collection of private support tickets or real customers.
No evaluated model generated the test questions or their answer key.

## Download and load

Choose **one** full-dataset representation:

- [`data/goldfishbench.jsonl.gz`](../data/goldfishbench.jsonl.gz): the entire
  11,136-row inventory, compressed to approximately 1.62 MB.
- [`data/domains/`](../data/domains/): four ordinary UTF-8 JSONL shards, each
  approximately 18–20 MB. Their union is the same inventory, not additional data.

[`data/sample.jsonl`](../data/sample.jsonl) is an eight-row subset with full,
unshortened inputs. Every example asks about an unsuitable recipient when
intervention is needed; the correct routing answer is **NO**. The examples cover
all four domains with neutral and name-pressure renderings. Do not count the
sample again when computing dataset size.

```python
import gzip
import json

with gzip.open("data/goldfishbench.jsonl.gz", "rt", encoding="utf-8") as f:
    items = [json.loads(line) for line in f]

item = items[0]
model_input = item["visible"]  # Only these fields belong in a model request.
answer_key = item["query_truth_gold"]  # Evaluation metadata; never send this.
```

File digests and the canonical uncompressed inventory digest are in
[`data/manifest.json`](../data/manifest.json). Statistics and the duplicate audit
are machine-readable in [`data/statistics.json`](../data/statistics.json).

## What is one example?

A scenario **family** fixes the task topic and recipient construction. Its four
semantic worlds cross intervention need and recipient suitability. Three
renderings describe each world: `neutral_direct`, `name_property_pressure`, and
`urgency_saturation`. Each rendered world has a joint routing question. A
preselected component panel also has separate intervention-need and suitability
questions. These are separate stateless requests, not a multi-question conversation.

| Unit | Count | Interpretation |
|---|---:|---|
| Scenario families | 662 | Grouping unit for family-level uncertainty |
| Semantic worlds | 2,648 | 662 families × 4 N-by-S cells |
| Rendered worlds | 7,944 | 2,648 worlds × 3 renderings |
| Joint routing questions, `Y` | 7,944 | One per rendered world |
| Component-panel families | 133 | Subset with separate component probes |
| Intervention-need questions, `N` | 1,596 | 133 × 4 × 3 |
| Recipient-suitability questions, `S` | 1,596 | 133 × 4 × 3 |
| Total distinct question rows | **11,136** | Y plus N and S; not independent scenarios |

The precision source composes **80 authored topic records and 15 operation
recipes**. This structure creates additional dependence across families; 662
families do not imply 662 independently authored topics. Report sensitivity to
topic and recipe grouping as well as family-level uncertainty.

## Decision policy and gold

The fully stated policy defines:

```text
N = current automated handling is insufficient
C = recipient can execute the required operation
U = recipient is authorized for that operation
A = recipient is accepting new work now
S = C AND U AND A
Y = N AND S
```

Recipient names, urgency, quoted requester wishes, and a planned future use date
do not override these gates. Qualified automated recipients can be suitable.
Suitability concerns the exact named recipient ID in the complete registry.
Where present, revision selection, operation aliases, deny-overrides-grant, and
input/output capability constraints are defined in the visible policy.

**Actual release scope:** all released worlds have `U=true` and `A=true`.
Unsuitable recipients in this inventory have `C=false`; they are plausible
capability negatives. The general policy includes authorization and availability,
but these data do **not** measure failures caused by `U=false` or `A=false`.
All questions are affirmative (`operator=identity`); complementary negative
questions and a polarity bridge are not part of this release.

| N | S | Correct Y | Questions per rendering |
|---:|---:|:---:|---:|
| 0 | 0 | NO | 662 |
| 0 | 1 | NO | 662 |
| 1 | 0 | NO | 662 |
| 1 | 1 | YES | 662 |

Within each rendering, `Y` has 662 YES and 1,986 NO answers. An always-NO
classifier therefore has **75% raw accuracy and 50% balanced accuracy**. N and S
component labels are each balanced: 798 YES and 798 NO. Use the imbalance-aware
metrics and condition-specific denominators described in
[`EVALUATION.md`](EVALUATION.md).

`query_truth_gold` is the truth of the proposition actually asked: N, S, or Y.
`canonical_action_gold` always describes the final routing action Y. These
fields intentionally differ in **798 component rows**. Component questions must
be scored against `query_truth_gold`, not against the routing action.

## Schema and safe model serialization

The JSON Schema is [`schemas/item.schema.json`](../schemas/item.schema.json).
Each row explicitly separates the visible payload from evaluation metadata:

| Fields | Purpose |
|---|---|
| `visible.policy`, `visible.item` | Complete fictional policy and case facts |
| `visible.recipient.name`, `visible.recipient.description` | Proposed recipient and complete registry/capability description |
| `visible.question`, `visible.options` | The exact model-visible question and YES/NO order |
| `item_id`, `family_id`, `world_id` | Stable question, family, and rendered-world identifiers |
| `semantic_world_id`, `latent_world_id` | Same underlying world across renderings |
| `query_ast`, `polarity`, `transformation_type` | Formal target and relation |
| `query_truth_gold`, `canonical_action_gold` | Question truth and canonical routing gold |
| `latent_facts`, `gold_derivation` | Evaluation-only facts and derivation |
| `tactic`, `representation`, `relations` | Controlled rendering and comparison links |
| `paired_baseline_item_id`, `paired_world_id` | Links to matched neutral counterparts |
| `source`, `generator` | Original provenance, source split, original-item hash, seed, template, and version |
| `annotation` | Draft status and pending reviewer/adjudication fields |
| `topic_cluster_id`, `operation_recipe_id` | Additional precision-source dependence groups, when present |

**Serialize only `visible` for inference.** IDs, filenames, cells, ASTs, latent
facts, gold, tactics, and paired comparison links are evaluation-only. They can
reveal the condition or label. The original inputs intentionally include the
policy facts needed to solve the task; those visible facts must remain present.

The two option orders are preserved exactly. They are approximately, not
perfectly, balanced: 5,664 rows are NO-first and 5,472 are YES-first. For Y alone,
the counts are 4,032 and 3,912. Parse the actual answer label using
`option_mapping`; do not infer YES from option position.

## Domains, provenance, and selection

| Domain | Families | Question rows |
|---|---:|---:|
| Customer support | 164 | 2,832 |
| Internal IT | 168 | 2,856 |
| Document/data access | 163 | 2,700 |
| Workflow escalation | 167 | 2,748 |
| **Total** | **662** | **11,136** |

Two historical acquisition sources form one reported suite:

| Generator/source version | Families | Question rows |
|---|---:|---:|
| `0.8.0-hardness` | 32 | 1,152 |
| `0.9.0-goldfish-precision` | 630 | 9,984 |

The 630 precision families are the common technically usable joint-decision
families for the original five systems, selected from the previously attempted
precision experiment. Selection was based on technical availability, not answer
correctness. This is not the complete 1,200-family prospective candidate pool,
nor a claim that all acquisition happened in one physical run. The later two
systems received this same fixed inventory; their technical missingness is
reported in results without deleting questions from this public dataset.

`source.original_item_sha256` hashes each original full item using UTF-8 canonical
JSON with sorted keys and compact separators. The export preserves exact visible
payloads, IDs, query ASTs, labels, relations, and grouping. It omits private
execution/account metadata and redundant mixed-project selection flags. The
source's undecided release-license marker is replaced by the author's authorized
**CC BY 4.0** release license; no prompt or answer key is rewritten.

## Splits, reuse, and contamination

Every original `split` and `source.source_split` is `generalization`. This name
is historical metadata, **not proof of a held-out public test split**. There is
no released train/dev partition and no guarantee that the public examples remain
unseen by later models.

All variants, N/S/Y siblings, and four cells of a family must stay together if
users create derived splits. For a stronger generalization study, also group
shared topics, operation recipes, and recipient-name pools. Do not select prompt
variants, thresholds, or model settings using final test performance. Public
release introduces contamination risk for future evaluations; record release
version and access dates.

## Validation and annotation status

The export checks all 11,136 rule-derived truths, unique item IDs, fixed family
grouping/source splits, complete four-cell/three-rendering inventory, and exact
source-visible preservation. It was also checked against the published JSON
Schema. File hashes make byte changes detectable.

There are **zero exact duplicate complete visible payloads**. A normalized
variable-text signature (numeric literals/recipient IDs normalized; policy and
options excluded) has zero collisions. The scoped near-duplicate check compares
2,430 neutral Y/N1/S0 pairs within shared topics, and older pairs within domains,
using word-trigram Jaccard similarity; none reach 0.90. This is **not** exhaustive
semantic deduplication or proof that the scenarios are independent. Shared policy,
template, topic, recipe, and sibling-question dependence is intentional. No rows
were removed on the basis of this audit.

All language remains **agent-authored, programmatically checked draft material**.
Independent human semantic reviews completed: **0**. Reviewer fields are null,
adjudication is pending, and equivalence judgments have not been human-validated.
An empty ambiguity-flag list is not evidence of completed review. This release
and its model measurements are exploratory, not confirmatory evidence.

## Intended use and limitations

Use the inventory to study recipient-specific routing, sensitivity to pressure
renderings, and behavioral component/joint-decision inconsistency. It is not a
production routing policy, a security certification, an exhaustive agent safety
test, or evidence for a universal persuasion attack. Results concern the named
systems, their recorded versions, this symbolic English distribution, and the
reported usable denominators. Strong performance is a legitimate outcome.

The core contrasts are capability negatives under explicit complete policies;
unknown facts, optional routing, real organizational policies, actual aquarium
animals, authorization/availability negatives, and natural noisy tickets require
separate datasets and claims. The released sentences can be long and repetitive
by design. No model chain of thought is used as a causal explanation.

## License and attribution

The fictional dataset is released under **Creative Commons Attribution 4.0
International (CC BY 4.0)**. Attribute **Muhammed Izzet Sezer**, the GoldfishBench
paper, repository, and dataset version. Indicate derived transformations. Code
and third-party paper class/font licenses are specified separately in the
repository. Publication of this repository does not imply an arXiv acceptance or
identifier.
