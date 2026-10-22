"""Recompute the released seven-model point estimates, fully offline."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from goldfishbench.data import load_rows, validate_rows
from goldfishbench.metrics import score_predictions


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = load_rows(ROOT / "data/goldfishbench.jsonl.gz")
    validate_rows(rows)
    summary = json.loads((ROOT / "results/summary.json").read_text())
    manifest = json.loads((ROOT / "results/predictions/manifest.json").read_text())
    conditions = {(c["condition_id"], c["tactic"]): c for c in summary["conditions"]}
    contrasts = {(c["condition_id"], c["pressure"]): c
                 for c in summary["rhetorical_contrasts"] if c["N"] and not c["S"]}
    checked, models = 0, []
    for entry in manifest["records"]:
        path = ROOT / "results/predictions" / entry["path"]
        require(hashlib.sha256(path.read_bytes()).hexdigest() == entry["compressed_sha256"],
                "published prediction checksum differs")
        predictions = load_rows(path)
        cid = entry["condition_id"]
        require(len(predictions) == 11136 and len({r["item_id"] for r in predictions}) == 11136,
                "published prediction inventory differs")
        report = score_predictions(rows, predictions)["models"][cid]
        require(report["all_questions"]["usable"] == entry["usable_answers"], "coverage differs")
        for tactic, result in report["routing"]["by_tactic"].items():
            original = conditions[cid, tactic]
            core = original["core_and_components"]["joint_core"]
            require(result["usable"] == core["usable"], "joint coverage differs")
            require(result["usable"] - result["semantic_errors"] == core["correct"], "joint correctness differs")
            require(math.isclose(result["balanced_accuracy"], core["balanced_accuracy_usable"], abs_tol=1e-12),
                    "balanced accuracy differs")
            need = result["paired_need"]
            require(need["usable_pairs"] == original["usable_pairs"], "need pair denominator differs")
            require(math.isclose(need["difference_N1_minus_N0"]["value"], original["value"], abs_tol=1e-12),
                    "need point estimate differs")
            composition = original["core_and_components"]["composition"]
            require(result["composition"]["usable_triplets"] == composition["usable_triplets"],
                    "component triplet coverage differs")
            require(result["composition"]["CFR"]["numerator"] == composition["Y_incorrect_given_both_correct"],
                    "CFR numerator differs")
            require(result["composition"]["CFR"]["denominator"] == composition["N_and_S_both_correct_denominator"],
                    "CFR denominator differs")
            checked += 1
        for tactic, result in report["routing"]["rhetoric_contrasts"].items():
            original = contrasts[cid, tactic]
            require(result["usable_pairs"] == original["usable_pairs"], "rendering denominator differs")
            require(math.isclose(result["difference_tactic_minus_neutral"]["value"], original["error_delta"], abs_tol=1e-12),
                    "rendering point estimate differs")
        models.append({"condition_id": cid, "usable_answers": report["all_questions"]["usable"],
                       "joint_usable": report["routing"]["usable"],
                       "joint_semantic_errors": report["routing"]["semantic_errors"],
                       "equal_rendering_mean_balanced_accuracy": report["routing"]["mean_tactic_balanced_accuracy"]})
    result = {"status": "PASS_PUBLISHED_POINT_ESTIMATES", "models": models,
              "conditions_checked": checked, "focal_rendering_contrasts_checked": len(contrasts),
              "new_model_calls": 0, "bootstrap_intervals_recomputed": False,
              "historical_648_endpoint_recomputed": False,
              "note": "The frozen scientific summary separately preserves uncertainty sensitivities and the historical endpoint."}
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
