"""Evaluate synthetic extraction cases offline by default; opt-in paid AI with --ai."""

import argparse
import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.m2.triage import extract_report


async def main(ai=False):
    cases = [
        json.loads(line)
        for line in (ROOT / "data/evaluation/synthetic_triage.jsonl")
        .read_text()
        .splitlines()
    ]
    correct = 0
    failures = []
    by_language = {}
    fields = {}
    for case in cases:
        result = await extract_report(case["text"], case["language"], use_ai=ai)
        errors = {
            key: {"expected": expected, "actual": result.get(key)}
            for key, expected in case["expected"].items()
            if result.get(key) != expected
        }
        correct += not errors
        bucket = by_language.setdefault(case["language"], {"cases": 0, "correct": 0})
        bucket["cases"] += 1
        bucket["correct"] += not errors
        for key, expected in case["expected"].items():
            count = fields.setdefault(key, {"cases": 0, "correct": 0})
            count["cases"] += 1
            count["correct"] += result.get(key) == expected
        if errors:
            failures.append({"id": case["id"], "errors": errors})
    summary = {
        "dataset": "synthetic template suite; not real-world validation",
        "cases": len(cases),
        "exact_match_cases": correct,
        "exact_match_rate": correct / len(cases),
        "by_language": by_language,
        "by_field": fields,
        "failures": failures,
        "mode": "ai_requested" if ai else "offline_rules",
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return bool(failures)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ai",
        action="store_true",
        help="Opt in to external OpenAI requests and usage costs.",
    )
    raise SystemExit(asyncio.run(main(parser.parse_args().ai)))
