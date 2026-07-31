# AI 辅助 Java 后端开发知识库

> 本文件只维护 AI 在 Java、JVM 与 Spring 生态中的专项用法。
> 跨语言的任务选择、代码审查、数据库与 API 验证见 `common-ai-dev-knowledge-base.md`；缓存和后端工程原则见 `common-backend-knowledge-base.md`。

---

## 1. Spring Boot 代码生成与审查

### 适合生成的内容

- **边界明确的样板代码** — Controller、DTO、参数校验、异常映射和配置属性类可由 AI 起草，但必须给出当前 Spring Boot、Java 和构建工具版本
- **分层结构草稿** — 让 AI 按 Controller、Application Service、Domain、Repository 的现有项目边界生成，不允许为了套模板擅自增加层级
- **配置迁移辅助** — 在明确目标版本和官方迁移说明后，辅助转换 `application.yml`、自动配置和依赖声明；生成结果必须通过启动测试验证
- **局部重构** — 构造器注入、消除循环依赖、拆分大类和收敛事务边界，应由现有测试证明行为等价

### 审查重点

- `@Transactional` 是否通过 Spring 代理调用，传播行为、只读属性和回滚异常是否符合业务语义
- Bean 生命周期、条件装配和配置绑定是否在当前 Spring Boot 版本有效
- Controller 是否把实体直接暴露，校验错误、业务错误和未知异常是否有稳定映射
- 阻塞调用是否进入错误的执行器，线程池、连接池和超时是否形成一致预算
- 日志、Actuator、metrics 和 trace 是否泄露敏感字段或制造高基数标签

### 提示词示例

```text
基于项目现有的 Spring Boot 版本和同目录代码风格，为 UserService 增加 createUser。
约束：
1. 使用构造器注入，不新增框架或 Lombok 依赖。
2. 事务只覆盖数据库状态变更，不在事务中执行远程调用。
3. 列出修改文件、失败路径和需要补充的测试。
4. 生成后运行现有构建与测试；无法验证的 API 明确标记，不得猜测。
```

### 连续追问与误区

1. AI 如何确认项目使用 Spring Boot 2 还是 3，`javax.*` 与 `jakarta.*` 差异如何验证？
2. 生成的事务注解在 self-invocation 下是否生效，测试如何证明？
3. 自动配置条件为什么未命中，用 `ConditionEvaluationReport` 能获得什么证据？
4. 只通过 `ApplicationContext` 启动是否足以证明真实 HTTP、数据库和序列化边界正确？

**常见误区：**

- 为减少代码量默认加入 Lombok、MapStruct 或新 starter，忽略依赖治理
- 把 `@Transactional` 加在任意方法上就认为事务生效
- 使用模型记忆中的配置键，不检查当前版本 metadata 和启动日志
- 只生成正常路径，没有验证校验失败、事务回滚和下游超时

---

## 2. Java 并发代码审查

### AI 可以辅助发现的问题

- 检查共享可变状态是否受同一同步协议保护，是否存在 check-then-act、迭代期间修改和不安全发布
- 标记 `CompletableFuture`、线程池和并行流中的阻塞调用、异常丢失、错误执行器与缺少超时
- 检查 `ThreadLocal` 清理、锁释放、`InterruptedException` 处理和任务取消传播
- 画出锁获取顺序、线程等待和回调关系，作为死锁或线程饥饿分析的假设输入

### 必须由运行证据验证的问题

- **线程安全不能只靠静态阅读证明** — 需要最小并发回归、重复压力测试、线程 dump、JFR 或 profiler；测试未复现也不等于形式证明
- **原子类不等于复合操作原子** — 多个 `Atomic*` 更新、读后写和跨对象不变量仍可能竞态
- **容器线程安全不等于业务线程安全** — `ConcurrentHashMap` 的单操作安全不能覆盖多个调用组成的业务事务
- **虚拟线程不是无成本线程** — 需验证 pinning、载体线程、连接池和下游并发限制，不能仅凭改用 virtual thread 宣称吞吐提升

### 连续追问与误区

1. 这段代码的共享状态、不变量和 happens-before 边分别是什么？
2. AI 指出的竞态能否写成先失败的并发测试，失败是否来自竞态而非测试本身不稳定？
3. 线程数、队列容量和拒绝策略如何由服务能力与下游预算推导？
4. 修复后如何用 JFR、线程 dump 和压力测试证明锁等待或任务堆积下降？

**常见误区：**

- AI 建议把字段加 `volatile`，但操作实际需要复合原子性
- 为规避同步全部改成 `ConcurrentHashMap`，不定义跨 key 不变量
- 吞掉 `InterruptedException` 或只打印日志，破坏取消协议
- 使用无界队列掩盖背压，直到内存耗尽或尾延迟失控

---

## 3. JVM 与性能排查辅助

### 上下文与证据要求

- 提供 JDK 版本、GC、容器 CPU/内存限制、启动参数、流量变化和问题时间窗口
- 保留关键英文错误原文，例如 `java.lang.OutOfMemoryError: Java heap space`、`GC overhead limit exceeded` 或 `unable to create native thread`
- 让 AI 对 GC 日志、线程 dump、JFR、heap dump 或 async-profiler 结果生成候选解释，但每个结论必须指向原始指标或调用栈
- 将 Java 堆、Metaspace、Code Cache、直接内存、线程栈、文件映射和容器 RSS 分开，不能把所有内存归到 heap

### 典型辅助流程

1. **CPU 飙高** — 先关联流量和容器配额，再定位高 CPU 线程，将系统线程 ID 与 Java 线程栈对齐，最后用 JFR 或采样 profiler 验证热点。
2. **内存增长** — 比较 Full GC 后存活集和分配速率，必要时分析 heap dump 的 dominator tree 与 GC Roots；同时检查 native memory 和线程数量。
3. **延迟抖动** — 对齐请求 p99、GC pause、safepoint、锁等待、线程池队列和下游 trace，避免只凭一条 GC 日志归因。
4. **类加载问题** — 核对类来源、ClassLoader 层级和依赖树，再分析 `ClassNotFoundException`、`NoClassDefFoundError`、`NoSuchMethodError` 的不同含义。

### 连续追问与误区

1. 这个结论能解释故障时间窗口内的哪些指标，反例是什么？
2. dump、JFR 或 profiler 对生产进程的 CPU、磁盘和停顿风险如何控制？
3. 增大 `-Xmx` 是修复、缓解还是延后故障，怎样区分？
4. 参数调整后吞吐、p99、GC 开销和容器成本如何与 baseline 对比？

**常见误区：**

- AI 看到 OOM 就建议增大堆，不区分 heap、Metaspace、direct memory 和 native thread
- 复制其他服务的 GC 参数，不验证对象生命周期、堆规模和 SLO
- 只提供截图或二手摘要，不保留可搜索的原始日志和时间戳
- 把一次 profiler 火焰图当作稳定结论，不检查采样窗口是否覆盖故障

---

## 4. JUnit、Mockito 与集成测试

### 测试生成原则

- 先把需求转成可观察行为和失败用例，再让 AI 生成最小实现；若测试一开始就通过，应检查是否覆盖了目标缺口
- JUnit 测试名表达业务行为，覆盖正常、边界和错误路径；参数化测试用于同一规则的输入矩阵，不把多个无关行为塞进一个用例
- Mockito 只隔离不可控协作者，优先断言返回值、状态和外部可见行为；`verify` 用于确有意义的交互契约，而不是复述实现步骤
- Spring 测试按范围选择：纯 Java 测试、slice test、`@SpringBootTest`、Testcontainers 或真实依赖环境，避免所有测试都启动完整上下文

### AI 生成测试的审查点

- 是否错误地 mock 被测对象、静态全局状态或简单值对象
- 是否因宽泛的 `any()`、默认返回值和过度 stub 让错误实现也能通过
- 是否断言真实异常类型、错误信息或业务状态，而不是只写 `assertNotNull`
- 是否处理时间、随机数、并发、Locale 和时区等不稳定来源
- 集成测试是否实际验证事务、序列化、数据库约束和容器启动，而不是仍由 mock 替代

### 提示词示例

```text
为 UserService.createUser 写 JUnit 5 测试。
先列出业务不变量和失败场景，再逐个写测试；使用真实 User 对象，只 mock 外部 Repository。
至少包含重复 email、密码编码失败和保存异常。
每个测试说明如果实现缺失时预期如何失败，不要修改生产协议来让测试通过。
```

### 连续追问与误区

1. 这个测试是否在修复前因预期原因失败，还是测试配置本身报错？
2. Mockito stub 删除后测试仍通过吗，它是否真正影响被测行为？
3. 数据库唯一约束、事务回滚和序列化需要哪一层集成测试？
4. 并发测试如何控制起跑时序、重复次数和超时，同时减少 flaky？

**常见误区：**

- AI 生成大量 mock 和 interaction verification，看似覆盖率高但没有行为保护
- 只测当前实现分支，不从需求和历史故障设计反例
- 为通过测试暴露生产代码内部方法，或改变业务协议
- 用 H2 内存数据库替代真实数据库后，宣称 SQL 与事务行为已验证

---

## 5. 常见幻觉与验证方法

| 幻觉类型 | 常见表现 | 验证方法 |
|----------|----------|----------|
| 不存在的 API | 生成当前 JDK、Spring 或测试库中没有的方法、注解或参数 | 核对当前依赖版本的官方 API，执行编译和最小运行示例 |
| 版本混用 | 混用 Spring Boot 2/3、`javax`/`jakarta`、旧版安全配置或废弃 JVM 参数 | 输出依赖树与运行时版本，查看迁移说明、编译错误和启动日志 |
| 错误并发保证 | 声称 `volatile`、并发容器或虚拟线程自动解决全部线程安全问题 | 写失败并发测试，检查 happens-before、不变量、JFR 和线程 dump |
| 错误 JVM 归因 | 仅凭 OOM、GC 或 CPU 现象直接给出参数方案 | 对齐时间线，分析 GC 日志、heap/native memory、profile 和容器指标 |
| 脆弱测试 | 测试只验证 mock、立即通过或依赖时间和线程调度 | 先观察 RED，进行 mutation 思考、重复运行和真实边界集成测试 |
| 虚构配置 | 生成不存在或已改名的 Spring 配置键 | 查看 configuration metadata、官方参考和 `ConditionEvaluationReport` |

### 验证闭环

1. **固定环境事实** — 记录 JDK、框架、插件和依赖版本，不允许 AI 自行假设。
2. **保留原始证据** — 保存完整编译错误、异常链、日志、dump 和测试命令，不只提供概括。
3. **构造可证伪检查** — 编译、静态分析、先失败的测试、最小复现或性能 baseline 至少选择一种。
4. **验证受影响范围** — 局部检查通过后运行模块测试、集成测试和构建，确认未破坏兼容性。
5. **人工承担结论** — 审查者能解释生成代码的线程、事务、内存和失败边界，再允许合并或发布。

### 各身份难度参考

| 题目 | 实习 | 应届 | 社招 1-3 年 |
|------|:----:|:----:|:----------:|
| Spring Boot 生成代码验证 | 基础 | 中等 | 深入 |
| Java 并发幻觉识别 | 基础 | 中等 | 深入 |
| JVM 证据链分析 | 了解 | 基础 | 深入 |
| JUnit 与 Mockito 边界 | 基础 | 中等 | 深入 |
