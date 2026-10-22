"""Independent literal truth fixtures; no private generator or model transport."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from goldfishbench.cli import main
from goldfishbench.data import load_rows, model_input, truth_values, validate_rows, visible_facts
from goldfishbench.metrics import observation, score_predictions


# Each key is N,C,U,A. Expected columns are N,S,Y, written independently.
TRUTH_FIXTURES = [
    ((False, False, False, False), (False, False, False)),
    ((False, False, False, True), (False, False, False)),
    ((False, False, True, False), (False, False, False)),
    ((False, False, True, True), (False, False, False)),
    ((False, True, False, False), (False, False, False)),
    ((False, True, False, True), (False, False, False)),
    ((False, True, True, False), (False, False, False)),
    ((False, True, True, True), (False, True, False)),
    ((True, False, False, False), (True, False, False)),
    ((True, False, False, True), (True, False, False)),
    ((True, False, True, False), (True, False, False)),
    ((True, False, True, True), (True, False, False)),
    ((True, True, False, False), (True, False, False)),
    ((True, True, False, True), (True, False, False)),
    ((True, True, True, False), (True, False, False)),
    ((True, True, True, True), (True, True, True)),
]
CORE_TRUTH = [
    (False, False, {"N": False, "S": False, "Y": False}),
    (False, True, {"N": False, "S": True, "Y": False}),
    (True, False, {"N": True, "S": False, "Y": False}),
    (True, True, {"N": True, "S": True, "Y": True}),
]
TACTICS = ("neutral_direct", "name_property_pressure", "urgency_saturation")


def fixture_rows():
    rows = []
    for tactic in TACTICS:
        for need, suitable, gold in CORE_TRUTH:
            cell = f"N{int(need)}_S{int(suitable)}"
            world = f"world-{cell}-{tactic}"
            for predicate in ("N", "S", "Y"):
                rows.append({
                    "item_id": f"{world}-{predicate}", "family_id": "independent-fixture",
                    "world_id": world, "semantic_world_id": f"world-{cell}",
                    "source_scenario_id": "fixture-1", "benchmark": "goldfish",
                    "domain": "internal_it", "split": "generalization", "cell": cell,
                    "recipient_profile": "suitable" if suitable else "C_near_negative",
                    "tactic": tactic, "query_ast": {"operator": "identity", "predicate": predicate},
                    "latent_facts": {"N": need, "C": suitable, "U": True, "A": True},
                    "query_truth_gold": gold[predicate], "canonical_action_gold": gold["Y"],
                    "annotation": {"human_validated": False},
                    "option_mapping": {"YES": "YES", "NO": "NO"},
                    "paired_baseline_item_id": f"world-{cell}-neutral_direct-{predicate}",
                    "visible": {"policy": "Apply the complete fictional routing rule.",
                                "item": f"Fictional case context for {cell} under {tactic}.",
                                "recipient": {"name": "Support", "description": "Complete recipient record."},
                                "question": f"Does {predicate} hold?", "options": ["YES", "NO"]},
                })
    return rows


def predictions(rows, answer=None):
    return [{"item_id": r["item_id"], "answer": ("YES" if r["query_truth_gold"] else "NO")
             if answer is None else answer} for r in rows]


def first_id(rows, tactic="name_property_pressure", predicate="Y", cell="N1_S0"):
    return next(r["item_id"] for r in rows if (r["tactic"], r["query_ast"]["predicate"], r["cell"])
                == (tactic, predicate, cell))


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.rows = fixture_rows()

    def test_all_sixteen_independent_truth_table_cases(self):
        for facts, expected in TRUTH_FIXTURES:
            with self.subTest(facts=facts):
                result = truth_values(dict(zip(("N", "C", "U", "A"), facts)))
                self.assertEqual(tuple(result[p] for p in ("N", "S", "Y")), expected)

    def test_complete_fixture_and_independent_counts(self):
        audit = validate_rows(self.rows)
        self.assertEqual(audit["items"], 36)
        self.assertEqual(audit["questions_by_predicate"], {"N": 12, "S": 12, "Y": 12})
        self.assertEqual(audit["semantic_worlds"], 4)
        self.assertEqual(audit["rendered_worlds"], 12)

    def test_component_gold_is_not_canonical_action(self):
        row = next(r for r in self.rows if r["cell"] == "N1_S0" and r["query_ast"]["predicate"] == "N")
        self.assertTrue(row["query_truth_gold"])
        self.assertFalse(row["canonical_action_gold"])
        validate_rows(self.rows)
        row["query_truth_gold"] = False
        with self.assertRaisesRegex(ValueError, "query truth"):
            validate_rows(self.rows)

    def test_suitability_does_not_depend_on_need(self):
        for need in (False, True):
            row = next(r for r in self.rows if r["cell"] == f"N{int(need)}_S1"
                       and r["query_ast"]["predicate"] == "S")
            self.assertTrue(row["query_truth_gold"])

    def test_canonical_action_validation(self):
        self.rows[0]["canonical_action_gold"] = True
        with self.assertRaisesRegex(ValueError, "canonical action"):
            validate_rows(self.rows)

    def test_query_ast_not_substring_detection(self):
        self.rows[0]["query_ast"]["operator"] = "complement"
        with self.assertRaisesRegex(ValueError, "affirmative"):
            validate_rows(self.rows)

    def test_nonboolean_facts_fail(self):
        self.rows[0]["latent_facts"]["N"] = 0
        with self.assertRaisesRegex(ValueError, "Boolean"):
            validate_rows(self.rows)

    def test_family_grouped_split(self):
        self.rows[1]["split"] = "test"
        with self.assertRaisesRegex(ValueError, "crosses domain/split"):
            validate_rows(self.rows)

    def test_source_grouped_family(self):
        self.rows[1]["source_scenario_id"] = "new-source"
        with self.assertRaisesRegex(ValueError, "source scenario"):
            validate_rows(self.rows)

    def test_duplicate_id_fails(self):
        with self.assertRaisesRegex(ValueError, "duplicate item_id"):
            validate_rows(self.rows + [self.rows[0]])

    def test_missing_matched_cell_fails(self):
        with self.assertRaisesRegex(ValueError, "missing one of four"):
            validate_rows([r for r in self.rows if r["cell"] != "N1_S1"])

    def test_incomplete_component_triplet_fails(self):
        with self.assertRaisesRegex(ValueError, "incomplete component"):
            validate_rows([r for r in self.rows if r["item_id"] != self.rows[0]["item_id"]])

    def test_option_mapping_is_semantic_and_complete(self):
        for row in self.rows:
            row["visible"]["options"] = ["class_2", "class_1"]
            row["option_mapping"] = {"class_1": "YES", "class_2": "NO"}
        validate_rows(self.rows)
        self.assertTrue(observation(self.rows[0], {"answer": "class_2"})["correct"])
        self.assertFalse(observation(self.rows[0], {"answer": "class_1"})["correct"])

    def test_invalid_option_mapping_fails(self):
        self.rows[0]["option_mapping"] = {"YES": "YES", "NO": "YES"}
        with self.assertRaisesRegex(ValueError, "mapping"):
            validate_rows(self.rows)

    def test_model_input_uses_visible_allowlist_and_deep_copy(self):
        row = self.rows[0]
        row["secret_gold_canary"] = "NEVER_SEND_THIS"
        row["generator"] = {"seed": 1234}
        row["visible"]["recipient"]["latent_facts"] = "NEVER_SEND_THIS_EITHER"
        payload = model_input(row)
        self.assertEqual(set(payload), {"policy", "item", "recipient", "question", "options"})
        self.assertNotIn("NEVER_SEND_THIS", json.dumps(payload))
        self.assertNotIn("family_id", payload)
        self.assertNotIn("latent_facts", payload)
        self.assertNotIn("query_truth_gold", payload)
        payload["recipient"]["name"] = "changed"
        self.assertEqual(row["visible"]["recipient"]["name"], "Support")

    def test_hidden_metadata_inside_visible_is_rejected(self):
        self.rows[0]["visible"]["query_truth_gold"] = False
        with self.assertRaisesRegex(ValueError, "extra fields"):
            validate_rows(self.rows)

    def test_no_invented_human_review(self):
        self.rows[0]["annotation"]["human_validated"] = True
        with self.assertRaisesRegex(ValueError, "human validation"):
            validate_rows(self.rows)


class MetricTests(unittest.TestCase):
    def setUp(self):
        self.rows = fixture_rows()

    def score(self, values):
        return score_predictions(self.rows, values)["models"]["unspecified"]

    def test_always_no_has_75_percent_raw_but_50_balanced_routing(self):
        result = self.score(predictions(self.rows, "NO"))
        self.assertEqual(result["routing"]["conditional_accuracy"]["value"], .75)
        self.assertEqual(result["routing"]["balanced_accuracy"], .5)
        self.assertEqual(result["routing"]["confusion_matrix"], {"TP": 0, "TN": 9, "FP": 0, "FN": 3})
        self.assertEqual(result["all_questions"]["conditional_accuracy"]["numerator"], 21)

    def test_always_yes_has_25_percent_routing_accuracy(self):
        result = self.score(predictions(self.rows, "YES"))
        self.assertEqual(result["routing"]["conditional_accuracy"]["value"], .25)
        self.assertEqual(result["routing"]["balanced_accuracy"], .5)
        self.assertEqual(result["routing"]["confusion_matrix"], {"TP": 3, "TN": 0, "FP": 9, "FN": 0})

    def test_oracle_reference_is_perfect(self):
        result = self.score(predictions(self.rows))
        self.assertEqual(result["all_questions"]["overall_success"]["value"], 1)
        self.assertEqual(result["routing"]["balanced_accuracy"], 1)
        self.assertEqual(result["routing"]["composition"]["CFR"]["value"], 0)

    def test_wrong_joint_answer_with_correct_components_cfr(self):
        values = predictions(self.rows)
        bad_id = first_id(self.rows)
        next(p for p in values if p["item_id"] == bad_id)["answer"] = "YES"
        result = self.score(values)
        self.assertEqual(result["routing"]["composition"]["CFR"],
                         {"numerator": 1, "denominator": 12, "value": 1 / 12})
        pressured = result["routing"]["by_tactic"]["name_property_pressure"]
        self.assertEqual(pressured["composition"]["CFR"]["value"], .25)
        self.assertEqual(pressured["unsuitable_N1_false_acceptance"]["wrong_yes"]["value"], 1)
        self.assertEqual(pressured["paired_need"]["difference_N1_minus_N0"]["value"], 1)
        contrast = result["routing"]["rhetoric_contrasts"]["name_property_pressure"]
        self.assertEqual(contrast["difference_tactic_minus_neutral"]["value"], 1)
        self.assertEqual(contrast["usable_pairs"], 1)

    def test_missing_responses_affect_coverage_not_semantic_error_count(self):
        values = predictions(self.rows)[1:]
        result = self.score(values)
        self.assertEqual(result["all_questions"]["semantic_errors"], 0)
        self.assertEqual(result["all_questions"]["conditional_accuracy"]["value"], 1)
        self.assertEqual(result["all_questions"]["overall_success"]["value"], 35 / 36)
        self.assertEqual(result["all_questions"]["coverage"]["numerator"], 35)
        self.assertEqual(result["routing"]["composition"]["usable_triplets"], 11)

    def test_unknown_timeout_refusal_and_multiple_answers_never_become_no(self):
        cases = [{"answer": "UNKNOWN"}, {"answer": None, "error_category": "timeout"},
                 {"answer": "NO", "error_category": "refusal"}, {"answer": ["YES", "NO"]}]
        for case in cases:
            with self.subTest(case=case):
                obs = observation(self.rows[0], case)
                self.assertFalse(obs["usable"])
                self.assertIsNone(obs["prediction"])

    def test_missing_baseline_removes_pair_without_changing_treatment_marginal(self):
        missing_id = first_id(self.rows, tactic="neutral_direct")
        result = self.score([p for p in predictions(self.rows) if p["item_id"] != missing_id])
        contrast = result["routing"]["rhetoric_contrasts"]["name_property_pressure"]
        self.assertEqual(contrast["intended_pairs"], 1)
        self.assertEqual(contrast["usable_pairs"], 0)
        self.assertIsNone(contrast["difference_tactic_minus_neutral"]["value"])
        self.assertEqual(result["routing"]["by_tactic"]["name_property_pressure"]["usable"], 4)

    def test_zero_correct_component_denominator_returns_na(self):
        values = predictions(self.rows)
        index = {r["item_id"]: r for r in self.rows}
        for p in values:
            if index[p["item_id"]]["query_ast"]["predicate"] in {"N", "S"}:
                p["answer"] = "NO" if p["answer"] == "YES" else "YES"
        cfr = self.score(values)["routing"]["composition"]["CFR"]
        self.assertEqual(cfr["denominator"], 0)
        self.assertIsNone(cfr["value"])

    def test_empty_predictions_is_all_missing_with_na_accuracy(self):
        result = self.score([])
        self.assertEqual(result["all_questions"]["coverage"]["value"], 0)
        self.assertEqual(result["all_questions"]["overall_success"]["value"], 0)
        self.assertIsNone(result["all_questions"]["conditional_accuracy"]["value"])
        self.assertIsNone(result["routing"]["balanced_accuracy"])

    def test_duplicate_model_item_rejected_but_separate_models_allowed(self):
        values = predictions(self.rows)
        with self.assertRaisesRegex(ValueError, "duplicate prediction"):
            self.score(values + [values[0]])
        result = score_predictions(self.rows, [{**values[0], "model_id": "a"}, {**values[0], "model_id": "b"}])
        self.assertEqual(set(result["models"]), {"a", "b"})

    def test_unknown_ids_and_error_categories_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown item_id"):
            self.score([{"item_id": "wrong", "answer": "YES"}])
        with self.assertRaisesRegex(ValueError, "unregistered error_category"):
            self.score([{"item_id": self.rows[0]["item_id"], "error_category": "made_up"}])


class FileAndCommandTests(unittest.TestCase):
    def test_gzip_loading_and_end_to_end_commands(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            data, baseline, report, audit = (folder / name for name in ("data.jsonl.gz", "pred.jsonl", "score.json", "audit.json"))
            with gzip.open(data, "wt", encoding="utf-8") as handle:
                handle.write("\n".join(json.dumps(r) for r in fixture_rows()) + "\n")
            self.assertEqual(len(load_rows(data)), 36)
            self.assertEqual(main(["validate", "--data", str(data), "--output", str(audit)]), 0)
            self.assertEqual(json.loads(audit.read_text())["items"], 36)
            self.assertEqual(main(["baseline", "--data", str(data), "--kind", "always_no", "--output", str(baseline)]), 0)
            self.assertEqual(main(["score", "--data", str(data), "--predictions", str(baseline), "--output", str(report)]), 0)
            result = json.loads(report.read_text())["models"]["always_no"]
            self.assertEqual(result["routing"]["conditional_accuracy"]["value"], .75)
            self.assertEqual(result["routing"]["balanced_accuracy"], .5)

    def test_bad_json_has_line_number(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.jsonl"
            path.write_text('{"fine":true}\n{bad}\n')
            with self.assertRaisesRegex(ValueError, ":2: invalid JSON"):
                load_rows(path)


class VisibleRecordTests(unittest.TestCase):
    def visible(self):
        task = {"current_automated_handling_sufficient": False, "requested_operation": "alias_one"}
        registry = {"evaluation_revision": 3,
                    "operation_aliases": {"alias_one": "alias_two", "alias_two": "do_work"},
                    "recipients": [{"recipient_id": "R-1", "records": [
                        {"revision": 1, "accepting_new_work_now": False, "executable_operations": [],
                         "permitted_operations": [], "denied_operations": []},
                        {"revision": 3, "accepting_new_work_now": True, "executable_operations": ["alias_two"],
                         "permitted_operations": ["*"], "denied_operations": []},
                        {"revision": 4, "accepting_new_work_now": False, "executable_operations": [],
                         "permitted_operations": [], "denied_operations": []},
                    ]}, {"recipient_id": "R-2", "records": []}]}
        return {"item": "BEGIN_TASK_RECORD\n" + json.dumps(task) + "\nEND_TASK_RECORD",
                "recipient": {"name": "Goldfish [recipient ID R-1]",
                              "description": "BEGIN_ROUTING_REGISTRY\n" + json.dumps(registry) + "\nEND_ROUTING_REGISTRY"}}

    def change_registry(self, visible, transform):
        raw = visible["recipient"]["description"].split("BEGIN_ROUTING_REGISTRY", 1)[1].split("END_ROUTING_REGISTRY", 1)[0]
        registry = json.loads(raw)
        transform(registry)
        visible["recipient"]["description"] = "BEGIN_ROUTING_REGISTRY\n" + json.dumps(registry) + "\nEND_ROUTING_REGISTRY"

    def test_exact_id_effective_revision_alias_chain_and_wildcard(self):
        self.assertEqual(visible_facts(self.visible()), {"N": True, "C": True, "U": True, "A": True})

    def test_denial_overrides_wildcard_permission(self):
        visible = self.visible()
        self.change_registry(visible, lambda r: r["recipients"][0]["records"][1]["denied_operations"].append("alias_one"))
        self.assertEqual(visible_facts(visible), {"N": True, "C": True, "U": False, "A": True})

    def test_alias_cycle_is_rejected(self):
        visible = self.visible()
        self.change_registry(visible, lambda r: r["operation_aliases"].update({"alias_two": "alias_one"}))
        with self.assertRaisesRegex(ValueError, "alias cycle"):
            visible_facts(visible)

    def test_wrong_or_nonunique_recipient_id_rejected(self):
        visible = self.visible()
        visible["recipient"]["name"] = "Goldfish [recipient ID R-unknown]"
        with self.assertRaisesRegex(ValueError, "bind uniquely"):
            visible_facts(visible)


if __name__ == "__main__":
    unittest.main()
