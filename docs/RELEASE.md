# Public release v1.0.0

This is the first public release of the GoldfishBench paper inventory, measured
answer snapshots, scientific summaries and offline evaluation software. It
does not announce an arXiv identifier or a peer-reviewed publication.

The release contains 11,136 question rows from 662 scenario families, exactly
preserving the evaluated visible prompts, query ASTs, symbolic truths and source
grouping. It includes 7,944 routing questions and 3,192 component questions. All
original source splits remain `generalization`; there is no new training split.
The data card describes the original five-model complete-case selection and
the later two-model evaluation of the same fixed inventory.

Seven normalized model snapshots contain 77,952 intended item/model slots and
77,941 usable answers. The remaining 11 are unavailable: nine Jev1.14 service
failures (five routing and four components) and two historical Clef-flash
component rate limits. Failed outputs are never converted to NO. The raw
provider response archives and account or billing metadata are excluded.

The unchanged manuscript has nine pages, three active vector figures and ten
references. Its PDF and source are included. The public result summary preserves
all 21 rendering conditions, all 56 cell-specific rhetorical contrasts and the
historical frozen 648-pair endpoint separately. The lightweight public verifier
recomputes current joint counts, balanced accuracy, need contrasts, focal
rendering contrasts and conditional composition failure fractions. It does not
claim to regenerate bootstrap intervals or the older endpoint from this
662-family release.

Completed release checks include independent Boolean fixtures, all 11,136
visible structured policy records, 34 unit tests, source-to-release data
equivalence, all-seven measured point estimates, archive/file checksums,
documentation links, chart readability and a release-content privacy scan.
These checks are software/agent checks. Independent human semantic reviews
remain zero, and all scientific conclusions remain exploratory.

Run the following from the repository root:

```bash
python tools/verify_release.py
python tools/verify_published_results.py
```

`release-manifest.json` binds every committed release payload file except
itself. Its version is a dataset/software release version, not an arXiv version.
The broader research workspace remains private; this public repository starts
with its own clean Git history.
