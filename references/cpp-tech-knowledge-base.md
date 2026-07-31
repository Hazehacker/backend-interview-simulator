# C++ 后端专项知识库

> 默认考察现代 C++。题目涉及 C++11/14/17/20/23、编译器 ABI、标准库或 glibc 实现时必须明确适用范围。

## 目录

- [1. 基础语义、存储期与链接](#1-基础语义存储期与链接)
- [2. 对象模型与面向对象](#2-对象模型与面向对象)
- [3. RAII、资源管理与异常安全](#3-raii资源管理与异常安全)
- [4. STL、模板与现代 C++](#4-stl模板与现代-c)
- [5. 内存管理与系统交互](#5-内存管理与系统交互)
- [6. 并发、原子操作与内存模型](#6-并发原子操作与内存模型)
- [7. 网络编程与高性能服务](#7-网络编程与高性能服务)
- [8. 工程排查与性能分析](#8-工程排查与性能分析)
- [9. 高频追问链与身份难度](#9-高频追问链与身份难度)

结论归属统一使用以下 marker：

- **[语言标准]**：C++ language standard 规定的可移植语义。未标版本时表示 C++11 及之后仍成立的核心语义；版本新增能力会单独注明。
- **[编译器/标准库实现]**：编译器优化、代码生成或某个 standard library implementation 的策略，不是所有实现必须采用的物理结构或固定常数。
- **[平台/ABI]**：目标架构、数据模型、calling convention、object ABI、链接器和二进制兼容性约束。结论必须绑定具体 target triple 与 ABI。
- **[OS/allocator]**：内核 API、libc、通用 allocator 或替代 allocator 的行为。阈值、缓存、回收和 RSS 表现必须绑定版本、配置与负载。

面试评价优先级是：标准语义正确 > 能区分实现边界 > 能分析生命周期与并发正确性 > 能用工具和证据验证。候选人主动说明“标准没有规定，需查看目标 ABI、实现或 profile”，通常比背固定地址、倍数、阈值和结构字段更有价值。

---

## 1. 基础语义、存储期与链接

### 基础问题与答案要点

#### 指针大小、空指针、野指针与悬空指针

**指针一定是 4 字节或 8 字节吗？**

- **[语言标准]** 不一定。标准只要求指针能表示其类型允许的地址和空指针等状态，不规定 `sizeof(T*)` 的固定值，也不保证对象指针与函数指针具有相同大小或表示。
- **[平台/ABI]** 常见 32-bit 或 64-bit 平台上的普通对象指针经常分别为 4 或 8 字节，但分段地址、能力指针、特殊地址空间和函数描述符都可能产生不同结果。
- `sizeof(p)` 测量指针对象本身，`sizeof(*p)` 测量所指类型；数组在大多数表达式中会衰变为首元素指针，但 `sizeof(array)` 仍是整个数组大小。
- 空指针值不等于“标准保证所有位都为 0”。`nullptr` 自 C++11 起具有 `std::nullptr_t` 类型，应优先于整数 `0` 和宏 `NULL` 参与重载解析。

**野指针、悬空指针和空指针有什么区别？**

- 野指针通常指未初始化或保存无效地址的指针；读取未初始化指针本身就可能产生未定义行为。
- 悬空指针曾指向有效对象，但对象生命周期已经结束，例如返回局部对象地址、容器重分配后保留旧地址、`delete` 后继续持有原指针。
- 空指针明确不指向对象，可比较和传递；解引用空指针是未定义行为。把释放后的指针赋为 `nullptr` 只能降低当前变量误用风险，不能修复其他别名。
- 防治重点是所有权、生命周期和失效规则，不是机械地在每次释放后“置空所有指针”。

#### 指针、引用与 `const`

**指针与引用有哪些标准语义差异？**

- **[语言标准]** 引用必须在初始化时绑定，之后不能通过赋值“改绑”；对引用赋值实际是给被引用对象赋值。指针是对象，可以为空、改指向并参与受约束的指针运算。
- **[语言标准]** `sizeof(ref)`、`typeid(ref)` 等表达式通常观察被引用类型或对象，不能据此得出“引用在机器上永远不占内存”。
- **[编译器/标准库实现]** 局部引用常可完全消除，不需要独立存储。
- **[平台/ABI]** 引用作为数据成员、跨函数边界传递或需要稳定对象布局时，ABI 往往以地址类表示实现；其成员大小、padding 和 calling convention 由目标 ABI 决定。引用抽象语义与物理存储必须分开回答。
- 引用在合法程序中应绑定对象或函数；通过解引用空指针等方式伪造“空引用”已经进入未定义行为，不能把它当成引用支持空值。

**`const T*`、`T* const` 和 `const T* const` 分别是什么？**

- `const T* p` 或 `T const* p` 是 pointer to const：不能通过 `p` 修改 `T`，但 `p` 可改指向。
- `T* const p` 是 const pointer：`p` 不能改指向，但可通过它修改非 const 的 `T`。
- `const T* const p` 同时限制改指向和经该指针修改对象。
- 顶层 `const` 修饰对象本身，底层 `const` 属于指向类型。按值形参的顶层 `const` 不构成不同函数类型；底层 `const` 会影响类型转换和重载。
- `const_cast` 只改变访问路径的 cv 限定。若原对象实际定义为 const，再通过去 const 的路径写入，行为未定义。

#### 值、指针、引用传参与生命周期

**值、指针和引用传参如何选择？**

- 小型可复制值或需要独立副本时按值传递；调用者可通过复制或移动提供参数。是否真正复制受语言语义和 copy elision 影响。
- 允许缺省目标时用指针、智能指针或显式 optional-like 类型表达；裸指针参数通常表示 non-owning，不应仅凭类型推断所有权转移。
- 必须引用既有对象且不接管所有权时使用 `T&`；只读借用常用 `const T&`。对小标量，按值通常比 `const T&` 更直接。
- 需要接管所有权时优先按值接收 `std::unique_ptr<T>` 或明确的 owning type；共享所有权才传 `std::shared_ptr<T>`，不要为了避免写生命周期规则而默认共享。
- `std::span`（C++20）和 `std::string_view`（C++17）是非 owning view。复制 view 不延长底层对象生命周期，返回指向局部或临时数据的 view 会悬空。

**临时对象绑定到引用后一定延长生命周期吗？**

- **[语言标准]** 临时对象直接绑定到某些局部 `const T&` 或 `T&&` 时，其生命周期可延长到该引用的生命周期，但规则依赖初始化上下文。
- 把引用继续传给另一个函数、存进引用成员、从函数返回该引用，通常不会再次延长原临时对象生命周期。
- 绑定到函数形参引用的临时对象通常只活到包含该调用的 full-expression 结束；函数返回该形参引用会留下悬空引用。
- 返回值优化和移动不能让指向局部对象的裸指针、引用或 view 变安全；应返回拥有对象的值。

#### 作用域、存储期与链接

**作用域、存储期和链接为什么不能混为一谈？**

- **[语言标准]** 作用域回答“名字在源码哪里可见”；存储期回答“对象存储从何时存在到何时结束”；linkage 回答“不同作用域或 translation unit 中的声明是否指同一实体”。
- 自动存储期对象通常在进入 block 时创建、离开时销毁，但精确生命周期还受初始化成功、异常展开和临时对象规则影响。
- 静态存储期对象的存储覆盖整个程序执行期，包括 namespace-scope 对象和 function-local `static`；初始化和析构顺序仍需单独分析。
- 线程存储期对象 `thread_local` 对每个线程拥有实例，其初始化时机和线程退出析构会影响动态库卸载、线程池和 shutdown。
- 动态存储期来自 `new` expression 或其他显式生命周期管理；“动态”不等于一定由 libc heap 的某个固定数据结构实现。

**`static` 在不同位置分别表达什么？**

- namespace scope 的 `static` 名字具有 internal linkage，只在当前 translation unit 关联。
- block scope 的 `static` 对象具有静态存储期，但名字仍只有 block scope。
- **[语言标准，C++11 起]** function-local static 的初始化具有线程安全保证：并发首次进入只完成一次初始化；初始化函数内部的递归、阻塞和异常仍需分析。
- class static data member 不属于每个实例。传统非 inline 成员通常需要类外定义；C++17 `inline static` data member 可在类内给出定义。

#### 头文件定义、ODR、`inline` 变量和 `extern "C"`

**为什么普通非 `inline` 函数或变量不应直接定义在公共头文件？**

- **[语言标准]** One Definition Rule（ODR）要求特定实体在整个程序中只有一个定义；某些实体如 class、template、inline function 和 inline variable 可在多个 translation unit 中出现满足严格等价条件的定义。
- 头文件被多个 translation unit 包含后，普通 external-linkage 定义会形成 multiple definition；include guard 只能防止同一 translation unit 重复包含，不能解决跨 translation unit ODR。
- template 和 inline 定义通常放在头文件，是为了让每个使用点可见；多份定义必须满足 token、name lookup 等 ODR 条件。宏让不同 translation unit 看到不同定义，可能形成难诊断的 ill-formed, no diagnostic required 问题。
- namespace-scope 非 volatile `const` 变量默认常具有 internal linkage，但这不应被当成随意在头文件复制有状态对象的设计手段。

**`inline` 是否等于编译器一定内联？**

- **[语言标准]** `inline` 的核心语言作用是允许满足条件的多份定义并表示同一实体，不承诺机器码 call 一定被展开。
- **[编译器/标准库实现]** 是否进行 inline optimization 由编译器基于优化级别、LTO、profile、函数体和调试要求决定；未写 `inline` 的函数也可能被优化内联。
- **[语言标准，C++17 起]** inline variable 可在多个 translation unit 中定义并表示一个实体，适合头文件常量或静态数据成员；它不等同于“每个 translation unit 一个副本”。

**`extern "C"` 做了什么，没有做什么？**

- **[语言标准]** language linkage 影响函数类型和具有 external linkage 的函数名等链接语义，用于与 C linkage 的接口对接。
- 它不把函数体变成 C，不关闭异常、构造析构、重载之外的 C++ 语义，也不自动保证任意 C++ class、reference、exception 或 STL type 可以跨 C ABI。
- **[平台/ABI]** 实际 symbol spelling、calling convention、结构布局和 C/C++ interoperability 仍取决于平台 ABI 与两端编译器。稳定边界通常使用 C-compatible 标量、显式布局的数据和 opaque handle。
- 不应让 C++ exception 穿过不理解异常 ABI 的 C 调用边界；应在边界内捕获并转换为错误码或显式状态。

### 连续追问

1. 在目标是 x86-64 时，能否直接断言所有对象指针和函数指针都是 8 字节？应查看哪些 ABI 或编译结果？
2. 为什么 `sizeof(int&)` 的写法不能证明引用不占对象布局空间？引用成员又如何验证？
3. `const int*`、`int* const` 与函数参数中的顶层 `const` 对重载分别有什么影响？
4. 返回 `const std::string&` 指向局部变量、临时对象和成员对象时，生命周期风险分别是什么？
5. `std::string_view` 参数为何通常高效，但把它保存为成员前必须确认什么？
6. block scope、automatic storage duration 和 no linkage 是否总是同时出现？举出 function-local static 的反例。
7. 两个 translation unit 包含同一个头文件，为什么 include guard 仍挡不住普通函数的 multiple definition？
8. inline function 在两个 translation unit 中受不同宏影响后，为什么可能链接成功却仍违反 ODR？
9. `extern "C"` API 为什么不应直接暴露 `std::string`、exception 或带虚函数的对象？

### 常见误区

- 固定回答“32 位指针 4 字节、64 位指针 8 字节”，不说明对象指针、函数指针、目标 ABI 和特殊地址空间
- 用 `sizeof(ref)` 推导“引用永远零成本且不占存储”，忽略 reference member、跨调用边界和 ABI
- 把空指针、野指针和悬空指针当成同一概念，只靠 `p = nullptr` 解决所有别名生命周期问题
- 声称 C++ 有“引用传递”后不再分析引用或 view 的借用生命周期
- 把 scope、storage duration、lifetime 和 linkage 混成“局部在栈上、全局在堆外”
- 认为 include guard 能解决跨 translation unit 的 ODR
- 把 `inline` 当成性能命令，把 inline variable 当成每个文件一个变量
- 认为 `extern "C"` 自动提供跨编译器、跨版本的完整 C++ ABI

### 身份难度

- **实习/校招**：能区分指针、引用、`const` 组合、空/野/悬空指针和四类存储期；知道指针大小平台相关。
- **初中级 C++ 开发**：能解释 view 与临时对象生命周期、scope/storage/linkage 差异、头文件 ODR、function-local static 和 C ABI 边界。
- **高级/资深 C++ 开发**：能审查跨 translation unit ODR、TLS shutdown、inline variable 和 ABI 暴露风险，并用 target triple、symbol、layout dump 或反汇编验证实现结论。

---

## 2. 对象模型与面向对象

### 基础问题与答案要点

#### C 与 C++ 的 `struct`、C++ 的 `struct` 与 `class`

**C 的 `struct` 与 C++ 的 class type 有何边界？**

- C 和 C++ 是不同语言，不能只回答“C++ struct 多了函数”。C++ class type 可有 constructor、destructor、member function、access control、inheritance、virtual function、template 等语义。
- C 中 tag name 与普通 identifier 处于不同 namespace，常写 `struct Node` 或配合 `typedef`；C++ 的 class name 可直接作为 type name 使用。
- 相同源码在 C 与 C++ 下的 initialization、implicit conversion、name lookup 和 type compatibility 可能不同。共享头文件应限定双方都接受的子集并分别编译验证。
- **[平台/ABI]** 即使字段看起来相同，跨语言二进制交互仍要约定整数宽度、alignment、packing、endianness 和 calling convention。

**C++ 中 `struct` 与 `class` 有什么差异？**

- **[语言标准]** 二者能力基本相同；`struct` 默认 member access 和 base-class access 是 `public`，`class` 默认是 `private`。
- “struct 只能放数据、class 才能有方法”是错误的。工程中常用 struct 表达简单 value type，用 class 强调 invariant，但这是约定而非语言限制。
- access control 是编译期语义，不是安全边界，也不必然改变对象物理布局。

#### `union`、alignment、padding 与类型性质

**`union` 的 active member 和 type punning 如何回答？**

- **[语言标准]** union 的 non-static data members 共享存储，任一时刻通常只有一个 member 的 lifetime 处于 active 状态。
- 读取非 active member 一般不能作为可移植 type punning；standard-layout union 的 common initial sequence 有受限例外，但不能推广为任意重解释。
- C++20 可用 `std::bit_cast` 表达满足约束的位级转换；跨版本可使用 `std::memcpy` 配合 trivially copyable 类型。`reinterpret_cast` 后直接解引用还要满足 lifetime、alignment 和 aliasing。
- union 含非 trivial member 时必须显式管理构造和析构；实际工程通常优先使用 `std::variant` 表达带标签的 sum type。

**alignment 和 padding 由谁决定？**

- **[语言标准]** `alignof(T)` 给出类型 alignment requirement，`sizeof(T)` 包含使数组元素正确对齐所需的 padding。C++23 前，对具有相同 access control 的 non-zero-size non-variant non-static data members，后声明成员具有更高地址；不同 access-control 段之间的顺序保证更弱，不能笼统说所有字段地址都按声明顺序递增。
- **[语言标准，C++23 起]** non-zero-size non-variant non-static data members 按声明顺序具有更高地址，不再以相同 access control 为前提；但声明为 `[[no_unique_address]]` 的成员是 potentially-overlapping subobject，可能与其他对象同址，不能把地址严格递增推广到它。
- **[平台/ABI]** 基本类型大小、自然对齐、tail padding 利用、bit-field 分配和 base subobject 布局由目标 ABI 进一步规定。
- `alignas` 可请求更严格的有效对齐；over-aligned dynamic object 需要匹配的 aligned allocation 支持。手工把任意字节地址转成 `T*` 不会自动满足 alignment。
- `#pragma pack`、compiler attribute 和 layout dump 是实现工具，不是 C++ 标准可移植协议。改变 packing 可能产生未对齐访问成本或 fault。

**standard-layout 与 trivially copyable 分别解决什么问题？**

- standard-layout 约束部分布局性质，适用于某些 C interoperability、`offsetof` 和 common initial sequence 场景；它不保证跨不同 ABI 的完整 wire format。
- trivially copyable 允许对象表示通过 character/byte array 或 `memcpy` 往返复制；它不代表字节序、padding 值和跨版本格式稳定。
- polymorphic class 通常不是 standard-layout。一个类型“字段全是 POD 风格”也不等于可直接持久化或发到网络。
- 面试中应分别检查 layout property、lifetime、aliasing、endianness 和 protocol compatibility，不能用“POD”一词包办。

#### 对象生命周期、构造析构与特殊成员

**对象 lifetime 何时开始和结束？**

- **[语言标准]** storage 可用不等于对象 lifetime 已开始。对象 lifetime 通常在获得适当 storage 并完成相应 initialization 后开始，在 destructor 开始或 storage 被复用/释放等规则下结束。
- lifetime 之外通过 glvalue 访问对象通常是未定义行为；少数操作和 implicit-lifetime type 有专门规则，不能把“内存里字节还在”当成对象仍存在。
- constructor 抛异常时，完整对象尚未构造成功，其 destructor 不执行；已经完成构造的 base 和 member subobject 会按规则析构，因此资源应放进成员 RAII type。
- destruction 顺序大体与 construction 相反：先执行最派生 destructor body，再销毁 members 和 bases；数组元素按反序销毁。静态对象跨 translation unit 的顺序需要额外控制。

**编译器何时隐式声明或删除 copy/move 操作？**

- special member functions 包括 default constructor、destructor、copy/move constructor 和 copy/move assignment。
- 用户声明某些 copy、move 或 destructor 会抑制或影响其他 special member 的隐式生成；成员或 base 不支持对应操作时，函数可能被定义为 deleted。
- `= default` 请求编译器生成语义，`= delete` 禁止调用；是否 trivial、`constexpr` 或 `noexcept` 还取决于成员、base 和标准版本。
- 不应只背“写析构就没有移动”一句口诀，应让编译器 traits、明确 default/delete 和测试表达类型契约。

#### 虚函数、虚析构与动态分派

**虚函数一定通过虚表调用吗？**

- **[语言标准]** 标准规定 virtual dispatch 的可观察语义，不要求 vtable、vptr 的存在、数量、位置或固定内存布局。
- **[平台/ABI]** 主流 C++ ABI 通常使用 vtable/vptr，并可能为 multiple inheritance 生成 pointer adjustment thunk，为 virtual inheritance 保存额外 offset 信息；具体布局必须绑定 Itanium C++ ABI、MSVC ABI 等目标。
- **[编译器/标准库实现]** 编译器在动态类型可证明时可 devirtualize，直接调用或内联；这不改变源码层面的 virtual 语义。
- constructor/destructor 期间的 virtual call 按当前构造或析构阶段的 class 处理，不会分派到尚未构造或已析构的更派生部分。

**base destructor 什么时候必须是 virtual？**

- 多态 base 允许 owning deletion 时，默认应使用 virtual destructor；普通删除路径下，经 non-virtual base pointer 删除实际 derived object 会产生未定义行为。
- **[语言标准，C++20 起]** destroying delete 为受控设计提供例外路径：若查找并选中 destroying `operator delete`，该 function 负责按真实对象契约完成析构和释放。不能把相关规则简化成“只要 base destructor 非 virtual 就一概走同一路径”，但也不能假设 destroying delete 会自动识别动态类型。
- 安全建议仍是：多态 base owning deletion 默认使用 virtual destructor；只有受控的 destroying delete/ownership design 能明确证明动态类型判定、完整析构、匹配释放和模块生命周期时，才考虑 non-virtual 方案。
- 只作为 non-owning interface 且禁止经 base 删除时，可使用 protected non-virtual destructor 表达约束；必须让所有权 API 与此一致。
- virtual destructor 会使类型 polymorphic，并通常带来 ABI/layout 影响；不能因此拒绝必要的正确性，也不应给所有 value type 无差别添加 virtual destructor。
- `override` 应用于 overriding function 以让编译器检查签名；`final` 可限制继续 override 或继承，并可能帮助优化，但首要作用是表达设计。

**多继承和虚继承的核心风险是什么？**

- non-virtual diamond 会包含多份共同 base subobject；virtual inheritance 让最派生对象共享一份 virtual base，由 most-derived constructor 负责构造。
- pointer 从 derived 调整到不同 base 时地址可能变化；`reinterpret_cast` 不能替代正确的 `static_cast`/`dynamic_cast` adjustment。
- `dynamic_cast` 对 polymorphic hierarchy 提供运行时检查；指针失败返回 null，引用失败抛 `std::bad_cast`。RTTI 成本和实现属于 ABI/编译器范围。
- 多继承本身不是错误，但跨 shared-library ABI、对象大小、构造顺序和 ownership interface 会更复杂。组合通常更容易维护。

#### Object slicing、covariance 与 ABI 稳定性

**什么是 object slicing？**

- 把 derived object 按值赋给 base object，只复制 base subobject，derived state 和动态类型被切掉；之后经该 base value 调 virtual function 也不会恢复原 derived。
- 多态对象应通过 reference、pointer 或明确的 type-erasure/value-polymorphism wrapper 传递；容器 `std::vector<Base>` 不能保存 heterogeneous derived values 而保持原动态类型。
- virtual function 的 covariant return 只适用于满足规则的 pointer/reference to class，不适用于任意 smart pointer。

**为什么“编译器相同就 ABI 稳定”仍不充分？**

- **[平台/ABI]** ABI 还受 compiler version/flags、standard library ABI、exception/RTTI 开关、packing、visibility、LTO、CPU feature 和 build mode 影响。
- 在 public ABI 暴露 STL container、inline private layout 或 polymorphic class，会把标准库实现和对象布局耦合给调用方。
- 稳定插件边界更常用 versioned C ABI、opaque handle、显式 ownership 和 capability negotiation；C++ 内部仍可使用 class 与 RAII。

### 连续追问

1. 同一个 `struct Packet` 同时被 C 和 C++ 编译，哪些源码和 ABI 条件必须分别验证？
2. 为什么 `union` 写入 `float` 后读取 `uint32_t` 不能直接当成可移植位转换？C++20 如何表达？
3. C++23 前后 member address ordering 有何变化？不同 access-control 段和 `[[no_unique_address]]` 为什么不能套用同一条“严格递增”结论？
4. standard-layout、trivially copyable 和“可直接序列化”为什么不是同义词？
5. placement new 已在同一地址构造新对象后，旧 pointer 何时可直接使用，何时需要 `std::launder`？
6. constructor 抛异常时，哪些 destructor 会执行，为什么把裸资源先申请再赋给成员有风险？
7. constructor 中调用 virtual function 为什么不会进入最派生 override？
8. 通过 `Base*` 删除 `Derived` 时，普通 non-virtual destructor 路径为什么不安全？C++20 destroying delete 若要形成受控例外，必须自行证明哪些条件？
9. multiple inheritance 下 `Derived*` 转成不同 base pointer 后数值为何可能变化？
10. 一个跨动态库接口暴露 `std::string` 和 virtual class 时，需要审查哪些 ABI 维度？

### 常见误区

- 只回答“struct 默认 public、class 默认 private”，完全忽略 C 与 C++ 是不同语言及跨语言 ABI
- 用 union 或 `reinterpret_cast` 随意 type punning，不检查 active member、lifetime、alignment 和 aliasing
- 把 standard-layout、trivially copyable、POD 和可持久化 wire format 混为一谈
- 不区分 C++23 前后的 member address ordering，或忽略 `[[no_unique_address]]` potentially-overlapping member 可同址
- 认为 storage 中有旧字节就代表旧对象 lifetime 仍在
- 把 vtable、vptr 数量和位置说成 C++ standard 保证
- 认为 constructor 中 virtual call 能访问完整 derived state
- 忘记 polymorphic base 的删除契约；或看到 C++20 destroying delete 后，就误以为任意 non-virtual base deletion 都会自动正确析构
- 把 virtual inheritance 说成“只省一份内存”，不解释 construction ownership 和 pointer adjustment
- 将同一 compiler family 误认为天然 ABI compatible

### 身份难度

- **实习/校招**：能区分 struct/class 默认权限、union 风险、padding、构造析构顺序、virtual function 和 virtual destructor。
- **初中级 C++ 开发**：能解释 standard-layout/trivially copyable、object slicing、constructor 异常、multiple inheritance adjustment 和对象 lifetime。
- **高级/资深 C++ 开发**：能严格区分 virtual semantics 与 vtable ABI，设计稳定的 shared-library 边界，并用 layout dump、symbol、RTTI 和反汇编证据审查 ABI。

---

## 3. RAII、资源管理与异常安全

### 基础问题与答案要点

#### RAII 与 ownership

**RAII 只用于管理内存吗？**

- RAII 将资源 acquisition 与对象 initialization 绑定，将 release 放入 destructor，使 normal return、early return 和 exception unwinding 共享同一清理路径。
- 资源包括 memory、file descriptor、socket、mutex、transaction guard、temporary file、mapped region 和 callback registration，不限于 `new`/`delete`。
- RAII type 必须明确 ownership、move/copy 语义和 destructor 的失败策略。仅在 destructor 里写 `delete`，但允许错误 copy，仍会 double free。
- 资源 handle 往往有合法的 invalid state；constructor 失败应不产生半初始化 owner，move 后 source 应保持可析构、可赋值的有效状态。

**裸指针是否一定不能出现？**

- 裸指针和引用适合表达 non-owning observation；问题不是“裸”本身，而是 ownership 与 lifetime 是否清晰。
- owning raw pointer 容易在 early return、exception 和复杂别名下泄漏，应封装进 RAII owner。
- API 不应从 `T*` 猜测 transfer；使用 `std::unique_ptr<T>`、factory return value、span/view 或命名清晰的 handle 表达契约。

#### Rule of Zero、Rule of Five 与 copy/move

**Rule of Zero 为什么优先于 Rule of Five？**

- Rule of Zero：让成员使用正确的 RAII type，使 compiler-generated destructor/copy/move 自然组合，业务 class 不直接管理裸资源。
- 若 class 直接拥有不可平凡资源并需要自定义生命周期，通常要整体审视 destructor、copy/move constructor、copy/move assignment，即 Rule of Five。
- 资源只能独占时应删除 copy 并提供 move；可以复制时必须定义 deep copy、shared ownership 或 copy-on-write 等明确语义。
- copy-and-swap 可提供清晰的 strong guarantee，但会有额外临时对象和资源峰值；不是所有 assignment 的唯一优雅实现。

**move 是否等于“零拷贝”？**

- **[语言标准]** move 只是对 rvalue 调用相应 overload 的机制；具体类型可能转移 handle，也可能逐元素移动，甚至退化为 copy。
- 标准库对象被 move 后通常处于 valid but unspecified state，只能执行其契约允许的操作；不能假设一定 empty。
- `std::move` 本身只做 cast，不移动任何字节。对 `const T` 使用 `std::move` 常无法调用需要 `T&&` 的 move constructor，可能转为 copy。
- 某些标准容器在 reallocation 时会根据 element move 是否 `noexcept`、是否可复制等条件选择 move 或 copy，以维持异常保证；这是契约条件与实现策略共同作用，不能概括为永远 move。

#### 异常安全保证

**no-throw、strong 和 basic guarantee 分别是什么？**

- no-throw guarantee：操作承诺不抛异常并完成其契约，常见于 destructor、swap 和 move primitive；`noexcept` 违约会调用 `std::terminate`。
- strong guarantee：失败时可观察状态像操作从未发生，常通过先构造临时结果再 commit/swap。
- basic guarantee：失败后 invariant 仍成立、没有资源泄漏，但值可能已经改变。
- no guarantee 意味着异常后连基本 invariant 都不能依赖。接口文档和 code review 应明确需要哪一层，而不是泛称“异常安全”。

**destructor 能否抛异常？**

- destructor 通常应为 non-throwing；在 stack unwinding 已有 active exception 时再让 destructor 逃出异常会触发 `std::terminate`。
- 释放失败若必须上报，应提供显式 `close`/`commit` 操作，让调用者处理错误；destructor 做 best-effort cleanup 或记录不可抛诊断。
- 默认 destructor 的 exception specification 受 members/bases 影响。显式写 `noexcept(false)` 极少是资源 owner 的好接口。

#### `unique_ptr`

**`unique_ptr` 的 ownership 和 deleter 有哪些细节？**

- `std::unique_ptr<T, D>` 表达 exclusive ownership，不可复制、可移动；离开作用域时通过 deleter 释放。
- deleter 是类型的一部分，可保存 file descriptor closer、C API release function 或 allocator context。stateful deleter 可能增大 `unique_ptr` 大小，empty deleter 常可被压缩，但布局属于实现。
- `unique_ptr<T[]>` 使用数组删除语义并提供下标；不能用 `unique_ptr<T>` 管理 `new T[]`。
- `release()` 只放弃 ownership 并返回 pointer，不释放资源；`reset()` 会释放旧资源并接管新 pointer。
- incomplete type 可与 `unique_ptr` 配合实现 pImpl，但执行默认 deleter 的位置必须看到 complete type；通常把 owning class destructor 定义在实现文件。

#### `shared_ptr`、`weak_ptr` 与控制块

**`shared_ptr` 通常包含什么，控制块负责什么？**

- **[语言标准]** `shared_ptr` 提供 shared ownership 语义。多个 handles 在最后一个 owning reference 消失时销毁 managed object；weak ownership 不延长 managed object lifetime。
- **[编译器/标准库实现]** 主流实现通常让 handle 保存 stored pointer 和 control-block pointer，控制块保存 strong/weak count、deleter、allocator 等；标准不规定字段布局和计数宽度。
- `std::make_shared` 通常可把 object 与 control block 放在一次 allocation 中，改善 locality 和异常安全；这是允许且常见的实现策略，不是“任何实现永远只分配一次”的语言级物理承诺。
- 当 strong count 为零时 object 被销毁；仍有 `weak_ptr` 时 control block 可能继续存在。make-shared 的组合 allocation 可能因此保留整块 storage，尽管 object lifetime 已结束。
- aliasing constructor 可共享一个 control block 但 stored pointer 指向相关 subobject；“`get()` 相同/不同”不能单独判断 ownership group。

**`shared_ptr` 的线程安全到底保证什么？**

- **[语言标准]** 不同 `shared_ptr` objects 即使共享 ownership，也可由不同线程执行 handle 层的操作而不因 control block 计数产生 data race。
- 同一个 `shared_ptr` object 被多个线程执行 non-const handle mutation，仍需 synchronization；C++20 可使用 `std::atomic<std::shared_ptr<T>>`。
- control block 引用计数安全不代表 pointee thread-safe。多个线程经各自 `shared_ptr<T>` 修改同一个 `T`，仍必须按 `T` 的 invariant 加锁或使用其他同步。
- `use_count()` 只是瞬时观察，不能作为“只有我一个 owner，所以无需同步”的可靠 check-then-act 条件。

**循环引用如何发生，`weak_ptr` 如何解决？**

- 若 ownership graph 中形成全是 strong edge 的 cycle，外部 handles 消失后 strong counts 仍非零，对象不会销毁。
- 将语义上 non-owning、parent/back-reference、observer 或 cache edge 改为 `weak_ptr`，可打破 ownership cycle。
- `weak_ptr::lock()` 原子地尝试取得临时 shared ownership，失败返回 empty `shared_ptr`；先 `expired()` 再使用会有 TOCTOU，应直接检查 `lock()` 结果。
- `enable_shared_from_this` 依赖对象已由合适的 `shared_ptr` ownership 建立；constructor 中调用 `shared_from_this()` 或为同一 raw pointer 创建多个独立 control blocks 都是严重错误。

#### 自定义 deleter 与跨模块释放

**为什么跨动态库边界经常需要自定义 deleter？**

- **[平台/ABI]** 分配和释放可能必须发生在相同 runtime、heap、allocator instance 或 module contract 下。调用方直接 `delete` 一个由另一模块特定 factory 分配的对象可能不兼容。
- factory 可返回带 module-provided deleter 的 unique/shared owner，或提供成对 `create/destroy` C ABI。
- deleter 还必须匹配资源种类：`fclose`、`closedir`、`munmap`、`SSL_free`、custom pool release 都不能用普通 `delete` 替代。
- deleter 中的 code 和 allocator context 必须比最后一个 owner 活得更久；动态库提前 unload 会让 function pointer 失效。

### 连续追问

1. 一个 class 同时拥有 file descriptor、heap buffer 和 mutex，如何用成员 RAII type 实现 Rule of Zero？
2. `std::move(const_obj)` 为什么可能调用 copy constructor？如何从签名判断？
3. vector reallocation 时，element move constructor 的 `noexcept` 为什么会影响异常保证和策略？
4. copy-and-swap 提供什么保证，又可能带来哪些 allocation 与峰值内存成本？
5. destructor 中 `close` 失败如何处理，为什么直接 throw 风险很高？
6. `unique_ptr<T, D>` 的 deleter 为什么会影响 owner type、size 和跨模块 ABI？
7. `make_shared` 后 object 已析构但大量 weak references 存在时，哪部分 storage 可能仍保留？
8. 两个线程各自持有一份 `shared_ptr<Counter>` 并执行 `counter->value++`，为什么 control block 安全仍不够？
9. 为什么 `if (p.use_count() == 1)` 不能建立可靠 exclusive-access 证明？
10. `weak_ptr::expired()` 后再调用 `lock()` 为什么仍可能失败？
11. 对同一 raw pointer 分别构造两个 `shared_ptr` 会发生什么，`enable_shared_from_this` 又依赖什么？

### 常见误区

- 把 RAII 等同于“析构时 delete 内存”，忽略 file、socket、lock、mapping 和 transaction 等资源
- 自定义 destructor 后仍依赖错误的 implicit copy，造成 double close/double free
- 认为 `std::move` 一定移动、一定 O(1)、move 后对象一定为空
- 只说“异常安全”而不区分 no-throw、strong、basic guarantee
- 从 destructor 直接抛出清理错误，不考虑 stack unwinding 与 terminate
- 用 `unique_ptr<T>` 管理 `new T[]`，或调用 `release()` 后误以为资源已经释放
- 把 `make_shared` 的常见单次 allocation 写成所有实现必须遵循的固定布局
- 把 control block thread-safety 等同于 pointee thread-safety
- 依赖 `use_count()` 实现同步，或用 `expired()` + 使用形成 TOCTOU
- 为同一 raw pointer 创建多个 control blocks，或在 constructor 中调用 `shared_from_this()`

### 身份难度

- **实习/校招**：能解释 RAII、exclusive/shared ownership、Rule of Zero/Five、move 基础和循环引用。
- **初中级 C++ 开发**：能设计 deleter、pImpl、copy/move 契约和异常保证，并准确区分 control block 与 pointee 的并发安全。
- **高级/资深 C++ 开发**：能审查复杂 ownership graph、跨模块释放、allocator/deleter lifetime、atomic shared ownership 和 failure-atomic API，而不是默认滥用 `shared_ptr`。

---

## 4. STL、模板与现代 C++

### 基础问题与答案要点

#### `vector` 的复杂度、capacity 与失效规则

**`vector` 如何增长，扩容倍数是多少？**

- **[语言标准]** 除 `std::vector<bool>` 特化外，`vector<T>` 提供 contiguous storage，末尾 insertion 具有 amortized constant complexity；标准不规定 capacity 的固定增长倍数。
- **[语言标准]** `std::vector<bool>` 是空间优化特化，元素访问使用 proxy reference，不表示一段连续 bool objects；不能把普通 `vector<T>` 的 `T*`、真实 `bool&` 或 contiguous range 直觉套给它。
- **[编译器/标准库实现]** 1.5 倍、2 倍或与请求容量/元素大小相关的策略都是实现选择，并可能随标准库版本、debug mode 和 allocator 改变。
- reallocation 时所有 references、pointers 和 iterators 都失效；未发生 reallocation 的 `push_back`/`emplace_back` 通常保留既有元素的 references/iterators，但旧 `end()` 失效。
- 在中间 insert 且未 reallocate 时，插入点及其后的 iterators/references 会失效；erase 会使被删除位置及其后的 iterators/references 失效。
- `reserve(n)` 只保证 capacity 至少达到请求并在不超过 capacity 前避免 growth reallocation，不改变 size；`resize(n)` 改变元素数量并构造/销毁元素。

**`shrink_to_fit()` 能否保证归还内存？**

- **[语言标准]** 它是 non-binding request，不能据此保证 capacity 变为 size 或 RSS 下降。
- **[OS/allocator]** 即使容器释放 allocation，allocator 也可能把 arena/cache 留在进程内而不立即归还 OS。
- 要证明内存改善，应同时看 container capacity、heap allocation profile、allocator stats、RSS/PSS 和工作集，而不是只看一项。

#### `deque`、`list`、`map` 与 `unordered_map`

**如何比较常见容器？**

- `deque` 支持 random access，在两端 insertion/removal 通常为 constant complexity，但不要求整段 contiguous；中间插入移动成本通常为 linear。
- **[语言标准]** `std::list` 的标准契约是 sequence container、bidirectional iterator、已知位置单元素 constant-time insertion/erase，以及除 erased elements 外的 iterator/reference 稳定性；range insertion/erase 的复杂度随处理的元素数增长。标准不规定 node 字段、指针数量或 allocation 粒度。
- **[编译器/标准库实现]** 主流标准库实现通常采用 doubly-linked nodes，并常见每节点 allocation、额外指针开销和较差 locality；这些是选型时应测量的实现特征，不是标准要求的物理布局。
- `map`/`set` 提供按 strict weak ordering 排序的 associative semantics，查找、插入、删除通常 logarithmic；“一定是红黑树”是主流实现而非标准要求。
- `unordered_map`/`unordered_set` 提供 average constant、worst-case linear 的查找/插入/删除复杂度；hash quality、load factor、adversarial keys 和 rehash 决定实际表现。
- 不应只按 Big-O 选容器。元素数量、cache locality、allocation、iteration pattern、稳定地址、排序需求和攻击面同样重要。

**迭代器失效怎样回答才可靠？**

- node-based ordered containers 的 insert 通常不使已有 iterators/references 失效，erase 只使被删元素失效；node handle 操作有单独契约。
- unordered containers 的 rehash 会使 iterators 失效，但对 elements 的 references/pointers 通常保持有效；erase 只使被删元素相关 handle 失效。
- deque 的不同 insert/erase 位置有细粒度规则：两端插入、中间插入、两端删除对 iterator/reference 的影响不同。不能用一句“deque 永不失效”概括，应查目标标准对应 operation 的契约。
- `end()` 也是 iterator，size 改变后经常需要重新取得。debug iterator 可更早报错，但不是 release build 的安全机制。

#### Algorithm、range 与 complexity contract

**STL complexity 是性能保证吗？**

- complexity 是抽象操作次数的上界或摊销约束，不等同于 wall-clock latency、allocation 次数、cache miss 或 syscall 数。
- comparator/hash 必须满足相应语义；违反 strict weak ordering 会破坏 ordered algorithm/container 前提，结果不是“排序稍有误差”。
- C++20 ranges 通过 iterator/sentinel、view 和 constraint 提高组合性；许多 views non-owning 且 lazy，底层 range 失效后 view 同样悬空。
- parallel algorithms 还受 execution policy、实现支持和 callable 副作用约束；不能默认指定 policy 就一定并行或更快。

#### Allocator、raw storage 与对象 lifetime

**allocator 分配的是对象还是 storage？**

- **[语言标准]** allocator abstraction 负责获得适当 raw storage；对象 construction/destruction 是独立 lifetime 操作。现代代码通常通过 `std::allocator_traits`、`std::construct_at`（C++20）和 `std::destroy_at` 表达。
- container allocator 还涉及 copy/move/swap 时是否 propagate、allocator equality 和 deallocation 必须回到兼容 allocator 的约束。
- `std::pmr`（C++17）把 memory resource 运行时多态化，适合 arena、request-scoped allocation 和批量释放；容器不能比其 `memory_resource` 活得更久。
- monotonic resource 的单次 deallocate 通常不回收个别块，优势来自批量生命周期；不适合无限增长的长期对象而没有 reset 边界。

**placement new 与 `std::launder` 分别解决什么？**

- placement new 在调用方提供的适当 storage 中开始新对象的 construction，本身不分配 backing storage；失败时 backing storage 仍由调用方管理。
- 新对象必须满足 size/alignment，旧 non-trivial object 通常要先正确 destruction；最终也不能对 placement object 使用普通 `delete`，除非 storage 确实来自匹配 new-expression 且契约允许。
- **[语言标准，C++17 起]** `std::launder` 用于特定场景下取得指向新对象的可用 pointer，例如 replacement 涉及 const/complete object、base subobject 等使旧 pointer 不能透明重定向的情况。
- `launder` 不是“让任意 type punning 合法”的工具，也不修复 alignment、strict aliasing 或不存在的 lifetime。

#### `auto`、`decltype`、value category 与 forwarding

**`auto` 与 `decltype` 的推导差异是什么？**

- `auto` 大体使用 template argument deduction 规则，按值形式通常去掉 top-level cv/reference；`auto&`、`const auto&`、`auto&&` 分别表达不同约束。
- `decltype(expr)` 对 unparenthesized id-expression/member access 有特殊规则；其他表达式根据 value category 推导 `T&`、`T&&` 或 `T`。`decltype((x))` 对 lvalue `x` 得到 reference type。
- `decltype(auto)` 保留 `decltype` 规则，返回局部变量时多一层括号可能意外返回 dangling reference。
- `auto` 不是“动态类型”，类型仍在 compile time 确定。

**右值引用、移动语义和完美转发有什么边界？**

- named variable 即使类型为 `T&&`，表达式本身仍是 lvalue；要再次按原 value category 转发需使用 `std::move` 或 `std::forward`。
- forwarding reference 只出现在发生 deduction 的特定 `T&&` 形式；class 中固定类型 `Widget&&` 不是 forwarding reference。
- reference collapsing 使 `T& &`、`T& &&`、`T&& &` 归并为 `T&`，只有 `T&& &&` 为 `T&&`。
- perfect forwarding 保留 value category 和 cv/ref，但也可能放大 overload、initializer-list、bit-field 和 lifetime 难题；不应把所有 wrapper 都写成无约束 universal reference。

#### Lambda、`constexpr`、SFINAE、concept 与 coroutine

**lambda capture 最容易错在哪里？**

- `[=]`/`[&]` 的 capture 语义不等于自动安全。异步执行的 reference capture 或捕获 `this` 可能在 closure 调用前悬空。
- capture `shared_ptr` 可延长对象 lifetime，但也可能形成 cycle；capture `weak_ptr` 后在执行时 `lock` 常更适合 callback registration。
- generalized lambda capture（C++14）可 move-capture unique resource；closure type 的 copy/move 能力由 captures 决定。
- 并发调用同一 mutable closure 仍需同步其 captured state。

**`constexpr` 是否表示一定在编译期执行？**

- `constexpr` 表示实体可参与 constant evaluation 并满足相应限制；在非 constant-expression 上调用 `constexpr` function 仍可在 runtime 执行。
- `consteval`（C++20）要求 immediate invocation 在 compile time 求值；`constinit`（C++20）约束 static/thread storage variable 的 initialization，不使变量自动 const。
- compile-time computation 会把部分成本转移到 build time 和 binary；是否更快仍需考虑 code size 与 runtime path。

**SFINAE、concept 和 coroutine 应如何分层？**

- SFINAE 在 template substitution 的 immediate context 失败时让 candidate 从 overload set 移除，不是捕获 template body 中所有错误的通用异常机制。
- `if constexpr`（C++17）在实例化时丢弃不选分支，适合局部 compile-time branching，但 condition 外的语法仍需合法。
- concept/constraints（C++20）用命名语义约束参与 overload ordering，通常比深层 `enable_if` 更易读；它们约束可用表达式，不自动证明业务语义。
- coroutine（C++20）由 compiler transform 为带 promise/frame 的 state machine。它不是 OS thread，也不自带 scheduler、I/O runtime、cancellation 或 backpressure。
- **[编译器/标准库实现]** coroutine frame 放在 caller、heap 还是被 elide，取决于 lifetime、optimization 和实现；不能固定回答“协程对象一定一次堆分配”。

### 连续追问

1. `vector` 连续 `push_back` 的 amortized O(1) 如何成立，为什么不需要标准规定固定 2 倍增长？
2. 普通 `vector<T>` 的 contiguous storage 为什么不能推广到 `std::vector<bool>`？proxy reference 对取地址和泛型代码有何影响？
3. `reserve` 后保存 element pointer，执行多少次 `push_back` 才安全？中间 insert 又为何不同？
4. 为什么 `shrink_to_fit` 后 RSS 可能不下降？
5. `std::list` 的标准只保证哪些 sequence/iterator/complexity/失效规则？doubly-linked nodes、每节点 allocation 和 locality 为何必须标成实现特征？
6. unordered lookup 为什么只有 average O(1)，rehash 分别使哪些 handles 失效？
7. comparator 返回 `a <= b` 而不是 strict ordering 会破坏什么前提？
8. pmr container 被移动到比 memory resource 更长的作用域会发生什么？
9. placement new 后为什么不能一律继续使用旧 pointer？`std::launder` 又不能修复哪些问题？
10. `decltype(x)` 与 `decltype((x))` 为什么不同？`decltype(auto)` 返回局部变量时有何风险？
11. 什么情况下 `T&&` 是 forwarding reference？named `T&&` 为什么是 lvalue expression？
12. `[this]` 捕获的 closure 放进异步队列后，如何保证对象 lifetime？
13. concept 相比 SFINAE 改善了什么，又没有自动保证什么？
14. coroutine suspend 后由谁 resume，frame 与 cancellation 的 ownership 应如何设计？

### 常见误区

- 把 `vector` growth 固定说成 2 倍或 1.5 倍，并冒充标准保证
- 把普通 `vector<T>` 的 contiguous storage 结论套到 `std::vector<bool>`，把 proxy reference 当成真实 `bool&`
- 只会背容器 Big-O，不考虑 locality、allocation、hash attack 和 iterator stability
- 认为 `reserve` 改变 size，或认为 `shrink_to_fit` 必须归还 RSS
- 认为 deque/list 的 iterator 永不失效，不按具体 operation 判断
- 把 `std::list` 固定说成 doubly-linked nodes 和每节点一次 allocation，不区分标准契约与主流实现
- 把 ordered map 固定实现为红黑树写进接口契约
- 把 allocator 的 raw storage 与对象 construction/lifetime 混为一谈
- 用 placement new 覆盖活对象却不析构，或把 `std::launder` 当万能 type-punning 修复
- 把 `auto` 当动态类型，混淆 `decltype(x)` 与 `decltype((x))`
- 对任何 `T&&` 都调用 `std::forward<T>`，不判断是否 forwarding reference
- 异步 lambda 按引用捕获局部变量或裸 `this`
- 认为 `constexpr` 一定 compile-time、coroutine 一定轻量且自带 scheduler

### 身份难度

- **实习/校招**：能比较主要容器、解释 vector size/capacity、基础失效规则、`auto`、move 和 lambda capture。
- **初中级 C++ 开发**：能按 operation 判断 iterator invalidation，解释 allocator/lifetime、forwarding、SFINAE 和异常保证对容器策略的影响。
- **高级/资深 C++ 开发**：能基于 workload 选择容器和 memory resource，审查 ranges/coroutine lifetime，并区分标准 complexity contract 与具体实现、cache 和 allocator 表现。

---

## 5. 内存管理与系统交互

### 基础问题与答案要点

#### `new`/`delete` 与 `malloc`/`free`

**两组 API 的语义差异是什么？**

- **[语言标准]** new-expression 先取得 storage，再构造 object，并返回带类型的 pointer；普通失败默认抛 `std::bad_alloc`，`std::nothrow` 形式失败返回 null。
- **[语言标准]** 普通 delete-expression 选择 non-destroying deallocation function 时，先调用 destructor，再调用匹配的 deallocation function；`delete nullptr` 安全且无效果。
- **[语言标准，C++20 起]** 若 deallocation function 查找选中 destroying `operator delete`，delete-expression 不再先单独调用 destructor，而由该 function 负责执行正确析构并释放 storage。实现该接口必须显式处理完整对象生命周期，不能把它当成普通释放回调。
- `malloc` 分配满足 fundamental alignment 要求的 raw storage，返回 `void*`，失败返回 null；它不普遍保证 over-aligned type 的额外对齐，也不调用 constructor。`free` 不调用 destructor。
- C++17 over-aligned type 可能使用 aligned `operator new/delete` overload；custom class-specific allocation function 也可参与。new-expression 不等同于固定调用 libc `malloc`。
- `new T[n]` 必须与 `delete[]` 匹配，`malloc/calloc/realloc` 必须与 `free` 匹配。混用 allocation/deallocation family 是未定义行为。

**`realloc` 为什么不能普遍替代 C++ object move？**

- `realloc` 操作 raw allocation，可能搬移字节并释放旧块；它不了解 non-trivial object 的 constructor、destructor、self pointer 和 invariant。
- 对一般 C++ object 数组直接 `realloc` 会破坏 lifetime 和对象语义。容器需按 element traits 构造/移动到新 storage，再销毁旧 elements。
- trivially copyable/implicit-lifetime 类型的低层 storage 仍要满足对应标准版本的 lifetime 和 API 前提，不能仅凭“看起来是 struct”判断。

#### Alignment、placement construction 与 aliasing

**手写内存池至少要保证什么？**

- 返回地址满足请求 type 的 alignment；块大小、header 和 free-list pointer 不能破坏对齐。
- allocation 只提供 storage，必须在正确时点开始 object lifetime；release 前必须结束 non-trivial object lifetime。
- pool 本身必须比所有从中分配的 objects 活得更久，并定义 thread-safety、cross-thread free 和 shutdown 行为。
- 处理 size class、large allocation、exception rollback、double free、use-after-free、poisoning 和 debug instrumentation。
- 若依赖 `reinterpret_cast` 或 freelist overlay，必须审查 aliasing、active lifetime 和 pointer provenance；“能在当前优化级别运行”不是标准正确性证据。

**strict aliasing 与 character access 如何理解？**

- **[语言标准]** 通过不允许的 glvalue type 访问 object 可能产生未定义行为并让 optimizer 做出看似反直觉的变换。
- `char`、`unsigned char` 和 `std::byte` 可用于检查 object representation，但把任意 bytes 当成已存在的复杂 `T` 仍需满足 lifetime、alignment 和 representation。
- `memcpy`/`bit_cast` 是位复制工具，不自动验证输入表示对目标类型是否有效；trap/invalid representation 和 padding 仍要考虑。

#### 内存池、碎片与替代 allocator

**内部碎片和外部碎片分别是什么？**

- 内部碎片是分配块或 size class 大于请求导致块内浪费；alignment 和 metadata 也会增加开销。
- 外部碎片是空闲总量足够但分散，难以满足连续大块请求；虚拟地址、page、arena 和物理驻留层面要分别观察。
- pool/arena 可通过统一 size/lifetime 减少 general-purpose allocator 开销，但可能增加峰值、延迟归还和跨请求内存滞留。
- 优化前需测 allocation rate、size distribution、lifetime distribution、contention、RSS/PSS、page fault 和 tail latency。

**jemalloc/tcmalloc 适合什么场景？**

- **[OS/allocator]** 它们是特定 allocator implementations，常通过 thread/per-CPU cache、size class 和多 arena 降低 contention，并提供 profiling/tuning 能力。
- 代价可能包括 cache 保留、fragmentation、RSS 与 live bytes 偏离、cross-thread free 行为和运维复杂度。
- 不能只因“高并发”就更换 allocator。应在同一 workload、相同 sampling 和 warm-up 条件下比较 throughput、P99、CPU、RSS、fault 与 release behavior。
- allocator replacement 还要检查 static/dynamic linking、sanitizer interposition、fork、huge page、container memory limit 和第三方库兼容性。

#### `brk`、`mmap`、虚拟内存与 RSS

**大块 `malloc` 一定走 `mmap`，小块一定走 `brk` 吗？**

- 不是 C++ 规范。**[OS/allocator]** 某些 glibc allocator 版本会综合大小、动态阈值、arena、历史请求和 tunable 选择 heap growth 或 anonymous mapping；固定阈值不是跨版本契约。
- 其他 libc 或 allocator 可以完全不同，macOS、Windows 与 Linux 的虚拟内存 API 也不同。
- 即使来自 `mmap`，page 通常按需建立物理驻留；virtual size、committed memory、RSS、PSS、dirty page 和 cgroup charge 不是同一指标。
- `free` 后 RSS 不立即下降，可能因为 arena/cache 保留、page 未满足归还条件、fragmentation 或内核记账时机；不能直接断言 memory leak。

**page fault 和 copy-on-write 如何影响服务？**

- 首次触碰 demand-paged memory 可能产生 minor fault；需要 I/O 或 swap 时可能出现 major fault，延迟性质完全不同。
- `fork` 后 page 通常 copy-on-write；父子任一方写入会产生 private copy。大进程 fork 后的 allocator/GC/写热点可能造成显著 RSS 峰值。
- Transparent Huge Pages、NUMA placement、page cache 和 memory reclaim 都会影响 tail latency，属于 OS 与部署环境问题，不是 C++ object model。

#### 泄漏、越界与释放后使用

**“进程内存一直涨”如何先分类？**

- 仍可达的 retention：ownership graph、无界 cache/queue 或长生命周期 owner 仍持有对象；使用 heap profiler、allocator profile、容量指标和引用链分析定位，LSan 默认不会把仍可达对象作为主要 leak 报告。
- owner 丢失造成的不可达 allocation：使用 LSan 或 Memcheck 等 leak detector 关联 allocation stack；LSan 默认主要报告不可达 allocation，不能据此排除仍可达 retention。
- allocator retention/fragmentation：live bytes 稳定但 reserved/RSS 高，需要 allocator stats 和 size/lifetime 分布。
- non-heap memory：thread stacks、mmap、shared memory、JIT/code、page cache、driver buffer 等。
- workload cache 或 queue 无上限：语义上仍可达，应检查容量指标和 heap/allocator profile，而不是等待 LSan 报 unreachable leak。
- 先建立指标定义和时间线，再决定是 code leak、capacity bug、allocator behavior 还是 OS accounting。

### 连续追问

1. `new T` 的 allocation function、constructor 和异常 rollback 按什么顺序发生？普通 delete 与 C++20 destroying delete 又分别由谁执行析构？
2. 为什么 `malloc(sizeof(T))` 后强转为 `T*` 不足以构造一般 `T`？
3. `delete[]` 与 `delete` 不匹配时，问题为什么不限于“少析构几个元素”？
4. class-specific `operator new` 和 placement new 分别改变哪一层语义？
5. over-aligned type 放入手写 byte buffer 时如何保证地址和 stride 对齐？
6. 内存池把 freed object 的首字节覆盖成 next pointer 时，需要检查哪些 lifetime/aliasing 条件？
7. jemalloc/tcmalloc 降低锁竞争后，为什么 RSS 反而可能更高？
8. glibc 的 `mmap` threshold 为什么不能写成 C++ 固定知识点？如何在目标环境验证？
9. virtual size 很大但 RSS 小，或 live heap 小但 RSS 大，各可能说明什么？
10. `free` 后 RSS 不降时，怎样区分 leak、fragmentation、cache retention 和未触碰映射？
11. 大进程 `fork` 后写入 allocator metadata 为什么可能造成 copy-on-write 峰值？

### 常见误区

- 把 `new/delete` 仅解释成 `malloc/free` 加 constructor/destructor，忽略 overload、alignment、array cookie 和异常 rollback
- 把所有 delete-expression 都概括为“语言先调用 destructor 再释放”，忽略 C++20 destroying `operator delete` 负责析构与释放的选择路径
- 混用 `new/free`、`malloc/delete`、`new[]/delete`
- 用 `realloc` 搬运 non-trivial C++ objects
- placement new 后对对象执行普通 `delete`，或忘记管理 backing storage
- 写内存池只关注 free list，不检查 alignment、lifetime、thread-safety 和 pool lifetime
- 把 `brk`/`mmap` 固定阈值、arena 数量或 size class 当成 C++ standard
- 把 virtual size、heap live bytes、RSS 和 cgroup memory 当成同一个指标
- 看到 RSS 不下降就断言泄漏，或看到 leak detector 无报告就排除无界 cache
- 未经 workload 证据直接切换 jemalloc/tcmalloc

### 身份难度

- **实习/校招**：能区分 object 与 storage、`new/delete` 与 `malloc/free`、数组匹配、基础 alignment 和 leak。
- **初中级 C++ 开发**：能正确使用 placement construction、分析 fragmentation/RSS、实现受限 pool 并用工具定位越界和 UAF。
- **高级/资深 C++ 开发**：能区分 C++ lifetime、allocator policy 与 OS VM，基于 workload 评估替代 allocator、NUMA/page fault/fork 风险和容器内存预算。

---

## 6. 并发、原子操作与内存模型

### 基础问题与答案要点

#### `thread`、mutex 与锁设计

**`std::thread` 的生命周期要注意什么？**

- joinable `std::thread` 在 destructor 时若仍未 `join`/`detach`，会调用 `std::terminate`；owner 必须定义结束协议。
- `detach` 不是自动资源管理。detached task 仍可能访问已销毁对象、丢失错误、拖延进程退出或继续持有资源。
- C++20 `std::jthread` destructor 会请求 stop 并 join，配合 `stop_token` 提供 cooperative cancellation；阻塞 API 仍必须实际响应取消。
- thread function 捕获 reference 时，referent 必须活到 thread 完成；`std::ref` 只改变参数包装，不延长 lifetime。

**mutex 应保护数据还是 invariant？**

- mutex 应保护跨多个字段和操作的 invariant，并明确 lock ownership；只说“这个变量加锁”经常遗漏 check-then-act。
- 使用 `std::lock_guard`、`std::unique_lock`、`std::scoped_lock` 让 unlock 走 RAII；多锁使用统一顺序或 deadlock-avoidance primitive。
- 不要持锁执行未知 callback、长 I/O 或可能 re-enter 的代码；需要时先复制状态、释放锁，再执行外部操作。
- `std::shared_mutex` 读多不等于一定更快；reader/writer 策略、starvation 和开销依赖实现，应 profile。

#### `condition_variable`、future 与 promise

**为什么 condition variable 必须配合 predicate loop？**

- wait 可发生 spurious wakeup；即使是 notify 唤醒，其他线程也可能先修改条件。
- 正确形式是持锁检查 predicate，不满足则 wait；`wait(lock, pred)` 封装了循环。
- 修改 predicate 对应共享状态通常在同一 mutex 保护下完成，再 notify。notify 本身不保存“事件次数”，先通知后等待可能丢失一次性信号设计。
- timeout 应使用 predicate overload 并区分 deadline 与一次 wake；循环使用 relative timeout 可能因多次 wake 延长总等待。

**future/promise 解决什么？**

- promise 设置 value 或 exception，future 获取结果并建立相应 synchronization；一个普通 future 通常只能 `get` 一次，`shared_future` 可多次共享读取结果。
- broken promise 会让 future 获得异常状态，而不是永久静默等待。
- `std::async` 的 launch policy 若未明确，implementation 可选择 async 或 deferred；需要线程/执行语义时必须明确 policy 或使用受控 executor/thread pool。
- future 不自动提供 cancellation、backpressure 或 bounded scheduling；生产服务通常还需 task ownership 与 executor contract。

#### Data race、happens-before 与 publication

**data race 为什么不是“偶尔读到旧值”这么简单？**

- **[语言标准]** 两个 potentially concurrent conflicting actions 访问同一 memory location，至少一个不是 atomic，并且 neither happens before the other 时形成 data race；程序行为未定义。
- compiler 可基于 data-race-free 假设重排、消除或合并访问，因此现象不只由 CPU cache 决定。
- happens-before 由 sequenced-before、synchronizes-with 等关系传递形成；线程真实时间先后或 `sleep` 不建立 C++ memory model 同步。
- mutex unlock 与之后成功 lock、thread start/join、condition variable、atomic release/acquire 等可建立规定关系，但每种 primitive 的边界不同。

**如何安全发布一个对象？**

- producer 完成普通 writes 后，以 release store 发布 pointer/flag；consumer 以读取到该值的 acquire load 接收，可看到 release 之前 sequenced writes。
- 若 consumer 的 acquire 没有读取到对应 release sequence 的值，就不能借此声称对象已发布。
- mutex-protected queue、one-time initialization 和 message passing 通常比手写 atomic publication 更易审查。
- `volatile` 不建立 inter-thread synchronization；它用于特定 observable side effect 场景，不能替代 atomic 或 mutex。

#### Atomic 与 memory order

**六种常见 memory order 如何理解？**

- `memory_order_relaxed` 保证该 atomic object 的操作原子性和 modification order，不建立跨对象的 release/acquire 可见性。
- `memory_order_release` 用于 store/RMW 的发布侧，`memory_order_acquire` 用于 load/RMW 的接收侧；当读取关系满足时建立 synchronizes-with。
- `memory_order_acq_rel` 常用于同时读旧值并发布新状态的 RMW。
- `memory_order_seq_cst` 在 acquire/release 等语义外，为 seq_cst operations 提供单一全序约束；它不自动让非原子冲突访问安全。
- `memory_order_consume` 长期存在实现与使用困难，主流实现常按 acquire 处理；面试不应把理论 dependency ordering 当成可随意依赖的优化。
- memory order 是程序证明的一部分，不是“relaxed 更快”的开关。没有完整 invariant 和 litmus test 时优先更清晰的 lock 或较强 ordering。

**CAS 的 `weak`、`strong` 和 failure order 有什么区别？**

- `compare_exchange_weak` 可 spuriously fail，适合本来就在 loop 中重试；`strong` 不允许这种额外的伪失败，但仍会因值不匹配失败。
- CAS 失败时会把实际值写回 `expected`，因此 retry loop 要重新计算 desired state。
- failure memory order 不能包含 release 语义，也不能强于相应成功 order 的允许范围；接口设计应显式审查。
- CAS loop 在高 contention 下可能大量重试，造成 cache-line bouncing 和 tail latency；lock-free 不等于低成本。

#### ABA、reclamation 与 progress guarantee

**什么是 ABA？**

- CAS 看到值从 A 变 B 又变 A，会误以为状态未变化；pointer 相同不代表指向的 logical node 还是同一代。
- tagged/versioned pointer 可降低 wrap 前 ABA，hazard pointer、epoch-based reclamation、reference counting 等解决 node lifetime/reclamation 的不同部分。
- 只解决 ABA 不代表解决 use-after-free；只延迟 free 也不代表 linearization 正确。
- reclamation scheme 需要处理 stalled thread、thread exit、batch、memory pressure 和 shutdown。

**lock-free、wait-free 和 obstruction-free 有何差异？**

- lock-free 通常保证系统整体持续取得进展，不保证某个线程不饥饿。
- wait-free 要求每个 operation 在有界步骤内完成，保证更强且实现成本更高。
- obstruction-free 只保证线程在独占执行足够久时完成。
- `atomic<T>::is_lock_free()` 可按对象/运行时查询，`is_always_lock_free`（C++17）给出 compile-time 属性；标准不保证所有 atomic type 都由无锁 CPU instruction 实现。
- 算法 lock-free 不等于业务更快。低 contention mutex 可能更省 CPU、更公平、更易维护。

#### False sharing 与 cache coherence

**false sharing 是什么？**

- 不同线程修改逻辑上独立但位于同一 coherence unit 的数据，会导致 cache line 在 cores 间反复转移。
- **[平台/ABI]** cache line 大小、NUMA topology 和 coherence behavior 是硬件/平台属性；不能把 64 bytes 当所有机器的 C++ 保证。
- C++17 提供 `std::hardware_destructive_interference_size` 等实现提供的常量，但其可用性和准确性仍需目标标准库/平台验证。
- padding 可能减少 false sharing，也会增大 footprint、降低 cache density；必须用 hardware counters 和 workload 验证。

### 连续追问

1. 为什么 `std::thread` destructor 不自动 detach 或 join？`jthread` 改善了什么但没有解决什么？
2. 两个字段分别用两个 mutex 保护，如何保证跨字段 invariant？
3. condition variable 已收到 notify，为什么 predicate 仍可能为 false？
4. 未指定 policy 的 `std::async` 为什么不能当成固定 thread-pool API？
5. “producer 先写，consumer 后读”在 wall clock 上成立，为什么仍可能没有 happens-before？
6. release store 与 acquire load 要满足什么读取关系，才能发布普通 object fields？
7. relaxed counter 安全在哪里，又不能用于证明哪些其他数据可见？
8. seq_cst atomic flag 为什么仍不能修复其他 non-atomic data race？
9. weak CAS loop 如何处理 expected 被更新和 spurious failure？
10. Treiber stack 只用 CAS 后，node reclamation 和 ABA 为什么仍是独立难题？
11. 一个 atomic 在当前平台 `is_lock_free()` 为 true，为什么算法仍未必 wait-free？
12. padding counter 到 64 bytes 为什么可能在另一平台无效或适得其反？

### 常见误区

- 随意 `detach` 线程，把失去 join/error/lifetime 管理当成异步化
- 用 mutex 保护单字段，却让业务 invariant 跨临界区破裂
- condition variable 使用 `if` 而非 predicate loop，或把 notify 当持久事件队列
- 认为 `sleep`、日志顺序或 CPU 执行先后能建立 happens-before
- 用 `volatile` 代替 atomic，或认为 atomic 会自动保护相邻普通字段
- 把 relaxed 理解为“CPU 可随意撕裂”，或把 seq_cst 理解为“全程序自动线程安全”
- CAS loop 不处理 expected 更新、failure order 和高竞争重试
- 只修 ABA tag，不设计安全 memory reclamation
- 把 lock-free 等同于 wait-free、无饥饿、无锁指令或一定更快
- 固定假设 cache line 64 bytes，不测 false sharing 和 footprint trade-off

### 身份难度

- **实习/校招**：能正确使用 thread join、mutex RAII、condition variable predicate、future/promise 和基础 atomic。
- **初中级 C++ 开发**：能用 happens-before 解释 publication，选择 memory order，识别 data race、deadlock、false sharing 和 CAS retry。
- **高级/资深 C++ 开发**：能给出 linearization 与 progress argument，设计 reclamation，验证 lock-free property，并用 TSan、litmus test 和 hardware counters 交叉证明。

---

## 7. 网络编程与高性能服务

### 基础问题与答案要点

#### Socket 生命周期、partial I/O 与 RAII

**一次 `read`/`write` 是否对应一条完整消息？**

- stream socket 提供 byte stream，不保留应用消息边界；一次 read 可少于请求、合并多条消息或返回 EOF，一次 write 也可能只写部分数据。
- 应用协议必须定义 frame，例如固定 header + length、delimiter 或自描述编码，并处理粘连、拆分、malformed length 和 size limit。
- non-blocking I/O 的 `EAGAIN`/`EWOULDBLOCK` 表示当前不能继续，不是连接失败；`EINTR`、half-close、RST 和 timeout 要按 operation 语义处理。
- file descriptor 应由 move-only RAII owner 管理，明确 close、shutdown、dup 和 ownership transfer；整数 fd 被复用后，旧异步事件可能错误指向新资源。

#### `epoll` 与 Reactor

**`epoll` 提供的是 readiness 还是 completion？**

- **[OS/allocator]** Linux `epoll` 报告 file descriptor 的 readiness/状态变化，应用收到事件后仍要执行实际 read/write；ready 不保证一次 I/O 完成整个业务请求。
- level-triggered 模式在条件仍满足时可重复报告；edge-triggered 模式只报告边沿，通常要 non-blocking 并循环 drain 到 `EAGAIN`，否则可能丢失继续处理机会。
- `EPOLLONESHOT` 事件触发后需要显式 rearm，适合避免同一 fd 被多个 workers 同时处理，但状态机更复杂。
- 必须处理 error/hangup，即使事件 mask 未显式请求；close 与 fd reuse、跨线程 remove、queued event 的竞态需要 generation/ownership 设计。

**Reactor 的核心职责是什么？**

- Reactor 将 readiness demultiplexing、connection state machine、timer、accept/read/write 和 callback dispatch 组织起来。
- one-loop-per-thread、shared acceptor、worker handoff 各有 cache locality、负载均衡和跨线程队列权衡。
- handler 必须有 bounded work，避免 event loop 被 CPU task 或 blocking call 阻塞；重任务应转到受控 executor，并把结果安全投回 owner loop。
- 高性能不是只看 event API。connection ownership、buffer lifecycle、backpressure、timer complexity、syscall batching 和 error path 更常决定稳定性。

#### `io_uring`

**`io_uring` 与 `epoll` 的模型差异是什么？**

- **[OS/allocator]** `io_uring` 通过 shared submission/completion rings 提交 operations 并接收 completion，可减少部分 syscall 和 context-switch 开销；它更接近 completion-oriented interface。
- 并非所有 operation、kernel version、filesystem 和 device 都有相同异步能力；某些路径可能转入内核 worker 或有不同限制。
- registered buffers/files、fixed resources、multishot、SQPOLL 等可降低开销，但增加 pinning、resource accounting、deployment privilege 和 lifecycle 复杂度。
- completion 到达时 user object、buffer 和 cancellation state 必须仍有效；“请求已超时”不等于内核不再写 buffer。
- 是否优于 epoll 取决于 operation mix、batch、payload、kernel、security policy 和现有框架。必须 benchmark，不应做 API 崇拜。

#### 零拷贝

**“零拷贝”是否真的一次 copy 都没有？**

- 通常指减少 user/kernel 间 CPU copy、context switch 或数据路径，不代表 NIC、DMA、page cache 和协议栈内部完全没有数据移动。
- **[OS/allocator]** Linux `sendfile` 可在 kernel-managed file/socket 路径间传输；`splice` 在支持的 descriptors/pipes 间移动引用；`MSG_ZEROCOPY` 等能力有各自 completion 和 buffer-reuse contract。
- `mmap` 避免显式 read copy，但访问仍会 page fault，并引入 mapping lifetime、SIGBUS、dirty/writeback 和 address-space 管理。
- TLS、compression、application framing 或需要修改 payload 时，纯 file-to-socket 路径可能不适用；现代 TLS/kernel offload 支持也需按目标环境验证。
- 零拷贝减少某类 CPU 成本，却可能增加 page pinning、completion bookkeeping、small-message overhead 和 tail latency。

#### Backpressure、buffer 与连接状态

**高性能服务为什么必须有 backpressure？**

- producer 持续快于 network/client 时，无界 output queue 会把吞吐问题转化为 memory exhaustion 和长尾。
- 每连接和全局都应有 queue/byte budget、high/low watermark、暂停读取、拒绝、降级或断开策略。
- buffer owner 必须活到异步 operation 确认完成；scatter/gather I/O 只复制 descriptor，不自动拥有应用 buffers。
- timeout 要区分 connect、TLS handshake、request header/body、upstream、write 和 idle；一个总 timeout 很难定位和治理。
- slowloris、oversized frame、connection churn 和 accept overload 都需要 protocol limit 与资源预算。

#### 多线程网络模型与性能验证

**多线程一定提高网络吞吐吗？**

- 多 loops 可利用多核，但 shared connection map、allocator、timer wheel、accept queue 和 metrics counter 可能形成 contention。
- `SO_REUSEPORT`、accept handoff、RSS/RPS、CPU affinity 和 NUMA locality 属于 Linux/部署优化，效果依赖 kernel/NIC/topology。
- cross-thread fd migration 会损失 locality 并增加 synchronization；固定 owner loop 常更简单，但热点连接可能负载不均。
- 应分别测 requests/s、P50/P99/P999、CPU cycles、syscalls、context switches、run queue、packet loss/retransmit、queue depth 和 memory。

### 连续追问

1. TCP 一次 `recv` 只拿到半个 header 时，状态机如何保留进度并防止恶意 length？
2. non-blocking `send` 只写出部分 buffer 后，下一次 writable event 如何继续？
3. epoll edge-triggered 为什么通常要 drain 到 `EAGAIN`？如果 handler 中途交给 worker，谁负责 rearm？
4. fd close 后很快被复用，旧 queued event 如何避免误操作新 connection？
5. Reactor loop 中调用 blocking DNS、disk I/O 或用户 callback 会造成什么？
6. io_uring completion 返回前，request object 与 buffer 能否释放？timeout/cancel race 如何收敛为一次完成？
7. registered buffer 为什么可能降低开销，也可能增加 pinned-memory 风险？
8. `sendfile` 在启用 application compression 或 user-space TLS 时为什么可能失去适用性？
9. “零拷贝”方案应测哪些 CPU、copy、fault、pinning 和 latency 指标？
10. output queue 达到 high watermark 后，继续读 request 会产生什么反馈循环？
11. one-loop-per-core 与 worker pool 混合时，connection state 由谁拥有，结果如何回到 owner？
12. QPS 上升但 P999、retransmit 和 RSS 恶化，能否称优化成功？

### 常见误区

- 把 TCP 当 message queue，假设一次 read/write 就是完整请求
- 把 `EAGAIN` 当连接错误，或不处理 partial write 和 half-close
- 认为 epoll 是异步完成 API，事件到来后无需真正 read/write
- edge-triggered 只读一次，不 drain 到 `EAGAIN`
- 只调用 close，不处理 fd reuse 与 queued event 的 generation/lifetime
- 把 io_uring 说成所有 kernel/operation 上都纯异步且必然更快
- request timeout 后立即释放仍可能被 completion 使用的 buffer
- 把 zero-copy 字面理解为硬件和内核中无任何 copy
- 没有 per-connection/global backpressure，只依赖机器内存吸收慢客户端
- 只看峰值 QPS，不看 tail latency、CPU、retransmit、queue 和内存

### 身份难度

- **实习/校招**：能解释 byte stream、partial I/O、non-blocking、epoll readiness、Reactor 和基础 frame。
- **初中级 C++ 开发**：能实现 connection state machine、ET drain/rearm、buffer ownership、timeout 和 backpressure。
- **高级/资深 C++ 开发**：能比较 epoll/io_uring/zero-copy 的内核边界，设计跨线程 ownership 与一次完成语义，并基于全链路指标优化而非只追 QPS。

---

## 8. 工程排查与性能分析

### 基础问题与答案要点

#### Core dump 与现场保护

**进程崩溃后第一步是什么？**

- 先保存原始 evidence：core、exact executable、shared libraries、build ID、debug symbols、启动参数、环境、container image、kernel/runtime 日志和崩溃时间线。
- **[OS/allocator]** core 是否生成受 shell/resource limit、core pattern、service manager、container policy、dumpability、磁盘与安全设置影响；只执行 `ulimit -c unlimited` 未必覆盖 systemd/container 环境。
- 不要先在生产二进制上重编译覆盖。source 相同但 compiler flags、LTO、dependency、strip 和 layout 不同，backtrace 可能失真。
- core 可能含 secret、request body 和用户数据，采集、传输和留存必须遵守权限与合规。

**常见 signal 能直接说明根因吗？**

- `SIGSEGV` 表示 invalid memory access 类结果，可能来自 null/UAF/out-of-bounds/stack overflow/corrupted return address，不等于“空指针”。
- `SIGABRT` 常来自显式 abort、assert、allocator 检测或 `std::terminate`；需要检查 stderr 和 terminating exception。
- `SIGBUS`、`SIGILL`、`SIGFPE` 等也要结合 fault address、instruction 和平台原因分析。
- signal 是症状入口。最终结论需要 stack、register、memory、sanitizer 或复现证据。

#### GDB 调试

**分析 core 的基本证据链是什么？**

```bash
gdb /path/to/exact-binary /path/to/core
(gdb) info threads
(gdb) thread apply all bt full
(gdb) frame 0
(gdb) info registers
(gdb) x/16gx ADDRESS
(gdb) disassemble /s
(gdb) disassemble /r START_ADDRESS, END_ADDRESS
(gdb) info line *ADDRESS
```

- 先确认 executable、core、shared libraries 和 symbols 匹配，再看 crashing thread 与所有线程。
- optimized build 中变量可能 optimized out、frame 被 inline、tail-call 或重排；`disassemble /s` 用于混合 source mapping，必要时结合 `/r`、明确地址范围和 `info line *ADDRESS` 对照真实指令字节与源码映射，不能把 source line 当成唯一执行顺序。
- corrupted stack 的第一帧未必是 root cause。UAF/overflow 往往早于 crash 很久，应结合 allocator/sanitizer、watchpoint 或 record/replay。
- 多线程 hang 需看所有 threads、lock owners、futex waits 和 application progress，不要只看当前 thread。

#### Valgrind 与 Sanitizers

**ASan、TSan、UBSan 分别擅长什么？**

- AddressSanitizer 通过 instrumentation 检测许多 heap/stack/global out-of-bounds、use-after-free 等 memory errors；它不能证明所有 lifetime/logic error 都不存在。
- ThreadSanitizer 检测 data race 和部分 synchronization misuse；开销较大，且通常不与 ASan 组合在同一个 build 中使用。
- UndefinedBehaviorSanitizer 检测配置启用的多类 UB，如部分 integer、alignment、vptr 和 shift 问题；recover/trap 方式影响运行行为。
- LeakSanitizer 常与 ASan 集成检测 unreachable allocations；语义上仍 reachable 的无界 cache 不会被当成 leak。
- Sanitizer 必须覆盖真实代码路径，并保留符号；custom allocator、assembly、prebuilt library 和 unsupported platform 会形成 blind spot。

**Valgrind 何时仍有价值？**

- Valgrind/Memcheck 可在不重新编译全部代码的部分场景检查 invalid access、uninitialized use 和 leak，适合支持的平台与可接受的高开销离线复现。
- 它通过不同机制工作，速度通常明显慢于编译期 sanitizers，SIMD/JIT/syscall 支持和平台可用性需确认。
- 工具不是互斥的：CI sanitizer、离线 Valgrind、allocator diagnostics 和 core analysis可覆盖不同盲区。

**Sanitizer 报告如何读？**

- 先读 error class 和 fault access，再看 allocation/free/creation stacks，而不是只看最终 crash stack。
- 第一条报告通常更接近根因；继续运行后的二次 corruption 可能制造噪声。
- symbolizer、frame pointer/debug info、suppressions 和 third-party library version 会影响可读性。
- 不应为“清空报告”无条件 suppress；每条 suppression 要有 owner、理由和到期条件。

#### `perf` 与 CPU 性能

**CPU 高时如何从证据开始？**

```bash
perf list
perf stat -e cycles,instructions,branches,branch-misses,cache-references,cache-misses -p PID -- sleep 30
perf record -F 199 -g -p PID -- sleep 30
perf report
```

- `perf stat` 使用显式且有限时长的 event set 观察 cycles、instructions、IPC、branch miss 和 cache miss；event 是否可用及其含义仍取决于 CPU、kernel 和 permission。
- TLB events 的名称依赖平台，先用 `perf list` 查看目标机器支持的事件，再通过 `-e` 显式选择；不能声称默认 `perf stat` 一定提供统一名称的 TLB 数据。
- `perf record/report` 用 sampling 定位 hot path；频率和时长需平衡 overhead 与代表性。
- call graph 质量依赖 frame pointer、DWARF unwind、inlining、JIT symbol 和 stripped binary；缺失 stack 不等于函数没有消耗。
- CPU flame graph 表示 sampled on-CPU stack 聚合，不直接表示 wall-clock 或 blocked time；I/O/lock 问题需要 off-CPU、scheduler、futex 或 tracing 证据。

**热点函数优化前要问什么？**

- 它是否真在目标 workload 的 critical path，采样占比是否稳定？
- 成本来自 instruction、branch misprediction、cache miss、allocation、lock contention 还是 syscall？
- 优化后 throughput、tail latency、CPU、memory 和 correctness 是否一起复验？
- compiler 是否已 inline/vectorize，改动是否引入 code bloat、false sharing 或更差 locality？

#### 线上 crash、hang 与性能回归流程

**如何把排查变成可复用流程？**

- 明确现象和指标定义：crash rate、hang、CPU、RSS、latency、error rate，建立首次出现时间和变更关联。
- 获取最小但完整证据：版本/build ID、traffic、thread/core/profile、allocator/kernel/container 指标。
- 提出可证伪假设，使用 sanitizer、targeted logging、fault injection、replay 或二分验证。
- 修复后补 regression test、runtime guard、metric 和 rollout/rollback 条件，避免只修现场。
- 性能回归使用相同硬件、频率策略、数据集、warm-up、并发和统计方法；一次 benchmark 数字不构成结论。

#### 编译器诊断与可观测性构建

**Release build 如何兼顾性能和可排查性？**

- 保留独立 debug symbols、build ID 和符号归档；binary 可 strip，但必须能按版本准确取回 symbols。
- 评估保留 frame pointer 的成本与可观测性收益；不同 architecture/unwinder 下结论不同。
- crash handler 只能执行 async-signal-safe 的最小操作，复杂 symbolization 和 allocation 放到外部 collector 或事后分析。
- structured logging、request ID 和 metrics 不应在 hot path 无界分配；观测代码也要有 backpressure 和 privacy policy。

### 连续追问

1. 服务设置了 core limit 仍没有 core，应继续检查 core pattern、service manager、container 和磁盘哪些条件？
2. 为什么必须保存 exact executable、shared libraries 与 build ID，而不是只保存源码 commit？
3. core 中顶层是 `memcpy`，如何判断根因是 source/destination lifetime、length corruption 还是更早的 heap overwrite？
4. optimized build 的变量 `optimized out` 时，可用哪些 register、assembly、DWARF 和复现证据继续分析？
5. ASan、TSan 为什么通常分 build 运行，各自会漏掉什么？
6. LeakSanitizer 无报告但 RSS 持续上涨，下一步检查哪些 allocator/non-heap/queue 证据？
7. Valgrind 很慢时，什么情况下仍值得使用？
8. perf 显示高 cycles 但 IPC 很低，可能从 memory stall、branch、lock 和 scheduling 哪些方向验证？
9. CPU flame graph 看不到大量请求延迟，为什么要补 off-CPU 或 scheduler 证据？
10. 修复 crash 后，怎样设计 regression test 才能证明捕获的是 root cause 而非偶然不崩？
11. signal handler 中直接调用复杂 logger、`malloc` 和 symbolizer 为什么危险？
12. 一次本地 benchmark 提升 20%，为什么仍不能直接发布为线上性能结论？

### 常见误区

- 只保存 core 不保存 exact binary、libraries、symbols 和 build ID
- 看到 `SIGSEGV` 就结论为空指针，看到 `SIGABRT` 就结论 assert
- 只看 crashing thread 的第一帧，不检查其他线程、allocation/free stack 和更早 corruption
- 把 optimized-out 变量或不完整 backtrace 当作无法继续分析
- 认为 sanitizer 跑过一次就证明没有 UB/data race/leak
- 为让 CI 变绿大范围 suppress sanitizer 报告
- 把 Valgrind、ASan、TSan、UBSan 当成完全等价工具
- 只看 flame graph 宽度，不区分 on-CPU、off-CPU、sampling bias 和 unwind 缺失
- 只优化最宽函数，不看 cache、lock、syscall 和 tail latency
- crash handler 中执行非 async-signal-safe 的复杂逻辑
- 用不同硬件、负载和 warm-up 的 benchmark 数字直接比较

### 身份难度

- **实习/校招**：能读取基础 backtrace，知道 core、debug symbol、ASan/Valgrind 和 perf 的用途。
- **初中级 C++ 开发**：能建立 crash evidence chain，选择 ASan/TSan/UBSan，分析多线程 hang、heap corruption 和 CPU profile。
- **高级/资深 C++ 开发**：能建设 build-ID/symbol pipeline、低风险线上 profiling、allocator/kernel 联合证据和可复现实验，并把修复转成 guard、test 与 rollout 标准。

---

## 9. 高频追问链与身份难度

### 基础问题与答案要点

#### 追问链 1：指针、引用与对象布局

**如何从“指针和引用有什么区别”逐步追到资深深度？**

1. 指针可空/改指向，引用必须绑定且不改绑。
2. 指针大小为什么不能固定回答 4/8 字节？
3. “引用不占内存”是 language abstraction 还是 ABI layout 结论？
4. reference member 如何影响 `sizeof`、copy assignment 和 standard-layout？
5. non-owning pointer/reference/view 的 lifetime 由谁保证？
6. 跨 shared-library 边界时 pointer representation、calling convention 和 allocator ownership 如何约定？

答案应从 **[语言标准]** 语义逐步进入 **[平台/ABI]** 验证，不能一开始就背某台机器的汇编，也不能在谈 object layout 时继续用“引用只是别名”回避存储问题。

#### 追问链 2：ODR、header 与二进制边界

**如何从“头文件能否定义变量”继续追问？**

1. declaration 与 definition 如何区分？
2. include guard 为什么不解决跨 translation unit ODR？
3. template、inline function 和 C++17 inline variable 为什么可放头文件？
4. 不同宏让 inline body 不一致会怎样？
5. namespace-scope `const`、`extern`、internal/external linkage 如何组合？
6. `extern "C"` 解决 name linkage 后，哪些 ABI/ownership/exception 风险仍存在？

高级候选人应主动提到 ill-formed, no diagnostic required、symbol visibility、LTO 和 stable C boundary，而不是把所有 linker error 都归为“重复 include”。

#### 追问链 3：对象 lifetime、placement new 与 allocator

**如何从“malloc 后能否强转成对象指针”继续追问？**

1. storage 与 object lifetime 有何区别？
2. trivial/implicit-lifetime 与 non-trivial type 的初始化边界是什么？
3. placement new 负责什么，不负责什么？
4. 覆盖旧对象前何时调用 destructor？
5. 旧 pointer 何时 transparent replacement，何时考虑 `std::launder`？
6. container allocator、pmr resource 和 backing arena 的 lifetime 如何组合？
7. custom pool 如何证明 alignment、aliasing、reclamation 和 thread-safety？

回答必须把 **[语言标准]** lifetime 与 **[OS/allocator]** 取得 page/heap storage 分开。

#### 追问链 4：多态、虚析构与 ABI

**如何从“虚函数怎么实现”避免背诵式回答？**

1. 先说明 standard 只规定 dynamic dispatch 语义。
2. 再以指定 ABI 的 vptr/vtable 作为常见实现模型。
3. constructor/destructor 中 virtual dispatch 为什么受限？
4. multiple/virtual inheritance 如何产生 pointer adjustment？
5. base deletion 为什么需要 virtual destructor 或禁止删除契约？
6. devirtualization 在什么证明下发生？
7. 为什么 public C++ polymorphic ABI 容易受 compiler/library/build flags 影响？

只画一张“对象头 8 字节 vptr”的图而不限定 ABI，最多算实现印象，不算完整答案。

#### 追问链 5：RAII、智能指针与异常安全

**如何从“shared_ptr 是否线程安全”继续追问？**

1. control block 与 pointee 分别是什么？
2. 不同 handles 和同一个 handle object 的并发规则有何不同？
3. 为什么 atomic reference count 不保护 `T`？
4. cycle、weak edge 和 `lock()` 如何设计？
5. `make_shared` 的 allocation/lifetime trade-off 是什么？
6. custom deleter 和 allocator context 如何跨模块存活？
7. constructor、assignment 和 batch update 分别需要 basic 还是 strong guarantee？

候选人若只说“shared_ptr 内部用了原子所以线程安全”，应继续给出两个线程同时执行 `pointee->mutate()` 的反例。

#### 追问链 6：容器、复杂度与失效

**如何从“vector 和 list 怎么选”继续追问？**

1. contiguous locality 与 node stability 的核心差异是什么？
2. vector amortized O(1) 是否要求固定 growth factor？
3. reserve、insert、erase 和 reallocation 分别使哪些 handles 失效？
4. list O(1) insertion 是否包含寻找位置和 allocation 成本？
5. unordered_map average/worst complexity 与 rehash 有何关系？
6. pmr/arena 如何改变 allocation 成本但不改变容器语义？
7. profile 显示 cache miss、allocation 或 RSS 时如何验证选型？

高水平回答会同时谈 contract、constant factor、locality、allocator 和 workload，不会只背 Big-O 表格。

#### 追问链 7：memory order、ABA 与 progress

**如何从“atomic 比 mutex 快吗”继续追问？**

1. data race 与 atomicity 分别解决什么？
2. relaxed counter 可以保证什么？
3. release/acquire 如何发布普通数据？
4. seq_cst 提供何种额外全序，又不能修复什么？
5. CAS loop 的 linearization point、failure order 和 contention 在哪里？
6. ABA 与 memory reclamation 为什么是两个问题？
7. lock-free、wait-free、fairness 和实际 latency 如何区分？
8. TSan、litmus test、benchmark 和 hardware counter 分别提供什么证据？

如果没有明确 invariant 和 happens-before graph，直接把所有 operation 改 relaxed 不应被视为优化能力。

#### 追问链 8：高性能 I/O 与排查

**如何从“epoll 为什么快”追到线上工程？**

1. readiness 与 completion 有何区别？
2. LT/ET、non-blocking、partial I/O 和 drain 的关系是什么？
3. Reactor 中 connection/buffer/timer 由谁拥有？
4. io_uring 在什么 operation/kernel 下可能获益，何时退化？
5. zero-copy 减少哪一类 copy，又新增什么 lifecycle/completion 成本？
6. backpressure 如何限制每连接和全局内存？
7. P99 恶化时如何结合 core/GDB、Sanitizer、perf、off-CPU 和 allocator stats？
8. 优化如何通过相同 workload 和 rollout guard 证明？

资深候选人应把 API 机制、ownership、资源预算和 evidence chain 串起来，而不是列出 epoll、io_uring、sendfile 名词。

### 连续追问

1. 候选人回答“64 位机器指针 8 字节”后，如何用 function pointer、target ABI 和 capability architecture 检查边界意识？
2. 候选人说“引用不占内存”后，如何用 reference member 与 calling convention 继续追问而不混淆抽象语义？
3. 候选人说“inline 防止重复定义”后，如何追问 token-equivalent definition、宏和 inline variable？
4. 候选人画出 vtable 后，如何追问 standard 是否规定、multiple inheritance adjustment 和 constructor dispatch？
5. 候选人说“Rule of Five”后，如何判断他是否真正理解 Rule of Zero 和 exception guarantee？
6. 候选人说“shared_ptr 原子计数所以线程安全”后，如何构造 pointee data race？
7. 候选人背出 vector 2 倍扩容后，如何追问 amortized proof 与 implementation freedom？
8. 候选人说“placement new 不分配内存”后，如何追问旧 lifetime、alignment、destruction 和 `launder`？
9. 候选人把 `mmap` threshold 写死后，如何让他区分 language、libc allocator 与 kernel？
10. 候选人说“atomic 无锁所以快”后，如何追问 runtime lock-free、wait-free、ABA 和 contention？
11. 候选人说“epoll 异步 I/O”后，如何区分 readiness、completion 与 actual read/write？
12. 候选人说“零拷贝没有 copy”后，如何追问 DMA、page cache、TLS 和 buffer completion？
13. 候选人拿到 core 只看当前栈后，如何引导构建 binary/symbol/thread/allocation evidence chain？

### 常见误区

- 追问只增加冷门名词，不沿同一 invariant、lifetime 或 evidence chain 深挖
- 用特定 x86-64、Itanium ABI、libstdc++ 或 glibc 行为代替所有 C++ 实现
- 只考候选人背标准条款编号，不考能否写出安全 API 和验证方法
- 把“知道 vtable/control block/vector growth 的常见结构”误判为“知道标准保证”
- 校招题直接要求 lock-free reclamation、io_uring kernel path 和 perf counter，身份难度失配
- 资深候选人只问语法 trivia，不考 ownership、ABI、concurrency proof 和线上排查
- 对答案中的限定条件扣分，反而奖励没有适用范围的绝对化结论
- 把没考察到的方向当作不会，或用一道偏题覆盖整个能力维度

### 身份难度

- **实习/校招**
  - 核心：指针/引用/`const`、storage duration、构造析构、virtual、RAII、常用容器、mutex/condition variable、基础 socket 与 GDB。
  - 合格边界：标准语义基本正确，能识别 dangling、double free、iterator invalidation 和 data race；实现细节在提示后愿意加限定。
  - 不应强求：背 ABI layout、allocator threshold、lock-free reclamation 或特定 kernel 内部路径。
- **1-3 年 C++ 后端**
  - 核心：ODR/linkage、Rule of Zero/Five、exception guarantee、smart pointer ownership、STL complexity/失效、memory order 基础、Reactor/backpressure、Sanitizer/perf。
  - 合格边界：能独立修复 lifetime/concurrency bug，解释工具证据，并按目标 standard/library/platform 限定结论。
- **高级 C++ 后端**
  - 核心：object lifetime、ABI、多继承、allocator/pmr、atomic publication、ABA/reclamation、io_uring/zero-copy trade-off、线上 crash 与性能证据链。
  - 合格边界：能设计低耦合 ownership 和 cancellation，给出 failure/progress/compatibility argument，并通过实验拒绝伪优化。
- **资深/基础设施方向**
  - 核心：跨编译器/动态库 ABI、memory resource architecture、lock-free correctness、kernel I/O 能力、NUMA/cache/allocator、可观测性和渐进发布。
  - 合格边界：不仅解释机制，还能明确 contract、适用范围、退化路径、资源预算、验证指标和长期维护成本。
  - 加分项：主动将未知实现细节转化为可执行验证，如 target-specific layout dump、symbol inspection、sanitizer matrix、litmus test、allocator profile 和 kernel capability probe。
