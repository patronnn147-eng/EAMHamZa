## Good practices (senior engineer and architect level)

This section contains the principles that separate code that works from code that
lasts. These are not rules for their own sake — each one exists because someone
discovered the hard way what happens when you ignore it. When working with me, apply
these automatically and explain which principle is at play when you use one.

---

### Code quality principles

**Write code for the next person, not the compiler.** The compiler does not care about
variable names. The next engineer who reads your code at 11pm during an incident does.
Name things so clearly that a comment would be redundant. If you cannot name a function
without using "and" (e.g., `validateAndSave`), it is doing two things and should be
two functions.

**The rule of three for abstraction.** Do not abstract the first time you write
something. Do not abstract the second time you write the same thing — just note the
duplication. Abstract the third time. Premature abstraction creates the wrong
abstraction, which is worse than duplication. Wrong abstractions are hard to undo
because code accumulates around them.

**Complexity budget.** Every system has a complexity budget. When you spend complexity
on infrastructure (a clever caching layer, a distributed queue, a custom serialization
format), you have less budget left for product complexity. Spend the budget on what
makes the product valuable, not on technical novelty. Boring infrastructure is a feature.

**Immutability by default.** Mutable shared state is the root cause of a large fraction
of bugs. Prefer values that cannot be changed after creation. When state must be
mutable, make mutation explicit, isolated, and intentional — not a side effect of
calling a function.

**Command-Query Separation (CQS).** A function either changes state (a command) or
returns data (a query) — not both. `getUserById(id)` returns a user and changes nothing.
`activateUser(id)` changes state and returns nothing meaningful. Functions that do both
are surprising and hard to test. Explain this principle when a function mixes reads and
writes.

**Fail fast, fail loud, fail early.** Validate inputs at system boundaries — the edge
of your application, the entry point of a function that expects specific data. A crash
at the boundary with a clear error message is infinitely better than corrupted data
propagating silently through your system for three hours before causing an invisible
failure. Defense in depth means checking at every layer, not trusting that the previous
layer did it correctly.

---

### Architecture principles

**The Dependency Rule (Clean Architecture).** Dependencies must point inward. The
business logic (domain layer) knows nothing about databases, HTTP, or frameworks. The
database and HTTP layers depend on the business logic, not the other way around. This
means you can swap PostgreSQL for MongoDB, or REST for GraphQL, without touching the
core logic. When this rule is violated, the framework owns you — when you upgrade it
or replace it, you are rewriting your entire application.

**Ports and Adapters (Hexagonal Architecture).** The application core defines
interfaces (ports) for everything it needs from the outside world — a database, an
email sender, a payment processor. The actual implementations (adapters) satisfy those
interfaces. The core never knows which adapter it is talking to. This makes testing
trivial: swap the real adapter for a fake one in tests, and the core does not know
the difference.

**Event-driven boundaries.** Services should communicate across boundaries with events
(asynchronous messages) rather than direct calls where possible. A direct call couples
the two services — if the downstream service is slow or down, the upstream service
feels it immediately. Events decouple them: the producer publishes and moves on; the
consumer processes when it can. Use Kafka, RabbitMQ, AWS SQS/SNS, or Redis Streams
depending on scale and durability requirements. Explain each trade-off when recommending one.

**The Strangler Fig for migrations.** Never stop the world to do a big rewrite.
Instead, build the new system alongside the old one, route a small percentage of traffic
to the new system, increase it gradually as confidence grows, and delete the old system
once traffic has fully migrated. This is the only safe way to replace a live system.

**Design for failure, not for success.** Every external call will eventually fail.
Every database will eventually be unavailable for a few hundred milliseconds. Design
around this reality: use retries with exponential backoff (wait 1s, then 2s, then 4s
between retries — not a tight loop that hammers a struggling service), circuit breakers
(stop calling a failing service after N failures, giving it time to recover), timeouts
(every outbound call needs a deadline — a call that never returns is worse than one
that returns an error), and bulkheads (isolate failures so one slow dependency does not
exhaust all threads and take down the entire application).

**Schema-first design.** Before writing any code that crosses a system boundary — an
API endpoint, a database table, a message format — write the schema first. The schema
is the contract. Once agreed, both sides can implement in parallel. Changing a schema
after the fact is expensive; designing it carefully upfront is cheap.

**The 12-Factor App.** Twelve principles for building software-as-a-service that is
portable and scalable. The most important: store config in environment variables (not
code), treat backing services (databases, queues) as attached resources that can be
swapped, keep stateless processes (store session data in the database, not in memory
on the server), and log to stdout (let the infrastructure collect and route logs).
Apply these in every new application.

**Distributed systems tradeoffs (CAP theorem).** In any distributed system, you can
guarantee at most two of three properties: Consistency (every read sees the most recent
write), Availability (every request gets a response), and Partition tolerance (the
system works even when network failures split it into parts). Since network failures
always happen eventually, you always sacrifice either consistency or availability.
Choose deliberately based on the use case: banking needs consistency; social media feeds
can tolerate eventual consistency. Explain this trade-off when a distributed data
decision comes up.

---

### API design principles

**Hypermedia and discoverability (HATEOAS).** A truly RESTful API includes links in its
responses that tell the client what actions are available from the current state. In
practice, most teams implement a pragmatic REST that omits hypermedia — acceptable, but
understand what is being given up.

**Idempotency everywhere that matters.** An idempotent operation produces the same
result no matter how many times you call it. `GET /users/123` is naturally idempotent.
`POST /orders` is not — calling it twice creates two orders. For operations with
real-world consequences (payments, emails, fulfillment), add an idempotency key: a
unique ID the client generates and sends with the request. If the server has already
processed that key, it returns the original result instead of doing it again. This is
how you safely handle retries after network failures.

**Versioning strategy.** URL versioning (`/v1/`, `/v2/`) is the most explicit and
cacheable. Header versioning (`Accept: application/vnd.myapp.v2+json`) is cleaner but
harder to debug. Pick one and stick with it. Never break a published version — add
capabilities in the current version, deprecate old capabilities with a sunset date,
release a new version only for breaking changes. The deprecation window should be at
least 6 months and communicated clearly.

**Pagination, filtering, and sorting are not optional.** Any endpoint that returns a
collection must support pagination from day one. Cursor-based pagination (return a
cursor pointing to the last item; next request starts from there) scales to any size
and handles concurrent inserts/deletes correctly. Offset pagination (`?page=3`) is
simpler but breaks when items are inserted during iteration and is slow on large
offsets. Always include the total count and next/previous cursor in the response.

---

### Database design principles

**Normalize first, denormalize for measured performance problems.** Normalized data
(each fact stored once, relationships via foreign keys) is correct and consistent.
Denormalized data (duplicated for read performance) is faster for specific queries but
creates synchronization problems — two copies of the same fact can disagree.
Start normalized. Denormalize only when you have measured a real performance bottleneck.

**Soft deletes and audit trails.** For any data that is regulated, legally significant,
or user-recoverable, never hard delete. Add a `deleted_at` timestamp column: `NULL`
means not deleted; a timestamp means it was deleted at that time. Add `created_at`,
`updated_at`, and `updated_by` to any table where changes need to be tracked. This costs
nothing to add at the beginning and is very expensive to add after the fact.

**Index strategy.** Every foreign key column must be indexed. Every column used in a
`WHERE`, `ORDER BY`, or `GROUP BY` clause in a frequently-run query should be considered
for an index. Indexes make reads faster but writes slower (the index must be updated).
Use `EXPLAIN ANALYZE` to verify an index is being used. A query plan that shows
"Seq Scan" (sequential scan — checking every row) on a large table is a problem.
Composite indexes (covering multiple columns) serve queries that filter on multiple
columns simultaneously.

**Connection pooling.** A database connection is expensive to create. A connection pool
keeps a set of connections open and reuses them. Without pooling, a spike in traffic
creates thousands of new connections simultaneously and can crash the database.
PgBouncer for PostgreSQL, HikariCP for Java/Spring Boot. Know the pool size and
configure it for the expected concurrency.

---

### Security principles (architect level)

**Defense in depth.** Never rely on a single security control. Validate input at the
API gateway, validate again in the service, and parameterize database queries regardless.
Each layer assumes the previous one could have been bypassed.

**Zero trust networking.** Assume the internal network is compromised. Every service
authenticates every request from every other service — no implicit trust because
something is "inside the firewall." Use mTLS (mutual TLS — both sides prove their
identity) for service-to-service communication. Use short-lived credentials that rotate
automatically.

**The principle of least privilege, rigorously applied.** Not just "this service only
reads from the database." Go further: this service only reads from these specific tables;
this IAM role can only write to this specific S3 bucket; this database user has no
permission to drop tables. When something is compromised, the blast radius is exactly
the scope of the permissions that were granted — no more.

**Cryptography: use the standard, do not invent.** Use AES-256 for symmetric encryption,
RSA-4096 or Ed25519 for asymmetric. Use bcrypt, scrypt, or Argon2 for password hashing
— not SHA256, which is fast (bad for passwords — fast hashing means fast brute force).
Never roll your own cryptographic algorithms. Ever.

**Threat modeling before building.** Before designing a new system or feature, ask:
what is an attacker trying to accomplish? What data is valuable? What are the entry
points? The STRIDE model (Spoofing, Tampering, Repudiation, Information Disclosure,
Denial of Service, Elevation of Privilege) is a structured way to think through threats.
Not every project needs a formal threat model, but every engineer should think through
these dimensions informally before finalizing a design.

---

### Performance principles

**Measure, then optimize.** Guessing where a performance bottleneck is is almost always
wrong. Profile first: find the actual slow code, the actual slow query, the actual
memory leak. Then fix that specific thing. Premature optimization wastes engineering
time and adds complexity without improving user experience.

**The performance hierarchy.** Fix the algorithm before fixing the implementation.
An O(n²) algorithm (one that gets dramatically slower as the data size grows) running
in optimized C will still be beaten by an O(n log n) algorithm in Python at scale.
Once the algorithm is right, fix the data access pattern (reduce N+1 queries, add
indexes). Once that is right, add caching. Only then tune the application code itself.

**Caching strategy: know the invalidation plan before adding the cache.** Caching means
storing a computed result so you do not have to compute it again. Cache at the right
layer: CDN caching for static assets, HTTP response caching for API responses that
change infrequently, application-level caching (Redis, Memcached) for expensive database
queries or external API calls. The hardest part of caching is invalidation — making sure
the cache does not serve stale data after the underlying data changes. Design the
invalidation strategy before adding the cache.

**Read replicas and CQRS (Command Query Responsibility Segregation).** For
read-heavy systems, separate the read path from the write path. In the database:
use read replicas that receive changes from the primary. In the application: CQRS
means having separate models for reading data and writing data — the write model
enforces business rules and invariants; the read model is optimized for how the
UI needs to display data (often denormalized for speed). This is an advanced pattern —
explain the trade-offs before implementing it.

---

### Testing principles (architect level)

**The testing pyramid.** The foundation is many fast unit tests. The middle is fewer,
slower integration tests. The top is a small number of end-to-end tests covering the
most critical user flows. The pyramid shape is deliberate — unit tests are cheap to run
and maintain; end-to-end tests are expensive and flaky. Inverting the pyramid (many
end-to-end tests, few unit tests) creates a slow, brittle test suite that teams stop
trusting and maintaining.

**Testing the behavior, not the implementation.** A test should express what the system
is supposed to do from the outside, not how it does it internally. If you rename a
variable and a test breaks, the test is testing implementation, not behavior. Good tests
survive refactoring because refactoring does not change what the code does, only how.

**Contracts and consumer-driven contract testing (Pact).** When two services communicate
via an API, both need to agree on the format. Consumer-driven contract testing means the
consumer defines what it expects (the contract), and both sides run tests against that
contract independently. The consumer proves it handles the responses correctly; the
provider proves it returns what the contract requires. Tools: Pact. Essential for
microservices where the teams deploying the consumer and provider are independent.

**Chaos engineering.** Deliberately introduce failures into a production (or
production-like) system to verify that it handles them gracefully. Kill a pod
randomly. Introduce network latency. Fail a database connection. Netflix invented this
practice with their Chaos Monkey tool. The goal is to find weaknesses before an
uncontrolled failure finds them for you. Explain this concept when discussing resilience.

---

### Frontend architecture principles

**Component design: composition over inheritance.** Build UIs from small, single-purpose
components that are composed together, not from large components that inherit behavior.
A `<Button>` knows how to render a button. A `<Form>` composes multiple inputs. A
`<CheckoutPage>` composes a form, a summary, and a payment section. Each component is
testable in isolation.

**State management: co-locate state as close to where it is used as possible.** Do not
put everything in a global store because it is convenient. UI state that only one
component needs lives in that component. State shared between a parent and a few
children can be lifted up to the parent. Only state that is genuinely global (current
user, theme, cart contents) belongs in a global store (Zustand, Redux Toolkit, Pinia,
NgRx). Over-use of global state makes applications impossible to reason about.

**The loading / error / empty / success pattern.** Every piece of UI that fetches data
has four possible states: loading (show a skeleton or spinner), error (show an error
message with a retry option), empty (show a meaningful empty state, not just nothing),
and success (show the data). Handling all four is not optional — users who see a spinner
forever or a blank page will not know if the app is broken or loading. Always implement
all four states.

**Performance budgets.** Set a budget for page weight (JavaScript bundle size), time-to-
interactive, and Largest Contentful Paint (LCP — the time until the main content is
visible, a key metric Google uses for search ranking). Enforce them in CI with tools
like Lighthouse CI or Bundlesize. A page that ships 5MB of JavaScript is a failure
before the first line of code is reviewed.

---

