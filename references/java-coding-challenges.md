# Java 后端编码题库

> 面试最后环节可选的 Java 编码题。难度从简单到中等，覆盖并发编程、Java 数据访问、设计模式、框架原理和服务端组件实现等方向。
>
> 面试官可根据候选人水平和剩余时间灵活选题，每题标注了难度和预估用时。
>
> **语言边界**：所有实现题、伪代码、并发原语和追问均按 Java 版本评估。数据库与系统级标准答案统一见 `references/common-backend-knowledge-base.md`；本文件只保留挑战题面和 Java 侧事务边界、资源生命周期、异常翻译、并发工具与测试关注点。

---

## 目录

- [1. 并发编程](#1-并发编程)
  - [1.1 生产者消费者模式](#11-生产者消费者模式)
  - [1.2 线程安全的单例模式](#12-线程安全的单例模式)
  - [1.3 实现一个简易线程池](#13-实现一个简易线程池)
  - [1.4 ConcurrentHashMap 核心操作](#14-concurrenthashmap-核心操作)
- [2. Java 数据访问与事务实现](#2-java-数据访问与事务实现)
  - [2.1 SQL 题：连续登录用户](#21-sql-题连续登录用户)
  - [2.2 索引设计题](#22-索引设计题)
  - [2.3 事务隔离级别实现](#23-事务隔离级别实现)
- [3. 设计模式](#3-设计模式)
  - [3.1 工厂模式实现](#31-工厂模式实现)
  - [3.2 策略模式实现](#32-策略模式实现)
- [4. 框架原理](#4-框架原理)
  - [4.1 简版 IOC 容器](#41-简版-ioc-容器)
  - [4.2 拦截器链实现](#42-拦截器链实现)
- [5. Java 服务端组件实现](#5-java-服务端组件实现)
  - [5.1 限流器实现](#51-限流器实现)
  - [5.2 分布式 ID 生成器](#52-分布式-id-生成器)
- [6. 数据结构](#6-数据结构)
  - [6.1 LRU 缓存实现](#61-lru-缓存实现)
  - [6.2 跳表实现](#62-跳表实现)

---

## 1. 并发编程

### 1.1 生产者消费者模式

**难度**：中等 | **预估用时**：10-15 分钟 | **高频指数**：⭐⭐⭐⭐⭐

**题目**：实现一个标准的生产者-消费者模式，使用阻塞队列

```java
import java.util.concurrent.*;

public class ProducerConsumerDemo {

    public static void main(String[] args) {
        // 使用有界阻塞队列，容量为 10
        BlockingQueue<Integer> queue = new ArrayBlockingQueue<>(10);

        // 启动 2 个生产者
        for (int i = 0; i < 2; i++) {
            final int producerId = i;
            new Thread(() -> {
                try {
                    int value = 0;
                    while (true) {
                        // TODO: 生产者逻辑
                        // 生产值并放入队列
                        // 放入成功后打印 "Producer X produced: Y"
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }, "Producer-" + producerId).start();
        }

        // 启动 3 个消费者
        for (int i = 0; i < 3; i++) {
            final int consumerId = i;
            new Thread(() -> {
                try {
                    while (true) {
                        // TODO: 消费者逻辑
                        // 从队列取出值
                        // 消费后打印 "Consumer X consumed: Y"
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }, "Consumer-" + consumerId).start();
        }
    }
}
```

**参考解答**：

```java
import java.util.concurrent.*;

public class ProducerConsumerDemo {

    public static void main(String[] args) {
        BlockingQueue<Integer> queue = new ArrayBlockingQueue<>(10);

        // 生产者
        for (int i = 0; i < 2; i++) {
            final int producerId = i;
            new Thread(() -> {
                int value = 0;
                try {
                    while (true) {
                        Thread.sleep((producerId + 1) * 100); // 模拟不同生产速度
                        queue.put(value);  // 阻塞直到队列有空位
                        System.out.println("Producer " + producerId + " produced: " + value);
                        value++;
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }, "Producer-" + producerId).start();
        }

        // 消费者
        for (int i = 0; i < 3; i++) {
            final int consumerId = i;
            new Thread(() -> {
                try {
                    while (true) {
                        int value = queue.take();  // 阻塞直到队列有元素
                        System.out.println("Consumer " + consumerId + " consumed: " + value);
                        Thread.sleep(150);  // 模拟消费处理时间
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }, "Consumer-" + consumerId).start();
        }
    }
}
```

**追问方向**：
- ArrayBlockingQueue vs LinkedBlockingQueue 的区别？（数组 vs 链表，有界 vs 无界）
- 阻塞队列的 `put(E)` 和 `offer(E)` 有什么区别？（`put` 在队列满时阻塞；无超时的 `offer` 立即返回 `false`，不抛异常；`add(E)` 满时才抛 `IllegalStateException`）
- 如何实现一个支持优先级的阻塞队列？

---

### 1.2 线程安全的单例模式

**难度**：简单 | **预估用时**：5-8 分钟 | **高频指数**：⭐⭐⭐⭐⭐

**题目**：写出线程安全的单例模式实现（至少两种）

**参考解答**：

```java
// 方案一：饿汉式（线程安全，但启动即创建，可能浪费资源）
class Singleton1 {
    private static final Singleton1 INSTANCE = new Singleton1();

    private Singleton1() {}

    public static Singleton1 getInstance() {
        return INSTANCE;
    }
}

// 方案二：懒汉式 + synchronized（线程安全，但性能差）
class Singleton2 {
    private static Singleton2 INSTANCE;

    private Singleton2() {}

    public static synchronized Singleton2 getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new Singleton2();
        }
        return INSTANCE;
    }
}

// 方案三：双重检查锁定（DCL，推荐）
class Singleton3 {
    // volatile 防止指令重排序
    private static volatile Singleton3 INSTANCE;

    private Singleton3() {}

    public static Singleton3 getInstance() {
        if (INSTANCE == null) {                 // 第一次检查
            synchronized (Singleton3.class) {
                if (INSTANCE == null) {         // 第二次检查
                    INSTANCE = new Singleton3();
                }
            }
        }
        return INSTANCE;
    }
}

// 方案四：静态内部类（推荐，更简洁）
class Singleton4 {
    private Singleton4() {}

    private static class Holder {
        private static final Singleton4 INSTANCE = new Singleton4();
    }

    public static Singleton4 getInstance() {
        return Holder.INSTANCE;
    }
}

// 方案五：枚举（Effective Java 作者推荐，最简洁）
enum Singleton5 {
    INSTANCE;

    public void doSomething() {
        // 业务方法
    }
}
```

**追问方向**：
- DCL 中为什么要用 volatile？（防止指令重排序）
- 饿汉式和懒汉式的区别？（资源浪费 vs 延迟初始化）
- 枚举单例为什么是线程安全的？（Java 规范保证）

---

### 1.3 实现一个简易线程池

**难度**：中等偏难 | **预估用时**：15-20 分钟 | **高频指数**：⭐⭐⭐⭐

**题目**：实现一个固定 worker 数量、带有界任务队列的教学线程池。要求：

- 构造参数必须校验；
- 生命周期显式区分 `RUNNING`、`SHUTDOWN`、`TERMINATED`；
- `shutdown()` 后拒绝新任务，但已接收任务必须排空；
- 构造时通过 `ThreadFactory` 创建 worker；任一 worker 创建或启动失败时必须回滚已启动线程，不能泄漏 non-daemon thread；
- 单个任务抛出 `RuntimeException` 不得破坏 worker 计数或阻止后续任务；fatal `Error` 不得被吞掉，并触发明确的全池关闭策略；
- 提供有界等待的 `awaitTermination(...)`。

```java
import java.time.Duration;

public class SimpleThreadPool {
    public SimpleThreadPool(int workerCount, int queueCapacity) { }
    public void execute(Runnable task) {
        // TODO: 实现逻辑
    }
    public void shutdown() { }
    public boolean awaitTermination(Duration timeout)
            throws InterruptedException { return false; }
}
```

**参考解答**：

```java
import java.time.Duration;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.locks.Condition;
import java.util.concurrent.locks.ReentrantLock;

public class SimpleThreadPool {
    enum State {
        RUNNING,
        SHUTDOWN,
        TERMINATED
    }

    private static final AtomicInteger POOL_IDS = new AtomicInteger();
    private static final long IDLE_CHECK_MILLIS = 100;

    private final BlockingQueue<Runnable> workQueue;
    private final Set<Thread> workers = new HashSet<>();
    private final ReentrantLock lifecycleLock = new ReentrantLock();
    private final Condition terminated = lifecycleLock.newCondition();
    private volatile State state = State.RUNNING;

    public SimpleThreadPool(int workerCount, int queueCapacity) {
        this(workerCount, queueCapacity, namedThreadFactory());
    }

    SimpleThreadPool(
            int workerCount,
            int queueCapacity,
            ThreadFactory threadFactory) {
        if (workerCount <= 0) {
            throw new IllegalArgumentException("workerCount must be > 0");
        }
        if (queueCapacity <= 0) {
            throw new IllegalArgumentException("queueCapacity must be > 0");
        }

        Objects.requireNonNull(threadFactory, "threadFactory");
        workQueue = new ArrayBlockingQueue<>(queueCapacity);
        List<Thread> startedWorkers = new ArrayList<>(workerCount);
        try {
            startWorkers(workerCount, threadFactory, startedWorkers);
        } catch (RuntimeException | Error constructionFailure) {
            finishConstructionRollback(startedWorkers);
            throw constructionFailure;
        }
    }

    private static ThreadFactory namedThreadFactory() {
        int poolId = POOL_IDS.incrementAndGet();
        AtomicInteger workerIds = new AtomicInteger();
        return task -> new Thread(
                task,
                "simple-pool-" + poolId
                        + "-worker-" + workerIds.getAndIncrement());
    }

    private void startWorkers(
            int workerCount,
            ThreadFactory threadFactory,
            List<Thread> startedWorkers) {
        lifecycleLock.lock();
        try {
            for (int index = 0; index < workerCount; index++) {
                Thread worker = Objects.requireNonNull(
                        threadFactory.newThread(this::runWorker),
                        "threadFactory returned null");
                workers.add(worker);
                // 先记录再 start；即使自定义 start() 启动后抛错也能 join。
                startedWorkers.add(worker);
                try {
                    worker.start();
                } catch (RuntimeException | Error startFailure) {
                    workers.remove(worker);
                    throw startFailure;
                }
            }
        } catch (RuntimeException | Error constructionFailure) {
            state = State.SHUTDOWN;
            for (Thread worker : startedWorkers) {
                try {
                    worker.interrupt();
                } catch (RuntimeException | Error wakeupFailure) {
                    if (wakeupFailure != constructionFailure) {
                        try {
                            constructionFailure.addSuppressed(wakeupFailure);
                        } catch (RuntimeException | Error ignored) {
                            // 回滚诊断不能覆盖最初的构造失败。
                        }
                    }
                }
            }
            throw constructionFailure;
        } finally {
            lifecycleLock.unlock();
        }
    }

    private void finishConstructionRollback(List<Thread> startedWorkers) {
        boolean interrupted = false;
        for (Thread worker : startedWorkers) {
            while (worker.isAlive()) {
                try {
                    worker.join();
                } catch (InterruptedException interruption) {
                    interrupted = true;
                }
            }
        }

        lifecycleLock.lock();
        try {
            workQueue.clear();
            workers.clear();
            state = State.TERMINATED;
            terminated.signalAll();
        } finally {
            lifecycleLock.unlock();
        }
        if (interrupted) {
            Thread.currentThread().interrupt();
        }
    }

    public void execute(Runnable task) {
        Objects.requireNonNull(task, "task");
        lifecycleLock.lock();
        try {
            if (state != State.RUNNING) {
                throw new RejectedExecutionException(
                        "thread pool is shutting down");
            }
            if (!workQueue.offer(task)) {
                throw new RejectedExecutionException("task queue is full");
            }
        } finally {
            lifecycleLock.unlock();
        }
    }

    public void shutdown() {
        lifecycleLock.lock();
        try {
            if (state == State.RUNNING) {
                state = State.SHUTDOWN;
            }
        } finally {
            lifecycleLock.unlock();
        }
    }

    public boolean awaitTermination(Duration timeout)
            throws InterruptedException {
        Objects.requireNonNull(timeout, "timeout");
        if (timeout.isNegative()) {
            throw new IllegalArgumentException("timeout must not be negative");
        }
        long remainingNanos = timeout.toNanos();
        lifecycleLock.lockInterruptibly();
        try {
            while (state != State.TERMINATED) {
                if (remainingNanos <= 0) {
                    return false;
                }
                remainingNanos = terminated.awaitNanos(remainingNanos);
            }
            return true;
        } finally {
            lifecycleLock.unlock();
        }
    }

    public boolean isTerminated() {
        return state == State.TERMINATED;
    }

    private void runWorker() {
        try {
            while (true) {
                if (state != State.RUNNING && workQueue.isEmpty()) {
                    return;
                }

                Runnable task;
                try {
                    task = workQueue.poll(
                            IDLE_CHECK_MILLIS, TimeUnit.MILLISECONDS);
                } catch (InterruptedException interrupted) {
                    // 本实现没有 shutdownNow；中断只用于让线程重新检查状态。
                    continue;
                }
                if (task == null) {
                    continue;
                }

                try {
                    task.run();
                } catch (RuntimeException taskFailure) {
                    reportTaskFailure(taskFailure);
                }
            }
        } catch (Error fatalError) {
            beginFatalShutdown();
            throw fatalError;
        } finally {
            lifecycleLock.lock();
            workers.remove(Thread.currentThread());
            try {
                if (workers.isEmpty() && state == State.SHUTDOWN) {
                    // Fatal Error 若耗尽最后一个 worker，剩余任务无法再执行。
                    workQueue.clear();
                    state = State.TERMINATED;
                    terminated.signalAll();
                }
            } finally {
                lifecycleLock.unlock();
            }
        }
    }

    private void beginFatalShutdown() {
        lifecycleLock.lock();
        try {
            if (state == State.RUNNING) {
                state = State.SHUTDOWN;
            }
        } finally {
            lifecycleLock.unlock();
        }
    }

    private static void reportTaskFailure(RuntimeException failure) {
        Thread thread = Thread.currentThread();
        Thread.UncaughtExceptionHandler handler =
                thread.getUncaughtExceptionHandler();
        if (handler != null) {
            try {
                handler.uncaughtException(thread, failure);
            } catch (RuntimeException ignored) {
                // RuntimeException 上报失败不能终止教学 worker。
            }
        }
    }
}
```

**语义边界**：

- `shutdown()` 是 graceful shutdown：只禁止新提交，不中断正在运行的任务，队列中的任务继续执行；队列为空且所有 worker 退出后进入 `TERMINATED`。
- 默认构造器使用命名 `ThreadFactory`；教学 overload 允许测试注入 factory。factory 必须返回尚未启动、执行传入 `Runnable` 的线程。任一 `newThread` 或 `start` 抛出 `RuntimeException`/`Error` 时，构造器把池切到回滚状态、interrupt 并 join 已启动 worker、清空集合、标记 `TERMINATED`，再原样抛出，不留下 non-daemon thread。
- 任务的 `RuntimeException` 会报告并隔离；任务 `Error` 不被 `reportTaskFailure` 吞掉。fatal `Error` 将池切到 `SHUTDOWN` 后原样逃逸到线程的 uncaught handler；剩余 worker 继续排空已接收任务并终止。若 fatal `Error` 耗尽最后一个 worker，无法执行的残余队列会被清空，避免 `awaitTermination` 永久等待。
- worker 的移除、最后一个 worker 的状态迁移和 `awaitTermination` 唤醒都位于 `finally` 路径。
- 该实现只用于讲清生命周期、有界队列、启动回滚和 fatal failure 策略，没有动态扩缩容、拒绝策略注入、统计或 `shutdownNow()` 等生产能力。生产代码应直接使用并正确配置 `ThreadPoolExecutor`。

**追问方向**：
- 为什么状态检查和 `offer` 必须在同一把锁内？如果分开会怎样？
- graceful shutdown 与 `shutdownNow()` 的契约有什么区别？
- `ThreadPoolExecutor` 如何处理任务异常、worker 替换和拒绝策略？
- 如何测试“shutdown 前已经入队的任务全部执行，shutdown 后提交被拒绝”？

---

### 1.4 ConcurrentHashMap 核心操作

**难度**：中等 | **预估用时**：10-15 分钟 | **高频指数**：⭐⭐⭐⭐⭐

**题目**：实现一个简易的分段锁 HashMap，理解 ConcurrentHashMap 的分段思想

```java
public class SegmentMap<K, V> {

    // 分段数
    private static final int SEGMENTS = 16;

    // 分段数组
    private final Segment<K, V>[] segments;

    public SegmentMap() {
        segments = new Segment[SEGMENTS];
        for (int i = 0; i < SEGMENTS; i++) {
            segments[i] = new Segment<>();
        }
    }

    // 计算 key 所在的分段索引
    private int segmentIndex(K key) {
        return Math.abs(key.hashCode() % SEGMENTS);
    }

    public V get(K key) {
        // TODO: 实现 get
        return null;
    }

    public V put(K key, V value) {
        // TODO: 实现 put
        return null;
    }

    // 分段内部类
    private static class Segment<K, V> {
        // 简单用 synchronized 模拟分段锁
        private final Object lock = new Object();
        private Map<K, V> map = new HashMap<>();

        V get(K key) {
            synchronized (lock) {
                return map.get(key);
            }
        }

        V put(K key, V value) {
            synchronized (lock) {
                return map.put(key, value);
            }
        }
    }
}
```

**参考解答**：

```java
import java.util.*;

public class SegmentMap<K, V> {

    private static final int SEGMENTS = 16;
    private final Segment<K, V>[] segments;

    public SegmentMap() {
        segments = new Segment[SEGMENTS];
        for (int i = 0; i < SEGMENTS; i++) {
            segments[i] = new Segment<>();
        }
    }

    private int segmentIndex(K key) {
        return Math.abs(key.hashCode() % SEGMENTS);
    }

    public V get(K key) {
        int index = segmentIndex(key);
        return segments[index].get(key);
    }

    public V put(K key, V value) {
        int index = segmentIndex(key);
        return segments[index].put(key, value);
    }

    // JDK 8 ConcurrentHashMap 的核心原理（简化的分段锁）
    // 不同分段可以并发访问，提高吞吐量

    private static class Segment<K, V> {
        private final Object lock = new Object();
        private volatile Map<K, V> map = new HashMap<>();

        V get(K key) {
            synchronized (lock) {
                return map.get(key);
            }
        }

        V put(K key, V value) {
            synchronized (lock) {
                return map.put(key, value);
            }
        }

        // JDK 8 ConcurrentHashMap 的改进：
        // 1. 取消分段锁，改用 Node + CAS + synchronized
        // 2. 锁的粒度更细，只锁单个桶
        // 3. 使用红黑树优化链表过长的情况
    }

    public static void main(String[] args) throws InterruptedException {
        SegmentMap<String, Integer> map = new SegmentMap<>();

        // 测试并发put
        List<Thread> threads = new ArrayList<>();
        for (int i = 0; i < 100; i++) {
            final int num = i;
            threads.add(new Thread(() -> {
                map.put("key" + (num % 10), num);
            }));
        }

        for (Thread t : threads) {
            t.start();
        }

        for (Thread t : threads) {
            t.join();
        }

        // 输出每个 key 的值（最后写入的）
        for (int i = 0; i < 10; i++) {
            System.out.println("key" + i + " = " + map.get("key" + i));
        }
    }
}
```

**追问方向**：
- JDK 7 和 JDK 8 的 ConcurrentHashMap 有什么区别？（分段锁 vs CAS + synchronized）
- 为什么要用 volatile 修饰 map？（保证可见性）
- CAS 的 ABA 问题如何解决？（版本号/时间戳）

---

## 2. Java 数据访问与事务实现

> SQL、索引、事务隔离和 MVCC 的标准语义只在 `references/common-backend-knowledge-base.md` 维护。本章保留挑战题面，但参考要点只讨论 Java 应用侧的 JDBC/Spring 事务边界、连接生命周期、异常翻译、并发与测试，不在此复制数据库标准答案。

### 2.1 SQL 题：连续登录用户

**难度**：中等 | **预估用时**：10-15 分钟 | **高频指数**：⭐⭐⭐⭐

**题目**：有一个用户登录表 `user_logins(user_id, login_date)`，找出连续登录天数>=3天的用户

```sql
-- 表结构
CREATE TABLE user_logins (
    user_id INT,
    login_date DATE
);

-- 示例数据
-- user_id | login_date
-- 1       | 2024-01-01
-- 1       | 2024-01-02
-- 1       | 2024-01-03  <- 连续3天
-- 1       | 2024-01-05  <- 断开
-- 2       | 2024-01-01
-- 2       | 2024-01-02
-- 2       | 2024-01-04  <- 只有2天连续

-- 请写出 SQL
```

**参考解答**：

数据库解法、窗口函数语义、复杂度和索引取舍统一见 `references/common-backend-knowledge-base.md`。Java 实现侧应继续检查：

- 使用参数绑定而不是拼接 SQL；日期映射明确使用 `LocalDate`，不要让默认时区参与纯日期计算。
- `Connection`、`PreparedStatement`、`ResultSet` 使用 try-with-resources；连接由事务框架托管时，不在 DAO 中自行提交或关闭框架拥有的连接。
- 大结果集设置合理的 fetch size、超时和取消路径；不要无界加载到 `List`。
- 集成测试至少覆盖重复日期、跨月/跨年、乱序输入、空结果和数据库方言；SQL 正确性不能只靠 mock 验证。

**追问方向**：
- 数据库语义与复杂度如何在公共知识库中验证？
- JDBC 日期类型和时区错误会如何污染结果？
- 如何用真实数据库执行计划和集成测试证明实现，而不是只 mock DAO？

---

### 2.2 索引设计题

**难度**：中等 | **预估用时**：8-10 分钟 | **高频指数**：⭐⭐⭐⭐⭐

**题目**：设计一个论坛系统的索引，包含以下查询场景

**场景**：
1. 按时间范围查询帖子 `WHERE create_time BETWEEN ? AND ?`
2. 按板块查询帖子 `WHERE board_id = ?`
3. 按用户查询帖子 `WHERE user_id = ?`
4. 查询某板块下某用户的帖子 `WHERE board_id = ? AND user_id = ?`

**请设计索引并说明理由**

**参考解答**：

索引标准答案、最左前缀、覆盖索引和执行计划判读统一见 `references/common-backend-knowledge-base.md`。Java 实现侧只补充：

- Repository 方法要让查询条件、排序和分页契约显式可见，避免一个“万能查询”隐藏不同访问路径。
- JPA/Hibernate 需检查生成 SQL、参数类型、隐式 join、N+1 和分页行为；MyBatis/JDBC 需检查动态 SQL 分支和参数绑定。
- 对迁移脚本做版本化、回滚或前向修复设计；应用发布顺序必须兼容索引尚未创建或正在在线构建的窗口。
- 测试使用代表性数据分布和实际执行计划；单元测试只证明 Java 分支，不证明数据库会选择目标索引。

**追问方向**：
- 如何从 Hibernate/MyBatis 最终 SQL 回到真实执行计划？
- 索引迁移与 Java 应用如何做到向前/向后兼容？
- 为什么 repository mock 不能证明索引设计有效？

---

### 2.3 事务隔离级别实现

**难度**：难 | **预估用时**：15-20 分钟 | **高频指数**：⭐⭐⭐

**题目**：说明 MySQL 四种隔离级别及其实现原理

**参考解答**：

四种隔离级别、consistent read、locking read、MVCC、ReadView 和 next-key lock 的标准答案统一见 `references/common-backend-knowledge-base.md`。不得在 Java 题库维护第二份数据库语义，也不得使用“RC 普通读加共享锁”“SERIALIZABLE 普通读加排他锁”或“RR 总在事务开始创建快照”这类错误概括。

Java 应用侧参考要点：

- JDBC `Connection#setTransactionIsolation` 和 Spring `@Transactional(isolation=...)` 表达的是请求的事务边界；实际支持和行为仍需核对驱动、连接池与数据库。
- `@Transactional` 通常依赖代理。self-invocation、异常被吞、rollback 规则、传播行为和异步线程切换都可能让预期事务边界失效。
- 连接必须在事务完成后归还连接池；手工 JDBC 使用 try-with-resources，并正确处理 commit、rollback 和 suppressed exception。
- Spring 的 `DataAccessException` 是异常翻译，不等于业务重试策略。重试需限定 transient failure、幂等性、次数、退避和整体 deadline。
- 隔离行为必须用至少两个独立连接/线程的集成测试验证，并用 latch/barrier 控制时序；同一连接内顺序执行不能证明并发现象。

**追问方向**：
- Java 代码在哪一层声明并实际开启事务？
- 连接池复用时如何防止隔离级别或 read-only 状态泄漏到下一请求？
- 如何设计两个连接的可重复并发测试，并区分数据库行为与 Spring 代理失效？

---

## 3. 设计模式

### 3.1 工厂模式实现

**难度**：简单 | **预估用时**：5-8 分钟 | **高频指数**：⭐⭐⭐⭐

**题目**：实现一个支付工厂，根据支付方式返回对应的支付处理器

```java
// 支付接口
interface Payment {
    void pay(double amount);
    void refund(double amount);
}

// 支付宝实现
class Alipay implements Payment {
    @Override
    public void pay(double amount) {
        System.out.println("支付宝支付：" + amount);
    }

    @Override
    public void refund(double amount) {
        System.out.println("支付宝退款：" + amount);
    }
}

// 微信支付实现
class WechatPay implements Payment {
    @Override
    public void pay(double amount) {
        System.out.println("微信支付：" + amount);
    }

    @Override
    public void refund(double amount) {
        System.out.println("微信退款：" + amount);
    }
}

// 工厂类
class PaymentFactory {
    // TODO: 实现 getPayment 方法
    public static Payment getPayment(String type) {
        // 根据 type 返回对应的 Payment 实现
        return null;
    }
}
```

**参考解答**：

```java
// 工厂实现
class PaymentFactory {

    private static final Map<String, Payment> PAYMENTS = new HashMap<>();

    static {
        PAYMENTS.put("alipay", new Alipay());
        PAYMENTS.put("wechat", new WechatPay());
        // 可以继续添加其他支付方式
    }

    public static Payment getPayment(String type) {
        Payment payment = PAYMENTS.get(type.toLowerCase());
        if (payment == null) {
            throw new IllegalArgumentException("不支持的支付方式：" + type);
        }
        return payment;
    }

    // 扩展：使用反射，支持通过类名动态创建
    public static Payment getPaymentByClass(String className) {
        try {
            Class<?> clazz = Class.forName(className);
            return (Payment) clazz.getDeclaredConstructor().newInstance();
        } catch (Exception e) {
            throw new RuntimeException("创建支付实例失败", e);
        }
    }
}

// 使用
public class Main {
    public static void main(String[] args) {
        Payment alipay = PaymentFactory.getPayment("alipay");
        alipay.pay(100.0);

        Payment wechat = PaymentFactory.getPayment("wechat");
        wechat.pay(200.0);
    }
}
```

**追问方向**：
- 工厂模式和 new 创建对象有什么区别？（解耦、便于扩展、隐藏创建细节）
- 简单工厂、工厂方法、抽象工厂的区别？
- Spring 中哪里用到了工厂模式？（BeanFactory、FactoryBean）

---

### 3.2 策略模式实现

**难度**：简单 | **预估用时**：5-8 分钟 | **高频指数**：⭐⭐⭐⭐

**题目**：实现一个订单折扣计算器，使用策略模式

```java
// 折扣策略接口
interface DiscountStrategy {
    double calculate(double originalPrice);
}

// 原价策略
class NoDiscount implements DiscountStrategy {
    @Override
    public double calculate(double originalPrice) {
        return originalPrice;
    }
}

// 满减策略
class FullDiscount implements DiscountStrategy {
    private double threshold;  // 满多少
    private double reduction;  // 减多少

    // TODO: 构造函数和实现

    @Override
    public double calculate(double originalPrice) {
        // 满 threshold 减 reduction
        return originalPrice;
    }
}

// 折扣策略
class PercentDiscount implements DiscountStrategy {
    private double percent;  // 折扣率，如 0.8 表示 8 折

    // TODO: 构造函数和实现

    @Override
    public double calculate(double originalPrice) {
        return originalPrice;
    }
}

// 订单类
class Order {
    private DiscountStrategy strategy;

    public void setStrategy(DiscountStrategy strategy) {
        this.strategy = strategy;
    }

    public double calculatePrice(double originalPrice) {
        return strategy.calculate(originalPrice);
    }
}
```

**参考解答**：

```java
// 满减策略
class FullDiscount implements DiscountStrategy {
    private double threshold;
    private double reduction;

    public FullDiscount(double threshold, double reduction) {
        this.threshold = threshold;
        this.reduction = reduction;
    }

    @Override
    public double calculate(double originalPrice) {
        if (originalPrice >= threshold) {
            return originalPrice - reduction;
        }
        return originalPrice;
    }
}

// 折扣策略
class PercentDiscount implements DiscountStrategy {
    private double percent;

    public PercentDiscount(double percent) {
        this.percent = percent;
    }

    @Override
    public double calculate(double originalPrice) {
        return originalPrice * percent;
    }
}

// 使用
public class Main {
    public static void main(String[] args) {
        Order order = new Order();

        // 使用满减策略
        order.setStrategy(new FullDiscount(100, 10));
        System.out.println("满减价格：" + order.calculatePrice(150));  // 140

        // 切换为折扣策略
        order.setStrategy(new PercentDiscount(0.8));
        System.out.println("8折价格：" + order.calculatePrice(150));  // 120

        // 切换为不打折
        order.setStrategy(new NoDiscount());
        System.out.println("原价：" + order.calculatePrice(150));  // 150
    }
}
```

**追问方向**：
- 策略模式和 if-else 相比有什么优势？（扩展性、可读性、单元测试）
- 策略模式和工厂模式有什么区别？（工厂创建对象，策略使用对象）
- Spring 中哪里用到了策略模式？（Resource、PropertyEditor）

---

## 4. 框架原理

### 4.1 简版 IOC 容器

**难度**：难 | **预估用时**：15-20 分钟 | **高频指数**：⭐⭐⭐

**题目**：实现一个简单的 IOC 容器，支持依赖注入

```java
import java.lang.reflect.*;
import java.util.*;

public class SimpleIOC {

    private Map<String, Object> beans = new HashMap<>();

    // 注册 bean
    public void register(String name, Object obj) {
        beans.put(name, obj);
    }

    // 获取 bean
    public Object getBean(String name) {
        return beans.get(name);
    }

    // 扫描并注入依赖
    public void autowire(Object obj) {
        // TODO: 实现自动注入
        // 1. 获取类的所有字段
        // 2. 查找 @Autowired 注解的字段
        // 3. 根据字段类型从容器中查找匹配的 bean
        // 4. 通过反射设置字段值
    }
}
```

**参考解答**：

```java
import java.lang.reflect.*;
import java.util.*;

public class SimpleIOC {

    private Map<String, Object> beans = new HashMap<>();
    private Map<Class<?>, String> classToName = new HashMap<>();

    public void register(Class<?> clazz, Object obj) {
        String name = clazz.getSimpleName();
        // 类名首字母小写作为 bean 名称
        name = name.substring(0, 1).toLowerCase() + name.substring(1);
        beans.put(name, obj);
        classToName.put(clazz, name);
    }

    public Object getBean(Class<?> clazz) {
        String name = classToName.get(clazz);
        return name != null ? beans.get(name) : null;
    }

    public Object getBean(String name) {
        return beans.get(name);
    }

    // 自动注入
    public void autowire(Object obj) {
        Class<?> clazz = obj.getClass();

        for (Field field : clazz.getDeclaredFields()) {
            // 检查 @Autowired 注解
            if (field.isAnnotationPresent(Autowired.class)) {
                Class<?> fieldType = field.getType();
                Object dependency = getBean(fieldType);

                if (dependency == null) {
                    throw new RuntimeException("找不到依赖：" + fieldType.getName());
                }

                try {
                    field.setAccessible(true);
                    field.set(obj, dependency);
                } catch (IllegalAccessException e) {
                    throw new RuntimeException("注入失败", e);
                }
            }
        }
    }

    // 组件扫描（简化版）
    public void scan(String basePackage) throws Exception {
        // 实际项目中会用类加载器扫描 basePackage 下的类
        // 这里简化处理，直接注册示例类
    }

    public static void main(String[] args) throws Exception {
        SimpleIOC ioc = new SimpleIOC();

        // 注册 bean
        UserService userService = new UserServiceImpl();
        OrderService orderService = new OrderServiceImpl();

        ioc.register(UserService.class, userService);
        ioc.register(OrderService.class, orderService);

        // 注入依赖
        ioc.autowire(userService);

        // 验证注入
        UserService us = (UserService) ioc.getBean(UserService.class);
        us.save();
    }
}

// 自定义注解
@Retention(RetentionPolicy.RUNTIME)
@interface Autowired {}

// 示例接口和实现
interface UserService {
    void save();
}

class UserServiceImpl implements UserService {
    @Autowired
    private OrderService orderService;

    @Override
    public void save() {
        System.out.println("UserService.save()");
        System.out.println("依赖注入成功：" + orderService);
    }
}

interface OrderService {}
class OrderServiceImpl implements OrderService {}
```

**追问方向**：
- Spring IOC 的初始化过程？（加载 BeanDefinition、实例化、依赖注入）
- BeanFactory 和 FactoryBean 有什么区别？
- 循环依赖如何检测和处理？（三级缓存）

---

### 4.2 拦截器链实现

**难度**：中等 | **预估用时**：10-15 分钟 | **高频指数**：⭐⭐⭐

**题目**：实现一个拦截器链，模拟 Spring MVC 的 HandlerInterceptor

```java
import java.util.*;

public class InterceptorChain {

    private List<Interceptor> interceptors = new ArrayList<>();

    // 添加拦截器
    public void addInterceptor(Interceptor interceptor) {
        interceptors.add(interceptor);
    }

    // 执行拦截器链
    public boolean execute(Object handler) {
        int lastSuccessfulIndex = -1;

        // TODO: 按顺序执行 preHandle
        // 记录最后一个成功返回 true 的拦截器索引
        // 任何一个返回 false，则中断执行，并只回调此前成功的拦截器
        // preHandle 抛异常时，也只回调此前成功的拦截器，并传入原异常

        try {
            // 执行目标处理逻辑
            // handler.handle();

            // 只对成功执行 preHandle 的拦截器逆向执行 postHandle
            for (int i = lastSuccessfulIndex; i >= 0; i--) {
                interceptors.get(i).postHandle(handler, null, null, null);
            }
        } finally {
            // 只对成功执行 preHandle 的拦截器逆向执行 afterCompletion
            for (int i = lastSuccessfulIndex; i >= 0; i--) {
                interceptors.get(i).afterCompletion(handler, null, null, null);
            }
        }

        return true;
    }
}

// 拦截器接口
interface Interceptor {
    boolean preHandle(Object handler, Object request, Object response);
    void postHandle(Object handler, Object request, Object response, Object model);
    void afterCompletion(Object handler, Object request, Object response, Exception ex);
}
```

**参考解答**：

```java
import java.util.*;

public class InterceptorChain {

    private List<Interceptor> interceptors = new ArrayList<>();

    public void addInterceptor(Interceptor interceptor) {
        interceptors.add(interceptor);
    }

    public boolean execute(Object handler) {
        int lastSuccessfulIndex = -1;

        try {
            // 按顺序执行 preHandle
            for (int i = 0; i < interceptors.size(); i++) {
                if (!interceptors.get(i).preHandle(handler, null, null)) {
                    // 只回调已经成功完成 preHandle 的拦截器。
                    triggerAfterCompletion(handler, lastSuccessfulIndex, null);
                    return false;
                }
                lastSuccessfulIndex = i;
            }
        } catch (RuntimeException e) {
            // 抛异常的 interceptor 未成功，不纳入 completion 范围。
            triggerAfterCompletion(handler, lastSuccessfulIndex, e);
            throw e;
        }

        Exception failure = null;
        try {
            // 执行目标处理逻辑
            System.out.println("执行 Handler: " + handler);

            // Handler 成功后，只对成功执行 preHandle 的拦截器逆序 postHandle。
            for (int i = lastSuccessfulIndex; i >= 0; i--) {
                interceptors.get(i).postHandle(handler, null, null, null);
            }
        } catch (RuntimeException e) {
            failure = e;
            throw e;
        } finally {
            triggerAfterCompletion(handler, lastSuccessfulIndex, failure);
        }

        return true;
    }

    private void triggerAfterCompletion(
            Object handler, int lastSuccessfulIndex, Exception failure) {
        for (int i = lastSuccessfulIndex; i >= 0; i--) {
            try {
                interceptors.get(i).afterCompletion(
                        handler, null, null, failure);
            } catch (Exception e) {
                // 记录日志，但不中断
                e.printStackTrace();
            }
        }
    }
}

// 使用示例
class Main {
    public static void main(String[] args) {
        InterceptorChain chain = new InterceptorChain();

        // 添加拦截器
        chain.addInterceptor(new AuthInterceptor());
        chain.addInterceptor(new LoggingInterceptor());
        chain.addInterceptor(new TransactionInterceptor());

        // 执行
        chain.execute(new UserHandler());
    }
}

// 示例拦截器
class AuthInterceptor implements Interceptor {
    @Override
    public boolean preHandle(Object handler, Object request, Object response) {
        System.out.println("AuthInterceptor.preHandle");
        return true;  // 返回 false 可中断执行
    }

    @Override
    public void postHandle(Object handler, Object request, Object response, Object model) {
        System.out.println("AuthInterceptor.postHandle");
    }

    @Override
    public void afterCompletion(Object handler, Object request, Object response, Exception ex) {
        System.out.println("AuthInterceptor.afterCompletion");
    }
}

// 模拟 Handler
class UserHandler {}
```

**追问方向**：
- `preHandle` 返回 false 会怎样？（中断执行；只对它之前已经返回 true 的拦截器逆序调用 `afterCompletion`，返回 false 的拦截器和未执行拦截器不回调）
- `preHandle` 抛异常会怎样？（只对它之前成功返回 true 的拦截器逆序调用 `afterCompletion` 并传入同一个异常；抛异常的拦截器和未执行拦截器不回调，随后原样抛出）
- 为什么 postHandle 和 afterCompletion 要逆向执行？（FILO，先执行的后处理）
- Filter 和 Interceptor 的区别？（Filter 是 Servlet 层面的，Interceptor 是框架层面的）

---

## 5. Java 服务端组件实现

> 限流与分布式 ID 的系统级语义、容量、故障和分布式取舍统一见 `references/common-backend-knowledge-base.md`。本章只评价 Java 类型、并发原语、时间源、异常与测试实现。

### 5.1 限流器实现

**难度**：中等 | **预估用时**：10-15 分钟 | **高频指数**：⭐⭐⭐⭐⭐

**题目**：实现一个滑动窗口限流器

```java
import java.util.*;

public class SlidingWindowRateLimiter {

    private final int maxRequests;      // 时间窗口内的最大请求数
    private final long windowSizeMs;    // 时间窗口大小（毫秒）
    private final Queue<Long> requests; // 请求时间戳队列

    public SlidingWindowRateLimiter(int maxRequests, long windowSizeMs) {
        if (maxRequests <= 0 || windowSizeMs <= 0) {
            throw new IllegalArgumentException(
                    "maxRequests 和 windowSizeMs 必须大于 0");
        }
        this.maxRequests = maxRequests;
        this.windowSizeMs = windowSizeMs;
        this.requests = new LinkedList<>();
    }

    // 尝试获取令牌
    public synchronized boolean tryAcquire() {
        // 教学示例使用墙钟；生产实现应注入单调时间源。
        long now = System.currentTimeMillis();
        long windowStart = now - windowSizeMs;

        // TODO:
        // 1. 移除窗口外的请求记录
        // 2. 检查当前请求数是否已达到上限
        // 3. 如果未达到，记录当前请求并返回 true

        return false;
    }
}
```

**参考解答**：

算法语义、窗口边界、分布式精度、阈值和故障取舍统一见 `references/common-backend-knowledge-base.md`，本文件不维护第二份限流标准答案。

Java-specific 实现关注点：

- 构造器校验容量和持续时间；用 `Deque<Long>` 或等价结构维护进程内状态，并让清理、容量检查、写入处于同一同步协议。
- 注入返回单调经过时间的接口，避免测试依赖真实 `sleep`。`System.nanoTime()` 只能计算同一进程内差值，不能当绝对时间戳或跨进程时间。
- 阻塞 API 必须定义 interrupt、deadline 和取消语义，不用固定轮询间隔忙等占用线程池 worker。
- 并发测试用 barrier 同时发起请求，断言上限、不变量和无数据竞争；性能结论需要 JMH/JFR 或同负载压测证据。
- 若需求升级为分布式限流，重新路由公共知识库做系统设计；不能把这个进程内 Java 类包装成分布式正确性答案。

**追问方向**：
- 算法和分布式取舍如何从公共知识库选择，本实现只负责哪些 Java 进程内不变量？
- 如何注入时间源，使窗口边界、回拨和超时测试无需真实 `sleep`？
- `synchronized` 版本在高竞争下如何建立 benchmark/JFR 证据，再决定是否分片或改用其他同步结构？
- 阻塞式 `acquire` 如何响应 interrupt、传播 timeout，并避免忙等占用 worker？
- `System.currentTimeMillis()` 回拨会怎样？（墙钟调整可能让窗口判断和超时失真；生产实现应注入可测试的单调时间源，Java 可用 `System.nanoTime()` 的差值计算经过时间，不能把它当作绝对时间戳）

---

### 5.2 分布式 ID 生成器

**难度**：难 | **预估用时**：15-20 分钟 | **高频指数**：⭐⭐⭐⭐

**题目**：设计一个分布式 ID 生成器，要求：趋势递增、不重复、高可用

```java
/**
 * 分布式 ID 格式（64 位）：
 *
 * | sign | timestamp | workid | sequence |
 * | 1位  |  41位     | 10位   | 12位    |
 *
 * - sign: 始终为 0，保证正数
 * - timestamp: 从某个 epoch 开始的时间戳（毫秒）
 * - workid: 机器/服务标识（最多 1024 个节点）
 * - sequence: 同一毫秒内的序列号（最多 4096）
 */
public class SnowflakeIdGenerator {

    // 2024-01-01 作为 epoch
    private static final long EPOCH = 1704067200000L;

    private final long workerId;

    public SnowflakeIdGenerator(long workerId) {
        this.workerId = workerId;
    }

    public long generate() {
        // TODO: 实现 ID 生成
        return 0;
    }
}
```

**参考解答**：

ID 方案、位宽预算、节点 ID 分配、回拨和可用性取舍统一见 `references/common-backend-knowledge-base.md`，本文件不维护第二份 Snowflake 标准答案。

Java-specific 实现关注点：

- 使用带符号 `long` 时先证明各字段位宽、shift、mask、epoch 寿命和正数约束；构造器拒绝越界 worker ID。
- 注入 wall clock 和等待/回拨策略，确定性测试同毫秒序列耗尽、回拨、跨 epoch 与时间戳溢出；不能在测试中依赖真实毫秒推进。
- 用 `synchronized`、lock 或 atomic state 维护 `(lastTimestamp, sequence)` 的复合不变量；若改成 CAS，必须证明整个状态原子更新，不只原子更新 sequence。
- 等待下一时间单位要定义 interrupt、deadline 和 CPU 占用；异常类型应区分配置错误、时钟错误和暂时容量耗尽。
- 多线程测试验证唯一性和单实例顺序，跨节点唯一性必须由节点 ID 分配与运维协议证明，单元测试不能替代该系统约束。

**追问方向**：
- Snowflake 类方案的通用取舍如何从公共知识库判断，本类只实现哪些 Java 侧不变量？
- 如何把 wall clock 与等待策略注入构造器，确定性测试同毫秒耗尽和时钟回拨？
- `synchronized` 是否满足目标吞吐，如何用 JMH 或压测验证而不是凭锁类型判断？
- 时间戳越界、worker ID 冲突和等待被中断时应返回什么异常，调用方如何区分可重试与配置错误？

---

## 6. 数据结构

### 6.1 LRU 缓存实现

**难度**：中等 | **预估用时**：10-15 分钟 | **高频指数**：⭐⭐⭐⭐⭐

**题目**：实现一个 LRU（最近最少使用）缓存

```java
import java.util.*;

public class LRUCache<K, V> {

    private final int capacity;
    private final Map<K, V> cache;

    public LRUCache(int capacity) {
        this.capacity = capacity;
        this.cache = new HashMap<>();  // TODO: 改为 LinkedHashMap 实现 LRU
    }

    public V get(K key) {
        // TODO: 获取并移动到尾部（最近使用）
        return null;
    }

    public void put(K key, V value) {
        // TODO: 放入并处理容量超限
    }
}
```

**参考解答**：

```java
import java.util.*;

public class LRUCache<K, V> {

    private final int capacity;
    private final LinkedHashMap<K, V> cache;

    public LRUCache(int capacity) {
        // LinkedHashMap 的 accessOrder=true 使其成为 LRU
        this.cache = new LinkedHashMap<K, V>(capacity, 0.75f, true) {
            @Override
            protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
                return size() > LRUCache.this.capacity;
            }
        };
        this.capacity = capacity;
    }

    public V get(K key) {
        return cache.getOrDefault(key, null);
    }

    public void put(K key, V value) {
        cache.put(key, value);
    }

    public String toString() {
        return cache.keySet().toString();
    }

    public static void main(String[] args) {
        LRUCache<String, Integer> cache = new LRUCache<>(3);

        cache.put("A", 1);
        cache.put("B", 2);
        cache.put("C", 3);
        System.out.println("初始: " + cache);  // [A, B, C]

        cache.get("A");  // 访问 A
        System.out.println("访问 A: " + cache);  // [B, C, A]（A 移到尾部）

        cache.put("D", 4);  // 添加 D，触发删除最老的 B
        System.out.println("添加 D: " + cache);  // [C, A, D]
    }
}
```

**手写实现（不使用 LinkedHashMap）**：

```java
import java.util.*;

public class LRUCache2<K, V> {

    private final int capacity;
    private final Map<K, Node<K, V>> cache;
    private final Node<K, V> head;  // 虚拟头节点
    private final Node<K, V> tail;  // 虚拟尾节点

    public LRUCache2(int capacity) {
        this.capacity = capacity;
        this.cache = new HashMap<>();
        this.head = new Node<>();
        this.tail = new Node<>();
        head.next = tail;
        tail.prev = head;
    }

    public V get(K key) {
        Node<K, V> node = cache.get(key);
        if (node == null) return null;
        moveToTail(node);  // 移到尾部
        return node.value;
    }

    public void put(K key, V value) {
        Node<K, V> node = cache.get(key);
        if (node != null) {
            node.value = value;
            moveToTail(node);
        } else {
            Node<K, V> newNode = new Node<>(key, value);
            cache.put(key, newNode);
            addToTail(newNode);

            if (cache.size() > capacity) {
                Node<K, V> removed = removeHead();
                cache.remove(removed.key);
            }
        }
    }

    private void moveToTail(Node<K, V> node) {
        removeNode(node);
        addToTail(node);
    }

    private void addToTail(Node<K, V> node) {
        node.prev = tail.prev;
        node.next = tail;
        tail.prev.next = node;
        tail.prev = node;
    }

    private Node<K, V> removeHead() {
        Node<K, V> oldHead = head.next;
        removeNode(oldHead);
        return oldHead;
    }

    private void removeNode(Node<K, V> node) {
        node.prev.next = node.next;
        node.next.prev = node.prev;
    }

    private static class Node<K, V> {
        K key;
        V value;
        Node<K, V> prev;
        Node<K, V> next;

        Node() {}
        Node(K key, V value) {
            this.key = key;
            this.value = value;
        }
    }
}
```

**追问方向**：
- LinkedHashMap 如何实现 LRU？（removeEldestEntry + accessOrder）
- LRU 和 LFU 的区别？（最近最少使用 vs 最不经常使用）
- Redis 中 LRU 和 LFU 是如何实现的？（近似 LRU、LFU 策略）

---

### 6.2 跳表实现

**难度**：难 | **预估用时**：15-20 分钟 | **高频指数**：⭐⭐⭐

**题目**：实现一个简化的跳表（Skip List）

```java
import java.util.*;

public class SkipList<K, V> {

    private static final int MAX_LEVEL = 16;

    // 跳表节点
    private static class Node<K, V> {
        K key;
        V value;
        Node<K, V>[] forwards;  // 每层的前向指针

        Node(K key, V value, int level) {
            this.key = key;
            this.value = value;
            this.forwards = new Node[level];
        }
    }

    private Node<K, V> head;
    private int level;
    private final Comparator<K> comparator;

    public SkipList(Comparator<K> comparator) {
        this.comparator = comparator;
        this.head = new Node<>(null, null, MAX_LEVEL);
        this.level = 0;
    }

    // 查找
    public V get(K key) {
        // TODO: 实现查找
        return null;
    }

    // 插入
    public void put(K key, V value) {
        // TODO: 实现插入（随机层高）
    }

    // 删除
    public void remove(K key) {
        // TODO: 实现删除
    }
}
```

**参考解答**：

```java
import java.util.*;
import java.util.concurrent.*;

public class SkipList<K, V> {

    private static final int MAX_LEVEL = 16;
    private static final double PROBABILITY = 0.5;

    private static class Node<K, V> {
        K key;
        V value;
        Node<K, V>[] forwards;

        Node(K key, V value, int level) {
            this.key = key;
            this.value = value;
            this.forwards = new Node[level];
        }
    }

    private final Node<K, V> head;
    private int level;
    private final Comparator<K> comparator;
    private final Random random;

    public SkipList(Comparator<K> comparator) {
        this.comparator = comparator;
        this.head = new Node<>(null, null, MAX_LEVEL);
        this.level = 0;
        this.random = new Random();
    }

    public void put(K key, V value) {
        Node<K, V>[] update = new Node[MAX_LEVEL];

        Node<K, V> current = head;
        for (int i = level - 1; i >= 0; i--) {
            Node<K, V> next = current.forwards[i];
            while (next != null && compare(key, next.key) > 0) {
                current = next;
                next = current.forwards[i];
            }
            update[i] = current;
        }

        Node<K, V> existing = current.forwards[0];
        if (existing != null && compare(key, existing.key) == 0) {
            existing.value = value;
            return;
        }

        // 随机层高
        int newLevel = randomLevel();
        if (newLevel > level) {
            // 旧跳表没有这些层，新增层的前驱都是 head。
            for (int i = level; i < newLevel; i++) {
                update[i] = head;
            }
        }

        Node<K, V> newNode = new Node<>(key, value, newLevel);
        for (int i = 0; i < newLevel; i++) {
            newNode.forwards[i] = update[i].forwards[i];
            update[i].forwards[i] = newNode;
        }

        if (newLevel > level) {
            level = newLevel;
        }
    }

    public V get(K key) {
        Node<K, V> current = head;

        for (int i = level - 1; i >= 0; i--) {
            Node<K, V> next = current.forwards[i];
            while (next != null && compare(key, next.key) > 0) {
                current = next;
                next = current.forwards[i];
            }
        }

        current = current.forwards[0];
        if (current != null && compare(key, current.key) == 0) {
            return current.value;
        }
        return null;
    }

    public void remove(K key) {
        Node<K, V>[] update = new Node[MAX_LEVEL];
        Node<K, V> current = head;

        for (int i = level - 1; i >= 0; i--) {
            Node<K, V> next = current.forwards[i];
            while (next != null && compare(key, next.key) > 0) {
                current = next;
                next = current.forwards[i];
            }
            update[i] = current;
        }

        current = current.forwards[0];
        if (current != null && compare(key, current.key) == 0) {
            for (int i = 0; i < level; i++) {
                if (update[i].forwards[i] != current) break;
                update[i].forwards[i] = current.forwards[i];
            }

            while (level > 0 && head.forwards[level - 1] == null) {
                level--;
            }
        }
    }

    private int randomLevel() {
        int level = 1;
        while (level < MAX_LEVEL && random.nextDouble() < PROBABILITY) {
            level++;
        }
        return level;
    }

    @SuppressWarnings("unchecked")
    private int compare(K k1, K k2) {
        if (comparator != null) {
            return comparator.compare(k1, k2);
        }
        return ((Comparable<K>) k1).compareTo(k2);
    }

    public void print() {
        for (int i = level - 1; i >= 0; i--) {
            System.out.print("Level " + i + ": ");
            Node<K, V> current = head.forwards[i];
            while (current != null) {
                System.out.print("[" + current.key + ":" + current.value + "] ");
                current = current.forwards[i];
            }
            System.out.println();
        }
    }

    public static void main(String[] args) {
        SkipList<Integer, String> skipList = new SkipList<>(Comparator.naturalOrder());

        skipList.put(3, "C");
        skipList.put(1, "A");
        skipList.put(5, "E");
        skipList.put(2, "B");
        skipList.put(4, "D");

        skipList.print();

        System.out.println("Get 3: " + skipList.get(3));
        System.out.println("Get 6: " + skipList.get(6));

        skipList.remove(3);
        System.out.println("After removing 3:");
        skipList.print();
    }
}
```

**追问方向**：
- 跳表和红黑树的区别？（跳表区间查询更快，实现更简单，高并发友好）
- 跳表的插入时间复杂度？（O(log n)，随机层高）
- Redis 中哪里用到了跳表？（ZSET 有序集合）

---

## 各身份难度参考

| 题目 | 实习 | 应届 | 社招 1-3 年 |
|------|:----:|:----:|:----------:|
| 1.1 生产者消费者 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| 1.2 单例模式 | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| 1.3 线程池 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| 1.4 ConcurrentHashMap | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 2.1 SQL 连续登录 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| 2.2 索引设计 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 2.3 事务隔离级别 | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 3.1 工厂模式 | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| 3.2 策略模式 | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| 4.1 IOC 容器 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 4.2 拦截器链 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| 5.1 限流器 | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 5.2 分布式 ID | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 6.1 LRU 缓存 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| 6.2 跳表 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
