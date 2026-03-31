## Project architecture selection

**What architecture is and why it matters more than any single line of code:**
Architecture is the set of decisions that are hardest to reverse. Changing a variable
name takes five seconds. Changing from a monolith to microservices takes six months and
breaks everything in the process. Architecture decisions compound over time — a good
one makes every future feature easier; a bad one makes every future feature harder.
The single most important architectural principle is this: match the architecture to the
actual complexity of the problem, not the complexity you imagine you might need someday.

**How to use this section:** When starting a project or evaluating an existing one,
describe it to me — the team size, the expected scale, the business domain, whether
the system is read-heavy or write-heavy, whether different parts need to scale
independently, and how quickly it is expected to grow. I will recommend the appropriate
architecture, explain exactly why, and warn you about the failure modes of that choice.

**The decision framework I use:**

Before recommending an architecture, I ask these questions:
1. How many engineers will work on this? (1-3, 4-10, 10-50, 50+)
2. What is the expected scale at launch vs in 2 years? (hundreds of users? millions?)
3. Is the domain well understood or still being discovered?
4. How often will different parts of the system change independently?
5. Does the team have experience operating distributed systems?
6. What is the cost of downtime? (blog post vs payment processor)
7. Is there a hard deadline?

The answers determine the architecture. Below is every architecture style, what it is,
when it is the right choice, when it is the wrong choice, and what it costs to migrate
away from it.

---

### Backend / System architectures

#### Monolithic Architecture

**What it is:** A single deployable unit containing the entire application — all the
business logic, all the data access code, all the HTTP handlers — in one codebase and
one process. Everything runs together and talks to one database.

**Real-world mental model:** Think of a Swiss Army knife. Every tool is in one place,
immediately accessible, no coordination overhead. The problem appears when the knife
gets too large to hold.

**When this is the right architecture:**
- Team of 1-8 engineers
- New product with unclear or rapidly changing requirements
- Expected scale of thousands to low hundreds of thousands of users
- Startup or MVP that needs to ship fast and iterate even faster
- Domain is not yet well understood — you are still learning what the boundaries are

**When experienced engineers choose it over microservices:** Most products will never
outgrow a well-built monolith. Monoliths eliminate distributed systems problems entirely
— no network latency between components, no partial failure, no distributed transactions.
Shopify, Stack Overflow, Basecamp, and GitHub ran as monoliths for years at enormous
scale. Do not split into services because it feels more professional.

**When to move away from it:**
- Independent teams need to deploy different parts without coordinating
- Different components have dramatically different scaling requirements (e.g., image
  processing needs 100x the compute of everything else)
- Deployments become so slow and risky that teams stop deploying frequently

**Migration cost:** High. Moving from a monolith to services requires identifying
boundaries, splitting data, building inter-service communication, and handling
distributed transactions. Plan six months minimum for a serious system.

---

#### Modular Monolith

**What it is:** A single deployable unit structured internally as independent modules
with strict boundaries between them. Each module owns its code and data. They communicate
through defined interfaces, not by calling each other's functions directly.

**Real-world mental model:** An office building. One building (one deployment), but each
floor (module) is its own department with its own rules, its own data, and a reception
desk (public interface) that other floors must go through.

**When this is the right architecture:**
- Team of 5-25 engineers
- Business domain is understood well enough to draw real boundaries
- You need the organizational benefits of microservices (clear ownership, independent
  development) without the operational burden
- You are not yet confident you have the right boundaries — the modular monolith lets
  you refine them before splitting

**The senior engineer's insight:** This is the architecture most teams should use but
almost nobody does, because it does not sound impressive. It gives you 80% of the
benefits of microservices at 20% of the complexity. If the modules have genuinely clean
boundaries, extracting one into its own service later is a day of work, not a month.

**What you must enforce:** Zero direct database access across module boundaries. Each
module has one schema/set of tables that only it can write to. Other modules ask through
the public interface or receive events. If two modules are querying the same table, the
boundary is wrong.

---

#### Microservices Architecture

**What it is:** The application is split into multiple small, independently deployable
services. Each service owns one business capability and its own database. Services
communicate over the network — typically via HTTP/REST, gRPC, or a message bus.

**Real-world mental model:** A city of independent shops. Each shop specializes in one
thing, sets its own hours, and can be renovated without closing the others. The
complexity is in the coordination — a customer who needs things from five shops has to
visit all five.

**When this is the right architecture:**
- 20+ engineers across multiple teams, each team owning a service end-to-end
- Different parts of the system genuinely need to scale independently at 10x-100x
  different rates
- Different services need different technology stacks (the payment service needs strict
  ACID transactions; the recommendation service needs Python and ML libraries)
- The business domain is well understood and stable enough to draw durable boundaries
- The team has experience running distributed systems — Kubernetes, service meshes,
  distributed tracing, circuit breakers

**What experienced engineers know that beginners do not:**
Microservices are not a solution to complexity — they move accidental complexity
(bad code in a monolith) to essential complexity (distributed systems problems). Every
microservice adds: network latency, partial failure, distributed transaction risk,
the need for distributed tracing, a deployment pipeline, a container, a service account,
a health check endpoint, and an ops runbook. You pay this tax for every service, forever.
Most teams that migrate to microservices prematurely spend the next two years fighting
the distributed systems problems they created.

**The only valid reason:** Independent deployability by autonomous teams. If teams are
stepping on each other deploying a monolith, microservices solve that. All other
justifications are usually premature.

---

#### Layered (N-Tier) Architecture

**What it is:** The application is divided into horizontal layers, each with a specific
responsibility. Classic three-layer: Presentation (HTTP handlers, controllers), Business
Logic (services, use cases), Data Access (repositories, database queries). Each layer
only talks to the layer directly below it.

**Real-world mental model:** A restaurant. The waiter (presentation) takes your order
and brings food but never touches the kitchen equipment. The chef (business logic) cooks
but does not interact with customers. The pantry (data access) stores ingredients but
does not cook.

**When this is the right architecture:**
- Any application where you want clear separation of concerns
- Default starting point for most backend applications
- Works inside a monolith, a modular monolith, or a microservice

**The senior engineer's warning:** The classic layering fails when the data access layer
leaks database concepts upward (passing `IQueryable` or `DbContext` to the service
layer), or when the service layer accumulates thousands of lines because the layers are
too coarse. Use it as a starting structure, then refine with Clean Architecture when it
grows.

---

#### Clean Architecture

**What it is:** Concentric rings of concern where dependencies can only point inward.
The outermost ring is infrastructure (databases, HTTP, frameworks). The next ring is
interface adapters (controllers, presenters). The next is application use cases. The
innermost ring is the domain — pure business logic with no dependencies on anything
external.

**Real-world mental model:** An onion. Peel off the outer layers and the core is
unchanged. You can replace the database layer without touching the business logic.
You can add a new API protocol without rewriting the use cases.

**When this is the right architecture:**
- Business logic is complex and must be testable in isolation from infrastructure
- Long-lived systems where frameworks, databases, or protocols are likely to change
- Teams that need to test business rules fast, without spinning up a database
- Domain-Driven Design projects with rich domain models

**What the dependency rule actually means in practice:** Your `User` domain entity
knows nothing about PostgreSQL, nothing about HTTP, nothing about Next.js. It is a
plain class or struct that could run in a console app, a web app, or a CLI. The
PostgreSQL adapter implements the `UserRepository` interface that the domain defines —
the domain does not know Postgres exists. This is the most important structural idea
in modern backend design. Apply it to every non-trivial project.

---

#### Hexagonal Architecture (Ports and Adapters)

**What it is:** Functionally identical to Clean Architecture in principle but described
differently. The application has a core (business logic). The core defines interfaces
called "ports" — what it needs from the outside world. External systems (database,
HTTP server, email provider, message queue) implement those interfaces as "adapters."
The core is completely ignorant of which adapters are connected.

**Real-world mental model:** A phone and its charging ports. The phone defines the port
standard. Any charger that fits the standard works — USB-C from any manufacturer. The
phone does not care which charger it is as long as it delivers power through the port.

**When to use it:** Same as Clean Architecture. The distinction is mostly conceptual.
Use whichever vocabulary the team is already familiar with.

**The practical benefit that beginners miss:** Testing. Because the core only knows
about interfaces (ports), you can plug in a fake adapter in tests. Instead of spinning
up a real PostgreSQL database for every test, you plug in an in-memory fake repository.
Tests run in milliseconds instead of seconds.

---

#### Event-Driven Architecture (EDA)

**What it is:** Services (or modules) communicate by publishing events to a shared bus.
A service does something, publishes an event ("OrderPlaced"), and moves on. Other
services that care about that event subscribe and react asynchronously — they are not
waiting for a response, and they may not run until seconds or minutes later.

**Real-world mental model:** A public announcement system. The speaker makes an
announcement and immediately continues their work. Everyone listening decides
independently what to do with the information. The speaker does not know or care who
is listening.

**When this is the right architecture:**
- Multiple downstream systems need to react to the same business event
- Loose coupling between services is a priority — producers must not know consumers
- Long-running processes or workflows span multiple steps over time
- Audit trail and event sourcing are requirements

**The failure modes that cost teams months:**
Event-driven systems fail in confusing ways. Messages arrive out of order (the "OrderShipped"
event arrives before "OrderPlaced"). Messages arrive twice (consumer processes it, crashes,
and the broker retries). Messages arrive never (broker goes down). Every consumer must
be idempotent (processing the same event twice has the same effect as once) and handle
out-of-order delivery gracefully. Design for all three failure modes upfront — retrofitting
idempotency into an existing consumer is difficult.

**Tooling:** Apache Kafka (high throughput, durable, replay), RabbitMQ (lower throughput,
simpler, transient), AWS SQS/SNS (managed, scales automatically, no operations burden),
Redis Streams (simple, in-memory, fast). Choose based on durability requirements and
operational capacity.

---

#### Serverless Architecture

**What it is:** Business logic runs as stateless functions in the cloud, invoked on
demand. You do not provision or manage servers. The cloud provider runs the function
when it is called and charges per invocation. AWS Lambda, Vercel Edge Functions,
Cloudflare Workers, Google Cloud Functions.

**Real-world mental model:** A light switch. The electricity is always available but
flows only when you flip the switch. You do not pay for electricity when the light is off.

**When this is the right architecture:**
- Unpredictable or spiky traffic — idle most of the time, bursting occasionally
- Event-triggered workloads: process a file when it is uploaded, send an email when
  a record changes, run a report at midnight
- Small teams that cannot afford infrastructure operations overhead
- Prototypes and MVPs where infrastructure cost must be near zero

**What experienced engineers know:**
Cold starts (the delay when a function runs for the first time after being idle) are
real and can be 200ms-3s depending on runtime and memory configuration. Keep functions
small and focused — a function that does too many things is slow to cold-start and hard
to debug. Serverless is terrible for: long-running processes (15-minute Lambda timeout),
heavy computational work, stateful workloads, and anything requiring persistent TCP
connections.

---

#### SOA (Service-Oriented Architecture)

**What it is:** An older approach to decomposing systems into services, typically
characterized by a central Enterprise Service Bus (ESB) that mediates all inter-service
communication, and services defined around enterprise capabilities rather than business
domains.

**When to use it:** Legacy enterprise environments where it already exists. Do not
start new systems with classical SOA — modern microservices or event-driven architecture
achieves the same goals without the ESB bottleneck.

---

#### CQRS (Command Query Responsibility Segregation)

**What it is:** The write path and the read path are completely separate models. Commands
change state; queries read state. They may use different code, different data models, and
in extreme implementations, different databases — one optimized for writes (normalized,
transactional), one optimized for reads (denormalized, pre-joined for specific views).

**Real-world mental model:** A bank. When you deposit money (command), it goes through
a teller who validates, records, and applies the transaction. When you check your balance
(query), you read from a ledger that has been pre-calculated for fast lookup. The same
database but two completely different paths — one write-optimized, one read-optimized.

**When this is the right architecture:**
- Read patterns are radically different from write patterns (a dashboard that aggregates
  data from many tables in a specific way, while writes are individual record changes)
- Read performance is a bottleneck and the write data model is normalized for correctness
- The system needs to support multiple consumers who need the same data in different shapes
- Used with Event Sourcing (storing the history of events rather than current state)

**When it is the wrong choice:** Most applications. CQRS adds significant complexity —
two models to maintain, synchronization between them, eventual consistency to manage.
Do not use it because it sounds sophisticated. Use it when read/write separation is a
measured, real bottleneck.

---

#### EDA + CQRS (Event-Sourced CQRS)

**What it is:** Combine event-driven architecture with CQRS. Write operations produce
events that are stored as the system of record (event sourcing — the current state of
the system is derived by replaying all events). Read models (projections) subscribe to
those events and maintain their own denormalized view optimized for queries.

**When this is the right architecture:**
- Audit trail and compliance requirements are non-negotiable
- The system must support time travel — reconstructing state at any point in history
- Multiple very different read views of the same underlying data
- Financial systems, healthcare records, legal document management

**The senior engineer's warning:** Event sourcing is a significant operational burden.
Schema evolution of events is hard. Replaying millions of events to rebuild a projection
takes time. Debugging requires understanding event sequences across time. Do not adopt
this pattern without real domain requirements driving it.

---

#### Space-Based Architecture

**What it is:** Eliminates the database as the central bottleneck by distributing data
and processing across in-memory data grids. Multiple "processing units" each hold a
subset of data in memory and handle requests locally. Changes are asynchronously
replicated to a persistence store.

**When to use it:** Extreme high-throughput systems (millions of transactions per second)
where even a fast database is a bottleneck. Trading systems, real-time gaming, ad serving.
Very specialized — almost no general web applications need this.

---

#### Peer-to-Peer Architecture

**What it is:** No central server. Each node is both a client and a server. Nodes
communicate directly with each other. The network is resilient because there is no
single point of failure.

**When to use it:** File sharing systems (BitTorrent), blockchain networks, some
real-time collaboration tools. Not appropriate for typical web applications.

---

#### Client-Server Architecture

**What it is:** The foundational pattern of the web. A client (browser, mobile app)
sends requests to a server. The server processes the request and returns a response.
The client and server are separate programs that communicate over a network.

**When to use it:** This is the baseline architecture of every web and mobile
application. Every other architecture in this list is a refinement or extension of this
basic model.

---

### Mobile architectures

#### MVC (Model-View-Controller)

**What it is:** Three components: Model (the data and business logic), View (the UI
that the user sees), Controller (the intermediary that handles user input, updates the
model, and chooses which view to show).

**Real-world mental model:** A vending machine. The items inside are the Model. The
display showing options is the View. The button you press is the Controller — it receives
your input, interacts with the items, and updates the display.

**When to use it:** Simple applications and UIKit-based iOS development. Falls apart
on large applications because the Controller becomes a "Massive View Controller" — a
class with thousands of lines that is impossible to test.

**The senior engineer's view:** MVC is fine for small screens and simple flows. As soon
as a screen has more than two or three interactions, the controller accumulates logic
that does not belong there. Move to MVVM before that happens.

---

#### MVP (Model-View-Presenter)

**What it is:** Similar to MVC but the Presenter is completely unaware of the Android
or iOS framework — it is plain code with no UI imports. The View is passive: it only
displays what the Presenter tells it and forwards events to the Presenter. The View
and Presenter communicate through an interface.

**When to use it:** Android development before Jetpack Compose and MVVM became standard.
The interface between View and Presenter makes unit testing the Presenter trivial —
you can test all presentation logic without a device or emulator.

---

#### MVVM (Model-View-ViewModel)

**What it is:** The ViewModel holds the UI state and exposes it as observable streams.
The View observes those streams and re-renders when they change. The ViewModel does not
know the View exists — it only exposes state and accepts commands.

**When to use it:** Default architecture for modern Android (ViewModel + LiveData or
StateFlow), SwiftUI on iOS, and WPF/.NET applications. In Flutter, this maps closely
to the BLoC pattern or Riverpod with StateNotifier.

**Why experienced engineers prefer it over MVC:**
The ViewModel is fully testable without a UI framework. You test the ViewModel by
calling its methods and asserting on its output state — no simulated clicks, no UI,
no device. This is the critical difference. Additionally, the ViewModel survives
configuration changes (screen rotation) on Android — the View is recreated, but the
ViewModel is not.

---

#### Clean Architecture (Mobile)

**What it is:** The same concentric rings as backend Clean Architecture applied to
mobile. Domain entities and use cases in the center, ViewModels/Presenters in the
middle ring, UI and data layers on the outside. Used in large mobile applications where
the business logic must be testable and reusable across platforms.

**When to use it:** Large mobile apps with complex business logic (fintech, healthcare),
apps where the domain logic is shared between iOS and Android via Kotlin Multiplatform,
and any mobile app where the business rules need to be testable independently of the
Android or iOS framework.

---

#### Redux Architecture

**What it is:** A single global store holds the entire application state as a plain
object tree. State can only change by dispatching an action (a plain description of
what happened). A reducer function takes the current state and an action and returns
the new state. The state is immutable — reducers return new objects, never mutate.

**When to use it:** React applications with complex shared state that many unrelated
components need to access and modify. The Redux DevTools time-travel debugger is
genuinely invaluable for complex state bugs.

**When experienced engineers avoid it:** Simple applications where Context + hooks is
enough. Redux adds boilerplate — actions, reducers, selectors, middleware. If a simpler
solution works, use it. Zustand is the lightweight modern alternative — same ideas,
a fraction of the code.

---

#### Flux Architecture

**What it is:** The predecessor to Redux, created by Facebook. Unidirectional data
flow: Action → Dispatcher → Store → View → (user interaction produces) → Action.
Redux is essentially a cleaner, reduced version of Flux.

**When to use it:** Largely historical — Redux has superseded it. Understand it to
understand where Redux came from, but build new systems with Redux or Zustand.

---

#### BLoC Pattern (Business Logic Component)

**What it is:** Flutter's standard architecture pattern. Each BLoC (Business Logic
Component) receives events (user actions), processes them, and emits states (the result).
The UI listens to state streams and rebuilds when a new state is emitted. Built on
Dart's `Stream` system or the `flutter_bloc` library.

**When to use it:** Every non-trivial Flutter application. The `flutter_bloc` library
enforces this pattern with clear conventions — events are sealed classes (every possible
action is named and typed), states are sealed classes (every possible UI state is named
and typed), and the BLoC is fully testable without Flutter widgets.

**The senior engineer's view:** BLoC is more verbose than simpler options like Riverpod
but the explicitness is its strength. Every state transition is named and auditable.
When debugging why the UI is in a wrong state, you look at the sequence of events and
states in the BLoC — it is a complete audit trail of every action the user took.

---

#### VIPER Architecture

**What it is:** A very strict separation pattern for iOS (Swift). Five components:
View (displays, forwards events), Interactor (business logic, use cases), Presenter
(formats data for display), Entity (plain data models), Router (navigation).

**When to use it:** Large iOS teams where strict separation and clear ownership are
required. Enforces single responsibility on every class. Very verbose — a simple screen
requires five files. Not worth the overhead for small apps.

---

#### MVI (Model-View-Intent)

**What it is:** The UI emits Intents (user actions). A function processes intents and
produces a new Model (state). The View renders the Model. Strictly unidirectional.
Similar to Redux but designed around reactive streams.

**When to use it:** Modern Android with Kotlin coroutines and Flow, and any reactive
mobile architecture where unidirectional data flow is a priority. Increasingly popular
as an alternative to MVVM in complex Android screens.

---

### Frontend / Web architectures

#### SPA (Single Page Application)

**What it is:** The browser loads one HTML page at startup. All subsequent navigation
happens by JavaScript manipulating the DOM — the URL changes and content updates, but
the browser never makes a full page request for a new HTML document.

**When to use it:** Applications where user experience is more important than first-load
performance — dashboards, productivity tools, admin panels. The first load is slow (large
JavaScript bundle); subsequent interactions are fast.

**The SEO problem:** Search engine crawlers traditionally cannot execute JavaScript —
they see a blank page. This has improved but SPAs still have SEO disadvantages. If SEO
matters, use SSR or SSG.

---

#### MPA (Multi-Page Application)

**What it is:** Each page is a separate HTML document returned by the server. Navigation
means a full browser request for a new HTML document.

**When to use it:** Content-heavy public websites, e-commerce, anything where SEO and
first-load performance are critical. Traditional Rails, Django, and Laravel apps are MPAs.
HTMX is a modern approach to adding interactivity to MPAs without a full frontend
framework.

---

#### SSR (Server-Side Rendering)

**What it is:** HTML is generated on the server for every request, then sent to the
browser. JavaScript then "hydrates" the page — takes over and makes it interactive.
Next.js, Nuxt.js, SvelteKit, Remix.

**When to use it:** Public-facing pages where SEO and Time-to-First-Byte matter (the
user sees content fast because HTML arrives ready to display), combined with the
interactive experience of a SPA once the JavaScript loads. The default for Next.js
App Router.

**The trade-off:** Server must do work on every request. Caching at the CDN level is
more complex than with SSG.

---

#### SSG (Static Site Generation)

**What it is:** HTML is generated at build time, not at request time. The server serves
pre-built files — no computation on each request. Extremely fast and cheap to serve.

**When to use it:** Blogs, documentation sites, marketing pages, any content that does
not need to be different per user or per request. Incremental Static Regeneration (ISR)
in Next.js is a middle ground — pages are statically generated but regenerated in the
background when content changes.

---

#### Isomorphic / Universal Apps

**What it is:** The same JavaScript code runs on both the server (for SSR) and the
client (for SPA-like interactivity after hydration). Next.js, Nuxt, and Remix are all
isomorphic frameworks.

**The complexity to explain every time:** Code that runs on both server and client must
be careful about what it accesses. `window`, `document`, and `localStorage` are only
available in the browser — code that uses them crashes on the server. Always guard with
`typeof window !== 'undefined'` checks or Next.js's `'use client'` directive.

---

#### Micro-Frontend Architecture

**What it is:** The frontend is split into independently deployable pieces, each owned
by a different team. A shell application composes them at runtime. Module Federation
(Webpack 5) is the most common implementation.

**When to use it:** Large organizations where multiple independent teams contribute to
one product and cannot coordinate deployments. Shares the complexity of microservices
but applied to the frontend. Like microservices, do not use it until the organizational
problem is real — the technical overhead is significant.

---

### Repository / Project structure

#### Monorepo

**What it is:** All services, packages, and apps live in a single Git repository.
Tooling (Nx, Turborepo, Bazel) provides incremental builds — only rebuild what changed.

**When to use it:**
- Multiple packages that share code (a React component library used across three apps)
- Multiple services that deploy together and are owned by one team
- You want atomic commits across multiple packages ("Update the API contract and the
  client that uses it in one commit")

**Tooling:**
- **Turborepo** — fast build orchestration for JavaScript/TypeScript monorepos. Caches
  build outputs locally and remotely. The best choice for most JS/TS monorepos.
- **Nx** — more opinionated, includes code generators, dependency graph visualization,
  and affected-command detection (only run tests for packages that changed). Excellent
  for large polyglot repos.
- **Bazel** — Google's build system. Language-agnostic, hermetic builds, extreme
  performance at very large scale. Complexity is high — only justified at large
  organizations.

---

#### Polyrepo

**What it is:** Each service or application has its own Git repository.

**When to use it:**
- Truly independent services with independent teams, independent release cycles, and
  no shared code
- Services in completely different languages with no common tooling

**The hidden cost:** Cross-service changes require multiple PRs, multiple CI runs, and
careful coordination of deployment order. Sharing a library means publishing it as a
package and bumping versions across every consumer. These coordination costs compound
with team size. Monorepos solve this; polyrepos don't.

---

### Architecture decision guide

When I start or review a project, I will use this decision tree automatically and
explain my reasoning:

**Solo developer or team of 1-3, new product:**
→ Modular Monolith with Clean Architecture internals + Layered structure + Monorepo if
there is a shared component library. PostgreSQL. Deploy to Railway or Render. No
Kubernetes, no microservices, no message queues unless one is genuinely needed.

**Team of 4-12, product with defined domain, 6+ months old:**
→ Modular Monolith (if boundaries are now clear) or careful first service extraction
for a genuinely separate concern (e.g., async image processing). CQRS on specific
read-heavy features if measured. Turborepo monorepo. Postgres + Redis. GitHub Actions
+ Docker + a managed Kubernetes service if scaling demands it.

**Team of 15+, multiple product squads, high scale:**
→ Microservices along bounded context lines. Event-driven communication between services.
CQRS + read replicas where read/write ratio warrants it. GitOps with Argo CD. Full
observability stack (OTel + Prometheus + Grafana + Sentry). Consider whether a
Modular Monolith per squad is better than one microservice per feature.

**Mobile app, single team:**
→ MVVM (Android/SwiftUI) or BLoC (Flutter). Clean Architecture for the domain layer
if business logic is complex. Redux/Zustand if state is shared across many unrelated
screens.

**Public marketing site or blog:**
→ SSG with Next.js or Astro. No backend unless needed. Vercel or Cloudflare Pages.

**Dashboard or admin tool:**
→ SPA or SSR with Next.js. Postgres + Prisma. shadcn/ui. No over-engineering.

**Anything with compliance, audit, or financial requirements:**
→ Event sourcing + CQRS + Clean Architecture. Every state change recorded as an
immutable event. Hexagonal architecture so the domain is testable without infrastructure.

I will always state which architecture I am recommending, why, and what the trigger
conditions are for evolving to the next level of complexity.

---

