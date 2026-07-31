# C++ 后端编码题库

> 本文件只用于 C++ 编码面试。默认使用 C++20；若岗位使用其他标准，面试官必须先说明。
> 评价顺序是：正确性、资源与线程生命周期、异常安全、边界条件、复杂度，最后才是微优化。
> 除明确标为设计题的题目外，参考代码均应能独立编译。无锁实现不作为实习生默认要求，候选人可先提交正确的锁版本。

---

## 1. RAII 文件句柄

### 实现可移动的文件描述符封装

**适用身份：** 实习 / 应届 / 社招

**考察点：** RAII、唯一所有权、move 语义、析构约束、系统调用错误处理。

**题目：** 实现 `UniqueFd`，独占一个 POSIX file descriptor。

- 输入：构造函数接收 `int fd`，`-1` 表示空句柄。
- 输出：提供 `get()`、`valid()`、`release()` 和 `reset()`；对象销毁时关闭仍持有的 fd。
- 约束：禁止复制，允许移动；self-move 不能泄漏；`reset` 新旧 fd 相同时不得先关闭再继续持有失效值。
- 禁止假设：fd 非负就一定属于本对象；`close` 成功后才算所有权结束；析构函数可以抛异常。

**参考实现要点：**

```cpp
#include <unistd.h>
#include <utility>

class UniqueFd {
public:
    UniqueFd() noexcept = default;
    explicit UniqueFd(int fd) noexcept : fd_(fd) {}
    ~UniqueFd() { close_owned(); }

    UniqueFd(const UniqueFd&) = delete;
    UniqueFd& operator=(const UniqueFd&) = delete;

    UniqueFd(UniqueFd&& other) noexcept
        : fd_(std::exchange(other.fd_, -1)) {}

    UniqueFd& operator=(UniqueFd&& other) noexcept {
        if (this != &other) {
            reset(other.release());
        }
        return *this;
    }

    int get() const noexcept { return fd_; }
    bool valid() const noexcept { return fd_ >= 0; }

    int release() noexcept {
        return std::exchange(fd_, -1);
    }

    void reset(int new_fd = -1) noexcept {
        if (new_fd == fd_) {
            return;
        }
        close_owned();
        fd_ = new_fd;
    }

private:
    void close_owned() noexcept {
        if (fd_ >= 0) {
            const int old = std::exchange(fd_, -1);
            // close() 失败也不能在析构路径抛异常或盲目重试：
            // EINTR 后 fd 是否仍有效存在平台差异。
            (void)::close(old);
        }
    }

    int fd_ = -1;
};
```

- 所有权在调用 `close` 前就从成员中取出，避免重入或错误路径二次关闭。
- 析构函数只做 best-effort cleanup；需要观察关闭错误的业务应提供显式 `close_checked()`。
- 测试至少覆盖默认对象、move construction、move assignment、`release`、`reset` 和同 fd `reset`。

**连续追问：**

1. 第一层：为什么 copy constructor 必须删除，而 move constructor 应为 `noexcept`？
2. 第二层：`release()` 与 `reset()` 的所有权变化分别是什么？调用者何时负责关闭？
3. 第三层：为什么不能在析构函数中抛出 `close` 错误？栈展开期间抛异常会发生什么？
4. 第四层：若封装 `FILE*`、socket 或数据库连接，deleter、无效值和关闭失败契约如何变化？

**常见错误：**

- 使用编译器生成的复制操作，导致两个对象重复关闭同一 fd。
- move 后没有把源对象置为无效，或 move assignment 覆盖旧 fd 前未关闭。
- `reset(fd_)` 先关闭再保存相同数字，留下看似有效但已关闭的句柄。
- 对 `close` 的 `EINTR` 无条件重试，误关已被其他线程复用的 fd。

---

## 2. Rule of Five 资源类

### 实现深拷贝字节缓冲区

**适用身份：** 应届 / 社招

**考察点：** Rule of Five、copy-and-swap、强异常保证、空对象不变量、溢出检查。

**题目：** 实现拥有连续字节存储的 `ByteBuffer`。

- 输入：构造函数接收长度；`operator[]` 按下标读写。
- 输出：复制后两个对象互不共享；移动后源对象保持可析构、可重新赋值。
- 约束：分配失败不得破坏赋值目标原状态；`size()==0` 时 `data()` 可为空。
- 禁止假设：`new[]` 永不失败；`memcpy` 可用于任意非 trivially-copyable 类型；self-assignment 不会发生。

**参考实现要点：**

```cpp
#include <algorithm>
#include <cstddef>
#include <memory>
#include <stdexcept>
#include <utility>

class ByteBuffer {
public:
    ByteBuffer() noexcept = default;

    explicit ByteBuffer(std::size_t size)
        : size_(size),
          data_(size == 0 ? nullptr : std::make_unique<std::byte[]>(size)) {}

    ByteBuffer(const ByteBuffer& other) : ByteBuffer(other.size_) {
        if (size_ != 0) {
            std::copy_n(other.data_.get(), size_, data_.get());
        }
    }

    ByteBuffer(ByteBuffer&& other) noexcept
        : size_(std::exchange(other.size_, 0)),
          data_(std::move(other.data_)) {}

    ByteBuffer& operator=(ByteBuffer other) noexcept {
        swap(other);
        return *this;
    }

    ~ByteBuffer() = default;

    void swap(ByteBuffer& other) noexcept {
        using std::swap;
        swap(size_, other.size_);
        swap(data_, other.data_);
    }

    std::size_t size() const noexcept { return size_; }
    std::byte* data() noexcept { return data_.get(); }
    const std::byte* data() const noexcept { return data_.get(); }

    std::byte& operator[](std::size_t index) {
        if (index >= size_) throw std::out_of_range("ByteBuffer index");
        return data_[index];
    }

private:
    std::size_t size_ = 0;
    std::unique_ptr<std::byte[]> data_;
};
```

- 按值赋值参数统一 copy/move assignment；参数构造失败时目标尚未改变。
- 成员声明顺序和构造顺序一致，空对象维持 `size_ == 0 && data_ == nullptr`。
- 若实际类只由标准容器组成，应优先 Rule of Zero；本题用于考察手工资源语义。

**连续追问：**

1. 第一层：为什么 copy constructor 不能只复制指针？
2. 第二层：copy-and-swap 如何提供强异常保证，代价是什么？
3. 第三层：为什么 move 操作的 `noexcept` 会影响 `std::vector` 扩容时的选择？
4. 第四层：若元素构造可能抛异常，原始存储、已构造元素计数和回滚应如何设计？

**常见错误：**

- `delete` 与 `delete[]` 不匹配，或复制后共享裸指针。
- 先释放目标再分配副本，分配失败后目标数据丢失。
- `size_` 与 `data_` 更新顺序导致异常后不变量破坏。
- 为展示 Rule of Five 手写本可由 `std::vector<std::byte>` 正确表达的生产代码。

---

## 3. 简化独占智能指针

### 设计并实现 `MiniUniquePtr`

**适用身份：** 应届 / 社招

**考察点：** 独占所有权、模板、deleter、move-only 类型、异常规格。

**题目：** 实现只支持单对象的 `MiniUniquePtr<T, D>`。

- 输入：可接收 `T*` 和 deleter；支持默认空对象。
- 输出：提供 `get`、`operator*`、`operator->`、`release`、`reset`、`swap` 和 bool 转换。
- 约束：禁止复制；移动后源为空；析构时 deleter 恰好调用一次。为聚焦所有权，本简化实现要求 `D` 的 default/copy/move construction、move assignment、swap 和 `D(T*)` 调用均不抛异常。
- 禁止假设：deleter 一定是空类型；数组与单对象删除规则相同；这些教学约束等同于标准库完整 deleter 契约。

**参考实现要点：**

```cpp
#include <cassert>
#include <functional>
#include <memory>
#include <type_traits>
#include <utility>

template <class T, class D = std::default_delete<T>>
class MiniUniquePtr {
public:
    static_assert(std::is_nothrow_default_constructible_v<D>,
                  "deleter default construction must not throw");
    static_assert(std::is_nothrow_invocable_v<D&, T*>,
                  "deleter invocation must not throw");
    static_assert(std::is_nothrow_move_constructible_v<D>,
                  "deleter move construction must not throw");
    static_assert(std::is_nothrow_copy_constructible_v<D>,
                  "deleter copy construction must not throw");
    static_assert(std::is_nothrow_move_assignable_v<D>,
                  "deleter move assignment must not throw");
    static_assert(std::is_nothrow_swappable_v<D>,
                  "deleter swap must not throw");

    MiniUniquePtr() noexcept = default;
    explicit MiniUniquePtr(T* ptr) noexcept : ptr_(ptr) {}
    MiniUniquePtr(T* ptr, D deleter)
        noexcept(std::is_nothrow_move_constructible_v<D>)
        : deleter_(std::move(deleter)), ptr_(ptr) {}

    ~MiniUniquePtr() noexcept {
        if (ptr_) deleter_(ptr_);
    }

    MiniUniquePtr(const MiniUniquePtr&) = delete;
    MiniUniquePtr& operator=(const MiniUniquePtr&) = delete;

    MiniUniquePtr(MiniUniquePtr&& other)
        noexcept(std::is_nothrow_move_constructible_v<D>)
        : deleter_(std::move(other.deleter_)), ptr_(other.release()) {}

    MiniUniquePtr& operator=(MiniUniquePtr&& other)
        noexcept(std::is_nothrow_move_assignable_v<D>) {
        if (this != &other) {
            reset();
            deleter_ = std::move(other.deleter_);
            ptr_ = other.release();
        }
        return *this;
    }

    T* get() const noexcept { return ptr_; }
    explicit operator bool() const noexcept { return ptr_ != nullptr; }
    T& operator*() const { assert(ptr_); return *ptr_; }
    T* operator->() const noexcept { return ptr_; }

    T* release() noexcept { return std::exchange(ptr_, nullptr); }

    void reset(T* next = nullptr) noexcept {
        if (next == ptr_) return;
        T* old = std::exchange(ptr_, next);
        if (old) deleter_(old);
    }

    void swap(MiniUniquePtr& other)
        noexcept(std::is_nothrow_swappable_v<D>) {
        using std::swap;
        swap(deleter_, other.deleter_);
        swap(ptr_, other.ptr_);
    }

private:
    [[no_unique_address]] D deleter_{};
    T* ptr_ = nullptr;
};
```

- 这是教学实现，不宣称覆盖 `std::unique_ptr` 的 converting move、array specialization、reference deleter 和精确条件 `noexcept`。
- class-level `static_assert` 在任何 raw pointer 被接管前拒绝可能抛异常的默认 deleter 构造；否则 `MiniUniquePtr(T*)` 的形参求值已经产生裸指针，而成员初始化失败会让它无人释放。
- 教学实现明确要求 deleter 的 default/copy/move/assignment/swap/invocation 均不抛异常。deleter 先于 pointer 初始化，避免其构造失败时提前从源对象 release 导致泄漏。
- 若面试时间有限，可先实现固定 `delete` 版本，再追问 deleter。

**连续追问：**

1. 第一层：`release` 为什么不删除对象，`reset` 为什么要删除旧对象？
2. 第二层：数组版本为何需要不同的删除表达式与下标接口？
3. 第三层：stateful 或 throwing deleter 对对象大小、raw-only constructor、move assignment 和异常规格有什么影响？如何放宽本题的 no-throw 教学约束？
4. 第四层：简化引用计数控制块时，strong/weak count、对象销毁和控制块销毁分别何时发生？

**常见错误：**

- `release()` 删除对象后返回悬空指针。
- move constructor 复制指针却不清空源对象。
- `MiniUniquePtr(T*)` 已接收 `new T`，随后默认构造 deleter 抛异常，导致尚未接管的裸指针泄漏。
- 用 `delete` 释放数组，或让 deleter 在析构路径抛出异常。
- 把这个教学实现当成可替代标准库的生产组件。

---

## 4. 正确关闭的线程池

### 实现固定线程数线程池

**适用身份：** 应届 / 社招

**考察点：** 线程生命周期、条件变量谓词、任务异常隔离、shutdown 语义、背压。

**题目：** 实现固定数量 worker 的线程池，支持提交无返回值任务和 drain shutdown。

- 输入：构造函数接收正整数线程数；`submit(std::function<void()>)` 提交任务。
- 输出：worker 执行任务；析构或 `shutdown()` 停止接收新任务，执行完已接收任务并 join。
- 约束：并发 `submit` 安全；任务抛异常不能使 worker 静默消失；`shutdown` 幂等；禁止从该池的 worker 内销毁池或调用 `shutdown`。
- 禁止假设：condition variable 不会 spurious wakeup；调用者永远先手动关闭；任务都成功。

**参考实现要点：**

```cpp
#include <condition_variable>
#include <cstddef>
#include <exception>
#include <functional>
#include <mutex>
#include <queue>
#include <stdexcept>
#include <thread>
#include <utility>
#include <vector>

class ThreadPool {
public:
    explicit ThreadPool(std::size_t count) {
        if (count == 0) throw std::invalid_argument("thread count is zero");
        try {
            for (std::size_t i = 0; i < count; ++i) {
                workers_.emplace_back([this] { worker_loop(); });
            }
        } catch (...) {
            shutdown_noexcept();
            throw;
        }
    }

    ~ThreadPool() noexcept { shutdown_noexcept(); }
    ThreadPool(const ThreadPool&) = delete;
    ThreadPool& operator=(const ThreadPool&) = delete;

    void submit(std::function<void()> task) {
        if (!task) throw std::invalid_argument("empty task");
        {
            std::lock_guard lock(mu_);
            if (stopping_) throw std::runtime_error("pool is stopping");
            tasks_.push(std::move(task));
        }
        cv_.notify_one();
    }

    std::exception_ptr take_error() noexcept {
        std::lock_guard lock(mu_);
        return std::exchange(first_error_, nullptr);
    }

    void shutdown() {
        std::call_once(shutdown_once_, [this] {
            {
                std::lock_guard lock(mu_);
                stopping_ = true;
            }
            cv_.notify_all();
            for (auto& worker : workers_) {
                if (worker.get_id() == std::this_thread::get_id()) {
                    // worker 内 shutdown/析构违反类契约；不能 detach 后继续访问 this。
                    std::terminate();
                }
                if (worker.joinable()) worker.join();
            }
            workers_.clear();
        });
    }

private:
    void shutdown_noexcept() noexcept {
        try {
            shutdown();
        } catch (...) {
            // 析构期间不能传播 std::thread::join 的 std::system_error；
            // 保留 joinable thread 同样会在其析构时 terminate。
            std::terminate();
        }
    }

    void worker_loop() noexcept {
        for (;;) {
            std::function<void()> task;
            {
                std::unique_lock lock(mu_);
                cv_.wait(lock, [this] { return stopping_ || !tasks_.empty(); });
                if (stopping_ && tasks_.empty()) return;
                task = std::move(tasks_.front());
                tasks_.pop();
            }
            try {
                task();
            } catch (...) {
                std::lock_guard lock(mu_);
                if (!first_error_) first_error_ = std::current_exception();
            }
        }
    }

    std::mutex mu_;
    std::condition_variable cv_;
    std::queue<std::function<void()>> tasks_;
    bool stopping_ = false;
    std::exception_ptr first_error_;
    std::vector<std::thread> workers_;
    std::once_flag shutdown_once_;
};
```

- `stopping_` 与队列在同一把锁下形成状态机，避免提交与关闭之间的数据竞争。
- 任务在锁外执行；否则一个慢任务会阻塞提交和其他 worker 取任务。
- 显式 `shutdown()` 不标 `noexcept`，让 `std::thread::join` 的 `std::system_error` 可报告给调用者；成功后 `call_once` 保证析构不会再次 join。若中途抛出，已 join 的 thread 已变为 non-joinable，后续 cleanup 只处理剩余 thread。
- 析构和构造失败回滚走 `shutdown_noexcept()`；任何 join 失败都会 `std::terminate`，因为对象不能安全销毁并遗留 joinable thread。从 worker 内关闭/销毁池是明确的 contract violation，同样 `terminate`。
- 教学版本保存首个任务异常供调用者提取；生产版本应定义完整 error sink、丢弃/聚合策略，并增加有界队列和拒绝策略。

**连续追问：**

1. 第一层：`wait(lock, predicate)` 解决了什么问题？
2. 第二层：drain shutdown 与 immediate shutdown 的状态机有何不同？
3. 第三层：显式 `shutdown` 的 `join` 抛 `std::system_error` 时，为什么不能把它无说明地藏在 `noexcept` 后触发 terminate？
4. 第四层：构造第 N 个线程失败、worker 内 shutdown、future 返回值和任务取消分别需要什么契约？

**常见错误：**

- `if` 等待而非 predicate loop，遇到虚假唤醒后读取空队列。
- 持锁执行任务，导致线程池实际上串行或死锁。
- 析构 `joinable` 的 `std::thread`，触发 `std::terminate`。
- 把可抛的 `join()` 包在未说明的 `noexcept shutdown` 中，错误只能以 terminate 表现。
- worker 内调用 `shutdown` 后尝试 join 自己，或为避开 self-join 而 detach 仍访问池状态。
- 任务异常逃出 worker，或吞掉异常且没有任何可观测错误通道。

---

## 5. 有界阻塞队列

### 实现支持关闭的 `BlockingQueue<T>`

**适用身份：** 实习 / 应届 / 社招

**考察点：** mutex、condition variable、背压、close 协议、异常安全。

**题目：** 实现多生产者多消费者的有界阻塞队列。

- 输入：正容量；`push(T)`；`pop()`。
- 输出：满时生产者等待，空时消费者等待；`close()` 后拒绝新元素，消费者可排空已有元素。
- 约束：`close()` 幂等；所有等待者最终被唤醒；`pop` 用 `std::optional<T>` 表示“已关闭且已排空”。为保证 `pop` 从队首 move 后可安全移除，本简化参考实现明确要求 `T` nothrow move constructible。
- 禁止假设：只有一个生产者；通知等于条件已成立；该 no-throw 教学约束自动适用于所有生产类型。

**参考实现要点：**

```cpp
#include <condition_variable>
#include <cstddef>
#include <deque>
#include <mutex>
#include <optional>
#include <stdexcept>
#include <type_traits>
#include <utility>

template <class T>
class BlockingQueue {
public:
    static_assert(std::is_nothrow_move_constructible_v<T>,
                  "T must be nothrow move constructible");

    explicit BlockingQueue(std::size_t capacity) : capacity_(capacity) {
        if (capacity == 0) throw std::invalid_argument("capacity is zero");
    }

    bool push(T value) {
        std::unique_lock lock(mu_);
        not_full_.wait(lock, [this] {
            return closed_ || queue_.size() < capacity_;
        });
        if (closed_) return false;
        queue_.push_back(std::move(value));
        lock.unlock();
        not_empty_.notify_one();
        return true;
    }

    std::optional<T> pop() {
        std::unique_lock lock(mu_);
        not_empty_.wait(lock, [this] {
            return closed_ || !queue_.empty();
        });
        if (queue_.empty()) return std::nullopt;
        T value = std::move(queue_.front());
        queue_.pop_front();
        lock.unlock();
        not_full_.notify_one();
        return value;
    }

    void close() noexcept {
        {
            std::lock_guard lock(mu_);
            closed_ = true;
        }
        not_empty_.notify_all();
        not_full_.notify_all();
    }

private:
    const std::size_t capacity_;
    std::mutex mu_;
    std::condition_variable not_empty_;
    std::condition_variable not_full_;
    std::deque<T> queue_;
    bool closed_ = false;
};
```

- 队列状态、关闭状态与等待谓词由同一 mutex 保护。
- `queue_.push_back` 抛异常时队列仍未增加，锁由 RAII 释放；不应发送成功通知。
- `static_assert` 是本简化实现的输入约束，不是通用 blocking queue 的必要条件；它避免 `pop` 移动队首时先改变源对象、随后抛异常而难以定义重试语义。
- 若要求超时，使用 `wait_until` 搭配绝对 deadline，避免反复虚假唤醒延长总超时。

**连续追问：**

1. 第一层：为什么关闭时要同时通知生产者和消费者？
2. 第二层：为什么 `pop` 在关闭后仍要返回缓冲区里的元素？
3. 第三层：若要支持 throwing move，怎样用复制、两阶段提取或保留原节点来定义 basic/strong guarantee，并避免丢失队首元素？
4. 第四层：怎样加入 deadline、stop token、公平性或批量操作而不破坏状态机？

**常见错误：**

- `close` 不加锁，与 `push/pop` 对状态产生 data race。
- 关闭后立即让消费者退出，丢弃已接受元素。
- 只 `notify_one`，导致部分永久等待者在关闭后无法退出。
- 用两个不一致的锁分别保护队列和关闭状态。

---

## 6. 并发安全 LRU 缓存

### 实现固定容量 LRU

**适用身份：** 实习 / 应届 / 社招

**考察点：** list/map 组合、不变量、iterator 稳定性、并发线性化、异常安全。

**题目：** 实现键值 LRU，`get` 命中后提升为最近使用，`put` 超容量时淘汰最久未使用项。

- 输入：正容量、键和值。
- 输出：`get` 返回 `std::optional<V>`；`put` 插入或更新。
- 约束：平均查找/更新为常数复杂度；并发调用安全；容量不超过上限。
- 禁止假设：只读 `get` 不修改状态；hash/equality/copy 永不抛；返回引用在解锁后仍安全。

**参考实现要点：**

```cpp
#include <cstddef>
#include <list>
#include <mutex>
#include <optional>
#include <stdexcept>
#include <unordered_map>
#include <utility>

template <class K, class V>
class LruCache {
    using Entry = std::pair<K, V>;
    using Iter = typename std::list<Entry>::iterator;

public:
    explicit LruCache(std::size_t capacity) : capacity_(capacity) {
        if (capacity == 0) throw std::invalid_argument("capacity is zero");
        if (capacity_ >= index_.max_size()) {
            throw std::length_error("capacity is too large");
        }
        // 插入新项后再淘汰旧项，最多短暂存在 capacity + 1 个 map 元素。
        index_.reserve(capacity_ + 1);
    }

    std::optional<V> get(const K& key) {
        std::lock_guard lock(mu_);
        auto found = index_.find(key);
        if (found == index_.end()) return std::nullopt;
        items_.splice(items_.begin(), items_, found->second);
        return found->second->second;
    }

    void put(K key, V value) {
        std::lock_guard lock(mu_);
        auto found = index_.find(key);
        if (found != index_.end()) {
            found->second->second = std::move(value);
            items_.splice(items_.begin(), items_, found->second);
            return;
        }

        // 淘汰目标的 hash lookup 在修改结构前完成；之后使用 iterator erase 不抛。
        auto victim = index_.end();
        if (items_.size() == capacity_) {
            victim = index_.find(items_.back().first);
            if (victim == index_.end()) {
                throw std::logic_error("LRU index invariant broken");
            }
        }

        items_.emplace_front(std::move(key), std::move(value));
        try {
            const auto insertion =
                index_.emplace(items_.front().first, items_.begin());
            if (!insertion.second) {
                throw std::logic_error("LRU key invariant broken");
            }
        } catch (...) {
            items_.pop_front();
            throw;
        }

        if (items_.size() > capacity_) {
            // reserve(capacity + 1) 保证上面的插入不会因负载增长触发 rehash，
            // 因而 victim iterator 在这里仍有效。
            index_.erase(victim);
            items_.pop_back();
        }
    }

private:
    const std::size_t capacity_;
    std::mutex mu_;
    std::list<Entry> items_;  // front 是最近使用。
    std::unordered_map<K, Iter> index_;
};
```

- 单锁版本是正确性基线；`get` 会调整链表，不能简单使用 shared lock。
- 核心不变量：map 与 list 一一对应、iterator 指向匹配 key、list size 不超过容量。
- 若 `V` 复制昂贵，应重新设计返回所有权，而不是直接返回解锁后可能失效的引用。

**连续追问：**

1. 第一层：为什么需要 `list` 与 hash map，两者各承担什么复杂度？
2. 第二层：为什么 `get` 不是逻辑上的只读并发操作？
3. 第三层：`emplace_front` 成功但 map 插入失败时如何回滚？
4. 第四层：分片 LRU 能提高吞吐，但如何改变“全局最久未使用”的语义？

**常见错误：**

- vector 删除中间元素导致线性复杂度，或保存会失效的 iterator。
- 返回内部 `V&` 后立即解锁，另一个线程可淘汰该对象。
- map 插入异常后 list 多出孤儿节点。
- 为追求“读写锁”把修改 recency 的 `get` 放在共享锁下。

---

## 7. SPSC 环形队列

### 从锁版本到原子版本

**适用身份：** 社招

**考察点：** SPSC 前提、环形缓冲、不变量、happens-before、memory order、对象生命周期。

**题目：** 先实现容量固定的单生产者单消费者队列；正确锁版本可通过基础评价，再讨论无锁版本。

- 输入：生产者调用 `try_push(int)`，消费者调用 `try_pop()`。
- 输出：满时 push 返回 false，空时 pop 返回空值；元素不丢失、不重复。
- 约束：恰好一个 producer thread 和一个 consumer thread；容量至少为 2；预留一个槽位区分满与空。
- 禁止假设：`volatile` 提供线程同步；relaxed 原子自动发布普通内存；该实现可安全扩展到 MPMC。

**参考实现要点：**

```cpp
#include <atomic>
#include <cstddef>
#include <optional>
#include <stdexcept>
#include <vector>

class SpscIntQueue {
public:
    explicit SpscIntQueue(std::size_t slots) : buffer_(slots) {
        if (slots < 2) throw std::invalid_argument("need at least two slots");
    }

    bool try_push(int value) noexcept {
        const auto tail = tail_.load(std::memory_order_relaxed);
        const auto next = increment(tail);
        if (next == head_.load(std::memory_order_acquire)) return false;
        buffer_[tail] = value;
        tail_.store(next, std::memory_order_release);
        return true;
    }

    std::optional<int> try_pop() noexcept {
        const auto head = head_.load(std::memory_order_relaxed);
        if (head == tail_.load(std::memory_order_acquire)) return std::nullopt;
        const int value = buffer_[head];
        head_.store(increment(head), std::memory_order_release);
        return value;
    }

    std::size_t usable_capacity() const noexcept {
        return buffer_.size() - 1;
    }

private:
    std::size_t increment(std::size_t value) const noexcept {
        return (value + 1) % buffer_.size();
    }

    std::vector<int> buffer_;
    alignas(64) std::atomic<std::size_t> head_{0};
    alignas(64) std::atomic<std::size_t> tail_{0};
};
```

- producer 对 `tail` 独占写，consumer 对 `head` 独占写；对方通过 acquire 观察 release 发布的索引和槽位访问。
- 这里只存 `int`，规避通用 `T` 的 placement construction、destruction 与异常问题。
- `alignas(64)` 是降低 false sharing 的意图，不是所有平台 cache line 大小的标准保证；性能仍需 benchmark。

**连续追问：**

1. 第一层：为什么预留一个槽位，容量 N 的数组只能存 N-1 个值？
2. 第二层：producer 的 release store 与 consumer 的 acquire load 发布了哪些普通内存写入？
3. 第三层：哪些同线程索引读取可用 relaxed，为什么不能把所有操作都改成 relaxed？
4. 第四层：支持通用 `T`、批量操作、计数器回绕或 MPMC 时，需要增加哪些生命周期和同步协议？

**常见错误：**

- 使用 `volatile` 代替 atomic，形成 data race。
- 没有限定 SPSC，却让多个 producer 同时写同一 tail 或槽位。
- 先发布 tail 再写槽位，consumer 读到尚未构造的数据。
- 只在 x86 上压力测试通过，就断言错误的 memory order 在所有架构正确。

---

## 8. 固定块内存池

### 设计固定大小对象池

**适用身份：** 应届 / 社招

**考察点：** alignment、对象与存储生命周期、placement construction、异常回滚、pool lifetime。

**题目：** 设计只服务单一类型 `T`、固定容量的对象池。

- 输入：容量 N；`create(args...)` 构造对象；`destroy(T*)` 析构并归还槽位。
- 输出：最多同时存活 N 个对象；耗尽时明确失败；池析构前所有借出对象必须归还。
- 约束：存储满足 `alignof(T)`；构造抛异常时槽位归还；禁止重复释放和释放外部指针。
- 禁止假设：拿到原始字节就已经存在 `T` 对象；`malloc` 永远满足 over-aligned `T`；池可早于对象销毁。

**参考实现要点（设计题）：**

- 构造函数一次性定长分配全部 `Slot` backing storage，例如 `std::unique_ptr<Slot[]>`，或一次构造最终长度的 `std::vector<Slot>`；初始化后永不 resize、reserve、reallocate 或移动这段存储。
- pool 对象禁止 copy，禁止 move：删除 copy/move constructor 与 assignment；外部存在任一存活 `T*` 时，pool 对象及 backing storage 必须保持地址稳定。
- `Slot` 含 `alignas(T) std::byte storage[sizeof(T)]`、占用标志和 free-list 索引。
- `create` 先从 free-list 取槽位，再用 `std::construct_at(reinterpret_cast<T*>(storage), args...)` 开始对象生命周期；若构造抛异常，把槽位重新挂回 free-list。
- `destroy` 先验证指针位于某个槽位起始地址且当前已占用，再调用 `std::destroy_at`，最后归还槽位。
- 单线程基线无需伪装成 lock-free；线程安全版本先用 mutex 保护 free-list 和占用状态。
- **验收不变量：**
  - `live_count + free_count == capacity`。
  - 每个槽位最多有一个存活 `T`。
  - 只有成功构造的对象才会析构，且恰好一次。
  - 任意异常路径都不丢槽位，不改变其他存活对象。
  - backing storage 从构造完成到 pool 销毁只分配一次且永不 reallocate/move；任一存活 `T*` 的地址保持稳定。
  - pool 本身禁止 copy/move，外部存活指针期间不能通过容器迁移或 swap 改变其 storage owner。
  - pool 销毁时 `live_count == 0`，否则按契约 assert 或返回显式错误，不静默释放活对象存储。

**连续追问：**

1. 第一层：原始存储可用与 `T` 对象生命周期开始有什么区别？
2. 第二层：构造函数抛异常后，free-list 如何恢复到调用前状态？
3. 第三层：如何验证传给 `destroy` 的地址确实是槽位起始且当前存活？
4. 第四层：线程本地缓存如何减少竞争，又会怎样影响内存归还、公平性和池析构？

**常见错误：**

- 把对齐后的字节直接当作已构造对象使用。
- 构造失败后未归还槽位，逐渐耗尽容量。
- pool 先销毁，外部仍持有对象指针，形成 use-after-free。
- 用可增长容器保存 `Slot`，扩容或移动 pool 后让全部外部 `T*` 悬空。
- 仅靠地址范围判断合法，未检查槽位边界、占用状态和 double free。

---

## 9. `epoll` Echo Server 骨架

### 设计 non-blocking Echo Server

**适用身份：** 应届 / 社招

**考察点：** Linux fd 生命周期、non-blocking I/O、LT/ET、partial read/write、连接状态机、背压。

**题目：** 在 Linux 上设计单 reactor 的 `epoll` Echo Server 骨架。

- 输入：监听地址与端口；客户端发送任意字节流。
- 输出：每个连接按接收顺序回显相同字节；peer 关闭后清理连接。
- 约束：listen/client fd 均为 non-blocking；正确处理 `EAGAIN`、`EINTR`、partial write、半关闭和 fd 复用。
- 禁止假设：一次 `read`/`write` 处理完整消息；一次 readiness 只对应一个事件；`EPOLLRDHUP` 到达时没有剩余可读数据。

**参考实现要点（设计题，Linux-only）：**

- 监听 socket 设置 `SO_REUSEADDR` 与 `O_NONBLOCK`，注册 `EPOLLIN`；accept 循环持续到 `EAGAIN`。
- 每个连接拥有独立状态：RAII fd、输入缓冲、待发送缓冲、发送偏移、关闭标志；禁止仅按整数 fd 保存无代际状态的悬空回调。
- LT 模式先保证正确；ET 模式要求 accept/read/write 都循环到 `EAGAIN`。
- `read == 0` 表示 peer 完成发送；仍应按协议决定是否发送已缓冲响应，再关闭。
- `write` 可能只写部分数据；Linux 可使用 `send(..., MSG_NOSIGNAL)` 防止 peer 已关闭时触发进程级 `SIGPIPE`。其他平台使用其明确等价能力；进程启动时全局忽略 `SIGPIPE` 会影响所有库和 socket，只能作为经过审查的进程级策略。
- 遇到 `EPOLLIN` 与 `EPOLLERR`/`EPOLLHUP`/`EPOLLRDHUP` 组合事件时，先按 non-blocking 规则 drain 已可读数据到 `EAGAIN`/EOF，再依据协议决定是否回显已缓冲数据或关闭，不能看到 HUP 就立即丢弃已读内容。
- `EPOLLERR` 使用 `getsockopt(fd, SOL_SOCKET, SO_ERROR, ...)` 读取并记录 pending error；`ECONNRESET`、发送时 `EPIPE` 和不可恢复的 `SO_ERROR` 进入统一清理。`EPOLLHUP`/`EPOLLRDHUP` 标记 peer 终止方向，不替代 read drain。
- 保留未成功发送的剩余区间并注册 `EPOLLOUT`，写空后移除该兴趣，避免 busy loop。
- 对单连接设置输入和输出 high-water mark；超过上限可暂停 `EPOLLIN` 或关闭连接，防止慢客户端造成无界内存。
- 处理事件前查找连接状态；关闭时先从 epoll 删除并移除状态，再由 RAII 关闭 fd。不得让旧事件操作已复用为新连接的同号 fd。
- **验收不变量：**
  - 每个已接受 fd 恰好关闭一次。
  - 输出缓冲始终等于“已读但尚未成功写回”的字节序列。
  - `EPOLLOUT` 只在存在待发送字节时启用。
  - 任何连接的缓冲均有硬上限，单个慢连接不能阻塞 reactor 或耗尽进程内存。
  - peer 关闭不会通过 `SIGPIPE` 终止整个进程；每次 send 的抑制策略或经审查的进程级策略必须明确。
  - `EPOLLERR` 必须读取 `SO_ERROR`；HUP/RDHUP/RESET/EPIPE 在 drain 和协议决策后只进入一次统一清理。
  - 所有错误路径都移除连接状态，不保留指向已销毁对象的回调。

**连续追问：**

1. 第一层：LT 与 ET 的读取循环有什么差异，为什么建议先写正确的 LT 版本？
2. 第二层：如何处理 partial write，并避免持续可写事件导致 CPU busy loop？
3. 第三层：fd number 很快复用时，旧事件或异步任务如何误伤新连接？如何用 generation/token 防护？
4. 第四层：`SIGPIPE`、`EPOLLERR/HUP/RDHUP`、`SO_ERROR` 与 read drain 的处理顺序是什么？
5. 第五层：多 reactor、跨线程 handoff、graceful shutdown 和连接级背压如何设计？

**常见错误：**

- 把 TCP 当消息协议，一次 `read` 对应一次完整请求。
- ET 下只读一次，剩余数据不再触发边沿。
- 永久订阅 `EPOLLOUT`，空闲连接持续唤醒。
- 未抑制 `SIGPIPE`，单个已关闭 peer 的写入终止整个进程；或无评估地全局忽略信号，改变第三方库行为。
- 把 `EPOLLHUP` 当成“立即 close”，未 drain 已就绪数据；忽略 `EPOLLERR` 的 `SO_ERROR`，或对 `ECONNRESET`/`EPIPE` 不做统一清理。
- 关闭 fd 后仍保留状态或异步任务，只按 fd 整数识别连接。

---

## 10. 综合评分提示

- **实习：** 优先选择 RAII、有界阻塞队列或锁版 LRU；能写出明确 ownership、关闭路径和基础测试即达标，不强制无锁。
- **应届：** 可选择 Rule of Five、线程池、内存池设计或 `epoll` 状态机；要求能解释异常路径和资源回收。
- **社招：** 可选择 SPSC、线程池关闭协议或 `epoll` 背压；必须区分语言保证、平台契约和性能假设。
- **一票否决风险：** double free/use-after-free、析构线程未 join、data race、错误 memory order 却声称“压力测试通过即正确”、异常后破坏所有权不变量。

每道实现题至少验证正常路径、边界、错误路径和资源退出。并发题应在普通测试之外运行 ThreadSanitizer；生命周期题应运行 AddressSanitizer/UndefinedBehaviorSanitizer。性能比较必须先保证语义一致，再提供可复现 benchmark。
