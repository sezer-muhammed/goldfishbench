# Contributing

Please report ambiguous questions, policy inconsistencies, parsing mistakes or
evaluation issues with `item_id` and `family_id`. Do not silently change released
gold labels or select examples according to model failures. Proposed language
changes require a new dataset version; keep all family siblings together.

Preserve UNKNOWN, abstention and technical failures as distinct outcomes.
Do not interpret them as NO. Report denominators and keep synthetic controlled
results separate from claims about real organizational workflows. Contributions
and automated checks do not count as independent human annotation.

The shipped evaluator is offline and contains no inference transport. Do not
commit provider keys, account/billing records, private raw response archives
or personal case data. Follow the tests and commands documented in `README.md`.
