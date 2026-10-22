"""Local commands only. This package never reads API keys or sends requests."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from .data import load_rows, validate_rows
from .metrics import score_predictions

DEFAULT_DATA = Path("data/goldfishbench.jsonl.gz")


def write_json(value, path):
    text = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "score", "baseline"):
        sub = subparsers.add_parser(name)
        sub.add_argument("--data", type=Path, default=DEFAULT_DATA,
                         help="One released JSONL or JSONL.gz file; do not concatenate the duplicate domain shards.")
        sub.add_argument("--output", type=Path)
        if name == "score":
            sub.add_argument("--predictions", type=Path, required=True)
        elif name == "baseline":
            sub.add_argument("--kind", choices=("always_no", "always_yes", "symbolic_oracle"), required=True)
    args = parser.parse_args(argv)
    try:
        rows = load_rows(args.data)
        audit = validate_rows(rows)
        if args.command == "validate":
            audit["dataset_file_sha256"] = hashlib.sha256(args.data.read_bytes()).hexdigest()
            write_json(audit, args.output)
        elif args.command == "score":
            predictions = load_rows(args.predictions)
            score = score_predictions(rows, predictions)
            score["dataset_file_sha256"] = hashlib.sha256(args.data.read_bytes()).hexdigest()
            score["prediction_file_sha256"] = hashlib.sha256(args.predictions.read_bytes()).hexdigest()
            write_json(score, args.output)
        else:
            lines = []
            for row in rows:
                truth = (row["query_truth_gold"] if args.kind == "symbolic_oracle"
                         else args.kind == "always_yes")
                meaning = "YES" if truth else "NO"
                label = next(k for k, v in row["option_mapping"].items() if v == meaning)
                lines.append(json.dumps({"item_id": row["item_id"], "answer": label,
                                         "model_id": args.kind}, ensure_ascii=False))
            text = "\n".join(lines) + "\n"
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(text, encoding="utf-8")
            else:
                print(text, end="")
        return 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(f"goldfishbench: {error}", file=sys.stderr)
        return 2
