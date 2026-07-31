#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_REFERENCES = (
    "common-backend-knowledge-base.md",
    "common-interviewer-styles.md",
    "common-evaluation-rubric.md",
    "common-ai-dev-knowledge-base.md",
    "java-tech-knowledge-base.md",
    "java-coding-challenges.md",
    "java-ai-dev-tools-knowledge-base.md",
    "cpp-tech-knowledge-base.md",
    "cpp-coding-challenges.md",
    "cpp-ai-dev-tools-knowledge-base.md",
    "go-tech-knowledge-base.md",
    "go-coding-challenges.md",
    "go-ai-dev-tools-knowledge-base.md",
)

REQUIRED_STATE_KEYS = (
    "language_mode",
    "primary_language",
    "secondary_language",
    "loaded_references",
    "covered_topics",
)

REQUIRED_ROUTING_PHRASES = (
    "单语言",
    "混合语言",
    "主语言",
    "次语言",
    "70%",
    "30%",
)

EXPECTED_ROUTES = (
    (
        "通用后端",
        "references/common-backend-knowledge-base.md",
        "进入通用后端阶段前",
    ),
    (
        "面试官风格",
        "references/common-interviewer-styles.md",
        "风格确认后、首次输出风格化话术前",
    ),
    (
        "评分",
        "references/common-evaluation-rubric.md",
        "开始评分前",
    ),
    (
        "通用 AI",
        "references/common-ai-dev-knowledge-base.md",
        "首次考察 AI 项目或 AI 开发能力时",
    ),
    (
        "Java 专项",
        "references/java-tech-knowledge-base.md",
        "首次进入 Java 专项前",
    ),
    (
        "Java 编码",
        "references/java-coding-challenges.md",
        "确认实际用 Java 编码后",
    ),
    (
        "Java AI 工具",
        "references/java-ai-dev-tools-knowledge-base.md",
        "common AI 已加载且首次考察 AI 辅助 Java 开发时",
    ),
    (
        "C++ 专项",
        "references/cpp-tech-knowledge-base.md",
        "首次进入 C++ 专项前",
    ),
    (
        "C++ 编码",
        "references/cpp-coding-challenges.md",
        "确认实际用 C++ 编码后",
    ),
    (
        "C++ AI 工具",
        "references/cpp-ai-dev-tools-knowledge-base.md",
        "common AI 已加载且首次考察 AI 辅助 C++ 开发时",
    ),
    (
        "Go 专项",
        "references/go-tech-knowledge-base.md",
        "首次进入 Go 专项前",
    ),
    (
        "Go 编码",
        "references/go-coding-challenges.md",
        "确认实际用 Go 编码后",
    ),
    (
        "Go AI 工具",
        "references/go-ai-dev-tools-knowledge-base.md",
        "common AI 已加载且首次考察 AI 辅助 Go 开发时",
    ),
)

REQUIRED_LOADING_RULES = (
    (
        "single-language loading rule",
        "单语言只加载实际主语言所需文件，不预读另外两门语言",
    ),
    (
        "secondary-language lazy-loading rule",
        "混合模式中，主语言和次语言分别在首次进入对应阶段时加载；"
        "进入次语言专项前才加载",
    ),
    (
        "coding-language loading rule",
        "编码题只加载实际编码语言的 coding 文件",
    ),
    (
        "common-AI-first loading rule",
        "AI 项目先加载 `references/common-ai-dev-knowledge-base.md`；"
        "AI 辅助语言开发再加载所用语言的 AI tools 文件",
    ),
)

STALE_PHRASES = (
    "name: java-backend-interview",
    "# Java 后端面试模拟器",
    "name: cpp-golang-backend-interview",
    "# C++/Golang 后端面试模拟器",
)

COMMON_ONLY_TOPICS = (
    "MySQL",
    "数据库",
    "Redis",
    "消息队列",
    "分布式系统",
    "系统设计",
    "网络与操作系统",
)

FRONTEND_ONLY_H2_MARKERS = (
    "前端",
    "Frontend",
    "React",
    "UI ",
    "UI/",
    "UX ",
    "UX/",
)

FORBIDDEN_REFERENCE_MARKERS = (
    "xiaolincoding.com",
    "cdn.xiaolincoding.com",
    "github.com/2637309949/go-interview",
)


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"missing file: {display_path(path)}")
    except UnicodeDecodeError as exc:
        errors.append(f"not utf-8: {display_path(path)}: {exc}")
    except OSError as exc:
        errors.append(f"cannot read file: {display_path(path)}: {exc}")
    return ""


def parse_routing_table(skill: str) -> list[tuple[str, str, str]]:
    match = re.search(
        r"^## 知识库路由\s*$\n(?P<section>.*?)(?=^##\s|\Z)",
        skill,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return []

    rows: list[tuple[str, str, str]] = []
    for line in match.group("section").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
        if len(cells) != 3 or cells[0] in {"用途", "---"}:
            continue
        if all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        rows.append((cells[0], cells[1], cells[2]))
    return rows


def iter_h2(content: str) -> list[str]:
    return re.findall(r"^##\s+(.+?)\s*$", content, re.MULTILINE)


def normalized_h2(heading: str) -> str:
    return re.sub(r"^\d+(?:\.\d+)*[.、]?\s*", "", heading).strip()


def validate() -> list[str]:
    errors: list[str] = []
    skill_path = ROOT / "SKILL.md"
    readme_path = ROOT / "README.md"
    skill = read_text(skill_path, errors)
    readme = read_text(readme_path, errors)

    for relative in ("LICENSE", ".gitignore"):
        if not (ROOT / relative).is_file():
            errors.append(f"missing file: {relative}")

    references_dir = ROOT / "references"
    reference_markdown = (
        sorted(references_dir.rglob("*.md"))
        if references_dir.is_dir()
        else []
    )
    top_level_references = [
        path for path in reference_markdown if path.parent == references_dir
    ]
    for path in reference_markdown:
        if path.parent != references_dir:
            errors.append(
                f"nested reference not allowed: {display_path(path)}"
            )

    actual_references = {path.name for path in top_level_references}
    expected_references = set(REQUIRED_REFERENCES)
    for filename in sorted(actual_references - expected_references):
        errors.append(f"unexpected reference: references/{filename}")

    for filename in REQUIRED_REFERENCES:
        path = ROOT / "references" / filename
        content = read_text(path, errors)
        if content and not content.startswith("# "):
            errors.append(f"missing H1 heading: references/{filename}")

    frontmatter = re.match(r"\A---\n(?P<body>.*?)\n---\n", skill, re.DOTALL)
    if not frontmatter:
        errors.append("SKILL.md has invalid YAML frontmatter boundary")
    else:
        names = re.findall(
            r"^name:[ \t]*(.*?)[ \t]*$",
            frontmatter.group("body"),
            re.MULTILINE,
        )
        valid_names = {
            "backend-interview-simulator",
            "'backend-interview-simulator'",
            '"backend-interview-simulator"',
        }
        if len(names) != 1 or names[0] not in valid_names:
            errors.append("SKILL.md name must be backend-interview-simulator")

    if skill and len(skill.splitlines()) > 500:
        errors.append("SKILL.md exceeds 500 lines")

    combined_public_text = f"{skill}\n{readme}"
    for phrase in STALE_PHRASES:
        if phrase in combined_public_text:
            errors.append(f"stale phrase: {phrase}")

    for key in REQUIRED_STATE_KEYS:
        if key not in skill:
            errors.append(f"missing state key in SKILL.md: {key}")

    for phrase in REQUIRED_ROUTING_PHRASES:
        if phrase not in skill:
            errors.append(f"missing routing rule in SKILL.md: {phrase}")

    routes = parse_routing_table(skill)
    if routes != list(EXPECTED_ROUTES):
        errors.append(
            "routing table mismatch: expected exact purpose/path/timing rows"
        )

    for rule_name, phrase in REQUIRED_LOADING_RULES:
        if phrase not in skill:
            errors.append(f"missing {rule_name}")

    language_reference_pattern = re.compile(
        r"^(?:java|cpp|go)-"
        r"(?:tech-knowledge-base|coding-challenges|ai-dev-tools-knowledge-base)"
        r"\.md$"
    )
    for path in reference_markdown:
        if not language_reference_pattern.match(path.name):
            continue
        content = read_text(path, errors)
        for heading in iter_h2(content):
            normalized = normalized_h2(heading)
            for topic in COMMON_ONLY_TOPICS:
                if normalized == topic or normalized.startswith(f"{topic} "):
                    errors.append(
                        f"common-only H2 in {display_path(path)}: {heading}"
                    )

    common_ai = read_text(
        ROOT / "references" / "common-ai-dev-knowledge-base.md", errors
    )
    for heading in iter_h2(common_ai):
        if any(marker.casefold() in heading.casefold()
               for marker in FRONTEND_ONLY_H2_MARKERS):
            errors.append(
                "frontend-only H2 in common-ai-dev-knowledge-base.md: "
                f"{heading}"
            )

    for path in reference_markdown:
        content = read_text(path, errors)
        for marker in FORBIDDEN_REFERENCE_MARKERS:
            if marker in content:
                errors.append(
                    "external source content embedded in "
                    f"{display_path(path)}: {marker}"
                )

    if "secondary_language" in skill and "不能与主语言相同" not in skill:
        errors.append("secondary language uniqueness rule is missing")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"validation failed: {len(errors)} error(s)")
        return 1
    print("validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
