# Java 后端专项知识库

> 本文件只维护 Java 语言、JVM、Spring 生态与 Java 工程排查能力。
> MySQL、Redis、消息队列、网络、操作系统、分布式与系统设计等跨语言内容统一见 `common-backend-knowledge-base.md`。

---

## 目录

- [1. Java 语言基础与集合](#1-java-语言基础与集合)
  - [1.1 String/StringBuilder/StringBuffer](#11-stringstringbuilderstringbuffer)
  - [1.2 集合框架](#12-集合框架)
  - [1.3 泛型](#13-泛型)
  - [1.4 其他基础](#14-其他基础)
- [2. Java 内存模型与并发](#2-java-内存模型与并发)
  - [2.1 Java 内存模型](#21-java-内存模型)
  - [2.2 synchronized](#22-synchronized)
  - [2.3 volatile](#23-volatile)
  - [2.4 JUC 并发工具](#24-juc-并发工具)
  - [2.5 线程池](#25-线程池)
  - [2.6 AQS](#26-aqs)
  - [2.7 CAS](#27-cas)
  - [2.8 Java 死锁排查](#28-java-死锁排查)
- [3. JVM](#3-jvm)
  - [3.1 内存结构](#31-内存结构)
  - [3.2 垃圾回收](#32-垃圾回收)
  - [3.3 垃圾收集器](#33-垃圾收集器)
  - [3.4 类加载](#34-类加载)
  - [3.5 性能调优](#35-性能调优)
- [4. Spring 与 Spring Boot](#4-spring-与-spring-boot)
  - [4.1 IoC / DI](#41-ioc--di)
  - [4.2 AOP](#42-aop)
  - [4.3 事务](#43-事务)
  - [4.4 循环依赖](#44-循环依赖)
  - [4.5 Spring Boot](#45-spring-boot)
- [5. Java 工程实践与排查](#5-java-工程实践与排查)
  - [5.1 构建、测试与发布](#51-构建测试与发布)
  - [5.2 JVM 进程排查](#52-jvm-进程排查)
  - [5.3 连续追问与常见误区](#53-连续追问与常见误区)

---

## 1. Java 语言基础与集合

### 1.1 String/StringBuilder/StringBuffer
- **[Java 规范] String 的不可变语义是什么？** — `String` 对外表示不可变字符序列：创建后其字符内容不会改变，拼接和替换返回新对象。`final` 类有助于维持实现封装，但不可变语义不能简化为“final 修饰字符数组”；规范也不要求使用某一种内部数组。
- **[JDK 标准库实现] 当前 OpenJDK 如何存储 String？** — JDK 9 起的 Compact Strings 通常使用 `byte[] + coder` 区分 LATIN1/UTF16 表示；更早版本常见 `char[]`。这是 JDK 实现和版本变化，不是 Java 语言保证，候选人不应因回答“不可变字符序列”而被要求背内部字段。
- **[版本变化] 字符串拼接如何回答？** — 编译器可把局部拼接改写为 `StringBuilder`，较新 JDK 还可能使用 `invokedynamic` 和不同拼接策略。循环或热点路径是否需要显式 builder 应看目标 JDK 生成代码和 benchmark，不能断言每个 `+` 都创建固定数量对象。
- **[JDK 标准库实现] StringBuilder 与 StringBuffer** — 两者都是可变字符序列；`StringBuffer` 方法带同步语义，`StringBuilder` 不提供线程安全保证。选择依据是共享与同步需求，不应仅用“性能一定更快”作绝对结论。

### 1.2 集合框架
- **ArrayList vs LinkedList** — ArrayList 基于数组，随机访问 O(1)；LinkedList 基于双向链表，头尾操作 O(1)；一般场景 ArrayList 更优
- **[Java 规范] 集合 API 保证什么？** — `List`、`Map` 等接口规定可观察行为，具体类文档规定复杂度、null、迭代器和并发契约；接口不规定内部数组增长倍数、桶布局或树化阈值。
- **[JDK 标准库实现] ArrayList 如何扩容？** — 常见 OpenJDK 实现使用延迟分配的对象数组，并在容量不足时按约 1.5 倍方向增长，再复制元素。默认容量和增长公式属于目标 JDK 源码细节，不是 Java API 契约；应用只应依赖摊销复杂度和公开方法语义。
- **[JDK 标准库实现] HashMap 如何处理碰撞？** — 现代 OpenJDK 可在桶内使用链表和红黑树；`TREEIFY_THRESHOLD`、`UNTREEIFY_THRESHOLD`、`MIN_TREEIFY_CAPACITY` 等常量解释某个实现版本的树化策略，不是 Java API 契约。面试应先评价 `equals/hashCode` 契约、平均复杂度和并发安全，再追问目标版本源码。
- **[版本变化] HashMap 与 ConcurrentHashMap** — JDK 7/8 的实现差异可作源码追问，但不能把历史头插死循环当作“所有 HashMap 不安全”的唯一理由。稳定结论是普通 `HashMap` 没有并发修改安全保证；`ConcurrentHashMap` 的分段、桶锁、CAS 和计数细节需限定 OpenJDK 版本。
- **fail-fast vs fail-safe** — fail-fast 通过 modCount 检测并发修改并抛出 ConcurrentModificationException；fail-safe 复制副本操作（CopyOnWriteArrayList）

### 1.3 泛型
- **泛型擦除机制** — 编译后泛型信息被擦除（替换为上限或 Object），类型转换需要显式处理；带来的问题：无法直接创建泛型数组、无法使用 instanceof T
- **PECS 原则** — Producer Extends（生产用 extends）、Consumer Super（消费用 super）。如 `List<? extends Number>` 可读不可写

### 1.4 其他基础
- **Object 通用方法** — equals、hashCode、toString、clone、finalize（已废弃）
- **重写 equals 必须重写 hashCode** — 两个对象 equals 则 hashCode 必须相同，否则放入 HashMap/HashSet 会出问题
- **深拷贝 vs 浅拷贝** — 浅拷贝引用共享内部对象；深拷贝递归复制所有嵌套对象

---

## 2. Java 内存模型与并发

### 2.1 Java 内存模型

- **JMM 解决什么问题？** — Java Memory Model 定义线程如何通过主内存交互，以及原子性、可见性和有序性的规则；它是语言级规范，不等同于 JVM 运行时内存区域
- **happens-before 有什么作用？** — 用于判断一个操作的结果是否对另一个操作可见。常见规则包括程序次序、监视器锁、volatile、线程启动与线程终止规则
- **指令重排序为什么不会破坏单线程语义？** — 编译器和处理器遵守 as-if-serial；多线程代码仍需通过锁、volatile、final 安全发布等方式建立顺序
- **final 字段的安全发布语义是什么？** — 构造函数内正确初始化且对象引用未逸出时，其他线程看到对象引用后也应看到 final 字段的初始化值

### 2.2 synchronized
- **synchronized 底层原理** — 同步语句块使用 `monitorenter`/`monitorexit` 指令，同步方法使用 `ACC_SYNCHRONIZED` 标识；具体 JVM 通过对象监视器及快速路径、竞争路径等机制实现。Java 规范保证同步语义，但不规定 HotSpot 对象头布局或固定的锁状态转换路径
- **偏向锁与锁状态如何理解？** — 偏向锁、轻量级锁、自旋和重量级 monitor 是历史 HotSpot 中用于解释 `synchronized` 优化的实现概念，不是 Java 规范规定的固定“锁膨胀流程”。JEP 374 自 JDK 15 起默认禁用偏向锁；不同 JDK 版本可能继续调整或移除相关实现，分析时应限定具体 JVM、版本、启动参数和竞争场景
- **synchronized 和 volatile 的区别** — volatile 仅保证可见性和有序性，不保证原子性，只能修饰变量；synchronized 三者都保证，可修饰方法和代码块

### 2.3 volatile
- **[Java 规范] volatile 保证什么？** — 对 volatile 变量的读写具有规定的同步顺序，volatile 写 happens-before 后续对同一变量的读，从而建立相关普通读写的可见性和有序性；它不把复合的读-改-写操作变成原子操作。
- **[JVM/GC 实现] 如何落到机器上？** — JIT 可能使用编译器屏障、CPU fence 或带顺序语义的指令实现上述契约。常见的 StoreStore/StoreLoad、LoadLoad/LoadStore 是解释屏障映射的模型，具体映射取决于目标 JVM、JIT 和 CPU 架构，不能表述为 Java 规范固定插入四种指令，也不能概括成“绕过 CPU 缓存、强制访问主存”。
- **volatile 能保证原子性吗？** — 不能。以 `i++` 为例，包含"读取-修改-写入"三步，volatile 只保证可见性，无法保证这三步的原子性

### 2.4 JUC 并发工具
- **synchronized 和 ReentrantLock 区别** — ReentrantLock 可中断（lockInterruptibly）、可设置公平/非公平锁、支持超时、支持多 Condition 分组唤醒；两者都是可重入锁
- **ReentrantLock 可重入原理** — 内部 state 计数。获取锁 state+1，释放-1，同一线程可重复获取，需释放相同次数
- **CountDownLatch vs CyclicBarrier** — CountDownLatch 倒计数，不可复用（一次性）；CyclicBarrier 可复用，等所有线程都到达屏障点再一起放行
- **Semaphore 用途** — 信号量，控制同时访问资源的线程数。如连接池大小限制
- **ThreadLocal 内存泄漏原因** — Entry 的 key（ThreadLocal）是弱引用，可被 GC 回收；但 value 是强引用，如果线程持续存活（线程池），value 无法回收导致泄漏。使用完务必调用 remove()

### 2.5 线程池
- **线程池七大参数** — corePoolSize、maximumPoolSize、keepAliveTime、unit、workQueue、threadFactory、handler
- **线程池工作流程** — 核心线程未满 → 创建核心线程；满了则入队列；队列满则创建非核心线程；达到最大线程数则执行拒绝策略
- **线程池拒绝策略** — AbortPolicy（抛异常）、CallerRunsPolicy（调用者执行）、DiscardPolicy（丢弃）、DiscardOldestPolicy（丢弃最老）。不允许丢弃选 CallerRunsPolicy
- **线程池分类** — FixedThreadPool（固定大小）、CachedThreadPool（弹性伸缩）、ScheduledThreadPool（定时任务）、SingleThreadExecutor（单线程）

### 2.6 AQS
- **AQS 原理** — 核心是 CLH 锁队列变体（双向队列 + 自旋阻塞）。state 表示同步状态（volatile），通过 CAS 原子操作管理。模板方法模式定义 acquire/release 流程
- **独占模式 vs 共享模式** — 独占（如 ReentrantLock）一次只一个线程获取锁；共享（如 CountDownLatch、Semaphore）多个线程可同时获取

### 2.7 CAS
- **CAS 原理** — 三个操作数：变量 V、预期值 E、新值 N。当 V=E 时原子更新为 N，否则重试。依赖 CPU 原子指令，Java 通过 Unsafe 类实现
- **CAS 的 ABA 问题及解决** — 变量被改成 B 又改回 A，CAS 误认为未被修改。解决：AtomicStampedReference 携带版本号
- **CAS 的缺点** — 循环时间长开销大；只能保证单一变量的原子性

### 2.8 Java 死锁排查

- **Java 中常见的死锁来源** — 多把 `synchronized` 监视器或 `ReentrantLock` 获取顺序不一致；线程池任务互相等待；持锁期间等待 `Future`、I/O 或回调
- **Java 锁如何预防死锁？** — 统一锁顺序；缩小同步区；使用 `tryLock(timeout)` 让等待可退出；避免持锁调用不受控代码；为线程池中的依赖任务预留容量
- **线程 dump 如何定位？** — 用 `jcmd <pid> Thread.print -l` 或 `jstack -l <pid>` 获取线程栈，检查 `BLOCKED`、`waiting to lock`、`locked` 与 JVM 报告的 deadlock cycle，再回到锁获取代码验证
- **JFR 与 Arthas 能补充什么证据？** — JFR 的 Java Monitor Blocked、Thread Park 事件可观察阻塞时长；Arthas `thread -b` 可快速定位阻塞其他线程的线程，但结论仍需结合多个时刻的线程 dump 和业务调用链

**连续追问：**
1. `synchronized` 和 `ReentrantLock` 的死锁在线程 dump 中分别可能呈现什么状态？
2. 如果没有形成严格死锁，只是锁竞争严重，如何用 JFR 或 Arthas 区分？
3. 修复锁顺序后，如何用并发测试、超时和压力测试证明问题没有复现？

**常见误区：**
- 只看到大量 `BLOCKED` 就判定死锁；锁竞争、慢临界区也会产生同样状态
- 只抓一次线程 dump；偶发问题至少应按时间间隔抓取多份，并关联 CPU、请求和 GC 指标

---

## 3. JVM

### 3.1 内存结构
- **[Java 规范] JVM 运行时数据区** — JVM Specification 定义 pc register、JVM stack、heap、method area、runtime constant pool 和 native method stack 等抽象区域及相关错误条件；“线程私有/共享”可帮助理解生命周期，但不等于规定物理内存布局。
- **[JVM/GC 实现] HotSpot 如何映射？** — HotSpot 通常把 Java heap 交给所选 collector 管理，并用 Metaspace 实现 method area 的大部分类型元数据；对象头、TLAB、指针碰撞/空闲列表和本地内存布局都属于 JVM 与 collector 实现。
- **[版本变化] PermGen 与 Metaspace** — HotSpot 在 JDK 8 移除了 PermGen 并使用本地内存中的 Metaspace。不能据此说“JVM 规范从 JDK 8 起把方法区改成元空间”，其他 JVM 也不必采用相同实现。
- **[JVM/GC 实现] 对象创建** — 类初始化检查、内存分配、零值初始化和构造调用是常见解释；TLAB、CAS、对象头和具体分配路径需限定 HotSpot、collector、逃逸分析与 JIT 优化，标量替换时甚至可能没有可观察的堆对象分配。

### 3.2 垃圾回收
- **如何判断对象已死亡** — 引用计数法（难以解决循环引用）；可达性分析法（从 GC Roots 向下搜索）
- **GC Roots 有哪些** — 虚拟机栈/本地方法栈引用的对象、方法区静态属性/常量引用的对象、同步锁持有的对象、JNI 引用的对象
- **四种引用类型** — 强引用（绝不回收）、软引用（内存不足时回收）、弱引用（下一次 GC 即回收）、虚引用（不影响生命周期，用于跟踪 GC）
- **[JVM/GC 实现] 回收算法与堆布局** — 标记、复制、整理、分区和分代是 collector 设计策略。Eden/Survivor/Old 是传统分代 HotSpot collector 的常见视图；G1 使用 Region，非分代 ZGC、Shenandoah 或其他 JVM 的布局与事件模型不同。
- **[版本变化] 分代与晋升** — 对象年龄、Survivor 目标、`MaxTenuringThreshold`、大对象阈值和 promotion policy 都依赖 collector、JDK 版本与自适应策略。“默认 15”“同年龄超过 50%”“大对象直接进老年代”不能作为所有现代 JDK 的固定答案。
- **[JVM/GC 实现] Minor/Young/Mixed/Full GC** — 日志术语与触发原因由 collector 定义。Full GC 不是 JVM 规范定义的统一事件，不能一概说成“老年代 GC”或“必然慢”；应结合 collector、cause、停顿阶段、回收范围和实际日志判断。

### 3.3 垃圾收集器
- **[JVM/GC 实现] 如何选择 collector？** — Serial、Parallel、G1、ZGC、Shenandoah 等针对吞吐、暂停、堆规模、CPU 和版本支持做不同权衡。先确认发行版、JDK 版本、默认 collector、容器限制和 SLO，再基于同负载指标选择；名称本身不证明更优。
- **[版本变化] CMS、G1 与 ZGC** — CMS 已从较新 OpenJDK 移除；G1 在 HotSpot JDK 9 起成为常见 server-class 默认；ZGC 经历实验、正式和分代实现演进。具体可用性、默认模式和参数必须查询目标发行版，不能把某个版本的默认值推广到全部 JVM。
- **[JVM/GC 实现] 暂停承诺如何表述？** — G1 的 pause target 是软目标；ZGC 旨在让大部分重工作并发执行、降低暂停对堆大小的敏感度，但仍受 root 数量、系统调度、CPU、页映射、JDK 版本和工作负载影响，不能承诺固定毫秒数或“完全不受堆大小影响”。
- **[JVM/GC 实现] 如何验证？** — 比较 allocation rate、live set、GC CPU、pause 分布、concurrent cycle、promotion/relocation failure、RSS 和应用 P99；只背阶段名称不能证明会调优。

### 3.4 类加载
- **类加载过程** — 加载 → 验证 → 准备（分配内存初始化零值）→ 解析（符号引用转直接引用）→ 初始化（执行 clinit）
- **双亲委派模型及原因** — 类加载器先委托父类处理，父类无法处理才自己加载。好处：防止类被重复加载，防止核心类被篡改。打破方式：自定义类加载器重写 loadClass
- **[版本变化] 方法区实现演变** — JVM 规范的方法区是逻辑区域；HotSpot 早期使用 PermGen，JDK 8 起主要由 Metaspace 实现。Metaspace 使用本地内存但仍受提交策略、类加载器存活和 `MaxMetaspaceSize` 等约束，不能说“完全不受大小限制”。

### 3.5 性能调优
- **[版本变化] 先确认工具边界** — 先执行 `java -version`、`jcmd <pid> VM.version` 和 `jcmd <pid> VM.flags`，再查该发行版当前支持的诊断命令与 flags。不要把已废弃、已移除或只适用于某 collector 的参数当通用推荐。
- **[JVM/GC 实现] GC 日志** — JDK 9+ HotSpot 优先使用 unified logging，例如 `-Xlog:gc*`，并按需要增加 age、heap 或 safepoint tags；旧版 `-XX:+PrintGCDetails` 等 legacy flags 只在对应 JDK 中使用。日志配置要限制轮转、磁盘与敏感信息。
- **[JVM/GC 实现] OOM 与 dump** — 先区分 Java heap、Metaspace、direct/native memory、线程或容器 OOM。优先用 `jcmd`、JFR、GC 日志和受控 heap dump 建证据；`jmap` 在不同版本的命令和风险不同，大堆生产 dump 前必须评估停顿与磁盘。
- **[JVM/GC 实现] 调参原则** — `-Xms/-Xmx`、collector 和 pause/throughput 目标要结合容器预算与 live set；`-Xmn`、tenuring 参数等可能不适用于目标 collector。先证明瓶颈，再在同负载下比较应用延迟、GC CPU、RSS 和错误率。

---

## 4. Spring 与 Spring Boot

### 4.1 IoC / DI
- **IoC/DI 是什么，解决了什么问题** — 控制反转，将对象创建和管理权交给 Spring 容器。降低耦合度，便于资源管理
- **依赖注入方式** — 构造函数注入（推荐，保证完整性和不可变性）、Setter 注入（可选依赖）、Field 注入（不推荐，隐藏依赖）
- **Bean 生命周期** — 实例化 → 属性填充 → 初始化（Aware 接口 → BeanPostProcessor → InitializingBean → init-method）→ 销毁（DisposableBean → destroy-method）

### 4.2 AOP
- **AOP 原理与代理选择** — Spring Framework 的默认规则是：目标对象实现接口时使用 JDK dynamic proxy；没有接口时使用 CGLIB；显式设置 `proxyTargetClass=true` 也会选择 CGLIB。Spring Boot 的自动配置默认值可能不同，例如 Spring Boot 2.7 默认使用 CGLIB，可通过 `spring.aop.proxy-target-class=false` 切换为 JDK proxy；必须核对目标 Boot 版本和项目配置
- **JDK proxy vs CGLIB** — 两者都在运行时创建代理。JDK proxy 基于接口；CGLIB 在运行时生成目标类的子类代理，因此不能覆盖 `final` 方法，也不能代理 `final` 类。代理方法上的 self-invocation 等调用边界仍需单独分析
- **Spring AOP vs AspectJ** — Spring AOP 运行时增强，AspectJ 编译时/类加载时增强；AspectJ 支持更多切入点类型，性能更优

### 4.3 事务
- **@Transactional 失效场景** — 同一个类内部方法调用（不走代理）；非 public 方法；rollbackFor 配置不当；异常被 catch 吞掉； propagation 配置不当（REQUIRES_NEW）；父子事务问题
- **事务传播行为** — REQUIRED（默认，加入当前事务）、REQUIRES_NEW（挂起当前事务新建独立事务）、NESTED（嵌套事务，Savepoint）、SUPPORTS/MANDATORY/NOT_SUPPORTED/NEVER

### 4.4 循环依赖
- **Spring 三级缓存解决循环依赖** — 一级缓存存成品 Bean、二级缓存存早期暴露对象（提前暴露，解决循环依赖）、三级缓存存 ObjectFactory（解决 AOP 代理对象重复生成问题）。结合时二级缓存存代理对象
- **@Lazy 如何解决循环依赖** — 注入代理对象而非真实 Bean，延迟初始化，打破循环调用链

### 4.5 Spring Boot
- **@Autowired vs @Resource** — @Autowired 按类型匹配，@Resource 按名称匹配；多实现时 @Qualifier 指定
- **Bean 作用域** — singleton（默认）、prototype（每次创建）、request、session 等。prototype 不纳入 Spring 生命周期管理
- **Spring Boot 自动配置原理** — `@EnableAutoConfiguration` 通过 `AutoConfigurationImportSelector` 发现并筛选自动配置候选。Spring Boot 2.7+ 和 3.x 的自动配置类注册使用 `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`；更早版本曾在 `META-INF/spring.factories` 的 `EnableAutoConfiguration` key 下注册。条件注解、排除项和类路径共同决定配置是否生效

---

## 5. Java 工程实践与排查

### 5.1 构建、测试与发布

- **如何保证 Java 构建可复现？** — 固定 JDK 与构建工具版本，使用 Maven Wrapper 或 Gradle Wrapper，锁定依赖版本并管理私服来源；CI 从干净环境构建，避免依赖开发机缓存
- **单元测试与集成测试如何分层？** — 纯业务逻辑优先快速单元测试；数据库、消息和 HTTP 边界使用集成测试或契约测试；少量端到端测试验证关键链路，不用大量慢测试替代分层验证
- **升级 JDK 或依赖时如何降低风险？** — 先读取迁移说明和兼容矩阵，运行编译、静态检查和完整测试，比较 GC、延迟与资源指标，再灰度发布并保留回滚路径
- **线上配置如何管理？** — 配置与制品分离，敏感值进入密钥系统；配置项有默认值、校验和变更审计，危险开关支持灰度并明确生效范围

### 5.2 JVM 进程排查

- **Java 进程 CPU 飙高如何定位？** — 先用监控确认时间窗口和容器配额，再定位高 CPU 线程，将操作系统线程 ID 转换后与 `jstack` 或 `jcmd Thread.print` 对齐；必要时用 JFR、async-profiler 或 Arthas 采样验证热点
- **内存持续增长如何区分泄漏和正常缓存？** — 观察 Full GC 后存活集、对象分配速率与缓存命中率；保留 heap dump 用 MAT 比较 dominator tree 和引用链，不能只凭单次堆占用下结论
- **频繁 Full GC 如何分析？** — 关联 GC 日志、堆分代、对象晋升、分配速率和停顿时间；先判断是容量不足、分配过快、内存泄漏还是显式 GC，再选择代码或参数方案
- **Java 请求延迟升高如何建立证据链？** — 同时查看入口延迟、线程池队列、锁竞争、GC、下游调用与数据库指标，用 trace 定位耗时跨度，profiling 只针对可疑时段，避免先改 JVM 参数再找原因

### 5.3 连续追问与常见误区

**连续追问：**
1. 你选择的指标能否区分 CPU、锁、GC 和下游等待？
2. 采样或 dump 对线上进程有什么开销，如何控制持续时间与范围？
3. 修复后用什么基线、压测和灰度指标证明收益，而不是只看一次请求？
4. 如果指标变好但错误率上升，回滚条件是什么？

**常见误区：**
- 把 JVM 参数调大当成默认解决方案，没有先确认对象生命周期和流量变化
- 只依赖 Arthas 的单次输出，不保留原始监控、线程 dump、GC 日志或 heap dump
- 在生产直接执行高开销诊断，不先评估权限、磁盘、CPU 和停顿风险
- 把框架默认行为当作跨版本事实，不核对当前 JDK、Spring Boot 与依赖版本
