# Backend Interview Simulator

[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

一个支持 Java、C++、Go 以及主次语言混合模式的后端技术面试 Skill。

它通过一个统一入口组织面试配置、项目深挖、通用后端、语言专项、可选编码题和证据化评分。适用于日常实习、暑期实习、校招和 1-3 年社招候选人，不代表任何公司的真实面试或内部题库。

## 核心特性

- **统一入口**：同一个 `SKILL.md` 处理 Java、C++、Go 和通用后端面试，不需要安装多个语言版本。
- **单语言与混合语言**：既可只面试一门语言，也可指定主语言和次语言；混合模式默认按 70% / 30% 分配语言专项，进入专项后冻结当前场次配置。
- **公共能力与语言专项分离**：数据库、缓存、消息队列、网络、操作系统、分布式系统和系统设计使用公共知识库；语言语义、运行时、工具链和编码题使用对应语言知识库。
- **简历和 JD 驱动**：根据候选人的真实项目证据和岗位要求调整问题，不臆测未提供的经历。
- **一问一答与连续追问**：每轮只问一个问题，再根据回答沿原理、边界、取舍和验证继续追问。
- **编码题跟随主语言**：编码环节默认使用主语言；只有用户明确要求时才切换到已配置的次语言。
- **分维度评分**：分别评价项目、通用后端、主语言、次语言、系统设计/工程和思维表达；未考察内容不按零分处理。
- **按需加载**：只在进入相应阶段时加载公共、语言专项、编码或 AI 辅助开发参考文件，避免把无关语言内容混入当前面试。

## 安装

当前没有经过验证的在线入口。可执行的安装方式是：

> 将仓库目录放入目标 Agent 的 skills 目录，并确保目录名为 `backend-interview-simulator`。

目录内应完整保留 `SKILL.md`、`references/`、`scripts/`、`README.md` 和 `LICENSE`，不要只复制单个 `SKILL.md`。

- **TRAE**：遵循当前版本 TRAE 的 skills 目录与加载规范。
- **Codex**：遵循当前版本 Codex 的 skills 目录与加载规范。
- **Claude**：遵循当前版本 Claude 的 skills 目录与加载规范。
- **OpenClaw**：遵循当前版本 OpenClaw 的 skills 目录与加载规范。

上述说明表示本仓库按各工具常见的 skills 目录方式组织，不表示已在 TRAE、Codex、Claude 和 OpenClaw 上分别完成端到端验证。具体目录位置、重载方式和 Skill 支持状态可能随客户端版本变化，请以对应产品的当前文档为准。

## 触发示例

安装并由 Agent 加载后，可以直接表达面试意图：

```text
开始一场 Go 后端模拟面试
```

```text
我是应届生，主语言 Java、次语言 Go，面试 45 分钟
```

```text
按 C++ 社招岗位 JD 深挖我的项目
```

```text
开始后端面试
```

最后一个示例没有指定语言，Skill 会继续询问单语言或混合语言及具体语言，不会默认选择 Java。其他缺失配置也会逐项确认，包括候选人级别、时长、面试官风格、纠错模式、是否包含编码题，以及是否提供简历或 JD。

面试过程中可说“继续”“跳过”“结束”或“换个风格”。提前结束时，报告只使用已经获得的回答证据，并标出未考察范围。

## 工作方式

默认阶段如下：

```text
配置 -> 简历/JD -> 项目 -> 通用后端 -> 主语言
     -> 次语言（仅混合模式）-> 编码（可选）-> 评分
```

公共知识库和语言知识库分开维护。单语言场次不会预加载另外两门语言；混合场次在首次进入主语言、次语言阶段时分别加载对应文件；编码题只加载实际编码语言的题库。

## 项目结构

```text
backend-interview-simulator/
├── .gitignore
├── LICENSE
├── README.md
├── SKILL.md
├── docs/
│   └── superpowers/
│       ├── plans/
│       │   └── 2026-07-30-backend-interview-simulator.md
│       └── specs/
│           └── 2026-07-30-backend-interview-simulator-design.md
├── references/
│   ├── common-ai-dev-knowledge-base.md
│   ├── common-backend-knowledge-base.md
│   ├── common-evaluation-rubric.md
│   ├── common-interviewer-styles.md
│   ├── cpp-ai-dev-tools-knowledge-base.md
│   ├── cpp-coding-challenges.md
│   ├── cpp-tech-knowledge-base.md
│   ├── go-ai-dev-tools-knowledge-base.md
│   ├── go-coding-challenges.md
│   ├── go-tech-knowledge-base.md
│   ├── java-ai-dev-tools-knowledge-base.md
│   ├── java-coding-challenges.md
│   └── java-tech-knowledge-base.md
└── scripts/
    ├── test_java_knowledge_boundaries.py
    ├── test_java_thread_pool.py
    ├── test_jd_coverage.py
    ├── test_validate_skill.py
    └── validate_skill.py
```

`SKILL.md` 定义触发条件、会话状态、语言路由和面试流程；`references/` 保存按阶段加载的公共与语言参考；`scripts/validate_skill.py` 执行仓库静态结构校验，`scripts/test_*.py` 保存 validator mutation、Java 线程池、Java 版本边界和 JD coverage 聚焦测试。`docs/` 保留公开的设计与实施计划，便于审阅演进过程，不参与 Skill 运行。`.superpowers/` 是本地任务 scratch，不属于公开项目结构。

## 来源与内容边界

- 本项目从 [Hazehacker/java-backend-interview-simulator](https://github.com/Hazehacker/java-backend-interview-simulator) 的 Java 版本演进而来。
- [XNefertar/backend-interview-simulator](https://github.com/XNefertar/backend-interview-simulator) 仅用于校准 C++ / Go 面试主题覆盖，不复用其题库骨架。
- [2637309949/go-interview](https://github.com/2637309949/go-interview) 与[小林 coding](https://xiaolincoding.com/) 仅用于校准 Go、计算机基础和通用后端主题覆盖。
- [JavaGuide](https://github.com/Snailclimb/JavaGuide) 用于校准 Java 与通用后端高频主题覆盖。
- **外部来源若未确认与本项目兼容的内容许可证，只能作为主题覆盖索引；不得复制或改写其正文、代码、图片、答案结构或题库骨架。C++、Go 和新增公共内容均独立编写。**

详细的访问日期、观察到的许可状态、允许用途和受影响文件见[设计文档](docs/superpowers/specs/2026-07-30-backend-interview-simulator-design.md#111-来源用途)。这些链接用于说明主题来源和覆盖校准，不表示外部项目为本仓库背书。外部项目及网站内容仍受各自许可证和使用条款约束，不因本仓库的 MIT License 而改变。语言、标准库、编译器、运行时和框架行为可能随版本变化，面试材料中的技术事实仍需结合目标版本、官方文档和实际实现复核。

## 隐私与敏感数据

- 上传简历或 JD 前，删除姓名、电话、邮箱、证件号等面试不需要的个人身份信息（PII）。
- 禁止向 Skill 或宿主 Agent 提供密码、API Key、Access Token、Refresh Token、Cookie、私钥、生产日志中的敏感值、公司保密内容或真实客户数据。
- 宿主 Agent、模型服务及其插件可能处理、传输或留存输入数据，具体边界由对应服务的隐私条款、部署方式和组织策略决定；本仓库无法替代这些服务作出隐私保证。
- 不要把真实简历或 JD 提交到本仓库。本地示例、测试和问题复现只能使用脱敏数据或模拟数据。
- `.gitignore` 只能降低本地文件被误提交的概率，不是访问控制、加密、数据擦除或隐私保证；敏感数据不应进入仓库工作区。

## 当前局限与验证边界

- 这是由 Markdown 指令和参考资料组成的 Skill，不是具有确定性执行结果的独立面试服务；实际提问和评分质量受宿主 Agent、模型和上下文影响。
- 当前只完成仓库静态校验和 Skill 元数据校验，未宣称在 TRAE、Codex、Claude、OpenClaw 上全部完成端到端对话验证。
- 时长用于裁剪面试阶段和题量，不是精确计时器；当前也不直接评价实时语音、语速、停顿或口语表现。
- PDF、图片或 Word 简历能否读取取决于宿主 Agent 提供的文件读取能力；无法读取时应改为粘贴文本。
- 题库用于面试覆盖和追问，不保证穷尽所有岗位、框架、语言版本或生产环境差异，也不能替代官方文档、编译运行和线上证据。
- 自动校验检查目录、元数据、路由和部分内容约束，不证明每个技术结论都适用于所有版本，也不证明模型会完全一致地遵循流程。

## 本地校验

在仓库根目录执行：

```bash
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/validate_skill.py
```

测试覆盖：

- 11 项 validator baseline/mutation，包括额外、缺失、嵌套 reference，递归来源扫描、语言预加载、延迟加载、路由和 H2 边界；
- 从 Markdown 抽取并动态编译运行 Java `SimpleThreadPool`，验证 graceful shutdown、构造失败回滚和 fatal `Error` 策略；
- Java 规范、JDK 标准库、JVM/GC 实现和版本变化边界；
- JD coverage、must-have 和整体星级门禁。

Java thread-pool 动态测试会自动发现 `JAVA_HOME`、`PATH`、常见 JDK 和 IDE JBR。找不到可用 JDK 时，该动态测试会显示 `skipped`；这表示 Java 编译运行未验证，不能视为动态测试通过。其他标准库测试仍会继续执行。

`SimpleThreadPool` 是用于讲解生命周期、启动回滚和 fatal failure 的教学实现，不替代 `ThreadPoolExecutor`。任一 `ThreadFactory.newThread` 或 `Thread.start` 失败时，构造器会 interrupt/join 已启动 worker 后原样抛出；任务 `RuntimeException` 被隔离，任务 `Error` 不被吞掉，并触发全池 `SHUTDOWN`，由剩余 worker 排空已接收任务。

全部测试和 validator 通过时，输出包含：

```text
OK
validation passed
```

## 许可证

本仓库中有权许可的原创及演进内容按 [MIT License](LICENSE) 发布。外部链接指向的项目、文章、图片和其他材料不属于本仓库授权范围，使用时应分别遵循其原始许可证与条款。
