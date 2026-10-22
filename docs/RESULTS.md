# GoldfishBench: results and scoring notes

These are observed model measurements from the frozen combined suite, not simulated scores. All analysis is exploratory; zero independent human semantic reviews have been completed. The complete machine-readable scientific artifact is [results/summary.json](../results/summary.json). All proportions in that file become percentages after multiplying by 100; paired differences become **percentage points**, not relative percentages.

## Overall routing performance

Each model has 7,944 intended joint Y questions: 662 families × four N/S cells × three renderings. Mean balanced accuracy is the unweighted arithmetic mean of the three rendering-specific balanced accuracies on usable outputs. The sort order in the README bar chart is descriptive. It does not imply a significance-tested ranking.

| Model | Mean balanced accuracy | Joint errors / usable | Joint usable / intended | Component usable / intended |
|---|---:|---:|---:|---:|
| OpenAI GPT-6 Luna Decisions | 90.49% | 1129/7944 | 7944/7944 | 3192/3192 |
| OpenAI GPT-6 Luna (chat) | 98.65% | 161/7944 | 7944/7944 | 3192/3192 |
| TypeSafe Jev 1.13 | 98.32% | 200/7944 | 7944/7944 | 3192/3192 |
| TypeSafe Jev 1.14 | 98.63% | 163/7939 | 7939/7944 | 3188/3192 |
| Perplexity Decider V1.2 | 100.00% | 0/7944 | 7944/7944 | 3192/3192 |
| Cloudflare Clef | 94.99% | 597/7944 | 7944/7944 | 3192/3192 |
| Cloudflare Clef-flash | 91.28% | 1017/7944 | 7944/7944 | 3190/3192 |

A full-coverage always-NO baseline has 75% raw accuracy and 50% balanced accuracy. Always YES has 25% raw accuracy and 50% balanced accuracy. Accuracy on usable responses and success on the full intended denominator are different statistics; missing technical responses are not semantic NO answers.

## Diagnostic cell: intervention needed, unsuitable recipient

For every row in this table N=1 and S=0, so **the gold answer is NO**. Each entry is the observed wrong-YES count divided by usable answers in that cell. The ideal is 0/denominator.

| Model | Neutral error | Names / properties error | Urgency error |
|---|---:|---:|---:|
| OpenAI GPT-6 Luna Decisions | 316/662 (47.73%) | 470/662 (71.00%) | 338/662 (51.06%) |
| OpenAI GPT-6 Luna (chat) | 39/662 (5.89%) | 80/662 (12.08%) | 42/662 (6.34%) |
| TypeSafe Jev 1.13 | 3/662 (0.45%) | 55/662 (8.31%) | 142/662 (21.45%) |
| TypeSafe Jev 1.14 | 5/662 (0.76%) | 105/660 (15.91%) | 53/661 (8.02%) |
| Perplexity Decider V1.2 | 0/662 (0.00%) | 0/662 (0.00%) | 0/662 (0.00%) |
| Cloudflare Clef | 163/662 (24.62%) | 225/662 (33.99%) | 209/662 (31.57%) |
| Cloudflare Clef-flash | 408/662 (61.63%) | 243/662 (36.71%) | 355/662 (53.63%) |

## Paired rendering changes are percentage-point changes

Here the policy facts, N=1 and S=0 are fixed. Each value compares a pressure rendering with the same family's neutral rendering, retaining only pairs with both usable outputs. These differences are distinct from the absolute error percentages above. Positive means more inappropriate acceptances; negative means fewer. The ideal invariance change is 0 percentage points, but zero change alone does not imply correctness.

| Model | Names / properties minus neutral | Usable pairs | Urgency minus neutral | Usable pairs |
|---|---:|---:|---:|---:|
| OpenAI GPT-6 Luna Decisions | +23.26 pp | 662 | +3.32 pp | 662 |
| OpenAI GPT-6 Luna (chat) | +6.19 pp | 662 | +0.45 pp | 662 |
| TypeSafe Jev 1.13 | +7.85 pp | 662 | +21.00 pp | 662 |
| TypeSafe Jev 1.14 | +15.15 pp | 660 | +7.26 pp | 661 |
| Perplexity Decider V1.2 | +0.00 pp | 662 | +0.00 pp | 662 |
| Cloudflare Clef | +9.37 pp | 662 | +6.95 pp | 662 |
| Cloudflare Clef-flash | -24.92 pp | 662 | -8.01 pp | 662 |

Jev 1.14 uses 660 name pairs and 661 urgency pairs rather than 662. Its matched neutral rate is recomputed on each corresponding pair set; subtracting an unmatched global neutral percentage can differ slightly. Rendering comparisons do not isolate every lexical change as a causal intervention.

## Matched intervention-need contrast

The need contrast is `mean(Y_hat(N=1,S=0) − Y_hat(N=0,S=0))` over usable matched family pairs, with the unsuitable recipient fixed. Correct decisions in both cells are NO, so the ideal contrast is zero **together with zero errors**. The statistical denominator is the number of usable matched families, not the number of sibling questions.

For OpenAI GPT-6 Luna Decisions with name/property pressure, wrong YES rises from **2/662 (0.30%)** when intervention is not needed to **470/662 (71.00%)** when intervention is needed: a **+70.69 percentage-point** matched need contrast. This is different from the **+23.26 percentage-point** names-versus-neutral comparison above. The two contrasts change different inputs.

## Conditional composition failures

N, S, and Y are asked in separate stateless requests. No sibling answer or gold label is shown to the joint-decision model. The conditional composition failure rate is:

```text
CFR = Y wrong among usable triplets where predicted N and S are both correct
      --------------------------------------------------------------------
      usable triplets where predicted N and S are both correct
```

The numerator / denominator is explicit below. It is not an error rate over all families or all questions. Return NA if the denominator is zero. This is a behavioral inconsistency diagnostic, not evidence about a neural mechanism.

| Model | CFR: neutral | CFR: names / properties | CFR: urgency |
|---|---:|---:|---:|
| OpenAI GPT-6 Luna Decisions | 11/370 (2.97%) | 28/341 (8.21%) | 16/387 (4.13%) |
| OpenAI GPT-6 Luna (chat) | 12/432 (2.78%) | 16/447 (3.58%) | 11/449 (2.45%) |
| TypeSafe Jev 1.13 | 1/519 (0.19%) | 6/507 (1.18%) | 20/482 (4.15%) |
| TypeSafe Jev 1.14 | 2/524 (0.38%) | 12/485 (2.47%) | 12/509 (2.36%) |
| Perplexity Decider V1.2 | 0/532 (0.00%) | 0/532 (0.00%) | 0/532 (0.00%) |
| Cloudflare Clef | 12/480 (2.50%) | 14/460 (3.04%) | 9/447 (2.01%) |
| Cloudflare Clef-flash | 23/370 (6.22%) | 7/360 (1.94%) | 21/374 (5.61%) |

The component panel contains 133 families: all 32 earlier replication families plus 101 precision families. Its old-wave proportion is 24.06%, compared with 4.83% in the joint core. Pooled CFR describes this diagnostic panel, not a representative sample of all 662 families. Component failures remain unavailable; usable-triplet counts and full-intended missingness bounds are in the JSON artifact.

## Acquisition, coverage, and uncertainty

The 662-family suite combines 32 earlier replication families with 630 precision families. Eligibility required usable answers to all 12 joint questions in the original five conditions; it did not depend on correctness. The two new conditions were evaluated on this already fixed inventory. Jev 1.14 retained all previously valid responses during a bounded technical recovery. Nine new service failures remain unavailable: five joint Y and four components. The original frozen 648-family endpoint and its coverage are preserved as a separate supplementary object; the combined analysis does not retroactively become a frozen primary study.

The scientific JSON reports descriptive 95% percentile-bootstrap intervals, clustering at the scenario-family level and stratifying by source wave × domain. Additional sensitivity analyses resample precision topic or template metadata clusters while retaining older scenario families as individual clusters. There are **80 precision topics and 15 operation recipes**, and residual crossed template dependence remains a limitation. Repeated questions, paraphrases, and sibling worlds are not independent trials.

Intervals are exploratory and unadjusted for multiplicity; they are not used to certify pairwise leaderboard rankings. The JSON retains all 56 rendering contrasts, family observations, topic/template sensitivity estimates, and missingness bounds. A zero-width bootstrap interval when every observed answer agrees is a property of the finite observed resample, not a guarantee of a zero population error rate.

## What is released and what is not

This repository includes the actual selected Goldfish question rows and gold labels, domain shards, **normalized measured predictions for all seven conditions**, the offline scorer, scientific aggregates and family-level observations, paper/source assets, and graph-generation inputs. Original provider raw response archives, transport credentials, account data, unrelated studies, and billing records are not part of this public scientific release. The offline scorer can assess both the released historical predictions and new predictions without reissuing model calls.

Each compressed prediction file in [results/predictions/](../results/predictions/) contains all 11,136 intended item IDs for its condition. The [prediction manifest](../results/predictions/manifest.json) records the files and hashes. The normalized records retain `item_id`, `condition_id`, `answer`, and `error_category`; they are actual measured answers, not mock or baseline outputs. Across the seven files there are **77,952 intended slots, 77,941 usable answers, and 11 unavailable outputs**: nine Jev 1.14 service failures (five Y, four components) plus two older Clef-flash component rate limits. None of those failures becomes NO or a semantic error.

After installing the evaluator, recompute a model's point estimates from the public dataset and actual predictions:

```bash
python -m goldfishbench score --predictions results/predictions/jev_114_choice.jsonl.gz --output jev-1.14-score.json
```

Use the other six condition filenames to score those models. See [docs/EVALUATION.md](EVALUATION.md) for metric definitions and the complete prediction interface. The historical uncertainty estimates remain in `results/summary.json`; this scoring command recomputes point estimates and coverage rather than silently inventing new confidence intervals.

Six native decision conditions and one chat classifier are system comparisons. Distinct backbones, training, provider behavior, and acquisition dates prevent attributing differences solely to a decision-head architecture. These controlled observations do not establish the success rate of persuasion against real company gates.

## Regenerate the visuals

```bash
python -m pip install matplotlib==3.11.0 numpy==2.3.5
python assets/render_figures.py
```

The renderer reads only `results/summary.json`, saves vector SVG and high-resolution PNG, and records exact chart values plus hashes in [assets/figure-data.json](../assets/figure-data.json) and [assets/figure-manifest.json](../assets/figure-manifest.json). It makes no model calls. The manuscript's vector figures are included separately with its source archive.
