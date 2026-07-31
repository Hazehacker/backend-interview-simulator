# Go 后端编码题库

> 本文件只用于 Go 编码面试。面试前应读取目标项目 `go.mod` 的 Go 版本和依赖版本。
> 每题都必须检查五件事：goroutine 由谁启动、由谁停止、channel 由谁关闭、错误如何传播、共享状态如何避免 race。
> 评价优先级是正确退出与错误语义，其次是边界和复杂度，最后才是减少 goroutine 或分配。
> 本文件完整参考实现的最低语言版本为 Go 1.20，边界由 `errors.Join` 决定；第三方依赖仍须以目标项目 `go.mod` 声明及实际 toolchain 编译结果为准。

---

## 1. Worker Pool 与有界并发

### 实现可取消的平方计算池

**适用身份：** 实习 / 应届 / 社招

**考察点：** worker pool、bounded concurrency、channel ownership、context、错误与退出路径。

**题目：** 实现 `SquareAll(ctx, values, workers)`，并发计算每个非负整数的平方，保持输出顺序。

- 输入：`context.Context`、整数切片、正 worker 数。
- 输出：与输入等长且顺序相同的平方切片。
- 约束：负数返回错误；context 取消后所有 goroutine 最终退出；并发度不超过 `workers`。
- 禁止假设：发送或接收永不阻塞；第一个错误出现后其他 worker 会自动停止；多个 sender 可以随意关闭结果 channel。

**参考实现要点：**

```go
package challenges

import (
	"context"
	"fmt"
	"math"
	"sync"
)

type squareJob struct {
	index int
	value int
}

type squareResult struct {
	index int
	value int
	err   error
}

func SquareAll(ctx context.Context, values []int, workers int) ([]int, error) {
	if workers <= 0 {
		return nil, fmt.Errorf("workers must be positive")
	}
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()

	jobs := make(chan squareJob)
	results := make(chan squareResult)
	var wg sync.WaitGroup

	wg.Add(workers)
	for i := 0; i < workers; i++ {
		go func() {
			defer wg.Done()
			for {
				select {
				case <-ctx.Done():
					return
				case job, ok := <-jobs:
					if !ok {
						return
					}
					result := squareResult{index: job.index}
					if job.value < 0 {
						result.err = fmt.Errorf("value[%d] is negative", job.index)
					} else if job.value != 0 && job.value > math.MaxInt/job.value {
						result.err = fmt.Errorf("value[%d] square overflows int", job.index)
					} else {
						result.value = job.value * job.value
					}
					select {
					case results <- result:
					case <-ctx.Done():
						return
					}
				}
			}
		}()
	}

	go func() {
		defer close(jobs)
		for i, value := range values {
			select {
			case jobs <- squareJob{index: i, value: value}:
			case <-ctx.Done():
				return
			}
		}
	}()

	go func() {
		wg.Wait()
		close(results)
	}()

	output := make([]int, len(values))
	for result := range results {
		if result.err != nil {
			cancel()
			// 继续 drain，保证已在发送路径上的 worker 能退出。
			for range results {
			}
			return nil, result.err
		}
		output[result.index] = result.value
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	return output, nil
}
```

- jobs 只有 feeder 关闭；results 只有“等待全部 worker 的协调 goroutine”关闭。
- worker 的 send 和 receive 都监听 `ctx.Done()`，避免调用者提前返回后泄漏。
- 本题结果写入只发生在收集 goroutine，因此无需额外 mutex。
- **并发协议检查：** feeder/协调者分别拥有 jobs/results 的 close；cancel 后 feeder 与 worker 都可退出；首错包装后返回；共享结果只由 collector 写，不产生 race。

**连续追问：**

1. 第一层：为什么不能由任意 worker 在退出时关闭 `results`？
2. 第二层：第一个错误后若立即 return 而不 cancel/drain，哪些 goroutine 可能阻塞？
3. 第三层：如何把输出改成流式且仍保序？重排缓冲的上界是什么？
4. 第四层：任务执行不可取消时，context 能保证什么，不能保证什么？

**常见错误：**

- 每个输入启动一个 goroutine，实际没有有界并发。
- receiver 关闭 jobs/results，和 sender 并发发送后触发 `send on closed channel`。
- 返回错误时没有取消或继续接收，worker 永久阻塞在发送。
- 多个 worker 直接写共享 map/slice 的不相交关系未证明，导致 race 或顺序错乱。

---

## 2. Context 超时与取消传播

### 并发查询两个下游并合并结果

**适用身份：** 应届 / 社招

**考察点：** deadline budget、cancel propagation、错误包装、goroutine join、部分结果语义。

**题目：** 实现 `LoadProfile`，并发调用两个可取消函数；任何一个失败时取消另一个，并在总预算及下游约定的取消收敛时间内返回。

- 输入：父 context、总 timeout、两个 `func(context.Context) (string, error)`。
- 输出：两个结果；任一失败时返回带来源的错误。
- 约束：必须调用 cancel；函数返回前等待已启动 goroutine 结束；不接受部分成功。两个下游必须遵守 context，在取消后于接口约定的有限时间内返回；否则“总预算内返回”和“同步 join”无法同时保证。
- 禁止假设：取消会让下游立即返回；timeout 从 goroutine 真正开始运行时才计算；`context.Canceled` 总是根因。

**参考实现要点：**

```go
package challenges

import (
	"context"
	"fmt"
	"time"
)

type profileResult struct {
	name  string
	value string
	err   error
}

func LoadProfile(
	parent context.Context,
	timeout time.Duration,
	loadUser func(context.Context) (string, error),
	loadRole func(context.Context) (string, error),
) (string, string, error) {
	if timeout <= 0 {
		return "", "", fmt.Errorf("timeout must be positive")
	}
	ctx, cancel := context.WithTimeout(parent, timeout)
	defer cancel()

	results := make(chan profileResult, 2)
	run := func(name string, load func(context.Context) (string, error)) {
		value, err := load(ctx)
		results <- profileResult{name: name, value: value, err: err}
	}
	go run("user", loadUser)
	go run("role", loadRole)

	var user, role string
	var firstErr error
	for i := 0; i < 2; i++ {
		result := <-results
		if result.err != nil && firstErr == nil {
			firstErr = fmt.Errorf("%s: %w", result.name, result.err)
			cancel()
		}
		switch result.name {
		case "user":
			user = result.value
		case "role":
			role = result.value
		}
	}
	if firstErr != nil {
		return "", "", firstErr
	}
	if err := ctx.Err(); err != nil {
		return "", "", err
	}
	return user, role, nil
}
```

- 长度为 2 的结果缓冲允许两个 goroutine 即使在 cancel 后也完成发送；主函数仍接收两次，实现 join。
- 下游必须遵守 context 并在取消后有界返回。若旧接口完全忽略 context 或可能永久阻塞，应先隔离或改造该接口，不能把它当成本函数的合法输入；Go 调用方无法安全强杀 goroutine。
- 若业务要区分 timeout 与 parent cancel，使用 `errors.Is` 检查错误链，并保留下游原始错误。
- **并发协议检查：** 主函数创建且不必关闭固定次数结果 channel；cancel 后仍接收两次以 join；首个接收错误保留来源；goroutine 不写外部共享变量，结果经 channel 转移。

**连续追问：**

1. 第一层：为什么 `defer cancel()` 即使正常完成也必须保留？
2. 第二层：为什么这里只有两个结果时使用缓冲 channel 能简化退出？
3. 第三层：为什么 cancel-aware 且有界返回是同步 join 的前置契约？如果下游不合作，应在哪一层隔离？
4. 第四层：如何把总 deadline 分配给重试、两个下游和结果合并，避免每层都重新给完整 timeout？

**常见错误：**

- 在子调用中使用 `context.Background()`，切断父取消链。
- 忘记 cancel timer，或函数提前返回时未等待已启动 goroutine。
- 只返回 `ctx.Err()`，覆盖了先发生且更有诊断价值的下游错误。
- goroutine 写外部局部变量，主线程同时读取，产生 race。

---

## 3. 生产者消费者与关闭责任

### 合并多个生产者的数据流

**适用身份：** 实习 / 应届 / 社招

**考察点：** channel close ownership、fan-in、WaitGroup、取消、发送端退出。

**题目：** 实现 `Merge(ctx, inputs...)`，把多个只读 input channel 合并成一个 output。

- 输入：context 与任意数量 `<-chan int`。
- 输出：只读 output，包含各 input 在取消前成功转发的值；顺序只保证单个 input 内部顺序。
- 约束：所有转发 goroutine 退出后才关闭 output；context 取消后不得因下游不再接收而泄漏。
- 禁止假设：input 一定由本函数关闭；nil input 会自动跳过；多个 sender 可分别关闭 output。

**参考实现要点：**

```go
package challenges

import (
	"context"
	"sync"
)

func Merge(ctx context.Context, inputs ...<-chan int) <-chan int {
	out := make(chan int)
	var wg sync.WaitGroup

	for _, input := range inputs {
		if input == nil {
			continue
		}
		wg.Add(1)
		go func(ch <-chan int) {
			defer wg.Done()
			for {
				select {
				case <-ctx.Done():
					return
				case value, ok := <-ch:
					if !ok {
						return
					}
					select {
					case out <- value:
					case <-ctx.Done():
						return
					}
				}
			}
		}(input)
	}

	go func() {
		wg.Wait()
		close(out)
	}()
	return out
}
```

- 本函数不拥有 input，绝不关闭它们；它拥有 out，并由唯一协调者关闭。
- nil input 若进入 select receive 会永久禁用该 case；这里显式跳过，避免无意义 goroutine。
- 取消时可能丢弃尚未转发的数据，这是接口的一部分；若要求 drain，应定义不同协议。
- **并发协议检查：** 上游拥有 input close，Merge 协调者拥有 output close；context 终止所有 forwarder；本题无独立 error channel；共享 WaitGroup 的 Add 先于 Wait，数据只经 channel 传递。

**连续追问：**

1. 第一层：为什么只有创建 output 的组件负责关闭它？
2. 第二层：为什么 receive 后向 out 发送时还要再 select 一次 context？
3. 第三层：取消与某次发送同时 ready 时，是否保证不再输出任何值？若业务要求强保证怎么设计？
4. 第四层：如何加入 per-source 公平性、错误 channel 或来源标识？

**常见错误：**

- 每个 forwarder `defer close(out)`，第一个退出后其他 sender panic。
- Merge 主函数 return 后立即 close(out)，此时 sender 仍在运行。
- 只在 receive 处检查 cancel，最终阻塞在无人接收的 output send。
- 主动关闭不属于自己的 input，破坏上游所有权。

---

## 4. 多 Goroutine 顺序打印

### 三个 goroutine 循环输出 A/B/C

**适用身份：** 实习 / 应届

**考察点：** 协调协议、channel token ownership、退出路径、避免泄漏。

**题目：** 实现 `OrderedABC(ctx, rounds)`，使用三个 goroutine 生成 `ABCABC...`。

- 输入：context 与非负轮数。
- 输出：长度为 `rounds*3` 的字符串。
- 约束：三个 worker 都必须在函数返回前退出；不得依赖 sleep 调度顺序；取消返回 `ctx.Err()`。
- 禁止假设：向带一个缓冲的 token channel 发送一定不阻塞；关闭 token channel 等同于停止协议。

**参考实现要点：**

```go
package challenges

import (
	"context"
	"fmt"
	"math"
	"strings"
	"sync"
)

func OrderedABC(ctx context.Context, rounds int) (string, error) {
	if rounds < 0 {
		return "", fmt.Errorf("rounds must not be negative")
	}
	if rounds > math.MaxInt/3 {
		return "", fmt.Errorf("rounds is too large")
	}
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()

	tokens := []chan struct{}{
		make(chan struct{}, 1),
		make(chan struct{}, 1),
		make(chan struct{}, 1),
	}
	values := []byte{'A', 'B', 'C'}
	out := make(chan byte)
	var wg sync.WaitGroup

	for i := 0; i < 3; i++ {
		current, next, value := tokens[i], tokens[(i+1)%3], values[i]
		wg.Add(1)
		go func() {
			defer wg.Done()
			for n := 0; n < rounds; n++ {
				select {
				case <-ctx.Done():
					return
				case <-current:
				}
				select {
				case out <- value:
				case <-ctx.Done():
					return
				}
				select {
				case next <- struct{}{}:
				case <-ctx.Done():
					return
				}
			}
		}()
	}

	go func() {
		wg.Wait()
		close(out)
	}()
	if rounds > 0 {
		tokens[0] <- struct{}{}
	}

	var builder strings.Builder
	builder.Grow(rounds * 3)
	for value := range out {
		builder.WriteByte(value)
	}
	if err := ctx.Err(); err != nil {
		return "", err
	}
	return builder.String(), nil
}
```

- token channel 由协议持有但不需要 close；取消负责让每个阻塞点退出。
- 最后一轮仍会留下一个 token，但 channel 有容量且不再被访问，不会阻塞或泄漏。
- 结果仅由收集者写 `strings.Builder`，避免并发写入 race。
- **并发协议检查：** token/results 都由本函数创建，只有 results 在全部 sender 退出后关闭；cancel 是唯一提前退出信号；错误由主函数返回；builder 仅由 collector 写。

**连续追问：**

1. 第一层：sleep 为什么不能提供顺序保证？
2. 第二层：最后一次 C 把 token 传回 A 时，为什么不会阻塞？
3. 第三层：若 token channel 改为无缓冲，最终退出会在哪里死锁？
4. 第四层：用 `sync.Cond` 实现时，谓词、broadcast 和取消如何表达？

**常见错误：**

- 多 goroutine 直接并发写同一个 builder 或 slice。
- 依赖固定 sleep，让测试偶尔通过。
- 任意 worker 关闭其他 worker 仍可能发送的 channel。
- context 只在循环开头检查，阻塞 send/receive 仍无法退出。

---

## 5. 并发安全 LRU

### 实现固定容量泛型 LRU

**适用身份：** 实习 / 应届 / 社招

**考察点：** `container/list`、map、mutex、不变量、锁内回调风险、race。

**题目：** 实现并发安全的 `LRU[K,V]`，支持 `Get` 和 `Put`。

- 输入：正容量、comparable key、任意 value。
- 输出：命中 `Get` 返回值并提升 recency；`Put` 超容量淘汰最久未用项。
- 约束：平均查找/更新为常数复杂度；所有共享 list/map 状态使用同一同步协议。
- 禁止假设：`Get` 是只读操作；返回内部指针在解锁后不会变化；回调可在持锁时安全执行。

**参考实现要点：**

```go
package challenges

import (
	"container/list"
	"fmt"
	"sync"
)

type lruEntry[K comparable, V any] struct {
	key   K
	value V
}

type LRU[K comparable, V any] struct {
	mu       sync.Mutex
	capacity int
	items    *list.List
	index    map[K]*list.Element
}

func NewLRU[K comparable, V any](capacity int) (*LRU[K, V], error) {
	if capacity <= 0 {
		return nil, fmt.Errorf("capacity must be positive")
	}
	return &LRU[K, V]{
		capacity: capacity,
		items:    list.New(),
		index:    make(map[K]*list.Element, capacity),
	}, nil
}

func (c *LRU[K, V]) Get(key K) (V, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()
	element, ok := c.index[key]
	if !ok {
		var zero V
		return zero, false
	}
	c.items.MoveToFront(element)
	return element.Value.(lruEntry[K, V]).value, true
}

func (c *LRU[K, V]) Put(key K, value V) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if element, ok := c.index[key]; ok {
		element.Value = lruEntry[K, V]{key: key, value: value}
		c.items.MoveToFront(element)
		return
	}
	element := c.items.PushFront(lruEntry[K, V]{key: key, value: value})
	c.index[key] = element
	if c.items.Len() > c.capacity {
		oldest := c.items.Back()
		entry := oldest.Value.(lruEntry[K, V])
		delete(c.index, entry.key)
		c.items.Remove(oldest)
	}
}
```

- `Get` 修改 list，基础版本使用单 mutex 最清晰；不要为追求 `RWMutex` 引入错误共享读取。
- 返回 `V` 的副本；若 `V` 内含 map/slice/pointer，调用者仍可能共享底层数据，API 要另行约束。
- 淘汰回调若存在，应先在锁内取出值并维护不变量，再在锁外调用。
- **并发协议检查：** 本题不创建 goroutine/channel，因而没有 close/cancel 责任；构造错误同步返回；所有内部 list/map 状态由同一 mutex 保护，但 `V` 指向的外部状态不自动 race-free。

**连续追问：**

1. 第一层：list 与 map 如何共同达到平均常数复杂度？
2. 第二层：为什么 `Get` 不能持 `RLock`？
3. 第三层：值中含有 map 或 slice 时，“返回副本”为什么不等于深拷贝或线程安全？
4. 第四层：分片后如何处理容量分配、热点 key 和全局 LRU 语义变化？

**常见错误：**

- list/map 使用不同锁，跨结构不变量在中间状态被其他 goroutine 观察。
- 持锁执行用户 callback，导致死锁或长时间阻塞。
- 返回 `*list.Element` 给调用者，解锁后内部节点被淘汰。
- 测试只验证最终长度，不运行 `go test -race` 检查并发访问。

---

## 6. 可取消 Token Bucket 限流器

### 实现本地令牌桶

**适用身份：** 应届 / 社招

**考察点：** time semantics、mutex、context wait、边界、race-free 配置。

**题目：** 实现单进程 token bucket，`Allow()` 非阻塞，`Wait(ctx)` 等待一个 token。

- 输入：每秒补充速率 `rate > 0`、容量 `burst >= 1`。
- 输出：令牌可用时成功；等待被取消时返回 `ctx.Err()`。
- 约束：token 不超过 burst；并发调用安全；时间倒退时不产生负 token。
- 禁止假设：ticker 精确逐 tick 运行；浮点计算没有边界误差；本地 limiter 可提供分布式全局限流。

**参考实现要点：**

```go
package challenges

import (
	"context"
	"fmt"
	"math"
	"sync"
	"time"
)

type TokenBucket struct {
	mu     sync.Mutex
	rate   float64
	burst  float64
	tokens float64
	last   time.Time
}

func NewTokenBucket(rate float64, burst int) (*TokenBucket, error) {
	if rate <= 0 || math.IsNaN(rate) || math.IsInf(rate, 0) || burst <= 0 {
		return nil, fmt.Errorf("rate must be finite and positive; burst must be positive")
	}
	if uint64(burst) > uint64(1)<<53 {
		return nil, fmt.Errorf("burst exceeds exact float64 integer range")
	}
	now := time.Now()
	return &TokenBucket{
		rate: rate, burst: float64(burst),
		tokens: float64(burst), last: now,
	}, nil
}

func (b *TokenBucket) refill(now time.Time) {
	if now.Before(b.last) {
		return
	}
	b.tokens = math.Min(b.burst, b.tokens+now.Sub(b.last).Seconds()*b.rate)
	b.last = now
}

func (b *TokenBucket) Allow() bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.refill(time.Now())
	if b.tokens < 1 {
		return false
	}
	b.tokens--
	return true
}

func (b *TokenBucket) Wait(ctx context.Context) error {
	for {
		if err := ctx.Err(); err != nil {
			return err
		}
		b.mu.Lock()
		now := time.Now()
		b.refill(now)
		if b.tokens >= 1 {
			b.tokens--
			b.mu.Unlock()
			return nil
		}
		waitSeconds := (1 - b.tokens) / b.rate
		const maxTimerDuration = time.Duration(1<<63 - 1)
		maxWaitSeconds := float64(maxTimerDuration) / float64(time.Second)
		var wait time.Duration
		if waitSeconds >= maxWaitSeconds {
			wait = maxTimerDuration
		} else {
			wait = time.Duration(waitSeconds * float64(time.Second))
		}
		if wait < time.Nanosecond {
			wait = time.Nanosecond
		}
		b.mu.Unlock()

		timer := time.NewTimer(wait)
		select {
		case <-timer.C:
		case <-ctx.Done():
			if !timer.Stop() {
				// Go 1.23 起 Timer channel 默认不再保留 stale value；
				// 非阻塞 drain 同时兼容旧工具链已触发的 timer。
				select {
				case <-timer.C:
				default:
				}
			}
			return ctx.Err()
		}
	}
}
```

- 按经过时间懒补充，不为 limiter 常驻启动 goroutine，也没有 ticker 泄漏。
- `Wait` 不在持锁期间等待；醒来后重新检查，多个 waiter 不会共同消费一个 token。
- 可测试版本应注入 clock，避免真实 sleep 和不可控时间。
- **并发协议检查：** 本题不创建 goroutine/channel，退出由调用方 context 控制；取消返回 `ctx.Err()`；token/last 全部由同一 mutex 保护，timer 只属于当前调用。

**连续追问：**

1. 第一层：为什么按 elapsed time 补充比依赖每个 ticker tick 更稳健？
2. 第二层：多个 waiter 同时醒来后为什么必须重新竞争并检查 token？
3. 第三层：如何处理 timer stop/drain，避免资源滞留或错误接收？
4. 第四层：如何定义每 key 限流、动态配置和分布式一致性？本实现不能提供哪些保证？

**常见错误：**

- 每次 `Wait` 启动一个永不退出的 ticker goroutine。
- 计算等待后不重新检查，多个 waiter 超发 token。
- 未锁保护 `tokens/last`，race detector 报告并发读写。
- 把本地进程速率误称为多实例全局精确速率。

---

## 7. HTTP Middleware Chain

### 实现顺序明确的中间件组合器

**适用身份：** 实习 / 应届 / 社招

**考察点：** `net/http` 接口、闭包捕获、调用顺序、panic recovery、ResponseWriter 状态。

**题目：** 实现 `Chain(final, middlewares...)`，使中间件按声明顺序从外到内执行。

- 输入：最终 `http.Handler` 和若干 `func(http.Handler) http.Handler`。
- 输出：组合后的 handler；`Chain(h, A, B)` 调用顺序为 `A-before, B-before, h, B-after, A-after`。
- 约束：nil final 返回错误或显式 panic；middleware 不得在请求期间修改共享 chain；错误/panic 语义由具体 middleware 定义。
- 禁止假设：写 header 后还能修改 status；recover 后一定能重写已经发送的响应；request context 可忽略。

**参考实现要点：**

```go
package challenges

import (
	"fmt"
	"net/http"
)

type Middleware func(http.Handler) http.Handler

func Chain(final http.Handler, middlewares ...Middleware) (http.Handler, error) {
	if final == nil {
		return nil, fmt.Errorf("final handler is nil")
	}
	current := final
	for i := len(middlewares) - 1; i >= 0; i-- {
		if middlewares[i] == nil {
			return nil, fmt.Errorf("middleware[%d] is nil", i)
		}
		current = middlewares[i](current)
		if current == nil {
			return nil, fmt.Errorf("middleware[%d] returned nil handler", i)
		}
	}
	return current, nil
}
```

- 逆序包装才能保持声明顺序的进入语义。
- middleware 在构建期组合，服务请求时只读 handler graph，天然避免链本身的 race。
- recovery middleware 必须记录 panic，并理解响应可能已部分写出；它不能承诺任何时刻都能改成干净的 500。
- **并发协议检查：** Chain 不创建 goroutine/channel；请求退出和错误传播由 handler/context 契约决定；构建错误同步返回；共享 middleware 状态必须自行同步，组合后的链只读。

**连续追问：**

1. 第一层：为什么包装循环必须逆序？
2. 第二层：日志、认证、timeout、recover 的相对顺序会怎样改变可观察行为？
3. 第三层：handler 已调用 `WriteHeader(200)` 后 panic，recover middleware 能否可靠发送 500？
4. 第四层：自定义 `ResponseWriter` 统计状态码时，如何保留 Flusher/Hijacker/Pusher 等可选接口？

**常见错误：**

- 正序包装导致执行顺序与配置相反。
- 在请求期间 append 全局 middleware slice，产生 race。
- recovery 吞掉 panic 且不记录 stack，或声称一定能替换已发送响应。
- middleware 丢弃 `r.Context()`，使取消、deadline 和 request-scoped 值失效。

---

## 8. Goroutine 泄漏诊断与修复

### 修复只取第一个结果的并发查询

**适用身份：** 实习 / 应届 / 社招

**考察点：** blocked send、cancel、buffer sizing、goroutine profile、退出证明。

**题目：** 下面模式为每个后端启动 goroutine，只返回第一个结果。请指出泄漏并修复。

```go
func FirstBroken(backends []func() string) string {
	results := make(chan string)
	for _, backend := range backends {
		go func(load func() string) {
			results <- load()
		}(backend)
	}
	return <-results
}
```

- 输入：若干可取消 backend。
- 输出：第一个成功结果；全部失败返回可匹配每个 cause 的聚合错误。
- 约束：所有 backend 必须遵守 context 并在取消后有界退出；函数返回前已 join 全部 backend。父 context 取消优先于取消后才到达的 late success。
- 禁止假设：未选中的 send 会自行结束；GC 会回收阻塞 goroutine；backend 都快速返回；winner 出现后可把 loser 留在后台。

**参考实现要点：**

```go
package challenges

import (
	"context"
	"errors"
	"fmt"
	"sync"
)

type firstResult struct {
	index int
	value string
	err   error
}

func First(
	parent context.Context,
	backends []func(context.Context) (string, error),
) (string, error) {
	if len(backends) == 0 {
		return "", fmt.Errorf("no backends")
	}
	if err := parent.Err(); err != nil {
		return "", err
	}
	ctx, cancel := context.WithCancel(parent)
	defer cancel()

	results := make(chan firstResult, len(backends))
	var wg sync.WaitGroup
	wg.Add(len(backends))
	for index, backend := range backends {
		go func(index int, load func(context.Context) (string, error)) {
			defer wg.Done()
			value, err := load(ctx)
			results <- firstResult{index: index, value: value, err: err}
		}(index, backend)
	}

	go func() {
		wg.Wait()
		close(results)
	}()

	var failures []error
	for {
		// select 在 cancel 与 result 同时 ready 时可任选；先检查一次并在
		// 收到 result 后复查，保证已发生的父取消压过随后到达的 success。
		if err := parent.Err(); err != nil {
			cancel()
			for range results {
			}
			return "", err
		}

		select {
		case <-parent.Done():
			cancel()
			for range results {
			}
			return "", parent.Err()
		case result, ok := <-results:
			if !ok {
				return "", errors.Join(failures...)
			}
			if err := parent.Err(); err != nil {
				cancel()
				for range results {
				}
				return "", err
			}
			if result.err != nil {
				failures = append(
					failures,
					fmt.Errorf("backend[%d]: %w", result.index, result.err),
				)
				continue
			}

			winner := result.value
			cancel()
			// Race-winner API 有意不把 winner 之后的 loser error 作为返回值；
			// 仍要 drain 到 close 以 join。生产实现可在这里记录 loser 指标。
			for range results {
			}
			return winner, nil
		}
	}
}
```

- 结果缓冲等于 backend 数，每个 backend 只发送一次；唯一 collector 在 `WaitGroup` 完成后 close，主函数 drain 到 close 后才返回。
- 父取消分支先 cancel 再 drain/join，且接收结果后复查 `parent.Err()`，防止已经发生的父取消被随后到达的 late success 覆盖。
- 全部失败用 `errors.Join` 聚合 wrapped cause，`errors.Is` 可匹配每个 backend error。
- success winner 确定后，loser error 不改变 race-winner 返回值是有意 API 语义；生产实现应记录指标或日志，但仍必须 join。所有 backend 都必须遵守 context 并有界返回。
- 诊断时比较稳定负载前后的 goroutine profile/数量，并检查阻塞栈，不能只看一次瞬时计数。
- **并发协议检查：** backend 只发送，collector 在全部 sender 退出后唯一 close；成功或父取消会触发 cancel 并 drain/join；失败只由主 goroutine 聚合；每个 backend 只发送不可变结果。

**连续追问：**

1. 第一层：原代码中第一个 sender 之后的 goroutine 阻塞在哪里？
2. 第二层：父取消与 success 同时 ready 时，为什么需要 select 前检查和接收后复查？
3. 第三层：`WaitGroup + close + drain` 如何证明函数返回前 loser 已退出？backend 不遵守 context 会怎样？
4. 第四层：为什么全失败适合 `errors.Join`，而 winner 后 loser error 只记录指标、不改变成功返回？

**常见错误：**

- 认为函数局部 channel 不可达后，阻塞 goroutine 会被 GC 自动回收。
- 只把 channel 缓冲改为 1；backend 多于 2 时仍可能阻塞。
- winner 后直接 return，把 loser 留在后台；或只保留首个失败，丢失其他可匹配 cause。
- loser 不接受 context，导致 drain/join 永久等待，违反 backend 的有界取消契约。
- 用固定 sleep 等待 goroutine 数下降，测试 flaky 且没有检查阻塞栈来源。

---

## 9. 使用 `errgroup` 汇总错误

### 并发校验多个分片

**适用身份：** 应届 / 社招

**考察点：** `errgroup.WithContext`、固定 worker、错误传播、context、完整覆盖与结果同步。

**题目：** 实现 `ValidateShards`，并发校验所有分片；第一个错误取消其余任务，并限制最大并发数。

- 输入：父 context、分片 ID、正并发上限、`validate(ctx, id) error`。
- 输出：全部成功返回 nil；失败返回包含分片 ID 的错误。
- 约束：使用 `golang.org/x/sync/errgroup`；只启动 `limit` 与 `len(shards)` 中较小数量的 worker；所有输入要么完成验证，要么因返回的 context/validation error 明确失败。调用期间 `shards` 不得被并发修改。
- 禁止假设：收到第一个错误后已经运行的函数会自动终止；validate 返回 nil 就代表父 context 未取消；不同依赖版本 API 完全相同。

**参考实现要点：**

```go
package challenges

import (
	"context"
	"fmt"
	"sync/atomic"

	"golang.org/x/sync/errgroup"
)

func ValidateShards(
	ctx context.Context,
	shards []string,
	limit int,
	validate func(context.Context, string) error,
) error {
	if limit <= 0 {
		return fmt.Errorf("limit must be positive")
	}
	if err := ctx.Err(); err != nil {
		return err
	}
	if len(shards) == 0 {
		return nil
	}
	group, groupCtx := errgroup.WithContext(ctx)
	workerCount := limit
	if len(shards) < workerCount {
		workerCount = len(shards)
	}
	var next atomic.Uint64

	for worker := 0; worker < workerCount; worker++ {
		group.Go(func() error {
			for {
				if err := groupCtx.Err(); err != nil {
					return err
				}
				index := int(next.Add(1) - 1)
				if index >= len(shards) {
					return nil
				}
				shard := shards[index]
				if err := validate(groupCtx, shard); err != nil {
					return fmt.Errorf("validate shard %q: %w", shard, err)
				}
				// validate 可能错误地在取消后返回 nil；不能把它当成成功。
				if err := groupCtx.Err(); err != nil {
					return err
				}
			}
		})
	}
	if err := group.Wait(); err != nil {
		return err
	}
	return ctx.Err()
}
```

- group context 在首个非 nil error 或 `Wait` 返回时取消；任务仍必须主动观察它并返回。
- 固定 worker 从 atomic index 领取唯一 shard；没有独立 producer goroutine、jobs channel 或会阻塞且不观察 context 的提交循环，因此 `Wait` 能 join 全部 worker。
- errgroup 部分只依赖 `WithContext/Go/Wait`（即 `errgroup.WithContext`、`Group.Go` 和 `Group.Wait`）。目标项目必须在 `go.mod` 声明兼容的 `golang.org/x/sync` 版本并用实际 toolchain 编译验证；不凭记忆声称无依据的最低版本。
- 本实现不使用 Go 1.21 才加入的 built-in `min`；普通条件计算 worker 数。文件整体最低语言版本仍由 `errors.Join` 决定为 Go 1.20。
- 任一 validation error 或外部取消都会使 group 返回 non-nil；其他 worker 观察 group context 后退出。若全部返回 nil，则每个输入 index 恰好被领取并验证一次。
- 若要收集全部错误而不是 fail-fast，应采用显式同步收集并定义错误顺序，不直接套用首错语义。
- **并发协议检查：** 本题不自建 channel/producer；group 拥有 worker join/cancel；首错或 context error 通过 `Wait` 返回；atomic index 保证分片只被领取一次，validate 内部状态仍由其自身负责同步。

**连续追问：**

1. 第一层：`WithContext` 返回的 context 何时取消？
2. 第二层：为什么固定 worker 比在调用者循环中用阻塞式提交更容易响应取消和证明 join？
3. 第三层：为什么 validate 在取消后返回 nil 时，worker 仍要复查 `groupCtx.Err()`？
4. 第四层：若必须返回全部错误、保留输入顺序且继续执行，数据结构和取消策略应如何改变？

**常见错误：**

- 在任务中继续使用原始 ctx，错过 group 首错取消。
- `group.Go` 内再启动未纳入 group 的 goroutine，`Wait` 无法 join。
- 提交循环达到并发上限后阻塞且不观察 context，导致错误已发生但调用者仍卡在提交。
- 看到部分任务返回 nil 就 false-success，未确保每个输入已验证或因 non-nil error 明确失败。
- 多 goroutine append 同一个 errors slice，形成 race。
- 把 `errgroup` 的首错返回误称为“汇总全部错误”。

---

## 10. 综合评分提示

- **实习：** 优先选择 producer/consumer、顺序打印、基础 worker pool 或 middleware chain；必须说清 channel 关闭者和 goroutine 退出条件。
- **应届：** 可选择 context fan-out、LRU、限流器、泄漏修复；要求能包装错误并运行 race detector。
- **社招：** 可选择 errgroup、复杂取消预算、流式保序或高负载 limiter；要求解释部分结果语义和生产诊断证据。
- **一票否决风险：** sender/receiver 关闭责任混乱、错误路径 goroutine 永久阻塞、用 sleep 当同步、共享 map/slice 未同步、吞掉首个根因错误。

所有完整实现都应至少执行 `gofmt`、`go vet`、单元测试和 `go test -race`。并发测试必须有 timeout，结束后验证所有 channel/worker 协议收敛；性能结论另用 benchmark、pprof 或 trace，不从单元测试耗时推断。
