#!/usr/bin/env python3
"""Portable smoke tests for the benchmark scripts."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
VALIDATE = ROOT / "scripts" / "validate_cases.py"
SCORE = ROOT / "scripts" / "score_reviews.py"


class ScriptSmokeTests(unittest.TestCase):
    def test_validator_accepts_a_binary_same_size_case(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = root / "inputs"
            (inputs / "forms").mkdir(parents=True)
            (inputs / "masks").mkdir()
            Image.new("RGB", (64, 32), "white").save(inputs / "forms" / "form.png")
            mask = Image.new("L", (64, 32), 0)
            for x in range(10, 50):
                for y in range(8, 24):
                    mask.putpixel((x, y), 255)
            mask.save(inputs / "masks" / "field.png")
            manifest = root / "manifest.jsonl"
            manifest.write_text(
                json.dumps(
                    {
                        "id": "content-hangul-001",
                        "track": "content",
                        "field_type": "hangul",
                        "source_image": "forms/form.png",
                        "mask_image": "masks/field.png",
                        "text": "금융기관",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(VALIDATE), "--manifest", str(manifest), "--input-root", str(inputs)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("VALIDATION PASSED", result.stdout)

    def test_scorer_reports_high_risk_exact_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.jsonl"
            manifest.write_text(
                json.dumps(
                    {
                        "id": "content-amount-001",
                        "track": "content",
                        "field_type": "amount",
                        "source_image": "forms/unused.png",
                        "mask_image": "masks/unused.png",
                        "text": "USD 1,250,000.00",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            reviews = root / "reviews.csv"
            reviews.write_text(
                "case_id,seed,observed_text,rendered_text_ok,mask_coverage_ok,visual_quality_1_to_5,style_match_1_to_5\n"
                "content-amount-001,42,USD 1,250,000.00,yes,yes,4,\n",
                encoding="utf-8",
            )
            # Quote the comma-containing observed value as a real CSV reader expects.
            reviews.write_text(
                "case_id,seed,observed_text,rendered_text_ok,mask_coverage_ok,visual_quality_1_to_5,style_match_1_to_5\n"
                "content-amount-001,42,\"USD 1,250,000.00\",yes,yes,4,\n",
                encoding="utf-8",
            )
            output = root / "summary.json"
            result = subprocess.run(
                [sys.executable, str(SCORE), "--manifest", str(manifest), "--reviews", str(reviews), "--output", str(output)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(summary["exact_match_rate"], 1.0)
            self.assertEqual(summary["high_risk_exact_match_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
