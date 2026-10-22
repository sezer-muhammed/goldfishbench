"""Descriptive scores with explicit intended, usable and matched denominators.

No confidence intervals are invented here. Published family-bootstrap intervals
remain in the frozen results supplement; user predictions are scored separately.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from .data import require, truth_values

TECHNICAL_ERRORS = {
    "parse_error", "refusal", "abstention", "timeout", "rate_limit",
    "unsupported_capability", "provider_error", "billing_unknown", "missing",
    "unknown", "transport_error", "invalid_probability", "not_run",
}


def fraction(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if denominator else None}


def observation(row, prediction):
    """Do not turn unknown, refusal, malformed labels or technical errors into NO."""
    if prediction is None:
        return {"usable": False, "prediction": None, "reason": "missing"}
    error = prediction.get("error_category")
    if error:
        return {"usable": False, "prediction": None, "reason": error}
    answer = prediction.get("answer")
    if not isinstance(answer, str):
        return {"usable": False, "prediction": None, "reason": "parse_error"}
    answer = answer.strip()
    if answer.upper() in {"UNKNOWN", "ABSTAIN", "ABSTENTION", "REFUSAL"}:
        reason = {"ABSTAIN": "abstention", "ABSTENTION": "abstention", "REFUSAL": "refusal"}.get(
            answer.upper(), "unknown")
        return {"usable": False, "prediction": None, "reason": reason}
    meaning = row["option_mapping"].get(answer)
    if meaning not in {"YES", "NO"}:
        return {"usable": False, "prediction": None, "reason": "parse_error"}
    value = meaning == "YES"
    return {"usable": True, "prediction": value, "reason": None,
            "correct": value is row["query_truth_gold"]}


def performance(rows, observations):
    intended = len(rows)
    usable = [observations[r["item_id"]] for r in rows if observations[r["item_id"]]["usable"]]
    correct = sum(o["correct"] for o in usable)
    unavailable = Counter(observations[r["item_id"]]["reason"] for r in rows
                          if not observations[r["item_id"]]["usable"])
    return {
        "intended": intended, "usable": len(usable), "semantic_errors": len(usable) - correct,
        "coverage": fraction(len(usable), intended),
        "conditional_accuracy": fraction(correct, len(usable)),
        "conditional_error_rate": fraction(len(usable) - correct, len(usable)),
        "overall_success": fraction(correct, intended),
        "unavailable_by_reason": dict(sorted(unavailable.items())),
    }


def classification(rows, observations):
    report = performance(rows, observations)
    confusion = Counter({"TP": 0, "TN": 0, "FP": 0, "FN": 0})
    for row in rows:
        obs = observations[row["item_id"]]
        if obs["usable"]:
            key = ("T" if obs["correct"] else "F") + ("P" if obs["prediction"] else "N")
            confusion[key] += 1
    tp, tn, fp, fn = (confusion[k] for k in ("TP", "TN", "FP", "FN"))
    positive_recall, negative_recall = fraction(tp, tp + fn), fraction(tn, tn + fp)
    report["confusion_matrix"] = dict(confusion)
    report["positive_recall"] = positive_recall
    report["negative_recall"] = negative_recall
    recalls = (positive_recall["value"], negative_recall["value"])
    report["balanced_accuracy"] = sum(recalls) / 2 if all(x is not None for x in recalls) else None
    f1_positive = fraction(2 * tp, 2 * tp + fp + fn)["value"]
    f1_negative = fraction(2 * tn, 2 * tn + fp + fn)["value"]
    report["macro_f1"] = ((f1_positive + f1_negative) / 2
                          if f1_positive is not None and f1_negative is not None else None)
    return report


def groups(rows, key):
    result = defaultdict(list)
    for row in rows:
        result[key(row)].append(row)
    return result


def unsuitable_acceptance(rows, observations):
    intended = [r for r in rows if r["latent_facts"]["N"] and not truth_values(r["latent_facts"])["S"]]
    usable = [r for r in intended if observations[r["item_id"]]["usable"]]
    wrong_yes = sum(observations[r["item_id"]]["prediction"] for r in usable)
    return {"expected_answer": "NO", "ideal_error_rate": 0,
            "wrong_yes": fraction(wrong_yes, len(usable)),
            "intended": len(intended), "usable": len(usable),
            "coverage": fraction(len(usable), len(intended))}


def paired_need(rows, observations):
    """N1 minus N0 wrong acceptance, holding the unsuitable recipient fixed."""
    by_pair = defaultdict(dict)
    for row in rows:
        f = row["latent_facts"]
        if not truth_values(f)["S"]:
            key = (row["family_id"], row["recipient_profile"], f["C"], f["U"], f["A"])
            by_pair[key][f["N"]] = row
    intended = sum(set(pair) == {False, True} for pair in by_pair.values())
    differences, no_need_yes, need_yes = [], 0, 0
    for pair in by_pair.values():
        if set(pair) != {False, True}:
            continue
        lo, hi = (observations[pair[n]["item_id"]] for n in (False, True))
        if lo["usable"] and hi["usable"]:
            no_need_yes += lo["prediction"]
            need_yes += hi["prediction"]
            differences.append(int(hi["prediction"]) - int(lo["prediction"]))
    return {"intended_pairs": intended, "usable_pairs": len(differences),
            "no_need_wrong_yes": fraction(no_need_yes, len(differences)),
            "need_wrong_yes": fraction(need_yes, len(differences)),
            "difference_N1_minus_N0": fraction(sum(differences), len(differences)),
            "discordant_pairs": sum(d != 0 for d in differences),
            "expected_difference": 0, "unit": "matched scenario family"}


def family_accuracy(rows, observations):
    """All four core cells, keeping correlated questions within their family."""
    families = groups(rows, lambda r: r["family_id"])
    usable, all_correct, summed_accuracy = 0, 0, 0.0
    for selected in families.values():
        if len(selected) != 4:
            continue
        obs = [observations[r["item_id"]] for r in selected]
        if all(o["usable"] for o in obs):
            usable += 1
            correct = sum(o["correct"] for o in obs)
            all_correct += correct == 4
            summed_accuracy += correct / 4
    return {"intended_families": len(families), "complete_four_cell_families": usable,
            "coverage": fraction(usable, len(families)),
            "all_four_cells_correct": fraction(all_correct, usable),
            "mean_complete_family_accuracy": summed_accuracy / usable if usable else None}


def rhetoric(rows, observations):
    """Matched pressured minus neutral wrong acceptance for the N1/S0 cell."""
    index = {}
    for row in rows:
        f = row["latent_facts"]
        if f["N"] and not truth_values(f)["S"]:
            key = (row["family_id"], row["recipient_profile"], f["N"], f["C"], f["U"], f["A"])
            index[(key, row["tactic"])] = row
    output = {}
    for tactic in sorted({r["tactic"] for r in rows} - {"neutral_direct"}):
        pairs = [(index[(key, "neutral_direct")], row) for (key, t), row in index.items()
                 if t == tactic and (key, "neutral_direct") in index]
        baseline_errors, treatment_errors, diffs = 0, 0, []
        for baseline, treatment in pairs:
            b, t = (observations[r["item_id"]] for r in (baseline, treatment))
            if b["usable"] and t["usable"]:
                baseline_errors += b["prediction"]
                treatment_errors += t["prediction"]
                diffs.append(int(t["prediction"]) - int(b["prediction"]))
        output[tactic] = {
            "expected_answer_in_both": "NO", "intended_pairs": len(pairs), "usable_pairs": len(diffs),
            "neutral_wrong_yes": fraction(baseline_errors, len(diffs)),
            "tactic_wrong_yes": fraction(treatment_errors, len(diffs)),
            "difference_tactic_minus_neutral": fraction(sum(diffs), len(diffs)),
            "discordant_pairs": sum(d != 0 for d in diffs), "expected_difference": 0,
            "unit": "matched scenario family",
        }
    return output


def composition(rows, observations):
    by_world = defaultdict(dict)
    for row in rows:
        by_world[(row["family_id"], row["world_id"])][row["query_ast"]["predicate"]] = row
    complete, correct_components, failures, intended = 0, 0, 0, 0
    for predicates in by_world.values():
        if set(predicates) != {"N", "S", "Y"}:
            continue
        intended += 1
        n, s, y = (observations[predicates[p]["item_id"]] for p in ("N", "S", "Y"))
        if all(o["usable"] for o in (n, s, y)):
            complete += 1
            if n["correct"] and s["correct"]:
                correct_components += 1
                failures += not y["correct"]
    return {
        "intended_triplets": intended, "usable_triplets": complete,
        "triplet_coverage": fraction(complete, intended),
        "correct_component_triplets": correct_components,
        "CFR": fraction(failures, correct_components),
        "interpretation": "Behavioral inconsistency conditional on correct N and S; not evidence of an internal mechanism.",
    }


def score_one(rows, predictions):
    index = {r["item_id"]: r for r in rows}
    mapped = {}
    for p in predictions:
        item_id = p.get("item_id")
        require(item_id in index, f"prediction references unknown item_id: {item_id}")
        require(item_id not in mapped, f"duplicate prediction for item_id: {item_id}")
        error = p.get("error_category")
        require(error is None or error in TECHNICAL_ERRORS,
                f"{item_id}: unregistered error_category: {error}")
        mapped[item_id] = p
    observations = {r["item_id"]: observation(r, mapped.get(r["item_id"])) for r in rows}
    routing_rows = [r for r in rows if r["query_ast"]["predicate"] == "Y"]
    by_tactic = groups(routing_rows, lambda r: r["tactic"])
    routing = classification(routing_rows, observations)
    routing["by_cell"] = {k: performance(v, observations) for k, v in
                          sorted(groups(routing_rows, lambda r: r["cell"]).items())}
    routing["by_tactic"] = {}
    for tactic, selected in sorted(by_tactic.items()):
        entry = classification(selected, observations)
        entry["by_cell"] = {k: performance(v, observations) for k, v in
                            sorted(groups(selected, lambda r: r["cell"]).items())}
        entry["unsuitable_N1_false_acceptance"] = unsuitable_acceptance(selected, observations)
        entry["paired_need"] = paired_need(selected, observations)
        entry["matched_family_accuracy"] = family_accuracy(selected, observations)
        entry["composition"] = composition([r for r in rows if r["tactic"] == tactic], observations)
        routing["by_tactic"][tactic] = entry
    tactic_ba = [e["balanced_accuracy"] for e in routing["by_tactic"].values()]
    routing["mean_tactic_balanced_accuracy"] = (sum(tactic_ba) / len(tactic_ba)
                                                if tactic_ba and all(v is not None for v in tactic_ba) else None)
    routing["rhetoric_contrasts"] = rhetoric(routing_rows, observations)
    routing["composition"] = composition(rows, observations)
    return {"all_questions": performance(rows, observations), "routing": routing,
            "components": {p: performance([r for r in rows if r["query_ast"]["predicate"] == p], observations)
                           for p in ("N", "S")},
            "submitted_prediction_rows": len(predictions)}


def score_predictions(rows, predictions):
    """Score one or more model_id groups; omitted records remain missing."""
    by_model = defaultdict(list)
    for prediction in predictions:
        model = prediction.get("model_id", prediction.get("condition_id", "unspecified"))
        require(isinstance(model, str) and bool(model.strip()), "model_id must be a nonempty string")
        by_model[model].append(prediction)
    if not by_model:
        by_model["unspecified"] = []
    return {
        "scorer_version": "1.0.0", "analysis_status": "DESCRIPTIVE_OFFLINE_USER_PREDICTIONS",
        "rates_are_fractions": True, "confidence_intervals": None,
        "missingness_policy": "Nonbinary, absent and technical outputs are unavailable, never semantic NO. Overall success uses the full intended denominator.",
        "pairing": "Matched cells, representations and N/S/Y siblings remain in one family; contrasts use only usable pairs/triplets.",
        "models": {model: score_one(rows, values) for model, values in sorted(by_model.items())},
    }
