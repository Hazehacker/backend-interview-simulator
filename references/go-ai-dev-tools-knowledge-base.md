# AI 辅助 Go 后端开发知识库

> 本文件只维护 AI 在 Go 语言、标准库、工具链、并发诊断和性能验证中的专项用法。
> 生成代码至少经过 `gofmt`、`go vet`、单元测试和 `go test -race`；性能结论必须有 Go benchmark 与 pprof/trace 证据。AI 的静态解释不能替代这些检查。

---

## 1. 模块、接口与标准库上下文

### 修改前必须读取的事实

AI 生成或修改 Go 代码前，应先读取：

- `go.mod` 的 `module`、`go`、`toolchain`、`require`、`replace` 和 `retract`。
- workspace 是否有 `go.work`，当前命令实际加载哪些 module。
- `go env GOOS GOARCH CGO_ENABLED GOPROXY GOWORK` 与目标部署环境。
- package 边界、internal 目录、build tag、generated file 和 platform-specific file。
- 目标接口的定义、已有实现、constructor、zero value contract 和错误约定。
- 标准库与第三方依赖的目标版本文档，而不是模型记忆中的最新 API。
- CI 实际执行的 format、vet、test、race、lint、build 和生成命令。

不要只根据目录名猜 package path，也不要看到一个 interface 就自动创建 mock、adapter 或新抽象。先找调用者与已有实现，确认变更点属于 provider 还是 consumer。

### 执行不受信仓库命令的安全边界

仓库内的 Makefile、shell script、`go generate` directive、测试入口和 analyzer 配置都是待审查代码，不能因为命令看似标准或由 AI 推荐就直接运行。执行前必须：

- 先阅读 wrapper script、`go:generate`、Make target、CI helper 和实际子命令，识别下载、上传、删除、写 home directory、启动服务与 shell expansion。
- 在 sandbox、容器或其他最小权限环境运行，不注入生产凭据、个人 token、SSH agent、云端 metadata、真实数据库连接串或业务数据。
- 默认限制网络和文件系统访问，只开放 module/workspace 与临时目录；依赖下载必须确认 proxy/source、module version、checksum 和网络目的地。
- 设置 CPU、内存、进程/goroutine、磁盘和时间上限，防止恶意或失控的 test、fuzz、benchmark 或 code generation 消耗宿主资源。
- dependency download、codegen、post-install hook、cgo build script、custom analyzer、tool install 和 test fixture bootstrap 必须先确认再运行。
- 不盲跑 arbitrary build/test command；无法隔离副作用时，先做静态检查或让人工确认具体命令与权限。

### 模块与依赖修改

AI 建议新增依赖时必须回答：

1. 标准库能否完成目标。
2. 当前 module 是否已有等价依赖。
3. 新依赖支持的 Go 版本是否兼容 `go.mod`。
4. 是否增加 transitive dependency、cgo、binary size 或供应链成本。
5. `go mod tidy` 会删除或新增什么，是否影响 build-tagged package。
6. license、维护状态和 vulnerability 审查由谁完成。

不能为了让本机编译通过随意加入 `replace` 指向本地路径，也不能在未说明原因时整体升级 dependency graph。依赖变化应通过 `go mod tidy` 后的 diff、`go list -m all` 和目标 package 测试验证。

### 接口与类型设计审查

- interface 应由使用方围绕最小行为定义，不是把实现类所有方法复制一遍。
- 接受 interface、返回具体类型通常能保留实现能力，但不是机械规则；要看 ownership、test seam 和 compatibility。
- typed nil 可能让 `error` 或其他 interface 非 nil；AI 生成 error wrapper 和 mock 时必须覆盖。
- method set 受 value/pointer receiver 影响；接口实现要用 compile-time assertion 或实际赋值编译验证。
- 泛型约束是 compile-time type set，不等于 runtime interface；不要用 `any` 和 type assertion 绕过本可静态表达的关系。
- zero value 是否可用、copy 是否安全必须明确；含 `sync.Mutex`、`sync.Once`、atomic 状态或 runtime handle 的类型通常不应在使用后复制。

接口变更还要检查所有实现、compile-time assertions、generated mocks 和跨 module consumer。AI 说“只加一个方法”并不代表兼容：给已有 interface 增加方法会让所有外部实现失效。

### 标准库 API 的版本核对

AI 常混用不同 Go 版本的 package API、runtime 行为和语言语义。验证顺序：

```bash
go version
go env GOMOD GOWORK GOOS GOARCH
go list -deps ./path/to/package
go doc package.Symbol
go test ./path/to/package
```

- 以目标 toolchain 的 `go doc`、源码和编译结果为准。
- 语言变化还要结合 `go.mod` 的 `go` line，不能只看安装的 toolchain。
- build constraint 应用 `go list` 验证实际选中文件，不凭文件后缀猜测。
- reflection、unsafe、runtime 和 compiler optimization 结论要标记为实现/版本相关。

### AI 生成代码的基础闭环

以下基础命令不是自动授权。执行前仍要审查不受信仓库脚本与生成入口，并在 sandbox/最小权限、无生产凭据、受限网络/文件/CPU/内存/时间的环境运行；dependency download、codegen、post-install 与 custom analyzer 先确认。

```bash
gofmt -w path/to/changed.go
go vet ./path/to/package
go test ./path/to/package
go test -race ./path/to/package
```

生产仓库应使用已有脚本或 CI target，避免局部命令漏掉 code generation、custom analyzer 或 integration tag。`gofmt` 通过只证明格式规范，`go vet` 也不是完整 correctness proof。

### 提示词示例

```text
先读取 go.mod、目标 package、接口定义、全部实现和现有测试。
只修改 package `worker`。
要求：
1. 不新增第三方依赖，除非先说明标准库为何不足。
2. 保留现有 error wrapping 和 context contract。
3. 检查 typed nil、pointer/value method set 和类型是否被复制。
4. 运行 gofmt、go vet、go test、go test -race。
5. 保留关键英文错误原文；未验证的 build tag 和平台明确列出。
```

### 连续追问

1. 为什么安装 Go 1.24 不代表 module 中所有语言语义都按 1.24 生效？
2. 给 interface 增加一个方法为何可能破坏仓库外的实现？
3. `go mod tidy` 产生大 diff 时，如何区分合法的 build-tag dependency 与误删？
4. `go vet` 通过后还需要哪些 compile、test 和 runtime 证据？

### 常见幻觉

- 生成目标 Go 版本不存在的标准库函数或字段。
- 使用错误 import path，或忽略 module path 与 internal 可见性。
- 自动加入第三方 package 解决标准库已能解决的问题。
- 认为 interface 值里装的是 nil pointer，所以 interface 一定等于 nil。
- 用 `replace ../local` 修复依赖并把本机路径带入提交。

---

## 2. Goroutine 生命周期与并发审查

### 每个 goroutine 都要有退出证明

AI 生成 `go func()` 时必须同时回答：

- 谁启动它，启动次数是否有上界。
- 正常完成条件是什么。
- 谁发送 cancel/close/stop 信号。
- 它可能阻塞在哪些 send、receive、lock、I/O、timer 或 syscall。
- 父函数提前返回、首错、timeout 和 shutdown 时如何退出。
- 谁等待它结束；不等待是否是有意的进程级后台生命周期。
- panic 和 error 如何被观察。

“goroutine 很轻量”不能作为省略生命周期的理由。阻塞 goroutine 会保留 stack、引用对象、timer、socket 和业务资源。

### Channel ownership 审查

- channel 的创建方应声明谁拥有发送权和关闭权。
- 一般由能够确定“不再有任何 sender”的协调者 close；receiver 不为通知 sender 而关闭数据 channel。
- close 是广播“以后不会再有值”，不是通用 cancellation。取消优先使用 context 或专用 done protocol。
- send 与 close 并发会 panic；多 sender 场景必须由单一协调者在全部 sender 退出后关闭。
- nil channel 的 send/receive 永久阻塞，常用于动态禁用 select case，但也容易造成泄漏。
- 从 closed channel receive 会立即返回零值和 `ok=false`；忽略 `ok` 可能形成零值 busy loop。
- 缓冲 channel 只改变阻塞时机，不自动解决 ownership、backpressure 或退出。

要求 AI 为 pipeline 画出：

```text
producer --owns send--> jobs --worker receives
workers --owns send--> results --collector receives
feeder closes jobs
coordinator waits workers, then closes results
context cancellation reaches every blocking edge
```

### Context 与取消传播

- `context.Context` 作为第一个参数沿调用链传递，不存入 struct 作为默认长期状态。
- 不用 `context.Background()` 替换已有 request context。
- 创建 `WithCancel`、`WithTimeout` 或 `WithDeadline` 后及时调用 CancelFunc，释放 timer 和 child reference。
- select 的每个可能永久阻塞 send/receive 都要考虑 `ctx.Done()`。
- context cancellation 是协作式的；被调用函数必须观察它，Go 不能安全强杀任意 goroutine。
- context value 只放 request-scoped metadata，不放可选业务参数或大型可变对象。
- 错误语义要区分父取消、deadline、业务错误和首个下游错误，不盲目用 `ctx.Err()` 覆盖根因。

### `sync`、atomic 与共享内存

- Go memory model 不保证 data-race 程序的业务结果；先消除 race，再讨论逻辑正确性。
- mutex 应保护明确不变量；不要给每个字段一把锁后失去跨字段原子性。
- `RWMutex` 只有在真实 read-only 临界区和 profile 证据下才可能有收益；LRU `Get` 等操作会写 recency。
- `WaitGroup.Add` 必须在相应 goroutine 可完成之前建立正确时序；不要让 `Wait` 与新的 `Add` 形成不受约束竞争。
- `sync.Once` 执行的函数 panic 后仍被视为已调用；AI 生成 lazy init 时应确认失败语义。
- atomic 只保护对应操作；多字段 invariant 仍需锁、不可变快照或明确 protocol。
- copylocks：使用后的 mutex、once 或含这些字段的 struct 不应按值复制，`go vet` 可发现部分问题。

### 常见并发生成缺陷

- range loop 中启动 closure 时忽略 module 的语言版本和变量捕获方式。
- 多 goroutine append 同一 slice、写同一 map 或更新 error 变量。
- error channel 无 buffer，调用者首错返回后 sender 泄漏。
- `time.After` 在热点循环中持续创建 timer；ticker 未 `Stop`。
- worker pool 关闭顺序错误：先 close result，再等待 sender。
- recovery 只在父 goroutine；子 goroutine panic 不会被另一个 goroutine 的 defer 捕获。
- `select { default: }` 轮询共享状态造成 busy loop。

### Race Detector 的正确位置

`go test -race` 是 AI 并发修改的最低动态验证，但它只报告当前执行路径观察到的 race：

- 增加并发测试、重复关键场景和真实 workload 可以提高覆盖概率。
- 未报告不证明没有 race，更不证明无 deadlock、goroutine leak 或业务顺序错误。
- race build 开销很大，不用于性能结论。
- 测试应使用 barrier、channel 或 hook 控制交错，不用 sleep 猜调度。
- 发现报告时保留完整英文 stack，包括 conflicting access 与 goroutine creation stack。

### 提示词示例

```text
审查这段 Go pipeline。
为每个 goroutine 输出 owner、block points、normal exit、error exit、cancel source、join point。
为每个 channel 输出 creator、sender、receiver、closer 和关闭前置条件。
指出共享 map/slice/error 的同步协议。
先设计能暴露 blocked send 或 race 的测试，再修改实现。
修改后运行 go test 和 go test -race；不要用 sleep 作为同步。
```

### 连续追问

1. channel close 与 context cancel 的语义分别是什么，什么时候不能互换？
2. 一个长度为 N 的结果缓冲为何能避免 N 个“一次发送”任务在调用者提前返回时阻塞？它不能解决什么？
3. race detector 无报告时，如何继续检查 goroutine leak、deadlock 和业务竞态？
4. 多字段状态都改成 atomic 后，如何证明快照不变量仍成立？

### 常见幻觉

- “channel 是线程安全的，所以整个 pipeline 没有 race。”
- “context cancel 会立即杀死所有 goroutine。”
- “加 buffer 就不会泄漏”，却没有计算 sender 上界。
- “只读 map 并发安全”，但另一个 goroutine 仍可能写。
- race detector 一次通过后宣称并发实现已被证明正确。

---

## 3. HTTP、RPC 与数据库代码审查

### `net/http` client 审查

AI 生成 outbound HTTP 代码时检查：

- 复用 `http.Client` 与 `Transport`，不要每次请求创建新的连接池。
- request 使用调用方 context，例如 `http.NewRequestWithContext`。
- 明确总 timeout、dial、TLS handshake、response header、idle connection 等不同预算，不把一个值复制到所有层。
- `Do` 成功得到 non-nil response 后，按契约关闭 body；是否需要 drain 取决于协议、响应大小和 Transport 复用要求。
- 检查 status code 后再 decode，不把非 2xx body 当成功对象。
- 限制 response body 大小，避免不可信响应耗尽内存。
- retry 只用于幂等或有 idempotency contract 的操作；必须受总 deadline、次数和 backoff 限制。
- 日志不输出 Authorization、Cookie、token 或完整敏感 body。

AI 常生成 `defer resp.Body.Close()` 在错误检查之前，导致 nil dereference；也常遗漏 body close，造成连接无法复用和资源增长。

### HTTP server 与 middleware 审查

- `http.Server` 设置合理的 header/read/write/idle 限制，并按服务协议评估 streaming 例外。
- handler 尊重 `r.Context()`；客户端断开或 server shutdown 后下游应可取消。
- 限制 request body，校验 content type，区分 decode error、validation error 和 trailing garbage。
- status/header 只能在首次写出前可靠设置；recovery 不能保证覆盖已发送响应。
- middleware 构建后应只读；请求级可变状态放在局部变量或受同步保护的对象。
- 自定义 `ResponseWriter` wrapper 要处理目标版本中的可选能力，不能无意破坏 streaming/hijacking。
- graceful shutdown 需要 deadline，并等待 handler 收敛；后台 goroutine 也要纳入生命周期。

### RPC client/server 审查

具体 RPC framework API 必须按项目依赖版本核对，但 Go 层面的审查问题稳定：

- deadline 是否从入站 context 传播到下游。
- status/error code 是否保留，不把全部错误转换为通用字符串。
- retry 是否由 client、middleware 和业务层重复执行，形成乘法放大。
- streaming 的 send/receive goroutine 是否有单一关闭协议和退出 join。
- request/response 是否被跨 goroutine 修改，生成对象是否允许复用。
- interceptor 顺序是否改变认证、日志、metrics、retry 和 recovery 语义。
- connection/client 是否长期复用，shutdown 时由谁关闭。

AI 不应凭记忆生成某框架 option；必须编译目标 module，并执行最小 integration test。

### `database/sql` 专项审查

这里审查的是 Go client 使用方式，不替代数据库设计：

- `*sql.DB` 是并发安全的连接池 handle，应长期复用，不每个请求 open/close。
- 所有 query/exec/begin 使用 context-aware API，让 deadline 可传播到 driver。
- `Rows`、`Stmt` 和 `Tx` 按所有权及时关闭；循环后检查 `rows.Err()`。
- transaction 明确 commit/rollback protocol。常见模式是在 begin 成功后 `defer tx.Rollback()`，成功路径显式 `Commit()`；仍需按 driver 契约处理错误。
- 不在 transaction 中执行无界远程调用或等待无关 goroutine。
- 占位符和 driver 行为按当前 driver 验证，不跨生态猜语法。
- `SetMaxOpenConns`、`SetMaxIdleConns`、`SetConnMaxLifetime` 等需要根据下游容量与观测设定，不复制魔法数字。
- 错误判断使用 `errors.Is/As` 和 driver 公开类型，保留 `%w` 链；不要解析不稳定错误字符串作为唯一协议。

### 错误传播与观测

- 用 `%w` 包装时增加 operation/resource context，不重复写无信息的“failed”。
- 库函数返回 error，由进程边界决定日志；避免每层都记录同一错误。
- panic 只用于不可恢复 programmer invariant，不替代普通 I/O、decode 或 validation error。
- 并发 fan-out 要定义首错、全部错误或部分结果语义；不同语义需要不同收集结构。
- metrics label 不放 request ID、完整 URL、SQL 或 error message 等高基数字段。

### 验证矩阵

| 生成代码 | 聚焦测试 | 额外检查 |
|----------|----------|----------|
| HTTP client | fake server 验证 status/body/timeout | connection reuse 与 body close |
| HTTP handler | `httptest` 正常/错误/取消 | race、body limit、partial response |
| RPC | in-process 或项目 test harness | deadline、status、stream exit |
| `database/sql` | driver mock 只测协议，真实环境测 driver 行为 | rows close、rollback、pool stats |
| retry | fake clock/可控失败序列 | 总预算、幂等性、放大倍数 |

### 连续追问

1. `http.Client` 为什么应复用，response body 未关闭如何影响连接池？
2. handler 已经写出部分 body 后 panic，recovery 能保证什么，不能保证什么？
3. `database/sql` 中 `DB`、`Conn`、`Tx`、`Rows` 的生命周期分别由谁管理？
4. client、RPC middleware 和业务层都重试 3 次时，最坏请求放大是多少，如何收敛？

### 常见幻觉

- 每次 HTTP 请求新建 Client/Transport，并声称能自动复用全局连接。
- 对所有请求无条件 retry，包括非幂等写。
- 忽略 `rows.Err()` 或 response body close。
- 生成不存在的 RPC option、driver error type 或错误占位符。
- 把 request context 换成 Background，导致超时与断连不能传播。

---

## 4. 测试、Race Detector、pprof 与 trace

### 格式、静态检查和测试顺序

Go AI 修改的最低本地闭环：

```bash
gofmt -w path/to/changed.go
go vet ./path/to/package
go test ./path/to/package
go test -race ./path/to/package
```

如仓库使用 `goimports`、custom analyzer、golangci-lint、build tags、code generation 或 Make target，应执行仓库定义的命令。不能用新增工具擅自重排全仓库 import 或格式化无关文件。

建议顺序：

1. 写一个因目标缺陷而失败的聚焦测试并确认 RED。
2. 做最小实现，运行 package test。
3. 执行 `gofmt` 与 `go vet`。
4. 执行 `go test -race`，确保测试覆盖并发路径。
5. 执行受影响 module/package 的更大范围测试。
6. 有性能声称时再运行 benchmark 和 profile。

### 可靠测试设计

- table-driven test 适合同一规则的输入矩阵，不把无关行为塞进一张表。
- 并发测试使用 channel、barrier、hook 或 fake dependency 控制时序。
- timeout 用于防止测试永久挂起，但不能以 sleep 后“可能完成”作为断言。
- 使用 `t.Cleanup` 关闭 server、cancel context、停止 goroutine 并检查临时资源。
- 测试 error chain 时使用 `errors.Is/As`，不要只比较完整字符串。
- 测试 context 时覆盖调用方取消、deadline、下游错误和正常完成。
- goroutine leak 测试优先验证协议 join；必要时比较稳定状态并分析 goroutine profile，不把瞬时总数当唯一断言。
- integration test 区分 mock 能证明的调用协议和真实 driver/network 才能证明的行为。

### Race Detector

常用命令：

```bash
go test -race ./path/to/package
go test -race -count=10 ./path/to/package
```

- `-count` 可提高执行覆盖概率，但不提供形式证明。
- 保留完整 `WARNING: DATA RACE`、Read/Write stack 和 goroutine creation stack。
- 修复共享访问协议，不用删除测试、降低并发或添加 sleep 掩盖报告。
- race build 有显著开销和不同 timing；不能拿它做性能 benchmark。
- 未执行到的路径、逻辑 deadlock、goroutine leak 和 channel ownership 错误可能没有 race report。

### Benchmark

使用标准 testing benchmark，并报告 allocation：

```bash
go test -run='^$' -bench='BenchmarkName$' -benchmem -count=10 ./path/to/package
```

最低要求：

- A/B benchmark 使用相同输入、setup 边界和 correctness contract。
- 不把一次结果或不同机器结果直接比较。
- 区分 `ns/op`、`B/op`、`allocs/op` 与服务级 latency/throughput。
- setup 是否计入要明确，必要时使用 benchmark timer 控制。
- 避免结果未消费而被 compiler 优化，也避免 benchmark 同时测随机生成或日志。
- 并发 benchmark 明确并发度、共享状态和目标 workload，不用 `RunParallel` 就自动代表线上。
- 统计比较应保存原始多次结果，可使用项目已有比较工具。

### pprof

pprof 用于回答“资源花在哪里”，不是自动给根因：

- CPU profile：采样 CPU stack，检查热点是否覆盖故障窗口。
- heap profile：区分 in-use 与 allocated 视角，结合 GC 时点解释。
- allocs profile：定位累计分配来源。
- goroutine profile：观察阻塞 stack 与数量，但要区分正常长期 goroutine。
- mutex/block profile：需要相应采样配置，数据有开销且表示等待样本，不等于完整因果。
- threadcreate 等 profile 只提供特定资源线索。

示意命令：

```bash
go test -run='^$' -bench='BenchmarkName$' -cpuprofile cpu.out ./path/to/package
go tool pprof -top cpu.out
```

服务环境要控制 profile 暴露权限、采样时长和生产开销，不把 debug endpoint 无保护暴露。

### Execution Trace

trace 适合观察 goroutine 调度、网络阻塞、syscall、GC、processor utilization 和 task/region 时间关系：

```bash
go test -run TestScenario -trace trace.out ./path/to/package
go tool trace trace.out
```

- trace 文件可能很大，应选择代表性短窗口。
- trace 能显示调度和阻塞现象，但业务根因仍需结合日志、profile 和代码协议。
- AI 对 trace 截图的解释必须指向具体时间区间、goroutine 和事件，不接受泛化的“调度器有问题”。
- profile 与 trace 有不同观察成本和问题类型，不能互相替代。

### 性能证据闭环

1. 定义问题指标：CPU、allocation、p99、goroutine、mutex wait 或 scheduler latency。
2. 固定 Go/toolchain、GOOS/GOARCH、CPU、环境变量、输入和并发度。
3. 建立 benchmark 或可重复 workload baseline。
4. 用 pprof/trace 定位证据，形成可证伪假设。
5. 做单一关键修改。
6. 重新运行 format、vet、test、race。
7. 重跑 benchmark/profile，比较收益与副作用。

### 连续追问

1. `go test -race` 为什么不能与普通 benchmark 数字直接比较？
2. heap profile 的 in-use 与 allocs 视角分别回答什么问题？
3. CPU profile 没有指向目标函数时，为什么不应按 AI 建议直接重写它？
4. trace 看到大量 runnable goroutine 时，还需要哪些业务、阻塞和 CPU 证据才能归因？

### 常见幻觉

- `gofmt`、`go vet` 通过就宣称程序正确。
- race detector 没报告就宣称没有 deadlock、leak 或业务竞态。
- benchmark 单次变快就断言优化有效。
- 只看 pprof top 一行，不检查采样窗口、调用图和 workload。
- 看到 trace 调度事件就归因 runtime，而不检查无界 goroutine 和阻塞协议。

---

## 5. AI 常见幻觉与验证方法

### 高风险幻觉表

| 幻觉类型 | 常见表现 | 必须验证 |
|----------|----------|----------|
| API/版本幻觉 | 使用目标 Go/依赖版本不存在的函数或 option | `go doc`、compile、目标版本测试 |
| 模块幻觉 | import path、internal 边界、replace 或 build tag 错误 | `go list`、`go mod tidy` diff |
| 并发幻觉 | channel 安全被扩展成整个状态安全 | ownership 表、`go test -race`、退出测试 |
| 取消幻觉 | 认为 cancel 会强杀 goroutine | 每个阻塞点与下游 context contract |
| 错误幻觉 | typed nil、错误链丢失、首错被 ctx error 覆盖 | `errors.Is/As`、失败路径测试 |
| HTTP/RPC 幻觉 | 错误 timeout/retry/stream close API | compile、fake/integration server |
| 数据访问幻觉 | DB 每请求创建、Rows 未关闭、Tx 状态错误 | protocol test、真实 driver 验证 |
| 性能幻觉 | goroutine 越多越快、少一次分配必然降低 p99 | benchmark、pprof、trace |

### 最小验证闭环

1. **审查执行边界**：把仓库命令视为不受信输入，先读脚本；使用 sandbox/最小权限且无生产凭据，限制网络、文件、CPU、内存和时间，确认 download/codegen/post-install/custom analyzer。
2. **固定上下文**：记录 `go version`、`go.mod` 语言版本、module graph、GOOS/GOARCH、build tags。
3. **保留原证据**：完整保存 compile error、panic stack、race report、test failure 或 profile 时间窗口。
4. **先构造 RED**：用单元测试、并发测试或可复现 benchmark 捕获目标问题。
5. **最小修改**：不顺手升级依赖、改公共 interface 或重构无关 package。
6. **基础检查**：执行 `gofmt`、`go vet` 和聚焦 `go test`。
7. **并发检查**：执行 `go test -race`，验证 cancel、close、error 和 join。
8. **范围检查**：执行受影响 module、build tag 和 integration test。
9. **性能检查**：有性能声称才运行 benchmark，并用 pprof/trace 解释。
10. **人工解释**：审查者能说清 goroutine/channel owner、错误语义和证据边界。

### 面试问题与评价

1. AI 生成一个 fan-out/fan-in pipeline，你如何列出每个 channel 的 creator、sender、closer 和退出前置条件？
2. `go test -race` 报告两个 stack 时，怎样定位共享对象和缺失的 synchronization？
3. AI 为 HTTP client 加三层 retry，你如何检查总 deadline、幂等性和请求放大？
4. benchmark 显示 allocs/op 下降但 ns/op 上升，应该如何解释和决策？
5. pprof 与 trace 分别适合回答哪些问题，哪些结论不能只靠其中一个得到？

**实习/应届达标：**

- 会运行 `gofmt`、`go vet`、`go test` 和 `go test -race`。
- 能说明 channel 关闭责任、context 取消和 error 返回路径。
- 能识别共享 map/slice、blocked send、timer/ticker 和 response body 泄漏。

**社招达标：**

- 能设计完整 goroutine lifecycle、deadline budget、首错/全错/部分结果语义。
- 能区分 mock protocol test 与真实 HTTP/RPC/driver 行为。
- 能用 benchmark、pprof 与 trace 建立性能证据链，并说明 race/profile 覆盖边界。

### 最终准入清单

- [ ] 仓库脚本、`go generate` 与测试入口已审查；命令在 sandbox/最小权限、无生产凭据、受限网络/文件/CPU/内存/时间条件下执行。
- [ ] 依赖下载、codegen、post-install、cgo build script、tool install 和 custom analyzer 的来源与副作用已确认。
- [ ] 目标 Go/toolchain、module graph、GOOS/GOARCH 与 build tags 已确认。
- [ ] `gofmt` 无差异，`go vet` 通过。
- [ ] 单元/集成测试覆盖正常、边界、错误和取消路径。
- [ ] `go test -race` 已运行，或未运行原因和风险已记录。
- [ ] 每个新增 goroutine 有 owner、退出条件、cancel source 和 join/进程生命周期说明。
- [ ] 每个 channel 的 sender、receiver、closer 和关闭前置条件明确。
- [ ] error 保留 cause，不存在 typed nil 或被无关 context error 覆盖。
- [ ] HTTP/RPC/database resource 有明确 close/reuse/timeout contract。
- [ ] 性能声称有可复现 benchmark，并由 pprof 或 trace 支撑。
- [ ] 未把 runtime 当前实现、单次测试或 AI 推断包装成规范保证。
