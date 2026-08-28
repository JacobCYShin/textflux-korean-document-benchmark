#!/usr/bin/env python3
"""Validate a private TextFlux Korean-document benchmark manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from PIL import Image


ALLOWED_TRACKS = {"content", "style"}
ALLOWED_FIELD_TYPES = {
    "hangul",
    "amount",
    "currency",
    "account",
    "swift",
    "date",
    "identifier",
    "mixed",
}
REQUIRED_KEYS = {"id", "track", "field_type", "source_image", "mask_image", "text"}
CASE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,79}$")


def parse_manifest(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    seen: set[str] = set()

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(case, dict):
            raise ValueError(f"line {line_number}: every entry must be a JSON object")
        missing = REQUIRED_KEYS.difference(case)
        if missing:
            raise ValueError(f"line {line_number}: missing keys: {', '.join(sorted(missing))}")
        case_id = case["id"]
        if not isinstance(case_id, str) or not CASE_ID_RE.fullmatch(case_id):
            raise ValueError(f"line {line_number}: invalid case id: {case_id!r}")
        if case_id in seen:
            raise ValueError(f"line {line_number}: duplicate case id: {case_id}")
        seen.add(case_id)
        cases.append(case)

    if not cases:
        raise ValueError("manifest contains no cases")
    return cases


def resolve_private_path(input_root: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label}: must be a non-empty relative path")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{label}: must stay inside INPUT_ROOT")
    resolved_root = input_root.resolve()
    resolved = (resolved_root / relative).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"{label}: resolves outside INPUT_ROOT") from exc
    return resolved


def check_image(path: Path, label: str) -> tuple[int, int]:
    if not path.is_file():
        raise ValueError(f"{label}: file not found: {path}")
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            return image.size
    except Exception as exc:  # Pillow raises format-specific errors.
        raise ValueError(f"{label}: cannot read image {path}: {exc}") from exc


def check_mask(path: Path, expected_size: tuple[int, int]) -> None:
    actual_size = check_image(path, "mask_image")
    if actual_size != expected_size:
        raise ValueError(
            f"mask_image: dimensions {actual_size[0]}x{actual_size[1]} "
            f"do not match source {expected_size[0]}x{expected_size[1]}"
        )

    with Image.open(path) as image:
        grayscale = image.convert("L")
        values = grayscale.get_flattened_data()
        total = grayscale.width * grayscale.height
        white = 0
        non_binary = 0
        for value in values:
            if value == 255:
                white += 1
            if value not in (0, 255):
                non_binary += 1

    if white == 0:
        raise ValueError("mask_image: has no editable (white) pixels")
    if white == total:
        raise ValueError("mask_image: covers the full source image")
    non_binary_ratio = non_binary / total
    if non_binary_ratio > 0.01:
        raise ValueError(
            f"mask_image: {non_binary_ratio:.2%} of pixels are not 0 or 255; "
            "use a binary mask"
        )


def validate_case(case: dict[str, Any], input_root: Path, allow_multiline: bool) -> None:
    case_id = case["id"]
    track = case["track"]
    field_type = case["field_type"]
    text = case["text"]

    if track not in ALLOWED_TRACKS:
        raise ValueError(f"{case_id}: track must be one of {sorted(ALLOWED_TRACKS)}")
    if field_type not in ALLOWED_FIELD_TYPES:
        raise ValueError(f"{case_id}: unsupported field_type: {field_type!r}")
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"{case_id}: text must be non-empty")
    if not allow_multiline and ("\n" in text or "\r" in text):
        raise ValueError(f"{case_id}: multiline text is not allowed in the single-line baseline")

    source_path = resolve_private_path(input_root, case["source_image"], f"{case_id}.source_image")
    mask_path = resolve_private_path(input_root, case["mask_image"], f"{case_id}.mask_image")
    source_size = check_image(source_path, "source_image")
    check_mask(mask_path, source_size)

    style_reference = case.get("style_reference")
    if track == "style" and not style_reference:
        raise ValueError(f"{case_id}: style cases require style_reference metadata")
    if style_reference is not None:
        check_image(resolve_private_path(input_root, style_reference, f"{case_id}.style_reference"), "style_reference")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--allow-multiline", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    try:
        cases = parse_manifest(args.manifest)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    input_root = args.input_root.resolve()
    if not input_root.is_dir():
        print(f"ERROR: INPUT_ROOT does not exist: {input_root}", file=sys.stderr)
        return 2

    for case in cases:
        try:
            validate_case(case, input_root, args.allow_multiline)
            print(f"OK    {case['id']}")
        except ValueError as exc:
            errors.append(str(exc))
            print(f"ERROR {exc}", file=sys.stderr)

    if errors:
        print(f"VALIDATION FAILED: {len(errors)} error(s), {len(cases)} case(s) checked", file=sys.stderr)
        return 1

    print(f"VALIDATION PASSED: {len(cases)} case(s) checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
