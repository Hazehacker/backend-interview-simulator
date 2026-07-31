#!/usr/bin/env python3
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import validate_skill


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ValidateSkillMutationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        for name in ("SKILL.md", "README.md", "LICENSE", ".gitignore"):
            shutil.copy2(PROJECT_ROOT / name, self.root / name)
        shutil.copytree(PROJECT_ROOT / "references", self.root / "references")
        self.original_root = validate_skill.ROOT
        validate_skill.ROOT = self.root

    def tearDown(self) -> None:
        validate_skill.ROOT = self.original_root
        self.temp_dir.cleanup()

    def assert_rejected(self, expected_fragment: str) -> None:
        errors = validate_skill.validate()
        self.assertTrue(
            any(expected_fragment in error for error in errors),
            f"expected error containing {expected_fragment!r}, got {errors!r}",
        )

    def mutate_skill(self, old: str, new: str) -> None:
        path = self.root / "SKILL.md"
        content = path.read_text(encoding="utf-8")
        self.assertIn(old, content)
        path.write_text(content.replace(old, new, 1), encoding="utf-8")

    def test_baseline_passes(self) -> None:
        self.assertEqual([], validate_skill.validate())

    def test_extra_fourteenth_reference_fails(self) -> None:
        (self.root / "references" / "extra.md").write_text(
            "# Extra\n", encoding="utf-8"
        )
        self.assert_rejected("unexpected reference")

    def test_nested_reference_fails(self) -> None:
        nested = self.root / "references" / "nested"
        nested.mkdir()
        (nested / "extra.md").write_text(
            "# Nested\n"
            "https://github.com/2637309949/go-interview\n",
            encoding="utf-8",
        )
        self.assert_rejected("nested reference not allowed")
        self.assert_rejected("external source content embedded")

    def test_missing_reference_fails(self) -> None:
        (self.root / "references" / "go-coding-challenges.md").unlink()
        self.assert_rejected("missing file: references/go-coding-challenges.md")

    def test_single_language_preload_all_rule_fails(self) -> None:
        self.mutate_skill(
            "- 单语言只加载实际主语言所需文件，不预读另外两门语言。",
            "- 单语言预加载 Java、C++、Go 的全部语言文件。",
        )
        self.assert_rejected("single-language loading rule")

    def test_missing_lazy_secondary_rule_fails(self) -> None:
        self.mutate_skill(
            "- 混合模式中，主语言和次语言分别在首次进入对应阶段时加载；"
            "进入次语言专项前才加载。",
            "- 混合模式开始时同时加载主语言和次语言文件。",
        )
        self.assert_rejected("secondary-language lazy-loading rule")

    def test_common_h2_in_coding_file_fails(self) -> None:
        nested = self.root / "references" / "nested"
        nested.mkdir()
        path = nested / "java-coding-challenges.md"
        source = self.root / "references" / "java-coding-challenges.md"
        path.write_text(
            source.read_text(encoding="utf-8") + "\n## MySQL\n",
            encoding="utf-8",
        )
        self.assert_rejected("common-only H2")

    def test_common_h2_in_language_ai_file_fails(self) -> None:
        path = self.root / "references" / "go-ai-dev-tools-knowledge-base.md"
        path.write_text(
            path.read_text(encoding="utf-8") + "\n## 系统设计\n",
            encoding="utf-8",
        )
        self.assert_rejected("common-only H2")

    def test_frontend_ai_h2_in_common_ai_fails(self) -> None:
        path = self.root / "references" / "common-ai-dev-knowledge-base.md"
        path.write_text(
            path.read_text(encoding="utf-8") + "\n## 前端 AI 实战\n",
            encoding="utf-8",
        )
        self.assert_rejected("frontend-only H2")

    def test_wrong_route_timing_fails(self) -> None:
        self.mutate_skill(
            "| Java 编码 | `references/java-coding-challenges.md` | "
            "确认实际用 Java 编码后 |",
            "| Java 编码 | `references/java-coding-challenges.md` | "
            "面试配置开始前预加载 |",
        )
        self.assert_rejected("routing table mismatch")

    def test_wrong_route_path_fails(self) -> None:
        self.mutate_skill(
            "| Go 专项 | `references/go-tech-knowledge-base.md` | "
            "首次进入 Go 专项前 |",
            "| Go 专项 | `references/go-coding-challenges.md` | "
            "首次进入 Go 专项前 |",
        )
        self.assert_rejected("routing table mismatch")


if __name__ == "__main__":
    unittest.main(verbosity=2)
