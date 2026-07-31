# Backend Interview Simulator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 Java 后端面试 skill 升级为单一入口的 `backend-interview-simulator`，支持 Java、C++、Go 单语言与主次语言混合面试。

**Architecture:** 保留一份通用面试流程、面试官风格、评分规则、通用后端和 AI 知识库；Java、C++、Go 的语言专项、编码题和 AI 辅助开发知识按文件隔离并按需加载。使用无第三方依赖的静态校验脚本检查 frontmatter、reference 路由、过期表述、通用内容重复和主次语言规则。

**Tech Stack:** Markdown、YAML frontmatter、Python 3 标准库、Git、Agent Skills 规范。

## Global Constraints

- skill 目录名和 frontmatter `name` 必须统一为 `backend-interview-simulator`。
- 用户只说“后端面试”时不得默认 Java，必须确认单语言或混合语言模式。
- 混合模式使用 `primary_language` 和 `secondary_language`，语言专项题量默认约为 70% / 30%。
- MySQL、Redis、消息队列、网络、操作系统、分布式和系统设计只在通用知识库维护一份。
- C++ 与 Go 必须使用独立知识库，不保留 C++/Golang 混合题库。
- `SKILL.md` 保持在 500 行以内，详细知识放在 `references/`。
- reference 文件保持一级可达，全部直接位于 `references/`。
- XNefertar、`go-interview`、小林 coding、JavaGuide 等未在本计划中确认兼容内容许可证的外部来源只作为主题覆盖索引；不得复制正文、代码、图片、答案结构或题库骨架。
- Go 版本敏感结论、C++ 标准或 ABI 相关结论必须标注适用范围。
- 文本文件使用 UTF-8；保留中文用户文档和面试话术。
- 不提交 `.claude/settings.local.json`、`.DS_Store`、简历、JD 或本地权限配置。
- 不修改 Git 远端；仓库改名和远端迁移不属于本计划。
- 未经用户明确要求不执行 Git commit。每个任务只提供建议提交信息。

---

## File Map

| Path | Responsibility |
|---|---|
| `SKILL.md` | 统一触发、信息收集、状态、流程、路由和异常规则 |
| `README.md` | 用户安装、触发示例、能力说明、目录和来源说明 |
| `.gitignore` | 排除本地配置、系统文件、简历和 JD |
| `scripts/validate_skill.py` | 确定性静态校验 |
| `scripts/test_validate_skill.py` | validator baseline 与 mutation tests |
| `scripts/test_java_thread_pool.py` | 从 Markdown 抽取并验证 Java 教学线程池 |
| `scripts/test_java_knowledge_boundaries.py` | Java 规范、JDK 与 JVM/GC 版本边界断言 |
| `scripts/test_jd_coverage.py` | JD coverage 与 must-have 评分门禁断言 |
| `references/common-backend-knowledge-base.md` | 数据库、缓存、网络、系统、分布式和系统设计 |
| `references/common-interviewer-styles.md` | 六种面试官风格和话术 |
| `references/common-evaluation-rubric.md` | 单语言与混合语言评分规则 |
| `references/common-ai-dev-knowledge-base.md` | LLM、Agent、RAG、MCP 和通用 AI 辅助后端实践 |
| `references/java-tech-knowledge-base.md` | Java、JVM、JUC、Spring |
| `references/java-coding-challenges.md` | Java 编码题 |
| `references/java-ai-dev-tools-knowledge-base.md` | AI 辅助 Java 开发 |
| `references/cpp-tech-knowledge-base.md` | C++ 语言、对象模型、STL、内存和并发 |
| `references/cpp-coding-challenges.md` | C++ 编码题 |
| `references/cpp-ai-dev-tools-knowledge-base.md` | AI 辅助 C++ 开发 |
| `references/go-tech-knowledge-base.md` | Go 语言、runtime、并发、GC 和工程排查 |
| `references/go-coding-challenges.md` | Go 编码题 |
| `references/go-ai-dev-tools-knowledge-base.md` | AI 辅助 Go 开发 |

---

### Task 1: 提升 Git 根目录并建立失败的静态校验

**Files:**
- Move: `java-backend-interview-simulator/.git` → `.git`
- Move: `java-backend-interview-simulator/SKILL.md` → `SKILL.md`
- Move: `java-backend-interview-simulator/README.md` → `README.md`
- Move: `java-backend-interview-simulator/LICENSE` → `LICENSE`
- Move: `java-backend-interview-simulator/references/` → `references/`
- Move: `java-backend-interview-simulator/.gitignore` → `.gitignore`
- Move: `java-backend-interview-simulator/.claude/` → `.claude/`
- Modify: `.gitignore`
- Create: `scripts/validate_skill.py`

**Interfaces:**
- Consumes: 当前内层 Git 仓库的 clean `main` 工作树。
- Produces: 外层目录成为 Git 根目录；现有 Git 历史不变；静态校验脚本以非零状态报告尚未完成的统一 skill。

- [ ] **Step 1: 记录迁移前 Git 证据**

Run:

```bash
git -C java-backend-interview-simulator status --short --branch
git -C java-backend-interview-simulator rev-parse HEAD
git -C java-backend-interview-simulator remote -v
```

Expected:

```text
## main...origin/main
```

保存 HEAD 值用于迁移后比对。工作树若不干净，停止迁移并先区分用户改动。

- [ ] **Step 2: 将 Git 元数据和工作树提升到外层**

Run from `<repo-root>`:

```bash
test ! -e .git
test -d java-backend-interview-simulator/.git
mv java-backend-interview-simulator/.git .git
mv java-backend-interview-simulator/.gitignore .gitignore
mv java-backend-interview-simulator/LICENSE LICENSE
mv java-backend-interview-simulator/README.md README.md
mv java-backend-interview-simulator/SKILL.md SKILL.md
mv java-backend-interview-simulator/references references
mv java-backend-interview-simulator/.claude .claude
rmdir java-backend-interview-simulator
```

Expected: `java-backend-interview-simulator/` 被移除，外层 `git rev-parse --show-toplevel` 返回当前目录。

- [ ] **Step 3: 保留但取消跟踪本地 Claude 权限配置**

Run:

```bash
git rm --cached .claude/settings.local.json
```

Expected: 文件仍存在于本机，`git status --short` 将其显示为 tracked deletion；后续 `.gitignore` 使其不再作为未跟踪文件出现。

- [ ] **Step 4: 更新忽略规则**

将 `.gitignore` 改为：

```gitignore
# Local runtime settings
.claude/settings.local.json

# OS metadata
.DS_Store

# Local interview inputs and source material
/JavaGuide/
/resume/
/JD/
```

- [ ] **Step 5: 验证 Git 历史未改变**

Run:

```bash
git rev-parse HEAD
git rev-parse --show-toplevel
git remote -v
git status --short
```

Expected:

- HEAD 与 Step 1 完全一致。
- `git rev-parse --show-toplevel` 返回 `<repo-root>`。
- `origin` 仍指向 `Hazehacker/java-backend-interview-simulator`，本任务不修改远端。
- `docs/` 为新增内容，`.claude/settings.local.json` 为 tracked deletion。

- [ ] **Step 6: 编写最终结构的失败校验**

创建 `scripts/validate_skill.py`：

```python
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

STALE_PHRASES = (
    "name: java-backend-interview",
    "# Java 后端面试模拟器",
    "name: cpp-golang-backend-interview",
    "# C++/Golang 后端面试模拟器",
)

COMMON_ONLY_TOPICS = (
    "MySQL",
    "Redis",
    "分布式系统",
    "系统设计",
    "网络与操作系统",
)

FORBIDDEN_REFERENCE_MARKERS = (
    "xiaolincoding.com",
    "cdn.xiaolincoding.com",
    "github.com/2637309949/go-interview",
)


def read_text(path: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"missing file: {path.relative_to(ROOT)}")
    except UnicodeDecodeError as exc:
        errors.append(f"not utf-8: {path.relative_to(ROOT)}: {exc}")
    return ""


def validate() -> list[str]:
    errors: list[str] = []
    skill_path = ROOT / "SKILL.md"
    readme_path = ROOT / "README.md"
    skill = read_text(skill_path, errors)
    readme = read_text(readme_path, errors)

    for relative in ("LICENSE", ".gitignore"):
        if not (ROOT / relative).is_file():
            errors.append(f"missing file: {relative}")

    for filename in REQUIRED_REFERENCES:
        path = ROOT / "references" / filename
        content = read_text(path, errors)
        if content and not content.startswith("# "):
            errors.append(f"missing H1 heading: references/{filename}")

    frontmatter = re.match(r"\A---\n(?P<body>.*?)\n---\n", skill, re.DOTALL)
    if not frontmatter:
        errors.append("SKILL.md has invalid YAML frontmatter boundary")
    elif "name: backend-interview-simulator" not in frontmatter.group("body"):
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

    for filename in REQUIRED_REFERENCES:
        route = f"references/{filename}"
        if route not in skill:
            errors.append(f"SKILL.md does not route to {route}")

    for language in ("java", "cpp", "go"):
        path = ROOT / "references" / f"{language}-tech-knowledge-base.md"
        if not path.is_file():
            continue
        content = read_text(path, errors)
        for topic in COMMON_ONLY_TOPICS:
            heading = re.compile(
                rf"^##\s+(?:\d+\.\s+)?{re.escape(topic)}(?:\s|$)",
                re.MULTILINE,
            )
            if heading.search(content):
                errors.append(
                    f"common topic duplicated in {path.name}: {topic}"
                )

    references_dir = ROOT / "references"
    if references_dir.is_dir():
        for path in references_dir.glob("*.md"):
            content = read_text(path, errors)
            for marker in FORBIDDEN_REFERENCE_MARKERS:
                if marker in content:
                    errors.append(
                        f"external source content embedded in {path.name}: {marker}"
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
```

- [ ] **Step 7: 运行校验并确认处于 RED**

Run:

```bash
python3 scripts/validate_skill.py
```

Expected: FAIL，至少包含 `missing file: references/common-backend-knowledge-base.md` 和 `SKILL.md name must be backend-interview-simulator`。

建议提交信息，仅在用户明确要求提交时使用：

```text
refactor: 提升后端面试 skill 仓库根目录

Co-authored-by: TRAE CLI <noreply@bytedance.com>
```

---

### Task 2: 拆分通用知识与 Java 专项

**Files:**
- Rename: `references/tech-knowledge-base.md` → `references/java-tech-knowledge-base.md`
- Rename: `references/coding-challenges.md` → `references/java-coding-challenges.md`
- Rename: `references/ai-dev-tools-knowledge-base.md` → `references/java-ai-dev-tools-knowledge-base.md`
- Rename: `references/ai-dev-knowledge-base.md` → `references/common-ai-dev-knowledge-base.md`
- Rename: `references/interviewer-styles.md` → `references/common-interviewer-styles.md`
- Rename: `references/evaluation-rubric.md` → `references/common-evaluation-rubric.md`
- Create: `references/common-backend-knowledge-base.md`
- Modify: all renamed files above

**Interfaces:**
- Consumes: Task 1 的平面 `references/` 目录和静态校验器。
- Produces: 通用后端、通用 AI、公共风格与评分文件，以及不再重复通用后端内容的 Java 三件套。

- [ ] **Step 1: 使用 Git rename 保留历史**

Run:

```bash
git mv references/tech-knowledge-base.md references/java-tech-knowledge-base.md
git mv references/coding-challenges.md references/java-coding-challenges.md
git mv references/ai-dev-tools-knowledge-base.md references/java-ai-dev-tools-knowledge-base.md
git mv references/ai-dev-knowledge-base.md references/common-ai-dev-knowledge-base.md
git mv references/interviewer-styles.md references/common-interviewer-styles.md
git mv references/evaluation-rubric.md references/common-evaluation-rubric.md
```

Expected: `git status --short` 将六个文件识别为 rename 或 delete/add 候选，内容仍完整。

- [ ] **Step 2: 创建通用后端知识库**

`references/common-backend-knowledge-base.md` 使用以下一级结构：

```markdown
# 通用后端技术知识库

## 目录
## 1. MySQL
## 2. Redis
## 3. 消息队列
## 4. 计算机网络
## 5. 操作系统
## 6. 分布式系统
## 7. 系统设计
## 8. 性能分析与故障排查
## 9. 工程实践
```

从原 Java 技术知识库迁入 MySQL、Redis、分布式、系统设计、网络和操作系统内容。将 `java-ai-dev-tools` 中的多级缓存选型迁入 Redis 或系统设计章节。每个核心主题至少包含基础问题、答案要点、连续追问和常见误区。

必须修正这些 Java 假设：

- “本地缓存占用 JVM 堆”改成“占用当前进程内存”，再按 Java/C++/Go 分别追问内存管理差异。
- 通用死锁题不再引用 `synchronized` 或 AQS；Java 实现细节留在 Java 文件。
- RPC、消息队列、缓存一致性和限流题不得使用单一语言框架作为标准答案。

- [ ] **Step 3: 将 Java 技术库收敛为语言专项**

`references/java-tech-knowledge-base.md` 只保留：

```markdown
# Java 后端专项知识库

## 目录
## 1. Java 语言基础与集合
## 2. Java 内存模型与并发
## 3. JVM
## 4. Spring 与 Spring Boot
## 5. Java 工程实践与排查
```

删除已迁入通用文件的 MySQL、Redis、分布式、系统设计、网络和操作系统章节。Java 并发中的死锁内容只保留 Java 锁、线程 dump、JFR、Arthas 等专项实现。

- [ ] **Step 4: 整理通用 AI 与 Java AI 工具内容**

`references/common-ai-dev-knowledge-base.md` 保留原有 LLM、Agent、RAG、MCP 和 AI 系统设计，并新增：

```markdown
## AI 辅助后端开发通用实践
### 适合与不适合 AI 辅助的任务
### AI 代码审查的证据边界
### 数据库与 API 设计中的验证要求
```

`references/java-ai-dev-tools-knowledge-base.md` 只保留 Java 相关内容：

```markdown
# AI 辅助 Java 后端开发知识库

## 1. Spring Boot 代码生成与审查
## 2. Java 并发代码审查
## 3. JVM 与性能排查辅助
## 4. JUnit、Mockito 与集成测试
## 5. 常见幻觉与验证方法
```

移除已经迁入通用 AI 或通用后端文件的数据库、API 和多级缓存重复内容。

- [ ] **Step 5: 调整 Java 编码题标题和边界**

将 H1 改为 `# Java 后端编码题库`。SQL、数据库和系统设计挑战题面可以继续存在，但通用语义与标准答案只能在 `references/common-backend-knowledge-base.md` 维护一份。Java 文件必须直接路由公共知识库，只保留 JDBC/Spring 事务边界、连接生命周期、异常翻译、Java 并发与测试等语言专项实现关注点。

- [ ] **Step 6: 调整公共评分文件的维度名称**

在 `references/common-evaluation-rubric.md` 中先完成结构性改名：

- “技术深度”拆为“通用后端能力”和“语言专项能力”。
- 保留实习、应届、社招三个身份层级。
- 为后续 Task 6 预留已命名的“主语言能力”和“次语言能力”段落，不写空白占位符。
- 明确未考察维度不打分。

- [ ] **Step 7: 运行静态检查**

Run:

```bash
python3 scripts/validate_skill.py
```

Expected: FAIL 仍然存在，但不再报告六个已创建或已重命名的 common/Java reference；主要剩余错误是 C++/Go 文件缺失和旧 `SKILL.md` 路由。

建议提交信息，仅在用户明确要求提交时使用：

```text
refactor: 拆分通用后端与 Java 专项知识库

Co-authored-by: TRAE CLI <noreply@bytedance.com>
```

---

### Task 3: 编写 Go 专项知识库

**Files:**
- Create: `references/go-tech-knowledge-base.md`

**Interfaces:**
- Consumes: 设计文档中的 Go 覆盖矩阵、参考仓库的 Go 主题、Go 官方 specification/runtime 文档。
- Produces: 不含 MySQL、Redis、分布式和通用系统设计的 Go 专项知识库。

- [ ] **Step 1: 建立 Go 文件目录和版本声明**

文件开头必须是：

```markdown
# Go 后端专项知识库

> 默认以当前稳定 Go 版本的语言规范和 runtime 行为为准。涉及历史行为时必须标注版本；实现细节不能表述为语言规范保证。

## 目录
## 1. 语言基础与类型系统
## 2. Slice、Map、String 与 Interface
## 3. Goroutine、Channel 与同步原语
## 4. GMP 调度与 Netpoller
## 5. 内存分配、逃逸分析与 GC
## 6. 标准库与服务端工程
## 7. 性能分析与故障排查
## 8. 高频追问链与身份难度
```

- [ ] **Step 2: 编写基础与类型系统题组**

必须覆盖并给出连续追问：

- Go 与 Java/C++ 的适用场景差异。
- `make` 与 `new`。
- 数组与切片。
- 字符串拼接、UTF-8、`rune` 和字节。
- `defer` 参数求值、LIFO、具名返回值和常见性能误区。
- 包初始化顺序与 `init`。
- struct tag、空结构体和零值。
- Go 只有值传递；slice、map、channel 等描述符复制后的共享行为。
- interface 可比较条件、typed nil 和类型断言。
- `unsafe.Pointer` 与 `uintptr` 的边界。

对于 `for range`，明确区分 Go 1.22 前后迭代变量语义，禁止只写“地址会变”或“地址不变”的绝对答案。

- [ ] **Step 3: 编写核心数据结构题组**

必须覆盖：

- slice 三元描述符、扩容的实现依赖、共享底层数组和内存滞留。
- map 的桶、扩容、遍历无序和并发读写限制。
- string 不可变语义与 `strings.Builder`。
- `iface`/`eface` 作为 runtime 实现概念，而非语言规范 API。
- 结构体可比较条件和内存对齐。

- [ ] **Step 4: 编写并发与 runtime 题组**

必须覆盖：

- goroutine 与 OS 线程、协程的差异。
- channel 的有缓冲/无缓冲、关闭、nil channel、阻塞和泄漏。
- `select`、超时、取消和公平性表述边界。
- `context` 传播、取消和禁止存放可选业务参数。
- Mutex、RWMutex、WaitGroup、Once、Cond、sync.Map、sync.Pool 和 atomic。
- GMP 中 G/M/P、local run queue、global queue、work stealing、sysmon、抢占。
- g0、gopark/goready、系统调用和 netpoller。

- [ ] **Step 5: 编写内存、GC 与工程排查题组**

必须覆盖：

- 逃逸分析及 `go build -gcflags="-m=2"` 的证据用法。
- mcache、mcentral、mheap 作为 runtime 实现。
- goroutine 栈伸缩，避免写死长期不变的初始栈大小。
- 并发标记清扫、三色抽象、写屏障、短 STW 阶段和 GC pacer。
- `GOGC`、`GOMEMLIMIT` 的权衡。
- goroutine 泄漏和仍被引用对象导致的内存增长。
- `go test -race`、pprof、trace、dlv 和 runtime metrics。
- `net/http` Transport 复用、响应体关闭和连接泄漏。

- [ ] **Step 6: 校验归属和外部复制风险**

Run:

```bash
rg -n '^## ([0-9]+\.)? ?(MySQL|Redis|分布式系统|系统设计|网络与操作系统)' references/go-tech-knowledge-base.md
rg -n 'xiaolincoding|2637309949|cdn\\.xiaolincoding|picgo' references/go-tech-knowledge-base.md
```

Expected: 两条命令均无输出。来源链接只在 README 致谢或设计文档出现，不嵌入题库正文。

- [ ] **Step 7: 运行静态检查**

Run:

```bash
python3 scripts/validate_skill.py
```

Expected: 不再报告 `go-tech-knowledge-base.md` 缺失；仍报告 C++、编码题、AI 工具和 SKILL 路由问题。

建议提交信息，仅在用户明确要求提交时使用：

```text
feat: 新增 Go 后端专项知识库

Co-authored-by: TRAE CLI <noreply@bytedance.com>
```

---

### Task 4: 编写 C++ 专项知识库

**Files:**
- Create: `references/cpp-tech-knowledge-base.md`

**Interfaces:**
- Consumes: 设计文档中的 C++ 覆盖矩阵、参考仓库主题和标准语义。
- Produces: 明确区分语言标准、ABI 和实现细节的 C++ 专项知识库。

- [ ] **Step 1: 建立 C++ 文件目录和标准声明**

文件开头必须是：

```markdown
# C++ 后端专项知识库

> 默认考察现代 C++。题目涉及 C++11/14/17/20/23、编译器 ABI、标准库或 glibc 实现时必须明确适用范围。

## 目录
## 1. 基础语义、存储期与链接
## 2. 对象模型与面向对象
## 3. RAII、资源管理与异常安全
## 4. STL、模板与现代 C++
## 5. 内存管理与系统交互
## 6. 并发、原子操作与内存模型
## 7. 网络编程与高性能服务
## 8. 工程排查与性能分析
## 9. 高频追问链与身份难度
```

- [ ] **Step 2: 编写基础语义与对象模型题组**

必须覆盖：

- 指针大小受目标平台影响，不能固定回答 4 或 8 字节。
- 野指针、悬空指针、指针与引用、const pointer 与 pointer to const。
- 值、指针、引用传参和生命周期。
- 自动、静态、线程、动态存储期与作用域、链接的区别。
- 头文件定义、ODR、`inline` 变量和 `extern "C"`。
- C 与 C++ 的 `struct` 差异；C++ `struct` 与 `class` 默认访问和继承权限。
- union、alignment、padding、standard-layout 和 ABI 限定。
- 虚函数、虚表、多继承、虚继承和虚析构。

“引用不占内存”只能作为抽象语义讨论；对象布局、成员引用和 ABI 必须单独限定。

- [ ] **Step 3: 编写资源管理、STL 与现代 C++ 题组**

必须覆盖：

- RAII、Rule of Zero/Five、拷贝与移动、异常安全保证。
- `unique_ptr`、`shared_ptr`、`weak_ptr`、控制块、循环引用和自定义 deleter。
- 明确 `shared_ptr` 控制块的线程安全不代表被管理对象线程安全。
- vector 扩容只表述为摊销复杂度和实现策略，不把固定倍数写成标准保证。
- deque、list、map、unordered_map 的结构、复杂度和迭代器失效。
- allocator、placement new 和对象生命周期。
- `auto`、`decltype`、右值引用、移动语义、完美转发、lambda、constexpr。
- SFINAE、concept、coroutine 按候选人级别分层。

- [ ] **Step 4: 编写内存、并发、网络和排查题组**

必须覆盖：

- new/delete 与 malloc/free 的语义差异。
- 对齐、内存池、碎片、jemalloc/tcmalloc 的适用场景。
- `brk`/`mmap` 阈值属于 allocator/glibc 实现，不写成 C++ 规范。
- thread、mutex、condition_variable、future/promise。
- atomic、CAS、ABA、memory order、happens-before 和 false sharing。
- lock-free 不等于 wait-free，也不保证一定更快。
- epoll、io_uring、零拷贝和 Reactor。
- core dump、GDB、Valgrind、ASan、TSan、UBSan 和 perf。

- [ ] **Step 5: 校验归属和外部复制风险**

Run:

```bash
rg -n '^## ([0-9]+\.)? ?(MySQL|Redis|分布式系统|系统设计|网络与操作系统)' references/cpp-tech-knowledge-base.md
rg -n 'xiaolincoding|cdn\\.xiaolincoding|picgo' references/cpp-tech-knowledge-base.md
```

Expected: 两条命令均无输出。

- [ ] **Step 6: 运行静态检查**

Run:

```bash
python3 scripts/validate_skill.py
```

Expected: 不再报告 Java、Go、C++ 技术文件缺失；主要剩余错误是 C++/Go 编码题、AI 工具和统一 SKILL/README。

建议提交信息，仅在用户明确要求提交时使用：

```text
feat: 新增 C++ 后端专项知识库

Co-authored-by: TRAE CLI <noreply@bytedance.com>
```

---

### Task 5: 拆分 C++/Go 编码题与 AI 辅助开发题库

**Files:**
- Create: `references/cpp-coding-challenges.md`
- Create: `references/go-coding-challenges.md`
- Create: `references/cpp-ai-dev-tools-knowledge-base.md`
- Create: `references/go-ai-dev-tools-knowledge-base.md`

**Interfaces:**
- Consumes: 参考仓库的混合 C++/Go 编码题和 AI 工具主题。
- Produces: 主语言可独立加载的编码题与 AI 开发题库。

- [ ] **Step 1: 编写 C++ 编码题库**

使用统一题目模板：

```markdown
### 题目名称

**适用身份：** 实习 / 应届 / 社招
**考察点：** 明确列出语言能力
**题目：** 给出输入、输出、约束和禁止假设
**参考实现要点：** 不只给最终代码
**连续追问：** 至少 3 层
**常见错误：** 未定义行为、生命周期、并发或复杂度风险
```

至少包含：

1. RAII 文件或连接句柄封装。
2. Rule of Five 资源类。
3. 简化 `unique_ptr` 或引用计数控制块设计题。
4. 线程池。
5. 有界阻塞队列。
6. LRU 缓存。
7. SPSC 队列并讨论 memory order。
8. 内存池。
9. epoll Echo Server 骨架。

不把无锁实现作为实习生默认题；必须允许先写正确的锁版本，再讨论无锁。

- [ ] **Step 2: 编写 Go 编码题库**

沿用相同模板，至少包含：

1. Worker Pool 和有界并发。
2. context 超时与取消传播。
3. 生产者消费者与 channel 关闭责任。
4. 多 goroutine 顺序打印。
5. 并发安全 LRU。
6. 限流器。
7. HTTP Router 或 middleware chain。
8. goroutine 泄漏诊断与修复。
9. 使用 `errgroup` 汇总错误。

每题必须检查 channel 的所有权、退出路径、错误传播和 race 风险。

- [ ] **Step 3: 编写 C++ AI 辅助开发题库**

章节固定为：

```markdown
# AI 辅助 C++ 后端开发知识库

## 1. 构建系统与依赖上下文
## 2. 生命周期、所有权与未定义行为审查
## 3. 并发和内存模型审查
## 4. 测试、Sanitizer 与性能证据
## 5. AI 常见幻觉与验证方法
```

必须强调：AI 生成的生命周期、原子内存序、模板报错修复和性能优化不能仅靠代码审查确认，必须通过编译器诊断、测试、Sanitizer 和 benchmark 验证。

- [ ] **Step 4: 编写 Go AI 辅助开发题库**

章节固定为：

```markdown
# AI 辅助 Go 后端开发知识库

## 1. 模块、接口与标准库上下文
## 2. Goroutine 生命周期与并发审查
## 3. HTTP、RPC 与数据库代码审查
## 4. 测试、Race Detector、pprof 与 trace
## 5. AI 常见幻觉与验证方法
```

必须强调：生成代码需要 `gofmt`、`go vet`、单元测试和 `go test -race`；性能结论必须有 benchmark/pprof 证据。

- [ ] **Step 5: 检查语言隔离**

Run:

```bash
rg -n 'goroutine|channel|GMP' references/cpp-*.md
rg -n 'shared_ptr|unique_ptr|memory_order|RAII' references/go-*.md
```

Expected: 无输出；跨语言比较只允许出现在通用知识库或明确标注的比较题中。

- [ ] **Step 6: 运行静态检查**

Run:

```bash
python3 scripts/validate_skill.py
```

Expected: 所有 required reference 均存在；失败项集中在旧 `SKILL.md` 元数据、状态、路由和旧 README 表述。

建议提交信息，仅在用户明确要求提交时使用：

```text
feat: 拆分 C++ 和 Go 编码及 AI 开发题库

Co-authored-by: TRAE CLI <noreply@bytedance.com>
```

---

### Task 6: 重写统一 SKILL 流程和混合语言评分

**Files:**
- Modify: `SKILL.md`
- Modify: `references/common-evaluation-rubric.md`
- Modify: `references/common-interviewer-styles.md`

**Interfaces:**
- Consumes: Task 2-5 的 13 个 reference 文件。
- Produces: 单入口、按需加载、可恢复的 Java/C++/Go 单语言和混合语言面试流程。

- [ ] **Step 1: 重写 frontmatter**

使用：

```yaml
---
name: backend-interview-simulator
description: >
  Use when users want to practice or simulate Java, C++, Go, Golang,
  mixed-stack, or general backend technical interviews, including
  resume-based and job-description-based interview preparation.
---
```

description 只描述触发条件，不概括内部执行流程。

- [ ] **Step 2: 将 SKILL 主体压缩为执行规则**

`SKILL.md` 使用以下结构，控制在 500 行以内：

```markdown
# 后端面试模拟器
## 角色与目标
## 一问一答原则
## 会话状态
## 第一步：确认面试配置
## 第二步：解析简历与 JD
## 第三步：项目深挖
## 第四步：通用后端考察
## 第五步：主语言专项
## 第六步：次语言专项
## 第七步：编码题
## 第八步：评分与反馈
## 知识库路由
## 中途切换、暂停与恢复
## 异常处理
## 禁忌事项
```

开场白和风格化长话术不再放在 SKILL，统一从 `common-interviewer-styles.md` 读取。

- [ ] **Step 3: 定义完整状态**

SKILL 中必须逐项出现：

```text
candidate_level
interview_duration
interviewer_style
correction_mode
language_mode
primary_language
secondary_language
coding_enabled
resume_provided
jd_provided
loaded_references
covered_topics
weak_points
follow_up_topics
remaining_stage
```

`covered_topics` 使用 `common:mysql-index`、`go:gmp` 这样的 `<scope>:<topic>` 标识。

- [ ] **Step 4: 实现配置与主次语言规则**

必须明确：

- 单语言：Java、C++、Go。
- 混合语言：先选主语言，再选不同的次语言。
- 次语言不能与主语言相同。
- 用户只说后端面试时不默认 Java。
- 语言专项默认约 70% 主语言、30% 次语言，但根据简历动态调整。
- 编码题默认使用主语言。
- JD 或简历出现第三种语言时先询问，不自动扩大范围。
- 只有 `language_weight_split.frozen=false` 且尚无语言专项证据时，才可调整单/混合模式、主次语言角色和比例。
- 首次进入任一语言专项前冻结配置；冻结后任何模式、角色或比例变更都必须结束当前场次并新开场次，旧场次证据不得投影到新配置。

- [ ] **Step 5: 编写 reference 路由表**

SKILL 中必须直接写出 13 条 `references/<filename>` 路径，并定义：

- 风格确认后加载 `common-interviewer-styles.md`。
- 进入通用阶段前加载 `common-backend-knowledge-base.md`。
- 首次进入对应语言前加载 `<language>-tech-knowledge-base.md`。
- 混合模式进入次语言阶段前才加载次语言文件。
- 编码题只加载实际使用语言的 coding 文件。
- AI 项目先加载 common AI；AI 辅助语言开发再加载对应语言 AI tools。
- 开始评分前加载 `common-evaluation-rubric.md`。
- `loaded_references` 防止重复读取。

- [ ] **Step 6: 重构评分文件**

`common-evaluation-rubric.md` 提供两个公式：

```text
单语言：
综合分 = 项目经验 + 通用后端 + 主语言 + 系统设计/工程 + 思维表达

混合语言：
综合分 = 项目经验 + 通用后端 + 主语言 + 次语言 + 系统设计/工程 + 思维表达
```

每个身份给出总和为 100% 的具体权重。次语言不能简单并入主语言。AI 能力和 JD 匹配作为附加评价，不在未考察时强行打分。

- [ ] **Step 7: 清理公共风格中的 Java 限定**

检查并替换：

- Doug Lea、AQS 等 Java 特定例子不能作为所有语言的固定深挖话术。
- 严厉风格不得人身攻击，删除“这都不知道？那你怎么敢投”等贬损表达。
- 工程型追问保留量化数据、故障排查和生产证据。

- [ ] **Step 8: 运行校验**

Run:

```bash
python3 scripts/validate_skill.py
wc -l SKILL.md
```

Expected:

- 不再报告 frontmatter、状态、路由、70/30 或旧 skill 名称错误。
- `SKILL.md` 行数不超过 500。
- 校验可能只因 README 仍含旧 Java 品牌而失败。

建议提交信息，仅在用户明确要求提交时使用：

```text
feat: 统一三语言后端面试流程

Co-authored-by: TRAE CLI <noreply@bytedance.com>
```

---

### Task 7: 更新公开 README 和安全边界

**Files:**
- Modify: `README.md`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: 最终文件结构和路由规则。
- Produces: 不虚构在线入口、安装地址或已验证能力的公开说明。

- [ ] **Step 1: 重写 README 品牌和能力说明**

README 使用：

```markdown
# Backend Interview Simulator

一个支持 Java、C++、Go 以及主次语言混合模式的后端技术面试 Skill。
```

核心特性必须包含：

- 一个统一入口。
- 单语言和混合语言。
- 通用后端与语言专项分离。
- 简历和 JD 驱动。
- 一问一答和连续追问。
- 编码题默认跟随主语言。
- 分维度评分。

- [ ] **Step 2: 提供准确安装说明**

删除 Java 版 socialistic.ai 在线入口，除非当前统一 skill 已有可验证的新页面。安装说明只写当前可执行方式：

```text
将仓库目录放入目标 Agent 的 skills 目录，并确保目录名为
backend-interview-simulator。
```

分别给出 TRAE/Codex/Claude/OpenClaw 使用者需要遵循各自 skill 目录规范的说明，不声称所有平台都已做端到端验证。

- [ ] **Step 3: 给出触发示例**

至少包含：

```text
开始一场 Go 后端模拟面试
我是应届生，主语言 Java、次语言 Go，面试 45 分钟
按 C++ 社招岗位 JD 深挖我的项目
开始后端面试
```

最后一个示例必须说明 skill 会继续询问语言，而不是默认 Java。

- [ ] **Step 4: 更新目录和来源说明**

README 的目录树必须与 File Map 一致。来源说明写清：

- 原 Java 版本来源。
- `XNefertar/backend-interview-simulator` 用于参考 C++/Go 主题。
- `2637309949/go-interview` 和小林 coding 用于覆盖校准。
- 新增内容独立编写；不复制许可证不明确来源的正文、代码、图片、答案结构或题库骨架。
- 技术事实仍需按具体语言版本和实现复核。

- [ ] **Step 5: 扫描过期和敏感内容**

Run:

```bash
rg -n '只支持 Java|Rust/Go/C\\+\\+ 等方向暂不涉及|java-backend-interview-simulator-a6d59a|C\\+\\+/Golang 后端面试模拟器' README.md SKILL.md references
git check-ignore -v .claude/settings.local.json .DS_Store docs/.DS_Store
git status --short
```

Expected:

- 第一条无输出。
- 三个本地文件均被 `.gitignore` 命中。
- `.claude/settings.local.json` 只表现为 tracked deletion，不重新加入版本控制。

- [ ] **Step 6: 运行静态校验进入 GREEN**

Run:

```bash
python3 scripts/validate_skill.py
```

Expected:

```text
validation passed
```

建议提交信息，仅在用户明确要求提交时使用：

```text
docs: 更新统一后端面试 skill 使用说明

Co-authored-by: TRAE CLI <noreply@bytedance.com>
```

---

### Task 8: 完成规范校验和场景验收

**Files:**
- Modify: `scripts/validate_skill.py`
- Create: `scripts/test_validate_skill.py`
- Create: `scripts/test_java_thread_pool.py`
- Create: `scripts/test_java_knowledge_boundaries.py`
- Create: `scripts/test_jd_coverage.py`
- Modify other public files only if validation exposes a defect.

**Interfaces:**
- Consumes: 完整统一 skill。
- Produces: 可复现的静态验证证据和明确的未验证边界。

- [ ] **Step 1: 将初始 RED validator 强化为最终结构校验**

最终 `scripts/validate_skill.py` 只使用 Python 标准库，并在保留 frontmatter、状态键、500 行、来源 marker 和旧名称检查的基础上增加：

- 使用 `references/` 下的递归 Markdown 清单；必须恰好包含设计中的 13 个顶层文件，额外、缺失或任何嵌套 Markdown 都失败。
- 解析 `SKILL.md` 的“知识库路由”表，按顺序精确比较 13 条用途、路径和加载时机。
- 精确检查单语言不预载其他语言、混合次语言延迟加载、编码只加载实际语言、common AI 先于语言 AI tools。
- 对递归清单扫描来源 marker；扫描所有 Java/C++/Go tech、coding、AI Markdown，拒绝 common-only H2。
- 扫描 common AI，拒绝前端专属 H2。

创建 `scripts/test_validate_skill.py`，至少覆盖 baseline、额外第 14 个 reference、缺失 reference、单语言预载 mutation、缺少次语言 lazy rule、coding/AI 的 common H2、common AI 前端 H2、错误 route path 和 timing。

- [ ] **Step 2: 运行 mutation tests 和项目静态校验**

Run:

```bash
python3 scripts/test_validate_skill.py
python3 scripts/validate_skill.py
```

Expected: mutation tests 全部通过，随后输出 `validation passed`。

- [ ] **Step 3: 运行 Java 与 JD 聚焦断言**

Run:

```bash
python3 scripts/test_java_thread_pool.py
python3 scripts/test_java_knowledge_boundaries.py
python3 scripts/test_jd_coverage.py
```

Expected: Java 线程池结构和动态 harness、Java 版本边界、JD coverage/must-have gate 全部通过。若系统默认 `java` 是无 JDK shim，可通过工具发现命令选择本机已有 JDK；未找到时必须报告动态 harness 未验证。

- [ ] **Step 4: 运行官方 skill 结构校验**

Run:

```bash
QUICK_VALIDATE="$(find "$HOME/.trae/skills" -path '*/skill-creator/scripts/quick_validate.py' -print -quit)"
test -n "$QUICK_VALIDATE"
python3 "$QUICK_VALIDATE" .
```

Expected: skill frontmatter、命名和目录通过校验。若工具输出英文错误，保留原文并按实际规则修复。

- [ ] **Step 5: 检查 Markdown、UTF-8 和 diff**

Run:

```bash
git diff --check
find . -type f -name '*.md' -print0 | xargs -0 file
git status --short
git diff --stat
```

Expected:

- `git diff --check` 无输出。
- Markdown 文件均被识别为 UTF-8 或 ASCII 文本。
- diff 只包含本计划范围内的根目录提升、skill、references、脚本和文档。

- [ ] **Step 6: 静态核对十个路由场景**

逐项对照 `SKILL.md`，确认：

1. Java 单语言只路由 common + Java。
2. C++ 单语言只路由 common + C++。
3. Go 单语言只路由 common + Go。
4. 主 Java、次 Go 延迟加载 Go。
5. 主 C++、次 Java 延迟加载 Java。
6. 主 Go、次 C++ 延迟加载 C++。
7. 编码题默认使用主语言。
8. “开始后端面试”先询问语言。
9. 简历出现未选择语言时先询问是否调整。
10. 提前结束只评价已考察维度。

Expected: 每个场景都能指向一条明确规则和一个存在的 reference 路径。

- [ ] **Step 7: 记录真实模型试跑边界**

当前计划在没有独立 agent 授权时不伪造端到端行为测试。最终报告必须明确：

```text
已完成：文件结构、frontmatter、路径、重复内容、路由规则和静态场景检查。
未完成：独立模型长对话中的真实按需加载和 70/30 题量执行验证。
```

若用户明确授权独立 agent 验证，再分别运行 Java、C++、Go 和混合模式四次前向测试，并只向测试 agent 提供安装后的 skill，不泄露预期答案。

- [ ] **Step 8: 最终安全检查**

Run:

```bash
git diff -- .claude/settings.local.json
rg -n 'api[_-]?key|access[_-]?token|refresh[_-]?token|password|cookie|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY' --glob '!docs/superpowers/**' .
```

Expected:

- `.claude/settings.local.json` 的 diff 是从版本控制删除。
- 没有真实凭据或私钥；文档中的通用单词若命中，逐条确认不是秘密。

建议最终提交信息，仅在用户明确要求一次性提交全部变更时使用：

```text
feat: 升级为多语言后端面试模拟器

Co-authored-by: TRAE CLI <noreply@bytedance.com>
```
