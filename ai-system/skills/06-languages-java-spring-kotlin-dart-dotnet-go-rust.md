### Java

**What it is:** Java is a statically typed, object-oriented, compiled language that runs
on the JVM (Java Virtual Machine — a runtime that executes Java bytecode, abstracting
away the operating system). Java has been one of the most widely used enterprise
languages for 30 years. Its verbosity is deliberate — explicit, readable code that large
teams can maintain over decades.

**When to use it:** Enterprise systems, teams with established Java expertise, JVM
ecosystem integrations (Kafka, Hadoop, Spark), Android development (though Kotlin is
now preferred), and anywhere long-term stability and the massive Java ecosystem matter.

#### Basics

**Compiled and statically typed:** Java code is compiled before running. `javac Main.java`
produces `Main.class` (bytecode). `java Main` runs it. The compiler catches type errors
before the code runs. Every variable has a declared type: `String name = "Alice"`,
`int age = 30`, `boolean isActive = true`. The compiler rejects code that passes the
wrong type to a function.

**Classes and objects:** Everything in Java lives inside a class. A class is a blueprint;
an object is an instance of that blueprint. `class User { String name; int age; }` —
this class has two fields. `User user = new User()` creates an instance. `user.name =
"Alice"` sets a field. A constructor is a special method that runs when the object is
created: `User(String name) { this.name = name; }`.

**Access modifiers:** `public` — accessible everywhere. `private` — accessible only
within the class. `protected` — accessible in the class and subclasses. (package-private)
— accessible in the same package. Always make fields `private` and provide getters/setters
(or use records). This is encapsulation — hiding internal state.

**Methods:** `public String greet() { return "Hello " + this.name; }`. Return type before
the name. `void` if nothing is returned. `static` methods belong to the class, not an
instance — call with `ClassName.method()`. Non-static methods belong to instances.

**`null` and NullPointerException:** `null` means "no value." Accessing any method on a
null reference throws `NullPointerException` — the most common Java runtime error.
Always check before accessing: `if (user != null) { user.getName() }` or use
`Optional<T>`. Explain `null` every time it appears.

**Collections:** `List<String> names = new ArrayList<>()` — ordered, duplicates allowed.
`Set<String> ids = new HashSet<>()` — unordered, no duplicates. `Map<String, User>
users = new HashMap<>()` — key-value pairs. Common operations: `add`, `remove`, `get`,
`contains`, `size`, `isEmpty`. Use `List.of(...)`, `Set.of(...)`, `Map.of(...)` for
immutable collections.

#### Mid-level

**Interfaces and inheritance:** `interface Printable { void print(); }`. A class that
`implements Printable` must provide the `print()` method. `class Dog extends Animal`
inherits all `Animal` members. Java has single inheritance (one parent class) but
multiple interface implementation. Prefer composition over inheritance — favor `has-a`
over `is-a` relationships.

**Generics:** `List<String>` vs `List` — generics enforce type safety in collections.
`public <T> T first(List<T> list)` is a generic method. `? extends Number` is a bounded
wildcard. Generics are erased at runtime (type erasure) — `List<String>` and `List<Integer>`
are the same class at runtime. This has implications for reflection and casting.

**Java 8+ functional features:** `List<User> active = users.stream().filter(u ->
u.isActive()).collect(Collectors.toList())`. Streams process collections declaratively.
`Optional<User> found = users.stream().filter(...).findFirst()` — wrap nullable results
in `Optional` to force callers to handle the empty case. Lambdas: `(a, b) -> a + b`.
Method references: `User::getName`. These are essential modern Java.

**Exceptions:** Checked exceptions (`throws IOException` in the method signature) must
be caught or declared. Unchecked exceptions (`RuntimeException` subclasses) need not be.
Use unchecked exceptions for programming errors; checked exceptions for recoverable
conditions. Never swallow exceptions with an empty catch block.

**Build tools — Maven and Gradle:** Maven uses `pom.xml` — XML configuration, convention
over configuration. Gradle uses `build.gradle` — a Groovy or Kotlin DSL, more flexible
and faster (incremental builds). Both manage dependencies from Maven Central. Use Gradle
for new projects; understand Maven for existing ones.

#### Senior

**JVM performance tuning:** The JVM JIT (Just-In-Time compiler) compiles hot bytecode
to native machine code at runtime — programs get faster the longer they run. The garbage
collector has multiple algorithms: G1GC (default, low latency), ZGC (sub-millisecond
pauses, for latency-sensitive services), Shenandoah (similar to ZGC). Tune heap size
with `-Xms` (initial) and `-Xmx` (maximum). Profile with async-profiler or JFR (JDK
Flight Recorder) — never guess at bottlenecks.

**GraalVM Native Image:** Compiles Java to a native binary ahead-of-time. Near-instant
startup (milliseconds instead of seconds), low memory footprint, suitable for serverless
and CLI tools. The trade-off: reflection, dynamic proxies, and classpath scanning
require explicit configuration. Spring Boot and Quarkus both support native images with
varying levels of friction.

---

### Spring Boot

**What it is:** Spring Boot is the standard framework for building Java backends. It
provides auto-configuration (detects libraries on the classpath and configures them
automatically), an embedded web server (no separate Tomcat installation), production
health checks, and integrations with every major database, message broker, and cloud
platform.

**When to use it:** Java REST APIs, microservices, batch processing, and any Java
backend where production-readiness and ecosystem maturity are priorities.

#### Basics

**Starting a project:** `start.spring.io` generates a project with chosen dependencies.
The main class: `@SpringBootApplication public class Application { public static void
main(String[] args) { SpringApplication.run(Application.class, args); } }`. `@SpringBoot
Application` enables component scanning, auto-configuration, and property loading.

**REST controllers:** `@RestController @RequestMapping("/api/users")` marks a class as
an HTTP controller. `@GetMapping("/{id}")` maps GET requests. `@PostMapping` maps POST.
`@RequestBody User user` deserializes the JSON body. `@PathVariable Long id` extracts
the URL parameter. Return the response object — Spring Boot serializes it to JSON
automatically using Jackson.

**`application.yml`:** Configuration file. `spring.datasource.url: jdbc:postgresql://
localhost/mydb`. `server.port: 8080`. `spring.jpa.show-sql: true` (logs generated SQL
— always enable in development). Properties can be environment-specific with profiles:
`application-dev.yml`, `application-prod.yml`. Activate a profile with `SPRING_PROFILES_
ACTIVE=prod`.

**Spring Data JPA:** Automatically implements repository interfaces. `interface UserRepository
extends JpaRepository<User, Long>` gives you `findById`, `findAll`, `save`, `delete`
for free. Custom queries by method name: `findByEmail(String email)` generates
`SELECT * FROM users WHERE email = ?`. `@Query` for complex queries.

**Validation:** `@NotNull`, `@Email`, `@Size(min=8)` on DTO fields. `@Valid` on the
controller method parameter triggers validation. Spring Boot returns 400 with details
on validation failure automatically.

#### Mid-level

**Dependency injection and beans:** `@Component`, `@Service`, `@Repository` mark classes
as Spring beans — Spring creates and manages them. `@Autowired` (or constructor injection)
injects them. Always use constructor injection — it makes dependencies explicit and
enables easy testing. `@Bean` methods in `@Configuration` classes create beans manually
for third-party classes.

**`@Transactional`:** Wraps a method in a database transaction — all operations succeed
or all roll back. Critical for multi-step database writes. Propagation: `REQUIRED` (join
existing transaction or create new — default), `REQUIRES_NEW` (always new transaction,
suspending the current), `SUPPORTS` (join if exists, no transaction if not). Critical
known bug: `@Transactional` on private methods does nothing — Spring proxies cannot
intercept private methods.

**Spring Security:** Configure with a `SecurityFilterChain` bean. `http.authorizeRequests(
).requestMatchers("/public").permitAll().anyRequest().authenticated()`. JWT integration:
add a `JwtAuthenticationFilter` before the `UsernamePasswordAuthenticationFilter`.
Method-level security: `@PreAuthorize("hasRole('ADMIN')")` on service methods.

**Actuator:** Adds production endpoints: `/actuator/health` (is the service healthy?),
`/actuator/metrics` (Prometheus-compatible metrics), `/actuator/info` (app version and
git commit). Always include Actuator. Secure the sensitive endpoints — never expose
`/actuator/env` or `/actuator/heapdump` publicly.

**Caching:** `@EnableCaching` activates caching. `@Cacheable("users")` on a service
method caches its result. `@CacheEvict("users")` invalidates the cache. Back with Redis
for distributed caching. Always define a TTL (time-to-live) to prevent stale data
accumulating indefinitely.

#### Senior

**N+1 problem with Hibernate:** Loading a list of entities then accessing a lazy-loaded
relationship for each one issues N+1 queries. `List<Order> orders = orderRepo.findAll()`
is 1 query. `orders.forEach(o -> o.getItems().size())` is N additional queries — one per
order. Fix with `JOIN FETCH` in JPQL: `SELECT o FROM Order o JOIN FETCH o.items`,
`@EntityGraph(attributePaths = "items")`, or Hibernate batch fetching
(`@BatchSize(size = 25)`). Always log SQL in development and check for N+1 on every
data-heavy feature.

**Spring Boot performance at scale:** Configure the embedded Tomcat thread pool
(`server.tomcat.threads.max`) based on expected concurrency. Use WebFlux (reactive stack)
for I/O-bound services that need to handle very high concurrency without the thread-per-
request overhead. Profile startup time with `spring.main.lazy-initialization=true` (lazy
beans start faster but first request is slower). Use Spring Native for serverless.

---

### Kotlin

**What it is:** Kotlin is a modern, statically typed language that runs on the JVM.
It is 100% interoperable with Java — Kotlin can call Java code and Java can call Kotlin.
Kotlin is Google's officially recommended language for Android development and an
increasingly popular alternative to Java for backend development.

**When to use it:** All new Android development, Spring Boot backends where the team
wants a more expressive language than Java, and any JVM project where null safety and
conciseness matter.

#### Basics

**`val` and `var`:** `val name = "Alice"` — immutable (like `const` in JS, `final` in
Java). Cannot be reassigned. `var count = 0; count = 1` — mutable. Default to `val`;
use `var` only when mutation is genuinely needed.

**Null safety:** The type system distinguishes nullable (`String?`) from non-nullable
(`String`). `val name: String = null` is a compile error. `val name: String? = null` is
allowed. Accessing a nullable value requires explicit handling: `name?.length` (safe call
— returns null if name is null), `name!!.length` (non-null assertion — crashes if null,
avoid in production), `name ?: "default"` (Elvis operator — use default if null).

**Data classes:** `data class User(val id: Long, val name: String, val email: String)`.
The compiler automatically generates `equals()`, `hashCode()`, `toString()`, and `copy()`.
`val updated = user.copy(name = "Bob")` creates a new User with only name changed.
Replaces 50+ lines of Java boilerplate with one line.

**String templates:** `"Hello $name"` or `"You have ${messages.size} messages"`. Always
prefer over concatenation.

**When expression:** `val result = when (status) { "active" -> "User is active"; "suspended"
-> "User is suspended"; else -> "Unknown status" }`. More powerful than Java's `switch`
— works as an expression, supports smart casts, and the compiler warns if not all cases
are covered for sealed classes.

**Extension functions:** Add functions to existing classes without modifying them.
`fun String.isPalindrome(): Boolean = this == this.reversed()`. Call as `"racecar".
isPalindrome()`. Extension functions are resolved at compile time — they do not modify
the class, they are syntactic sugar for a static function call.

#### Mid-level

**Lambdas and higher-order functions:** `list.filter { it > 0 }.map { it * 2 }` — lambdas
use `{}` syntax. `it` is the implicit single parameter name. Higher-order functions take
functions as parameters or return them. `inline` functions eliminate lambda allocation
overhead — use on performance-critical higher-order functions.

**Sealed classes and when:** `sealed class Result<T> { data class Success<T>(val data: T)
: Result<T>(); data class Error(val message: String) : Result<Nothing>() }`. Sealed
classes restrict which classes can extend them — all subclasses must be in the same
file. Combined with `when`, the compiler enforces that all cases are handled. Use for
representing bounded sets of states (API result, UI state, navigation events).

**Scope functions:** `let`, `run`, `apply`, `also`, `with`. These are higher-order
functions that execute a block in the context of an object. `user?.let { sendEmail(it) }`
— run only if non-null. `User().apply { name = "Alice"; age = 30 }` — configure an
object. `user.also { logger.info("Creating $it") }` — side effect without changing the
value. Overusing scope functions makes code hard to read — use them purposefully.

**Coroutines:** Kotlin's solution for async programming. `suspend fun fetchUser(id: Long):
User` — a function that can pause and resume without blocking a thread. `launch { ... }`
starts a coroutine that does not return a value. `async { ... }.await()` starts a
coroutine that returns a value. Run in a `CoroutineScope` — all coroutines in a scope
are cancelled when the scope is cancelled.

**`Flow`:** Kotlin's reactive stream. `flow { emit(1); emit(2); emit(3) }` creates a
cold stream (only runs when collected). `flowOf(1, 2, 3)`. Operators: `map`, `filter`,
`catch`, `onEach`, `collect`. In Android: `StateFlow` for observable state, `SharedFlow`
for events. In Spring Boot: reactive endpoints return `Flow<T>`.

#### Senior

**Structured concurrency:** The defining feature of Kotlin coroutines. Every coroutine
belongs to a scope. When the scope is cancelled (e.g., the HTTP request is cancelled,
the Android Activity is destroyed), all child coroutines are cancelled automatically.
This prevents coroutine leaks — the equivalent of thread leaks in Java. In Android, use
`viewModelScope` (cancelled when ViewModel is cleared) and `lifecycleScope` (cancelled
when the lifecycle ends). In backend, use `withContext(Dispatchers.IO)` for blocking I/O.

**Kotlin Multiplatform (KMP):** Share business logic between iOS, Android, backend, and
web. Kotlin code compiles to JVM bytecode, JavaScript, and native machine code (for iOS
and desktop). The architecture: shared `commonMain` code contains domain logic, platform-
specific `androidMain`, `iosMain`, `jvmMain` contain platform implementations. This is
the future of mobile cross-platform development for teams invested in Kotlin.

---

### Dart / Flutter

**What it is:** Dart is a statically typed, garbage-collected language by Google. Flutter
is a UI framework that uses Dart to build apps from a single codebase targeting iOS,
Android, Web, and Desktop. Flutter renders its own widgets using Skia (or Impeller on
newer versions) — it does not use native platform controls.

**When to use it:** When you need to target both iOS and Android from one codebase, the
UI must be pixel-perfect and identical across platforms, and the team can invest in
learning Dart and Flutter.

#### Basics

**Everything is a widget:** The fundamental concept. Text, padding, a button, a color
background, the entire screen — all widgets. You build UIs by nesting small widgets to
create larger ones. `Scaffold(appBar: AppBar(title: Text('Home')), body: Center(child:
Text('Hello')))` is a complete screen.

**`StatelessWidget`:** A widget whose appearance depends entirely on its inputs
(constructor parameters) and never changes. `class Greeting extends StatelessWidget {
final String name; const Greeting({required this.name}); @override Widget build(
BuildContext context) { return Text('Hello $name'); } }`.

**`StatefulWidget`:** A widget that has internal state that can change. Two classes:
the widget (immutable, stores config) and the state (mutable, holds state and `build`).
`setState(() { count++ })` triggers a rebuild. Use for locally owned state (a toggle,
a form field value, a loading indicator).

**Layout widgets:** `Column` stacks children vertically. `Row` stacks horizontally.
`Stack` layers children on top of each other. `Expanded` makes a child fill available
space. `Padding(padding: EdgeInsets.all(16), child: ...)` adds padding. `Container` is
a box with optional decoration, padding, margin, and size.

**Navigation:** `Navigator.push(context, MaterialPageRoute(builder: (_) => NewScreen()))`
pushes a new screen. `Navigator.pop(context)` goes back. For production apps use
`go_router` — it provides URL-based navigation, deep linking, and a cleaner API.

**`pubspec.yaml`:** The project manifest. Add dependencies under `dependencies:`. Run
`flutter pub get` to install. `flutter pub upgrade` updates to the latest compatible
versions.

#### Mid-level

**State management options:** `setState` is fine for local state. For shared state:
**Provider** is simple, widely used, stable. **Riverpod** is the evolution of Provider —
type-safe, testable, no `BuildContext` required, supports code generation. **BLoC**
(`flutter_bloc`) is more structured — Events in, States out, fully testable. Choose
based on complexity: `setState` → Provider → Riverpod → BLoC as complexity grows.

**BLoC pattern:** `Bloc<Event, State>` receives events, processes them, emits states.
`BlocBuilder<UserBloc, UserState>(builder: (context, state) { if (state is Loading) ...
})` rebuilds the widget when state changes. Separate the BLoC (business logic) from
the widget (UI) — the BLoC knows nothing about Flutter widgets, making it fully
unit-testable.

**Async in Flutter:** `FutureBuilder<User>(future: fetchUser(), builder: (context, snapshot)
{ if (snapshot.connectionState == ConnectionState.waiting) return CircularProgressIndicator();
if (snapshot.hasError) return Text('Error'); return UserCard(snapshot.data!) })` — handle
loading, error, and success states. `StreamBuilder` does the same for streams.

**`const` constructors:** Mark constructors and their instantiation as `const` when all
values are compile-time constants. Flutter can skip rebuilding `const` widgets entirely —
they are identical across rebuilds. `const Text('Hello')` is much faster than `Text(
'Hello')` in a list of items. Use `const` everywhere possible.

**Platform channels:** Call native iOS/Android code from Dart using `MethodChannel`. The
channel serializes arguments to a basic value type (string, number, map, list), sends
across the Dart/native boundary, and the native side deserializes and handles it. For
high-frequency calls, use FFI (dart:ffi) — direct function calls with no serialization.

#### Senior

**Flutter rendering pipeline:** The framework layer (widget tree) computes layout and
paint instructions. The engine (Impeller/Skia) executes GPU draw calls. A frame is
produced 60 or 120 times per second. A jank frame (dropped frame) means some work took
longer than 16ms (60fps) or 8ms (120fps). Profile with Flutter DevTools — the Flame
chart shows where time is spent. Causes of jank: heavy synchronous computation in the
build method, excessive widget rebuilds, slow images, or large asset decompression.

**Isolates:** Dart is single-threaded. CPU-intensive work blocks the UI thread. Use
`Isolate.spawn` or `compute()` (simpler) to move work to a separate isolate that runs
in parallel. Isolates do not share memory — communicate via messages (SendPort/ReceivePort).

**Widget testing vs integration testing:** Widget tests use `flutter test` — they test
a single widget in isolation without a device. Integration tests (using `integration_test`
package) run on a real device or emulator and test the full app. Unit test BLoC/Riverpod
providers without Flutter at all — these are the fastest and most reliable tests.

---

### .NET / C\#

**What it is:** .NET is Microsoft's cross-platform development platform. C# is its primary
language — statically typed, compiled, with a syntax similar to Java but with many more
modern features. ASP.NET Core is the web framework within .NET for REST APIs and web apps.
.NET runs on Windows, macOS, and Linux.

**When to use it:** Enterprise environments with Microsoft infrastructure, Windows-hosted
services, game development (Unity), teams with existing .NET expertise, and any backend
where Microsoft's long-term support commitment and comprehensive documentation matter.

#### Basics

**Types and variables:** `string name = "Alice"` or `var name = "Alice"` (type inferred).
`int age = 30`. `bool isActive = true`. `var` is not dynamic — the type is fixed at
compile time. C# has value types (structs, int, bool — live on the stack, copied on
assignment) and reference types (classes, strings — live on the heap, copied by
reference). This distinction matters for performance and equality semantics.

**Classes and records:** `class User { public string Name { get; set; } public int Age
{ get; init; } }`. Properties replace public fields — they have `get` and `set` accessors
and can have logic. `record User(string Name, int Age)` is an immutable data type with
auto-generated `Equals`, `GetHashCode`, and `ToString`. Prefer records for DTOs and
value objects.

**Nullable reference types:** Enable in the project file: `<Nullable>enable</Nullable>`.
`string name` cannot be null. `string? name` can be null. The compiler warns on
potential null dereferences. This eliminates NullReferenceException at compile time —
always enable it.

**`async`/`await`:** `async Task<User> GetUserAsync(int id) { var user = await db.Users.
FindAsync(id); return user; }`. Methods returning `Task` or `Task<T>` are async.
`await` pauses until the Task completes without blocking the thread. The `Async` suffix
on method names is a convention — always follow it. Use `ValueTask<T>` instead of
`Task<T>` for hot paths where the result is often available synchronously.

**LINQ (Language Integrated Query):** `var activeUsers = users.Where(u => u.IsActive).
OrderBy(u => u.Name).Select(u => new { u.Id, u.Name }).ToList()`. LINQ queries
collections declaratively. Works on in-memory collections (`IEnumerable`) and databases
(EF Core translates to SQL). `ToList()`, `FirstOrDefault()`, `Any()`, `Count()` are
terminal operations that execute the query.

**Dependency injection (built-in):** Register services in `Program.cs`: `builder.Services.
AddScoped<IUserRepository, UserRepository>()`. Three lifetimes: `AddSingleton` (one
instance for the app lifetime), `AddScoped` (one per HTTP request), `AddTransient` (new
instance per injection). Inject via constructor: `public UsersController(IUserRepository
repo) { _repo = repo; }`.

#### Mid-level

**Entity Framework Core:** The standard ORM for .NET. Define entities (classes with `[Key]`
and navigation properties). Create a `DbContext` with `DbSet<User> Users`. Query with
LINQ: `await context.Users.Where(u => u.IsActive).ToListAsync()`. EF Core generates SQL.
Code-first migrations: `dotnet ef migrations add AddUserTable`, `dotnet ef database update`.
Always inspect the generated migration SQL before applying to production.

**Middleware pipeline:** ASP.NET Core processes requests through a pipeline of middleware.
`app.UseAuthentication()` then `app.UseAuthorization()` — order matters. Custom middleware:
`app.Use(async (context, next) => { /* before */ await next(); /* after */ })`. The
pipeline is bidirectional — middleware runs code before and after the rest of the pipeline.

**Options pattern for configuration:** `services.Configure<DatabaseOptions>(configuration.
GetSection("Database"))`. Inject `IOptions<DatabaseOptions>` into services. Strongly
typed configuration validated at startup. Never access `IConfiguration` directly in
services — always use the Options pattern for testability.

**Minimal APIs vs Controllers:** Minimal APIs (`app.MapGet("/users", async (IUserService
svc) => await svc.GetAllAsync())`) are concise and fast — less abstraction overhead.
Controllers are more structured and explicit. Use Minimal APIs for simple services, use
controllers for complex APIs with many endpoints and cross-cutting concerns.

**`IDisposable` and `using`:** Resources (file handles, database connections, HTTP
clients) must be explicitly released. `using (var connection = new SqlConnection(cs))
{ ... }` ensures `Dispose()` is called even if an exception occurs. `await using` for
async disposal. Never instantiate `HttpClient` per request — use `IHttpClientFactory`
which manages lifetime and connection pooling correctly.

#### Senior

**Span<T> and Memory<T>:** Zero-allocation slicing of arrays and strings. `ReadOnlySpan<char>
slice = "Hello World".AsSpan(0, 5)` — no string allocation, just a view into the
original. Critical for high-throughput services where GC pressure is a bottleneck.
`Span<T>` is stack-only; `Memory<T>` can be on the heap and used in async code.

**Source generators:** Compile-time code generation using Roslyn. EF Core uses them for
query compilation. System.Text.Json uses them for AOT-compatible serialization. Write
your own to eliminate runtime reflection — important for AOT builds and startup performance.

**SignalR:** Real-time bidirectional communication (WebSockets with fallbacks). `hub.
Clients.All.SendAsync("ReceiveMessage", message)` pushes to all connected clients.
Scale out with a Redis backplane when running multiple server instances — without it,
messages only reach clients connected to the same server.

---

### Go

**What it is:** Go (also called Golang) is a statically typed, compiled language made by
Google. It is designed for simplicity — a small language spec, fast compilation, and
built-in concurrency primitives. Go produces a single self-contained binary with no
runtime dependencies. Docker, Kubernetes, Terraform, and many cloud tools are written in Go.

**When to use it:** Backend services where performance and concurrency matter, CLI tools,
DevOps tooling, network services, and any project where simplicity and operational
efficiency (small binaries, fast startup, low memory) are priorities.

#### Basics

**Variables and types:** `var name string = "Alice"` or short declaration: `name :=
"Alice"`. Types: `string`, `int`, `int64`, `float64`, `bool`, `byte`. Constants: `const
MaxRetries = 3`. Go is strongly typed — no implicit conversions. `int` is platform-
dependent size (32 or 64 bit); use `int64` for explicit size.

**Functions:** `func add(a int, b int) int { return a + b }`. Multiple return values
(Go's key feature): `func divide(a, b float64) (float64, error) { if b == 0 { return
0, errors.New("division by zero") }; return a / b, nil }`. Callers receive both values:
`result, err := divide(10, 2)`.

**Error handling:** Go has no exceptions. Functions return errors as values. Always
check: `result, err := someFunc(); if err != nil { return fmt.Errorf("context: %w", err)
}`. `%w` wraps the error — callers can unwrap with `errors.Is` or `errors.As`. Never
ignore errors by assigning to `_` unless you have a deliberate reason.

**Structs:** `type User struct { ID int64; Name string; Email string }`. Create: `user
:= User{ID: 1, Name: "Alice", Email: "alice@example.com"}`. Access: `user.Name`. Methods
on structs: `func (u User) Greet() string { return "Hello " + u.Name }`. Pointer
receiver for mutation: `func (u *User) SetName(n string) { u.Name = n }`.

**Packages and imports:** Every Go file starts with `package main` (for executables) or
`package mypackage` (for libraries). Import: `import ("fmt"; "net/http")`. The package
name is the last element of the import path. Unused imports cause a compile error —
Go enforces this strictly.

**Slices and maps:** `names := []string{"Alice", "Bob"}`. Append: `names = append(names,
"Charlie")`. `users := map[string]User{"alice": aliceUser}`. Access: `users["alice"]`.
Check existence: `user, ok := users["alice"]; if !ok { /* key not found */ }`. Always
check the second return value when accessing a map.

#### Mid-level

**Interfaces:** `type Storer interface { Save(user User) error; FindByID(id int64) (User, error) }`.
Any type that implements the methods satisfies the interface — no explicit `implements`.
This is structural typing (duck typing with type safety). Interfaces are typically small
(one or two methods). Define interfaces where they are used (in the consuming package),
not where they are implemented.

**Goroutines and channels:** `go doWork()` starts a goroutine — a lightweight concurrent
function. Goroutines are multiplexed onto OS threads by the Go scheduler. Channels
pass data between goroutines: `ch := make(chan int)`. Send: `ch <- 42`. Receive:
`value := <-ch`. Buffered channels: `make(chan int, 10)` does not block until the buffer
is full. Select statement: `select { case v := <-ch1: ... case v := <-ch2: ... default:
... }` — waits for whichever channel is ready.

**`sync` package:** `sync.Mutex` for mutual exclusion — `mu.Lock()`/`mu.Unlock()` (always
defer unlock: `defer mu.Unlock()`). `sync.RWMutex` for read-write locking — multiple
concurrent readers, exclusive writer. `sync.WaitGroup` waits for a group of goroutines:
`wg.Add(1)` before `go func() { defer wg.Done(); ... }()`, then `wg.Wait()`.

**Context:** `context.Context` carries deadlines, cancellation signals, and request-
scoped values. Pass as the first parameter to every function that does I/O: `func
GetUser(ctx context.Context, id int64) (User, error)`. Check cancellation in long
loops: `select { case <-ctx.Done(): return ctx.Err() default: /* continue */ }`.
Create with deadline: `ctx, cancel := context.WithTimeout(parentCtx, 5*time.Second);
defer cancel()`.

**Testing:** `_test.go` files are test files. `func TestAdd(t *testing.T) { result :=
add(2, 3); if result != 5 { t.Errorf("expected 5, got %d", result) } }`. `go test ./...`
runs all tests. Table-driven tests: `tests := []struct{ a, b, want int }{{2, 3, 5}, {0,
0, 0}}; for _, tt := range tests { got := add(tt.a, tt.b); if got != tt.want { t.Error(...) } }`.

#### Senior

**Goroutine lifecycle management:** A goroutine that runs forever is a goroutine leak —
memory accumulates. Every goroutine needs a clear termination condition. Use context
cancellation for graceful shutdown. `errgroup.Group` from `golang.org/x/sync/errgroup`
manages a group of goroutines where any error cancels the rest — the correct pattern
for fan-out work.

**`pprof` profiling:** `import _ "net/http/pprof"` adds profiling endpoints. `go tool
pprof http://localhost:6060/debug/pprof/heap` analyzes heap. `go tool pprof .../profile`
analyzes CPU. The flame graph shows which functions use the most time/memory. Run with
`-race` flag in tests and staging — the race detector finds data races with low overhead.

**Memory optimization:** Avoid allocations in hot paths. `sync.Pool` reuses objects:
`var pool = sync.Pool{New: func() any { return &Buffer{} }}; buf := pool.Get().(*Buffer);
defer pool.Put(buf)`. Use `strings.Builder` for string concatenation. Preallocate slices
when the size is known: `make([]User, 0, expectedLen)` allocates capacity without
setting length.

**Go modules and versioning:** `go.mod` declares the module name and dependencies.
`go get package@v1.2.3` adds a specific version. `go mod tidy` removes unused
dependencies. Module proxies (`GOPROXY=https://proxy.golang.org`) cache modules for
reliable builds. Vendor with `go mod vendor` for builds that must not access the network.

---

### Rust

**What it is:** Rust is a systems programming language focused on memory safety without
a garbage collector. It prevents memory bugs (use-after-free, null pointer dereferences,
data races, buffer overflows) at compile time. Performance is comparable to C and C++.

**When to use it:** Performance-critical systems, CLI tools where binary size and startup
time matter, WebAssembly, game engines, operating system components, and anywhere memory
safety is critical without GC overhead.

#### Basics

**Ownership:** The foundational concept. Every value in Rust has an owner — one variable.
When the owner goes out of scope, the value is dropped (memory freed) automatically.
`let s = String::from("hello")` — `s` owns the string. `let s2 = s` — ownership moves
to `s2`, `s` is now invalid. `println!("{}", s)` after moving causes a compile error.
This eliminates use-after-free entirely.

**Borrowing and references:** To use a value without taking ownership, borrow it with a
reference. `let s = String::from("hello"); let len = calculate_length(&s)` — pass a
reference (`&s`). The function borrows `s` but does not own it. Rules: any number of
immutable references (`&T`) OR exactly one mutable reference (`&mut T`) at a time — never
both simultaneously. This prevents data races at compile time.

**Data types:** `i32`, `i64`, `u32`, `u64`, `f32`, `f64`, `bool`, `char`. Strings:
`String` (heap-allocated, owned), `&str` (reference to string data). Tuples: `(1, "hello",
true)`. Arrays: `[1, 2, 3; 3]` (fixed size). Vectors: `Vec<i32>` (dynamic size).

**Structs and enums:** `struct User { name: String, email: String }`. Enums can hold
data: `enum Result<T, E> { Ok(T), Err(E) }` — Rust's built-in result type. `enum
Option<T> { Some(T), None }` — Rust's null-safe type. There is no `null` in Rust.

**Pattern matching:** `match result { Ok(value) => println!("{}", value), Err(e) =>
eprintln!("Error: {}", e) }`. The compiler verifies all cases are handled — no
silently ignored cases. Match on structs, enums, tuples, ranges, guards. `if let Ok(v)
= result { ... }` for single-case matching.

**`?` operator:** `fn read_file(path: &str) -> Result<String, io::Error> { let content
= fs::read_to_string(path)?; Ok(content) }`. The `?` returns early with the error if
the result is `Err`, or unwraps the `Ok` value. It is the idiomatic way to propagate
errors without `match` on every call.

#### Mid-level

**Traits:** Rust's interfaces. `trait Describable { fn describe(&self) -> String; }`.
Implement for a type: `impl Describable for User { fn describe(&self) -> String { ... } }`.
Standard traits: `Debug` (format with `{:?}`), `Display` (format with `{}`), `Clone`,
`Copy`, `Iterator`, `From`/`Into` (type conversions), `Serialize`/`Deserialize` (serde).
Derive common traits: `#[derive(Debug, Clone, PartialEq)]`.

**Lifetimes:** When a reference is returned from a function, Rust needs to know how long
it lives. `fn first<'a>(s: &'a str) -> &'a str` — the returned reference lives as long
as the input. Lifetime annotations are usually inferred (lifetime elision rules). You
only write them explicitly when the compiler cannot infer. Lifetime errors mean "this
reference might not be valid" — they prevent dangling pointers.

**`thiserror` and `anyhow`:** For library errors, use `thiserror`: `#[derive(Error)] enum
AppError { #[error("user not found: {0}")] NotFound(u64), #[error("database error")]
Database(#[from] sqlx::Error) }`. For application-level errors where you just want to
propagate and display, use `anyhow::Result<T>` — add context with `.context("while
fetching user")`.

**Closures and iterators:** Rust's iterators are lazy and zero-cost. `users.iter().filter(
|u| u.is_active).map(|u| &u.name).collect::<Vec<_>>()`. Closures capture their
environment. `move |x| x + offset` captures `offset` by value (moves it into the
closure). Iterator combinators compile to tight loops — no overhead versus a manual for
loop.

**Cargo and crates:** `Cargo.toml` is the project manifest. `cargo build`, `cargo test`,
`cargo run`. `cargo add serde --features derive` adds a dependency. `cargo clippy` runs
the linter — treat all warnings as errors in CI: `RUSTFLAGS="-D warnings"`. `cargo fmt`
formats code. `cargo audit` scans for known vulnerabilities.

#### Senior

**Async Rust with Tokio:** `tokio` is the standard async runtime. `#[tokio::main] async
fn main() { ... }`. `async fn fetch_user(id: u64) -> Result<User> { ... }`. `tokio::join!
(fetch_user(1), fetch_user(2))` runs concurrently. `tokio::spawn(async { ... })` creates
an independent task. The `Future` trait is the async abstraction — a future does nothing
until polled. The runtime polls futures to completion.

**`Send` and `Sync`:** Trait bounds for concurrency. `Send` means a type can be moved to
another thread. `Sync` means a reference can be shared between threads. These bounds are
automatically derived for most types. A type with a `Rc<T>` (non-atomic reference count)
is not `Send`. Understanding these traits explains the compile errors you get when trying
to share data between async tasks.

**Zero-cost abstractions:** Rust's generics are monomorphized — the compiler generates
specialized code for each type, with no runtime overhead. Trait objects (`dyn Trait`) use
dynamic dispatch (like virtual functions) and are the alternative when monomorphization
is not desired. Profile with `perf` or `cargo flamegraph` before deciding which to use.

---

