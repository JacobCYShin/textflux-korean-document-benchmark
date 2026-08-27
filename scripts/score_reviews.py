#!/usr/bin/env python3
"""Score manually transcribed TextFlux outputs against a benchmark manifest."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


HIGH_RISK_TYPES = {"amount", "currency", "account", "swift", "date", "identifier"}


def load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        case = json.loads(line)
        case_id = case.get("id")
        if not isinstance(case_id, str) or not isinstance(case.get("text"), str):
            raise ValueError(f"manifest line {line_number}: id and text are required")
        if case_id in cases:
            raise ValueError(f"manifest line {line_number}: duplicate case id: {case_id}")
        cases[case_id] = case
    return cases


def levenshtein(left: str, right: str) -> int:
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for index, left_char in enumerate(left, start=1):
        current = [index]
        for other_index, right_char in enumerate(right, start=1):
            current.append(min(current[-1] + 1, previous[other_index] + 1, previous[other_index - 1] + (left_char != right_char)))
        previous = current
    return previous[-1]


def positive(value: str | None) -> bool:
    return (value or "").strip().lower() in {"yes", "y", "true", "1", "pass"}


def optional_score(value: str | None) -> float | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        score = float(value)
    except ValueError as exc:
        raise ValueError(f"invalid numeric score: {value!r}") from exc
    if not 1 <= score <= 5:
        raise ValueError(f"score must be in [1, 5]: {value!r}")
    return score


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        cases = load_manifest(args.manifest)
        with args.reviews.open("r", encoding="utf-8-sig", newline="") as review_file:
            rows = list(csv.DictReader(review_file))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    required_columns = {"case_id", "seed", "observed_text", "rendered_text_ok", "mask_coverage_ok"}
    if not rows:
        print("ERROR: reviews file contains no rows", file=sys.stderr)
        return 2
    if not required_columns.issubset(rows[0]):
        missing = required_columns.difference(rows[0])
        print(f"ERROR: reviews file is missing columns: {', '.join(sorted(missing))}", file=sys.stderr)
        return 2

    invalid_case_ids = sorted({row["case_id"] for row in rows if row["case_id"] not in cases})
    if invalid_case_ids:
        print(f"ERROR: unknown case IDs in reviews: {', '.join(invalid_case_ids)}", file=sys.stderr)
        return 2

    results: list[dict[str, Any]] = []
    total_edits = 0
    total_expected_characters = 0
    exact_matches = 0
    rendered_ok = 0
    mask_ok = 0
    high_risk_total = 0
    high_risk_exact = 0
    visual_scores: list[float] = []
    style_scores: list[float] = []

    for row in rows:
        case = cases[row["case_id"]]
        expected = case["text"]
        observed = row["observed_text"]
        edits = levenshtein(expected, observed)
        exact = expected == observed
        total_edits += edits
        total_expected_characters += len(expected)
        exact_matches += int(exact)
        rendered_ok += int(positive(row.get("rendered_text_ok")))
        mask_ok += int(positive(row.get("mask_coverage_ok")))

        visual_score = optional_score(row.get("visual_quality_1_to_5"))
        style_score = optional_score(row.get("style_match_1_to_5"))
        if visual_score is not None:
            visual_scores.append(visual_score)
        if style_score is not None:
            style_scores.append(style_score)

        high_risk = case.get("field_type") in HIGH_RISK_TYPES
        if high_risk:
            high_risk_total += 1
            high_risk_exact += int(exact)

        results.append(
            {
                "case_id": row["case_id"],
                "seed": row["seed"],
                "field_type": case.get("field_type"),
                "expected_text": expected,
                "observed_text": observed,
                "exact_match": exact,
                "edit_distance": edits,
                "rendered_text_ok": positive(row.get("rendered_text_ok")),
                "mask_coverage_ok": positive(row.get("mask_coverage_ok")),
                "visual_quality_1_to_5": visual_score,
                "style_match_1_to_5": style_score,
                "notes": row.get("notes", ""),
            }
        )

    count = len(results)
    summary = {
        "review_count": count,
        "exact_match_rate": exact_matches / count,
        "character_error_rate": total_edits / max(total_expected_characters, 1),
        "rendered_text_ok_rate": rendered_ok / count,
        "mask_coverage_ok_rate": mask_ok / count,
        "high_risk_exact_match_rate": (high_risk_exact / high_risk_total) if high_risk_total else None,
        "mean_visual_quality": (sum(visual_scores) / len(visual_scores)) if visual_scores else None,
        "mean_style_match": (sum(style_scores) / len(style_scores)) if style_scores else None,
        "results": results,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
