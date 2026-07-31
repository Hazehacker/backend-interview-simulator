#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "references" / "java-tech-knowledge-base.md"


class JavaKnowledgeBoundaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = SOURCE.read_text(encoding="utf-8")

    def test_required_boundary_labels_exist(self) -> None:
        for label in (
            "[Java 规范]",
            "[JDK 标准库实现]",
            "[JVM/GC 实现]",
            "[版本变化]",
        ):
            self.assertIn(label, self.text)

    def test_string_semantics_are_separate_from_compact_string_storage(self) -> None:
        self.assertIn("不可变语义", self.text)
        self.assertIn("byte[] + coder", self.text)
        self.assertIn("Compact Strings", self.text)

    def test_collection_constants_are_not_presented_as_contracts(self) -> None:
        self.assertIn("不是 Java API 契约", self.text)
        self.assertIn("TREEIFY_THRESHOLD", self.text)
        self.assertIn("MIN_TREEIFY_CAPACITY", self.text)

    def test_volatile_jmm_and_barrier_mapping_are_separate(self) -> None:
        self.assertIn("volatile 写 happens-before 后续对同一变量的读", self.text)
        self.assertIn("屏障映射", self.text)
        self.assertIn("目标 JVM、JIT 和 CPU 架构", self.text)

    def test_gc_and_tooling_are_conditional(self) -> None:
        self.assertIn("Full GC 不是 JVM 规范定义的统一事件", self.text)
        self.assertIn("不能承诺固定毫秒数", self.text)
        self.assertIn("-Xlog:gc*", self.text)
        self.assertIn("先执行 `java -version`", self.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
