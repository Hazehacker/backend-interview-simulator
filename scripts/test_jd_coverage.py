#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUBRIC = ROOT / "references" / "common-evaluation-rubric.md"


class JdCoverageGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = RUBRIC.read_text(encoding="utf-8")

    def test_coverage_formula_and_threshold_are_explicit(self) -> None:
        self.assertIn(
            "JD 覆盖率 = 已验证 JD 要求数 ÷ 可评估 JD 要求总数", self.text
        )
        self.assertIn("80%", self.text)

    def test_low_coverage_suppresses_numeric_rating(self) -> None:
        self.assertIn("JD 覆盖率低于 80%", self.text)
        self.assertIn("不得输出整体星级或 `X/5`", self.text)
        self.assertIn("证据不足 / 待验证", self.text)

    def test_unverified_must_have_suppresses_numeric_rating(self) -> None:
        self.assertIn("任何 must-have 仍未验证", self.text)
        self.assertIn("不得输出整体星级或 `X/5`", self.text)

    def test_five_of_five_requires_coverage_and_evidence(self) -> None:
        self.assertIn("5/5", self.text)
        self.assertIn("JD 覆盖率达到 90%", self.text)
        self.assertIn("不得把少量强回答归一化为“高度匹配”", self.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
