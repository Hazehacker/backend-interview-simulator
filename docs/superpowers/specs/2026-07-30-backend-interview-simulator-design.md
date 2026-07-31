# Backend Interview Simulator 统一 Skill 升级设计

## 1. 背景与目标

当前项目只有 `java-backend-interview-simulator/`，面试流程、触发条件、技术题库和文档均以 Java 为中心。

本次升级目标是将其改造为单一的 `backend-interview-simulator` skill，通过一个入口支持：

- Java 后端面试
- C++ 后端面试
- Go 后端面试
- 主语言加次语言的混合技术栈面试

外部仓库和网站只用于建立主题覆盖索引。除本项目可追溯的原始 Java 基线外，未确认兼容内容许可证的来源不得提供正文、代码、图片或可复制骨架；C++、Go 和新增公共内容全部独立编写。

## 2. 设计原则

### 2.1 单一入口

只保留一个 `SKILL.md` 和一个触发名称。用户说“后端面试”时由 skill 询问技术栈，而不是让用户预先判断应安装或触发哪个子 skill。

### 2.2 通用知识只维护一份

MySQL、Redis、消息队列、计算机网络、操作系统、分布式系统、系统设计、性能排查和工程实践不属于某一种语言，统一放入通用后端知识库。

### 2.3 语言知识按需加载

Java、C++、Go 的语言专项知识和编码题分别维护。单语言面试不加载其他语言题库；混合面试先加载主语言，在进入次语言阶段时再加载次语言。

### 2.4 控制上下文成本

`SKILL.md` 只保留触发条件、会话流程、状态和文件路由规则。详细题目、参考答案、评分细则和话术放入 `references/`。

所有 reference 文件直接位于 `references/` 下并由 `SKILL.md` 直接引用，避免深层目录影响发现和按需读取。文件名使用语言前缀表达归属。

## 3. 最终目录结构

项目根目录本身作为 skill 目录，不再保留一层 `java-backend-interview-simulator/`：

```text
backend-interview-simulator/
├── SKILL.md
├── README.md
├── LICENSE
├── scripts/
│   ├── validate_skill.py
│   ├── test_validate_skill.py
│   ├── test_java_thread_pool.py
│   ├── test_java_knowledge_boundaries.py
│   └── test_jd_coverage.py
└── references/
    ├── common-backend-knowledge-base.md
    ├── common-interviewer-styles.md
    ├── common-evaluation-rubric.md
    ├── common-ai-dev-knowledge-base.md
    ├── java-tech-knowledge-base.md
    ├── java-coding-challenges.md
    ├── java-ai-dev-tools-knowledge-base.md
    ├── cpp-tech-knowledge-base.md
    ├── cpp-coding-challenges.md
    ├── cpp-ai-dev-tools-knowledge-base.md
    ├── go-tech-knowledge-base.md
    ├── go-coding-challenges.md
    └── go-ai-dev-tools-knowledge-base.md
```

`README.md` 作为公开仓库的用户安装和使用说明保留，不承担 agent 执行规则；执行规则只写在 `SKILL.md` 中。

## 4. Skill 元数据与触发

frontmatter 使用统一名称：

```yaml
---
name: backend-interview-simulator
description: >
  Use when users want to practice or simulate Java, C++, Go, Golang, mixed-stack,
  or general backend technical interviews, including resume-based and JD-based interviews.
---
```

描述只负责覆盖触发场景，不在 frontmatter 中重复面试流程。中文触发词包括但不限于：

- 开始面试、模拟面试、练习面试
- 后端面试、Java 面试、C++ 面试、Go 面试、Golang 面试
- 准备字节、腾讯、阿里、美团、快手等后端技术面试
- 根据简历或岗位 JD 模拟技术面试

用户只说“后端面试”时不得默认选择 Java。

## 5. 面试信息收集

面试开始前收集：

1. 候选人身份：日常实习、暑期实习、校招、社招 1-3 年。
2. 技术栈模式：单语言或混合语言。
3. 主语言：Java、C++、Go。
4. 次语言：仅混合模式填写，且不能与主语言相同。
5. 面试时长：30、40、45 或 60 分钟。
6. 面试官风格。
7. 是否提供简历。
8. 是否提供目标岗位 JD。
9. 是否包含编码题。
10. 纠错模式：严格模式或即时引导模式。

用户已经提供的信息直接复用，只追问缺失字段。所有问答保持“一次只问一个问题”。

## 6. 面试流程

```text
信息确认
→ 简历与 JD 分析
→ 项目深挖
→ 通用后端考察
→ 主语言专项
→ 次语言专项（混合模式）
→ 编码题（可选）
→ 综合评分与改进建议
```

时间不足时按以下优先级裁剪：

1. 保留项目深挖。
2. 保留主语言专项。
3. 保留最终反馈。
4. 减少通用后端题数量。
5. 减少或取消次语言专项。
6. 编码题仅在用户已明确选择时保留。

## 7. 主次语言规则

### 7.1 单语言模式

- 只加载该语言专项题库。
- 编码题使用该语言。
- 通用后端题从公共知识库选取。

### 7.2 混合模式

- 主语言专项约占语言题的 70%，次语言约占 30%。
- 比例用于控制总体方向，不要求机械精确。
- 项目经历明显偏向次语言时，可基于简历动态调整比例。
- 编码题默认使用主语言，用户明确指定时可改用次语言。
- 评分分别展示主语言和次语言能力。

### 7.3 技术栈变更

- `SKILL.md` 中冻结的语言配置是最终运行合同，本设计不得放宽它。
- 只有 `frozen=false` 且尚无任何语言专项证据时，才可调整 `language_mode`、主/次语言角色与比例。
- 首次进入任一语言专项前将 `frozen` 设为 `true`；冻结后当前场次不得改变模式、主语言、次语言或比例。
- 简历或 JD 出现未选择的语言时，未冻结且无语言证据可询问忽略或调整；冻结后只能忽略，或结束当前场次并新开场次。
- 不因偶然出现某个语言关键词就自动扩大考察范围。
- 新场次重新收集语言配置，旧场次证据不得投影到新配置。

## 8. Knowledge Base 路由

| 文件 | 加载时机 |
|---|---|
| `common-interviewer-styles.md` | 风格确认后、首次输出面试官话术前 |
| `common-backend-knowledge-base.md` | 进入通用后端考察前 |
| `common-evaluation-rubric.md` | 面试结束并开始评分前 |
| `common-ai-dev-knowledge-base.md` | 候选人首次提到 AI 项目、Agent、RAG、MCP 等经验时 |
| `<language>-tech-knowledge-base.md` | 首次进入对应语言专项前 |
| `<language>-coding-challenges.md` | 使用对应语言进行编码题前 |
| `<language>-ai-dev-tools-knowledge-base.md` | 首次考察 AI 辅助对应语言开发时 |

`loaded_references` 记录已读取文件，禁止无意义重复加载。

## 9. 知识库边界

### 9.1 通用后端

`common-backend-knowledge-base.md` 包含：

- MySQL
- Redis
- 消息队列
- 计算机网络
- 操作系统
- 分布式锁、分布式事务、分布式 ID
- RPC、服务治理与一致性
- 高并发和系统设计
- 性能分析、故障排查和工程实践

### 9.2 Java 专项

`java-tech-knowledge-base.md` 包含：

- Java 语言基础和集合
- JVM、GC、类加载和调优
- Java 内存模型
- JUC、AQS、线程池和并发工具
- Spring、Spring Boot 和常见框架机制

### 9.3 C++ 专项

`cpp-tech-knowledge-base.md` 包含：

- 基础语义：指针与引用、`const`、`static`、作用域、存储期和链接属性
- C 与 C++ 边界：`extern "C"`、`struct`、`class`、`union` 和对象布局
- 对象模型、虚函数和多态
- RAII、智能指针和异常安全
- STL 容器、迭代器和 allocator
- 模板、泛型和现代 C++ 特性
- 手动内存管理、内存池和泄漏排查
- atomic、memory order 和 lock-free
- epoll、io_uring、零拷贝和高性能网络编程
- 工程排查：core dump、GDB、Valgrind、AddressSanitizer 和性能分析

### 9.4 Go 专项

`go-tech-knowledge-base.md` 包含：

- 基础语义：`make` 与 `new`、数组与切片、`for range`、字符串与 `rune`
- 初始化与类型系统：`defer`、`init`、struct tag、空结构体、interface 与 typed nil
- 参数传递、多返回值、指针、`unsafe.Pointer` 和逃逸分析
- slice、map、string、interface 和反射
- goroutine、channel、select 和 context
- GMP 调度和 netpoller
- GC、写屏障、逃逸分析和内存分配
- sync、atomic、errgroup 和常见并发模式
- net/http、RPC 和 Go 工程实践
- 工程排查：race detector、pprof、trace、dlv、goroutine 泄漏和内存泄漏

### 9.5 AI 内容

- `common-ai-dev-knowledge-base.md` 只保存 LLM、Agent、RAG、MCP、Context Engineering 和 AI 系统设计等通用内容。
- 各语言 `ai-dev-tools` 文件只保存 AI 辅助该语言开发、测试、调试和审查的具体场景。
- Agent Loop 等通用原理不得在三个语言文件中重复。

### 9.6 编码题

- Java、C++、Go 编码题独立维护。
- 相同问题可以跨语言出现，但实现要求、易错点和追问必须符合语言习惯。
- 不把 C++ 的内存管理题直接翻译为 Go，也不把 Java 框架题硬套到其他语言。

## 10. 知识点统一格式

新增或重构的核心知识点采用以下结构：

```markdown
### 主题

- 基础问题
- 答案要点
- 连续追问
- 常见错误与质疑点
- 不同候选人身份的难度边界
```

不强制一次性重写所有既有题目；迁移阶段优先保证技术归属正确、路由正确和无重复，再逐步统一格式。

## 11. 外部知识来源与复核

### 11.1 来源用途

统一边界：**外部来源若未确认与本项目兼容的内容许可证，只能作为主题覆盖索引；不得复制或改写其正文、代码、图片、答案结构或题库骨架。C++、Go 和新增公共内容均独立编写。**

| 来源 URL / 仓库 | 检查基线 | 观察到的许可状态 | 本项目允许用途 | 影响的本地文件 | 复制边界 |
|---|---|---|---|---|---|
| `https://github.com/Hazehacker/java-backend-interview-simulator` | commit `b0d14406ea9062a14c340ad59f25aee0fb2b9402` | 本地基线含 MIT License | 作为本项目 Java 版本的可追溯演进基线 | `SKILL.md`、Java references、README | 按 MIT 基线演进；新增内容仍单独复核 |
| `https://github.com/XNefertar/backend-interview-simulator` | 2026-07-30 访问；未记录 commit | 未确认兼容内容许可证 | 仅校准 C++ / Go 主题覆盖 | C++ / Go tech、coding、AI references | **no copied prose/code/images**；不复制题库骨架 |
| `https://github.com/2637309949/go-interview` | 2026-07-30 访问；未记录 commit | 未确认兼容内容许可证 | 仅校准 Go runtime、并发、GC 和工程主题 | Go tech、coding references | **no copied prose/code/images** |
| `https://xiaolincoding.com/interview/golang.html` 与 `https://xiaolincoding.com/interview/cpp.html` | 2026-07-30 访问 | 未确认兼容内容许可证 | 仅校准 Go、C++ 与计算机基础主题 | common backend、C++ / Go references | **no copied prose/code/images** |
| `https://github.com/Snailclimb/JavaGuide` | 2026-07-30 访问；本轮未记录 commit | 本轮未重新确认兼容内容许可证 | 仅校准 Java 与通用后端主题覆盖 | common backend、Java references | **no copied prose/code/images** |

公开可访问不等于允许复制。若未来需要超出主题索引使用某个来源，必须先记录精确 commit、许可证文本、兼容性结论和受影响文件，再单独审查。

### 11.2 覆盖矩阵

Go 题库至少覆盖：

| 层次 | 主题 |
|---|---|
| 基础 | `make/new`、数组与切片、字符串与 `rune`、`defer`、`init`、struct tag、空结构体 |
| 类型系统 | interface 比较、typed nil、值传递、指针、`unsafe.Pointer`、反射 |
| 数据结构 | slice、map、string 的底层结构、扩容、并发安全与常见陷阱 |
| 并发 | goroutine、channel、select、context、Mutex、RWMutex、sync.Map、sync.Pool |
| Runtime | GMP、work stealing、抢占、栈伸缩、g0、gopark/goready、netpoller |
| 内存 | 逃逸分析、mcache/mcentral/mheap、GC、三色标记、写屏障、STW、GOGC |
| 工程 | net/http、连接复用、race detector、pprof、trace、dlv、泄漏排查 |
| 编码 | 并发控制、顺序打印、生产者消费者、超时取消和 goroutine 生命周期 |

C++ 题库至少覆盖：

| 层次 | 主题 |
|---|---|
| 基础 | 指针、引用、`const`、`static`、作用域、存储期、链接属性、`extern "C"` |
| 对象模型 | `struct/class/union`、构造析构、虚函数、虚表、多继承、虚继承和对象布局 |
| 资源管理 | RAII、Rule of Zero/Five、智能指针、循环引用、异常安全和自定义删除器 |
| STL | vector、deque、list、map、unordered_map、迭代器失效、allocator 和复杂度 |
| 现代 C++ | `auto`、`decltype`、右值引用、移动语义、完美转发、lambda、concept 和 coroutine |
| 并发 | thread、mutex、condition_variable、future、atomic、memory order 和 lock-free |
| 内存与系统 | new/delete、malloc/free、对齐、brk/mmap、内存池、虚拟内存和零拷贝 |
| 工程 | core dump、GDB、Valgrind、Sanitizer、性能分析和线上崩溃定位 |
| 编码 | 资源管理类、线程同步、并发容器、LRU、内存池和高性能网络组件 |

### 11.3 技术事实复核

外部面试资料只作为候选主题，答案必须重新编写并至少经过以下检查：

- 标注适用的 Go 版本、C++ 标准版本、编译器或 runtime 实现范围。
- 优先依据 Go 官方 specification、runtime 源码、C++ 标准语义和主流实现文档。
- 区分语言规范保证、特定 runtime/标准库实现和经验性性能结论。
- 不使用绝对化说法回答版本敏感问题。
- 对存在争议的表述增加限定条件或将其改造成追问。

重点复核项包括：

- Go `for range` 变量语义及不同 Go 版本的变化。
- Go goroutine 栈大小、GC 阶段、写屏障和调度实现。
- Go interface 与 typed nil、逃逸分析和对象分配位置。
- C++ 引用是否占用存储、对象布局和 ABI 相关结论。
- `shared_ptr` 控制块线程安全与被管理对象线程安全的区别。
- `malloc` 的 `brk`/`mmap` 阈值、STL 扩容策略等实现相关结论。

## 12. 会话状态

`SKILL.md` 维护以下逻辑状态：

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

状态规则：

- `covered_topics` 使用 `<scope>:<topic>` 格式，例如 `common:mysql-index`、`go:gmp`。
- 每次只问一个问题，先分析回答，再追问、纠正或切换主题。
- 同一知识点不重复考察，除非候选人的回答产生新的追问方向。
- 严格模式连续两次错误或完全无法作答时再纠正。
- 即时引导模式发现关键错误后立即指出并继续追问。

## 13. 评分设计

最终报告包含：

- 综合评分
- 项目经验
- 通用后端能力
- 主语言能力
- 次语言能力，仅混合模式显示
- 系统设计与工程实践
- 思维逻辑和表达
- AI 能力，仅实际考察后显示
- 优势、薄弱点和下一步学习建议
- JD 匹配分析，仅提供 JD 时显示

提前结束时必须说明评分只覆盖已考察范围。未实际考察的维度不得虚构分数。

## 14. 异常与边界处理

- 未指定语言：先确认，不默认 Java。
- 简历读取失败：保留关键英文错误信息，允许粘贴文本继续。
- JD 与所选语言冲突：明确指出冲突，由用户决定是否调整主次语言。
- 冷门主题未被题库覆盖：可以基于可靠知识继续，但在报告中标记为“非题库扩展考察”。
- 技术结论存在版本差异：先确认版本或标准，不武断判错。
- 用户提前结束：立即进入反馈，不继续追问。
- 用户要求跳过：记录未考察，不按错误答案扣分。

## 15. 迁移策略

1. 将当前 skill 根目录从 `java-backend-interview-simulator/` 提升到项目根目录。
2. 重写统一 `SKILL.md` 的元数据、信息收集、状态和路由规则。
3. 将现有 Java 技术题库拆成 Java 专项和通用后端两部分。
4. 使用参考仓库、`go-interview` 和小林 coding 仅建立 C++/Go 主题覆盖索引。
5. 独立编写并复核 C++/Go 内容，不复制许可证不明确来源的正文、代码、图片、答案结构或题库骨架。
6. 按语言拆成两套文件，清理 Java 遗留表述、语言混用和重复通用章节。
7. 拆分三种语言的编码题和 AI 辅助开发题库。
8. 更新评分规则，使单语言和混合语言报告都成立。
9. 更新 README 的名称、安装方式、触发示例、目录结构和能力边界。
10. 删除旧目录前核对所有内容已迁移，避免丢失用户现有资料。

## 16. 验收标准

### 16.1 静态结构

- 项目根目录存在 `SKILL.md`、`README.md`、`LICENSE` 和 `references/`。
- `scripts/validate_skill.py` 能检查元数据、13 个 reference 精确集合、路由表、按需加载语义、公共内容边界和过期表述。
- `scripts/test_validate_skill.py` 跟踪 validator mutation tests；Java 线程池、Java 版本边界和 JD coverage 另有聚焦测试脚本。
- frontmatter 名称为 `backend-interview-simulator`，与 skill 目录名一致。
- 所有 reference 路径存在且能从 `SKILL.md` 直接发现。
- 不再存在仅代表旧版本的 `java-backend-interview-simulator/` 目录。

### 16.2 内容一致性

- 不存在“只支持 Java”的过期表述。
- 不存在“C++/Golang 共用一套语言专项题库”的设计。
- MySQL、Redis、分布式和系统设计等通用知识只保留一份。
- 通用 AI 原理不在三个语言文件中重复。
- C++/Go 内容不存在大段外部原文或来源图片。
- 版本敏感结论带有适用范围，不把实现细节写成语言规范。

### 16.3 路由场景

至少静态验证以下场景：

1. Java 单语言面试。
2. C++ 单语言面试。
3. Go 单语言面试。
4. 主 Java、次 Go。
5. 主 C++、次 Java。
6. 主 Go、次 C++。
7. 编码题默认跟随主语言。
8. 只说“后端面试”时先询问语言。
9. 简历出现未选择语言时先询问是否调整。
10. 提前结束时只评价已考察内容。

### 16.4 验证边界

静态检查只能证明结构、路径和规则完整，不能证明真实模型在长对话中始终正确执行。完成静态验证后，还应使用真实会话做 Java、C++、Go 和混合模式的端到端试跑，并记录实际路由偏差。

## 17. 非目标

本次升级不包含：

- Rust、Python、Node.js 等其他后端语言。
- 语音识别或实时音视频面试。
- 在线计时器和独立前端界面。
- 真实公司内部面试题采集。
- 将面试评分包装为客观招聘结论。

这些能力只有在三语言版本稳定后再单独评估。
