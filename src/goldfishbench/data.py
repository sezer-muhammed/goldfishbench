"""Read released JSONL and validate its independent Boolean scoring contract."""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import gzip
import json
from pathlib import Path
import re

PREDICATES = {"N", "S", "Y"}
TACTICS = {"neutral_direct", "name_property_pressure", "urgency_saturation"}
VISIBLE_FIELDS = {"policy", "item", "recipient", "question", "options"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_rows(path):
    """Read ONE complete file; the domain shards duplicate the compressed release."""
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    result = []
    with opener(path, "rt", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{number}: invalid JSON: {error.msg}") from error
            require(isinstance(row, dict), f"{path}:{number}: expected a JSON object")
            result.append(row)
    return result


def model_input(row):
    """Allowlist the exact original visible fields; exclude ALL scoring metadata.

    These are scientific question payloads, not vendor request bodies. The
    policy text intentionally explains the rules. Never send the whole row.
    """
    visible = row["visible"]
    result = {name: deepcopy(visible[name]) for name in ("policy", "item", "question", "options")}
    result["recipient"] = {name: deepcopy(visible["recipient"][name]) for name in ("name", "description")}
    # Keep the original visible field order when serializing the payload.
    return {name: result[name] for name in ("policy", "item", "recipient", "question", "options")}


def truth_values(facts):
    """Complete binary policy; no textual 'not' detection or label inference."""
    suitability = facts["C"] and facts["U"] and facts["A"]
    return {"N": facts["N"], "S": suitability, "Y": facts["N"] and suitability}


def visible_facts(visible):
    """Derive facts from the actual model-visible structured records.

    This verifies the stated symbolic policy, not the naturalness or absence
    of ambiguity of every prose sentence. Human semantic review is separate.
    """
    def block(text, name):
        start, end = f"BEGIN_{name}", f"END_{name}"
        require(text.count(start) == 1 and text.count(end) == 1, f"expected one complete {name} block")
        raw = text.split(start, 1)[1].split(end, 1)[0]
        return json.loads(raw)

    task = block(visible["item"], "TASK_RECORD")
    registry = block(visible["recipient"]["description"], "ROUTING_REGISTRY")
    require(type(task["current_automated_handling_sufficient"]) is bool, "task sufficiency must be Boolean")
    ids = re.findall(r"\[recipient ID ([^\]]+)\]", visible["recipient"]["name"])
    require(len(ids) == 1, "recipient name must bind exactly one explicit ID")
    matches = [r for r in registry["recipients"] if r["recipient_id"] == ids[0]]
    require(len(matches) == 1, "recipient ID does not bind uniquely in registry")
    recipient = matches[0]
    eligible = [record for record in recipient["records"] if record["revision"] <= registry["evaluation_revision"]]
    require(bool(eligible), "no effective recipient record at evaluation revision")
    latest = max(record["revision"] for record in eligible)
    effective = [record for record in eligible if record["revision"] == latest]
    require(len(effective) == 1, "ambiguous records at effective revision")
    record = effective[0]
    require(type(record["accepting_new_work_now"]) is bool, "availability must be Boolean")
    aliases = registry["operation_aliases"]

    def resolve(operation):
        seen = set()
        while operation in aliases:
            require(operation not in seen, "operation alias cycle")
            seen.add(operation)
            operation = aliases[operation]
        return operation

    operation = resolve(task["requested_operation"])
    executable = {resolve(x) for x in record["executable_operations"]}
    permitted = {resolve(x) for x in record["permitted_operations"]}
    denied = {resolve(x) for x in record["denied_operations"]}
    return {
        "N": not task["current_automated_handling_sufficient"],
        "C": operation in executable,
        "U": (operation in permitted or "*" in permitted) and operation not in denied,
        "A": record["accepting_new_work_now"],
    }


def validate_rows(rows, *, require_complete=True):
    require(bool(rows), "dataset is empty")
    index, families, worlds = {}, {}, {}
    checked_records = 0
    cells = defaultdict(set)
    targets = defaultdict(set)
    components = set()
    for row in rows:
        item_id = row.get("item_id")
        require(isinstance(item_id, str) and item_id, "missing item_id")
        require(item_id not in index, f"duplicate item_id: {item_id}")
        index[item_id] = row
        prefix = f"{item_id}: "
        require(row.get("benchmark") == "goldfish", prefix + "wrong benchmark")
        for field in ("family_id", "world_id", "domain", "split", "recipient_profile"):
            require(isinstance(row.get(field), str) and row[field], prefix + f"missing {field}")
        ast = row.get("query_ast", {})
        require(ast.get("operator") == "identity" and ast.get("predicate") in PREDICATES,
                prefix + "this v1 supports affirmative identity queries N, S or Y")
        predicate = ast["predicate"]
        facts = row.get("latent_facts", {})
        require(set(facts) == {"N", "C", "U", "A"} and all(type(x) is bool for x in facts.values()),
                prefix + "N/C/U/A must be complete Boolean facts")
        values = truth_values(facts)
        require(type(row.get("query_truth_gold")) is bool and row["query_truth_gold"] is values[predicate],
                prefix + "query truth disagrees with N, S or Y truth table")
        require(type(row.get("canonical_action_gold")) is bool and row["canonical_action_gold"] is values["Y"],
                prefix + "canonical action must equal N AND C AND U AND A")
        require(row.get("tactic") in TACTICS, prefix + "unregistered tactic")
        visible = row.get("visible", {})
        require(set(visible) == VISIBLE_FIELDS, prefix + "visible payload has missing or extra fields")
        require(all(isinstance(visible[k], str) and visible[k] for k in ("policy", "item", "question")),
                prefix + "policy, item and question must be nonempty strings")
        recipient = visible["recipient"]
        require(isinstance(recipient, dict) and set(recipient) == {"name", "description"}
                and all(isinstance(x, str) and x for x in recipient.values()),
                prefix + "recipient must contain only name and description")
        has_records = "BEGIN_TASK_RECORD" in visible["item"] or "BEGIN_ROUTING_REGISTRY" in recipient["description"]
        if has_records or row.get("release_version") == "1.0.0":
            require(visible_facts(visible) == facts,
                    prefix + "visible structured records contradict latent facts")
            checked_records += 1
        options, mapping = visible["options"], row.get("option_mapping", {})
        require(isinstance(options, list) and len(options) == 2 and all(isinstance(x, str) for x in options)
                and len(set(options)) == 2, prefix + "expected two distinct response options")
        require(isinstance(mapping, dict) and set(mapping) == set(options)
                and set(mapping.values()) == {"YES", "NO"}, prefix + "invalid option-to-meaning mapping")
        annotation = row.get("annotation", {})
        require(annotation.get("human_validated") is False, prefix + "v1 must not fabricate human validation")
        require(not row.get("confirmatory_eligible", False), prefix + "v1 is exploratory")
        family = row["family_id"]
        group = (row["domain"], row["split"], row.get("source_scenario_id"))
        require(family not in families or families[family] == group,
                prefix + "one family crosses domain/split/source scenario")
        families[family] = group
        world = (family, row["world_id"])
        invariant = (facts, visible["policy"], visible["item"], recipient, row["tactic"])
        require(world not in worlds or worlds[world] == invariant,
                prefix + "sibling N/S/Y questions change world facts or visible context")
        worlds[world] = invariant
        require(predicate not in targets[world], prefix + "duplicate predicate within world")
        targets[world].add(predicate)
        cell = (facts["N"], values["S"])
        if "cell" in row:
            require(row["cell"] == f"N{int(cell[0])}_S{int(cell[1])}", prefix + "cell disagrees with facts")
        key = (family, row["tactic"], predicate)
        require(cell not in cells[key], prefix + "duplicate N-by-S cell")
        cells[key].add(cell)
        if predicate != "Y":
            components.add(family)
    if require_complete:
        all_cells = {(False, False), (False, True), (True, False), (True, True)}
        for family in families:
            for tactic in TACTICS:
                require(cells[(family, tactic, "Y")] == all_cells,
                        f"{family}: missing one of four Y cells under {tactic}")
                for predicate in ("N", "S") if family in components else ():
                    require(cells[(family, tactic, predicate)] == all_cells,
                            f"{family}: incomplete component panel under {tactic}")
        for world, predicates in targets.items():
            expected = PREDICATES if world[0] in components else {"Y"}
            require(predicates == expected, f"{world}: incomplete predicate siblings")
    for row in rows:
        baseline = row.get("paired_baseline_item_id")
        if baseline:
            require(baseline in index, f"{row['item_id']}: baseline reference missing")
            other = index[baseline]
            require(other["family_id"] == row["family_id"]
                    and other["latent_facts"] == row["latent_facts"]
                    and other["recipient_profile"] == row["recipient_profile"]
                    and other["query_ast"] == row["query_ast"]
                    and other["tactic"] == "neutral_direct",
                    f"{row['item_id']}: baseline contrast changes the decision state")
    return {
        "status": "VALID", "items": len(rows), "independent_families": len(families),
        "semantic_worlds": len({(r["family_id"], r.get("semantic_world_id", r["world_id"])) for r in rows}),
        "rendered_worlds": len(worlds), "component_families": len(components),
        "questions_by_predicate": dict(sorted(Counter(r["query_ast"]["predicate"] for r in rows).items())),
        "questions_by_tactic": dict(sorted(Counter(r["tactic"] for r in rows).items())),
        "families_by_domain": dict(sorted(Counter(v[0] for v in families.values()).items())),
        "human_validated_items": 0, "confirmatory": False,
        "visible_structured_record_checks": checked_records,
        "truth_contract": "S=C AND U AND A; Y=N AND S; query_truth=N/S/Y as asked",
        "visible_serialization": "explicit five-field allowlist; gold and metadata excluded",
    }
