# AI 辅助 C++ 后端开发知识库

> 本文件只维护 AI 在 C++ 语言、构建、测试、诊断与性能验证中的专项用法。
> 任何生成结果都必须绑定目标 C++ standard、compiler、standard library、target、build flags 和运行平台。AI 的代码解释不是编译证据，静态阅读也不能单独证明生命周期、原子同步或性能结论。

---

## 1. 构建系统与依赖上下文

### AI 开始修改前必须获取的事实

让 AI 先读取真实项目，而不是直接生成一个“通常正确”的 CMake 片段。最小上下文包括：

- C++ standard：项目是否明确使用 C++17、C++20 或 C++23，是否禁用 compiler extension。
- compiler 与版本：Clang、GCC、MSVC 或其他工具链；target triple、sysroot 和交叉编译环境。
- standard library：libstdc++、libc++ 或其他实现；其 ABI 开关和部署环境是否一致。
- 构建入口：CMake preset、Bazel target、Meson setup、Make target 或项目封装脚本。
- 编译选项：warning、optimization、debug info、exception、RTTI、LTO、sanitizer 和 ABI 相关宏。
- 依赖来源：系统包、源码子模块、包管理器或 vendored 代码；版本和 link mode 是否固定。
- 目标类型：静态库、动态库、可执行文件、插件或跨语言 ABI；测试和生产是否使用同一组关键定义。

如果这些事实未知，AI 应列出待确认项，不应擅自补上最新版依赖、切换 standard library 或改变异常/RTTI 策略。

### 执行不受信仓库命令的安全边界

仓库脚本、构建入口和测试命令都属于待审查代码，不能因为名称是 `build`、`test` 或由 AI 推荐就默认可信。执行前必须：

- 先阅读 wrapper script、CMake/Bazel hook、package manager 配置和实际子命令，识别下载、上传、删除、写 home directory、启动服务与 shell expansion。
- 在 sandbox、容器或其他最小权限环境运行，不注入生产凭据、个人 token、SSH agent、云端 metadata 或真实业务数据。
- 默认限制网络和文件系统访问，只开放构建所需的 workspace 与临时目录；依赖下载必须确认来源、版本、校验和及网络目的地。
- 设置 CPU、内存、进程数、磁盘和时间上限，防止恶意或失控的编译、测试、fuzz/benchmark 消耗宿主资源。
- dependency download、codegen、post-install hook、自定义 compiler/plugin、custom analyzer 和 test fixture bootstrap 必须先确认再运行。
- 不盲跑 arbitrary build/test command；无法隔离副作用时，先做静态检查或让人工确认具体命令与权限。

### 构建修改的审查顺序

1. **复现原始命令**：从干净 build directory 执行项目已有 configure 和 build 命令，保留第一条 compiler/linker error。
2. **定位 target 边界**：确认 include directory、compile definition、compile option 和 link dependency 应属于哪个 target。
3. **使用 target-scoped 配置**：优先 `target_compile_features`、`target_include_directories`、`target_link_libraries` 等局部声明，避免全局 flags 污染无关 target。
4. **检查传递属性**：`PRIVATE`、`PUBLIC`、`INTERFACE` 必须对应真实消费关系，不能为了让本机编译通过全部改成 `PUBLIC`。
5. **验证生成命令**：查看 verbose build 或 compilation database，确认 AI 修改实际进入目标 translation unit。
6. **验证安装和消费**：库项目还要测试 install/export 后由独立 consumer 引用，不能只验证源码树内构建。

### 模板报错与链接错误的处理

AI 对长模板诊断适合做“候选根因压缩”，不适合直接把最后一行错误当根因。要求它按以下格式分析：

- 第一处用户代码实例化点是什么。
- substitution、constraint 或 overload resolution 在哪一步失败。
- 哪个候选被排除，原因来自类型、cv/ref、lifetime 还是 concept。
- 最小修复是否改变 public API、value category 或 overload set。
- 应增加哪个最小 compile test 防止回归。

链接错误要先区分：

- declaration 存在但 definition 缺失；
- template definition 对实例化点不可见；
- symbol name/namespace/signature 不一致；
- static library link order 或 transitive dependency 缺失；
- ABI、visibility、architecture 或 standard library 不一致；
- ODR violation、重复定义或 inline 定义不等价。

不要让 AI 用“把定义都移到头文件”“加入所有库”“关闭 warning/error”作为默认修复。

### 可复现提示词

```text
先读取当前 target 的构建文件、compile_commands.json 和失败命令。
环境：C++20、Clang 17、libc++、arm64。
任务：只修复 target `cache_tests` 的第一处编译错误。
要求：
1. 保留完整英文 compiler diagnostic，并指出第一处用户代码实例化点。
2. 不新增依赖，不修改全局 compiler flags，不关闭 warning。
3. 说明修复是否影响 ABI、exception specification 或 overload resolution。
4. 用原失败命令和该 target 的测试验证；未运行的配置明确标记。
```

### 连续追问

1. AI 如何确认实际编译的是 C++20，而不是只看到 `CMAKE_CXX_STANDARD` 就下结论？
2. header-only dependency 为什么仍可能有 ABI、macro 和 compile option 冲突？
3. 模板错误最后出现的 standard library stack 为什么经常不是根因位置？
4. 本机 debug build 通过后，为什么仍要验证 release、sanitizer 和目标部署 toolchain？

### 常见幻觉

- 生成不存在的 CMake command、target 名或 package component。
- 混用 GCC、Clang 和 MSVC flags，或把某个 compiler extension 当成标准语法。
- 未读取 build graph 就新增全局 include path、definition 或 linker option。
- 看到 `undefined reference` 就补库，未核对 signature、namespace、ABI 和 link order。
- 修改 template constraint 后只说“编译器能推导”，没有实际编译目标实例。

---

## 2. 生命周期、所有权与未定义行为审查

### 先画所有权与借用关系

AI 审查 C++ 生成代码时，应先为每个资源回答：

- 谁创建，谁拥有，谁销毁；
- 所有权是唯一、共享、外部托管还是纯借用；
- 借用能否跨线程、回调、容器重分配、异步任务或协程挂起点；
- move 后源对象满足什么不变量；
- 构造中途失败、赋值失败和析构阶段分别清理什么；
- raw pointer/reference/view 是否可能比 owner 活得更久。

仅看到 smart pointer 并不能结束审查。`std::shared_ptr` 可以避免特定对象过早销毁，但不能自动避免 cycle、data race、逻辑资源泄漏或 pointee 并发访问。

### AI 应重点标记的生命周期风险

- 返回局部对象的 pointer、reference、iterator、`std::span` 或 `std::string_view`。
- lambda 以引用捕获局部变量后进入异步执行器。
- container reallocation/erase 后继续使用 pointer、reference 或 iterator。
- 把 `this` 捕获进生命周期超过对象的 callback。
- custom deleter 与资源实际释放 API 不匹配。
- placement construction 后遗漏 destruction，或对象 lifetime 尚未开始就访问存储。
- base class 通过 base pointer 删除但 destructor 非 virtual。
- move assignment 覆盖旧资源、self-move 或 moved-from 状态处理错误。
- exception 路径中部分构造对象、锁、fd、内存或事务 token 未回滚。

### 异常安全必须用不变量表达

要求 AI 明确每个 operation 的保证等级，而不是笼统说“异常安全”：

- **no-throw guarantee**：操作不会抛；常用于 destructor、swap 和资源释放路径，但必须符合成员真实能力。
- **strong guarantee**：失败时对外可观察状态与调用前等价；常通过先构造临时结果再 commit。
- **basic guarantee**：失败后对象仍满足不变量且无资源泄漏，但值可能变化。
- **no guarantee**：异常后状态不受约束；若这是有意契约必须明确写出。

审查顺序是：列不变量、找可能抛点、判断每个抛点前后的已提交状态、检查 RAII rollback，最后再评价保证等级。给函数机械添加 `noexcept` 不是优化；若内部异常逃出，会调用 `std::terminate`。

### 未定义行为不能靠“运行正常”排除

AI 应把以下结论标记为待动态或编译器验证：

- use-after-free、double delete、out-of-bounds、invalid downcast；
- signed overflow、invalid shift、misalignment、strict aliasing violation；
- uninitialized read、invalid object lifetime、错误 format argument；
- data race、并发访问非线程安全对象；
- 越过 API lifetime contract 的 view、iterator 和 callback。

一次普通运行没有崩溃，只说明该输入与构建未观察到故障，不证明不存在 undefined behavior。优化级别、allocator、线程调度和目标架构变化都可能改变表现。

### 审查与验证矩阵

| 风险 | 静态审查问题 | 最小运行证据 |
|------|--------------|--------------|
| owning pointer | copy/move/delete 是否唯一 | unit test + ASan/LSan |
| borrowed view | owner 是否覆盖全部使用期 | boundary test + ASan |
| exception rollback | 哪些操作已提交 | fault injection test |
| polymorphic delete | base destructor 是否 virtual | compile test + UBSan |
| iterator invalidation | 哪个操作会失效 | targeted test + debug iterator（若实现支持） |
| integer/shift/alignment | 前置条件是否可证明 | UBSan + boundary cases |

### 提示词示例

```text
审查这段 C++20 代码的所有权和异常安全。
先输出资源表：resource、owner、borrower、release point、exception path。
再列出每个 public operation 的不变量和 guarantee。
不要把 shared ownership 当成线程安全。
给出能在修复前失败的测试，并分别指定 ASan、UBSan 或 LSan 的验证价值。
如果只能怀疑而不能证明，标记为 hypothesis，不要写成已确认缺陷。
```

### 连续追问

1. `std::string_view` 按值传递为什么仍可能悬空？
2. copy-and-swap 提供强保证时，copy 成本、allocator propagation 和 self-assignment 如何变化？
3. constructor 第三个成员初始化抛异常时，哪些 destructor 会运行，类自身 destructor 会不会运行？
4. ASan 未报错为何不能证明所有 lifetime contract 都正确？

### 常见幻觉

- 看到 smart pointer 就断言“无内存泄漏、线程安全”。
- 认为 move 一定清空所有字段，或 moved-from 对象只能析构不能赋值。
- 把 `noexcept` 当作忽略错误的语法，未分析 terminate 路径。
- 用一次 debug 运行证明 iterator、view 或 reference 生命周期安全。
- 为修复悬空引用把所有值改成共享所有权，制造 cycle 和不清晰生命周期。

---

## 3. 并发和内存模型审查

### 先定义共享状态与同步协议

AI 在给出锁、atomic 或 lock-free 修改前，必须列出：

- 哪些对象会被哪些线程访问；
- 哪些访问互相冲突，是否至少一个是写；
- 每个业务不变量由哪把 mutex、哪条消息传递或哪组 atomic order 保护；
- object lifetime 是否覆盖所有线程访问；
- shutdown 如何阻止新工作、唤醒等待者并 join；
- callback 和 task exception 如何传播或隔离。

“字段改成 atomic”只保护该字段的原子访问，不自动保护跨字段不变量、容器内部状态或 pointee。

### Mutex 与 condition variable 审查

- condition variable wait 必须绑定 predicate，并在同一 mutex 下读取 predicate 状态。
- 修改 predicate 后决定在锁内还是锁外 notify，应基于不变量和调度成本，不能机械套模板。
- 不在持锁期间执行未知 callback、阻塞 I/O、长任务或等待另一个 future。
- 明确 lock ordering；AI 若建议新增第二把锁，必须给出全局顺序或证明不会嵌套。
- shutdown 要区分停止接收、drain、immediate cancel 和 join；一个 bool 往往不足以表达复杂状态。
- thread destructor、异常路径和构造中途失败都必须处理 joinable thread。

### Atomic 与 memory order 审查

对每个 atomic operation 要求 AI回答：

1. 它保证的是原子读改写，还是还承担发布/获取普通内存的同步作用？
2. release operation 前有哪些写入要发布？
3. acquire operation 后有哪些读取依赖它可见？
4. 两者通过哪个 reads-from 或 release sequence 建立 synchronizes-with？
5. 若改成 relaxed，会丢失哪条 happens-before？
6. object reclamation 如何保证没有线程仍持有旧 pointer？

AI 生成的 `memory_order_relaxed/acquire/release/acq_rel/seq_cst` 不能仅靠代码看起来合理就接受。最少应有：

- 手工画出的 happens-before 关系；
- 对算法前提的文字证明；
- ThreadSanitizer 可覆盖的并发测试；
- 目标弱内存架构测试或可信模型工具（若项目采用）；
- 与正确锁版本的差分测试。

ThreadSanitizer 能发现许多实际 data race，但不证明算法线性化、memory order 最小性、ABA 安全或 reclamation 正确。

### Lock-free 不是默认答案

- 面试和生产修改都应先建立正确的锁版本与行为测试。
- lock-free 只表示系统级进展保证，不等于低延迟、低 CPU 或在当前负载更快。
- CAS loop 必须处理重试、contention、ABA、false sharing、backoff 和 starvation。
- pointer-based lock-free structure 还需要 hazard pointer、epoch、RCU-like protocol 或其他安全 reclamation。
- AI 若删除 mutex，必须提供等价语义、线性化点和 benchmark；仅说“减少锁竞争”不构成证据。

### 并发测试要求

- 用 barrier/latch 或明确握手建立起跑条件，不用 sleep 猜调度。
- 测试结束有 deadline，失败时输出线程状态或最小诊断。
- 重复运行只是提高暴露概率，不是正确性证明。
- 同一测试分别在普通 build、ThreadSanitizer build 和必要的 AddressSanitizer build 下运行。
- shutdown、空队列、满队列、exception、取消、构造失败和析构顺序都要有用例。

### 提示词示例

```text
审查这段 SPSC queue，不要先改 memory order。
输出：
1. producer/consumer 各自独占写的状态；
2. 每个槽位写入、索引发布、索引观察和槽位读取的 happens-before 链；
3. 每个 atomic operation 当前 order 的必要性；
4. relaxed 替换实验会破坏的具体可见性；
5. 与 mutex baseline 做差分测试的方案。
最后给出 TSan 能检查什么、不能检查什么。
```

### 连续追问

1. data race 与业务 race condition 有什么区别？无 data race 是否等于算法正确？
2. condition variable 为什么允许 spurious wakeup，predicate 应由谁保护？
3. release/acquire 同步建立后，哪些非 atomic 写入对读取线程可见？
4. TSan 通过后，为什么还不能证明 lock-free queue 的 reclamation 和线性化正确？

### 常见幻觉

- 用 `volatile` 解决线程可见性或原子性。
- 把所有 atomic 都改成 relaxed 并以“单变量原子”解释跨对象协议。
- 把所有操作都改成 sequential consistency，就宣称生命周期和算法一定正确。
- TSan 无报告即断言没有并发缺陷。
- 未建立性能 baseline 就把 mutex 改成 CAS loop。

---

## 4. 测试、Sanitizer 与性能证据

### 编译器是第一道验证

AI 生成 C++ 后至少执行目标项目的真实 compile command。建议在项目允许时启用严格 warning，但不得未经评估就修改整个仓库的 warning policy。
执行这些命令前仍要应用“不受信仓库”边界：先审查入口，在 sandbox/最小权限下运行，不带生产凭据，限制网络、文件访问和 CPU/内存/时间；依赖下载、codegen、post-install 与 custom analyzer 先确认。

典型局部验证命令示意：

```bash
cmake --preset debug
cmake --build --preset debug --target target_tests --verbose
ctest --preset debug --output-on-failure
```

独立小程序可使用：

```bash
clang++ -std=c++20 -Wall -Wextra -Wpedantic -Wconversion \
  -pthread example.cpp -o example
./example
```

实际命令必须以项目已有配置为准。只运行 formatter 或静态阅读不能发现 missing include、ODR、template instantiation、link 和 ABI 问题。

### 测试分层

- **Compile test**：模板是否可实例化、concept/overload 是否选择正确、header 是否 self-contained。
- **Unit test**：值语义、不变量、边界、异常和资源释放。
- **Concurrency test**：协调后的交错、shutdown、cancel 和压力场景。
- **Integration test**：真实 allocator、filesystem、socket、dynamic library 或目标 ABI。
- **Regression test**：先证明旧实现因预期原因失败，再验证修复。

AI 生成测试时要警惕：

- 只验证不崩溃，没有断言不变量；
- 测试复制了实现算法，二者可能一起错；
- 只测 happy path，没有注入 allocation、constructor、I/O 或 callback failure；
- 并发测试依赖 sleep；
- benchmark 被当作正确性测试。

### Sanitizer 选择

| 工具 | 主要发现 | 不能证明 |
|------|----------|----------|
| AddressSanitizer | 常见越界、use-after-free、部分 use-after-scope | 所有生命周期契约、逻辑泄漏、线程正确性 |
| UndefinedBehaviorSanitizer | 多类可动态检测的 undefined behavior | 标准中所有 UB、未执行路径 |
| LeakSanitizer | 进程退出时可达性相关的内存泄漏 | fd、连接、线程等非内存资源泄漏 |
| ThreadSanitizer | 被执行路径上的许多 data race | 无业务 race、无死锁、lock-free 算法正确 |
| MemorySanitizer | 部分未初始化内存读取（依赖完整插桩环境） | 未插桩依赖中的全部问题 |

常见命令示意：

```bash
clang++ -std=c++20 -O1 -g -fno-omit-frame-pointer \
  -fsanitize=address,undefined example.cpp -pthread -o example_asan
./example_asan

clang++ -std=c++20 -O1 -g -fno-omit-frame-pointer \
  -fsanitize=thread example.cpp -pthread -o example_tsan
./example_tsan
```

- ASan 与 TSan 通常分别构建运行，不应假设可随意组合。
- sanitizer 改变布局、时序和性能；sanitizer build 不用于性能结论。
- 某些平台、allocator、static link 或第三方 binary 与 sanitizer 不兼容，必须记录未覆盖范围。

### Benchmark 的最低证据标准

AI 声称“更快”“减少分配”“降低锁竞争”前，至少提供：

- 与语义等价 baseline 的 A/B 实现；
- 固定 compiler、flags、CPU、频率策略、输入分布和并发度；
- warmup、重复运行和统计结果，而非一次 wall-clock；
- 防止 dead-code elimination 的消费方式；
- 吞吐、延迟分位、CPU、allocation 和 contention 中与目标相关的指标；
- correctness tests 与 sanitizer tests 先通过；
- profile 指向被修改热点，而不是只看到 benchmark 数字变化。

microbenchmark 只回答受控小场景。线上收益还受 cache、NUMA、allocator、I/O、batching 和 workload distribution 影响。

### 性能审查流程

1. 描述业务指标和回归幅度。
2. 获取可复现 baseline。
3. 用 profiler 或硬件计数器定位热点。
4. 让 AI提出多个可证伪假设，不直接给“优化版”。
5. 每次只改变一个关键因素。
6. 运行正确性、sanitizer 和 benchmark。
7. 检查 p50/p99、CPU、memory、binary size 或 build time 是否发生副作用。

### 连续追问

1. 为什么 sanitizer build 的耗时不能用于证明生产优化收益？
2. ASan、UBSan、TSan 各自更适合验证哪些 AI 修改？
3. benchmark 快 10% 时，应检查哪些环境噪声、语义差异和统计问题？
4. compiler 优化掉待测逻辑时，benchmark 会产生什么假象？

### 常见幻觉

- 生成代码“语法看起来正确”就跳过 compiler。
- 一个 sanitizer 通过后推导所有 memory、thread 和 UB 风险均消失。
- 从 Big-O 或减少一行分配代码直接断言性能提升。
- 用 debug 与 release、不同 compiler flags 或不同输入比较。
- profile 没指向目标函数，仍按 AI 猜测重写热点。

---

## 5. AI 常见幻觉与验证方法

### 高风险幻觉表

| 幻觉类型 | 常见表现 | 必须验证 |
|----------|----------|----------|
| 不存在或版本错误的 API | 混用不同 standard、compiler intrinsic 或 library version | 目标 toolchain 编译与官方 header |
| 错误 lifetime | 返回临时 view、异步捕获引用、move 后重复释放 | 边界测试、ASan/LSan、所有权审查 |
| 错误 exception guarantee | 随意加 `noexcept`，部分提交后宣称强保证 | fault injection、不变量测试 |
| 错误原子序 | 无 happens-before 证明就选择 relaxed/acquire/release | 内存模型推导、TSan、弱内存测试 |
| 错误模板修复 | 用 cast、删除 constraint 或移头文件掩盖根因 | 原实例化命令、compile test |
| 错误性能结论 | “无锁必然更快”“move 一定零成本” | 等价 benchmark、profile、目标负载 |
| 错误平台假设 | 写死 pointer、cache line、fd 或 syscall 行为 | target/ABI/OS 文档与目标运行 |

### 最小验证闭环

1. **审查执行边界**：把仓库命令视为不受信输入，先读脚本；使用 sandbox/最小权限且无生产凭据，限制网络、文件、CPU、内存和时间，确认 download/codegen/post-install/custom analyzer。
2. **固定上下文**：记录 standard、compiler、standard library、target、flags、依赖和运行平台。
3. **保留原错误**：完整保存第一条 compiler/linker/sanitizer 英文诊断与调用栈，不只贴 AI 摘要。
4. **先构造反例**：把修复目标变成 compile failure、unit failure、sanitizer report 或 benchmark baseline。
5. **最小修改**：不顺手升级依赖、切换 build system 或重写无关抽象。
6. **局部验证**：原失败命令、聚焦测试和对应 sanitizer。
7. **范围验证**：相关 target、integration configuration 和 release build。
8. **性能验证**：只有正确性闭环后才运行 benchmark/profile。
9. **人工解释**：审查者能说明 ownership、exception guarantee、happens-before 和证据边界。

### 面试问题与评价

1. AI 生成一个拥有裸指针的类，你会先问哪些 ownership 和 Rule of Zero/Five 问题？
2. AI 把 mutex 改成 atomic 后，怎样证明跨字段不变量仍成立？
3. 一段 template error 有数百行，怎样找第一处用户实例化点而不是删除 constraint？
4. AI 声称 SPSC queue 提升 3 倍，哪些 correctness、sanitizer 和 benchmark 条件缺一不可？
5. ASan/TSan 都通过后，还有哪些未覆盖风险必须人工分析？

**实习/应届达标：**

- 会先编译和运行测试，不把 AI 输出直接当答案。
- 能识别悬空 reference/view、重复释放、未 join thread 和基础 data race。
- 知道 ASan 与 TSan 解决不同问题，性能要有 benchmark。

**社招达标：**

- 能绑定 build target、ABI、exception guarantee 和 concurrency invariant。
- 能解释 sanitizer 覆盖边界、happens-before 和 lock-free reclamation 风险。
- 能设计等价 baseline、可复现 benchmark 与 profile 驱动的优化闭环。

### 最终准入清单

- [ ] 仓库脚本和构建入口已审查；命令在 sandbox/最小权限、无生产凭据、受限网络/文件/CPU/内存/时间条件下执行。
- [ ] 依赖下载、codegen、post-install、自定义 compiler/plugin 和 custom analyzer 的来源与副作用已确认。
- [ ] 真实目标由目标 compiler 成功编译并链接。
- [ ] 新旧行为由聚焦测试覆盖，错误路径和退出路径已验证。
- [ ] ownership、borrow 和 object lifetime 有明确契约。
- [ ] exception guarantee 与所有 `noexcept` 声明可解释。
- [ ] 并发共享状态、锁顺序、happens-before 和 shutdown 可解释。
- [ ] 对应 ASan/UBSan/TSan/LSan 已运行，或未运行原因和风险已记录。
- [ ] 性能声称有等价 benchmark 与 profile 证据。
- [ ] 未把单个 compiler、standard library、ABI 或 OS 实现写成通用标准保证。
