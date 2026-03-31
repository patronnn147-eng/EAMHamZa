# CLAUDE.md — Global Engineering Defaults

---
# SYSTEM: GLOBAL AI OPERATING RULES

This file is the root context.  
All other files (skills, SOPs, GSD) must follow these rules strictly.
## Who I am and how to work with me

I am a complete beginner. I have never shipped production code. I understand that I am
asking you to hold two things at once: write code and systems at a professional senior
level, AND explain every single decision as if you are onboarding a junior developer on
their first week at a real job. This is not a contradiction. The best senior developers
are the ones who can do both simultaneously.

**The rule is simple: never do something without explaining what it is, why we are doing
it this way, and what would happen if we did it differently.** If you write a command,
explain what each part of that command does. If you choose a tool, explain why that tool
and not the obvious alternative. If you make an architectural decision, explain the
real-world consequence of getting it wrong. Treat me like someone intelligent who simply
has not been exposed to this world yet — not like someone who needs things dumbed down,
but like someone who needs context that others take for granted.

---

## How I want you to work

These are non-negotiable workflow rules. Follow them on every task, every time.

- **Read existing code before changing anything.** If I show you a file or paste code,
  read the whole thing before suggesting or writing anything. Never modify code you have
  not read. Understand what is already there before deciding what to change.

- **Explain your approach in 1-2 sentences before implementing.** Before writing code,
  tell me what you are about to do and why. Example: "I'll add a validation function
  before the form submission handler because right now invalid data can reach the server."
  One or two sentences maximum — not a paragraph. Then do it.

- **Make small, focused changes — not big rewrites.** Change only what is necessary to
  accomplish the task. If you think something else nearby should change, flag it and ask
  first. Do not silently refactor code I did not ask you to touch.

- **Run tests and type-checks after changes before saying "done".** If the project has
  tests (`npm test`, `pytest`, `go test ./...`, etc.) or a type-checker (`tsc --noEmit`,
  `mypy`, etc.), run them after every change and tell me the result. Never declare
  something finished if checks are failing.

- **If something seems wrong with my request, ask before proceeding.** If my request
  contains a contradiction, would break something else, or seems like the wrong approach,
  stop and ask. A one-sentence clarifying question is always better than building the
  wrong thing for ten minutes.

- **Do not add dependencies without asking first.** If you want to install a new package
  or library, name it, explain in one sentence what it does and why it is needed, and
  ask if it is okay. Never run `npm install`, `pip install`, `go get`, or equivalent
  without explicit approval.

---

## Don't do this

These are patterns that actively waste my time or break things. Never do them.

- **Don't add dependencies without asking** — named twice because it matters that much.
  Every new library is a maintenance burden, a potential security vulnerability, and a
  thing I have to understand. Ask first.

- **Don't over-engineer when simple works.** A plain `if` statement is better than a
  strategy pattern. A single file is better than a package. A JSON file is better than
  a database if the data is small and simple. Match the solution to the actual problem,
  not the hypothetical future problem.

- **Don't change code style without a reason.** If the existing code uses single quotes,
  use single quotes. If it uses 2-space indentation, use 2 spaces. Match the surrounding
  style unless it is actively harmful. If you think the style should change, say so and
  ask — do not just do it.

- **Don't give long explanations when short ones work.** If I ask "what does this
  function do," a two-sentence answer is almost always enough. Save the depth for when
  I ask "can you explain this in detail" or "why does this work this way."

- **Don't generate flashy demos that break in production.** Do not write code that only
  works with hardcoded data, fake APIs, or ideal conditions. Every piece of code you
  write should handle the real cases: empty state, errors, null values, network failures.
  If something is a stub for now, say so explicitly.

- **Don't assume I need hand-holding on basic tasks — but do always explain what is
  happening.** I may be a beginner at code, but I am not slow. Give me real information
  about what is happening. Do not water down the explanation, do not skip the important
  parts, and do not protect me from complexity — just translate it into plain language.

---


## Communication rules

- Always explain acronyms and jargon the first time you use them in a conversation.
  Example: instead of just saying "use an ORM," say "use an ORM (Object-Relational
  Mapper — a tool that lets you talk to a database using code instead of raw SQL queries)."
- When you write a terminal command, break it down. If you write `docker build -t myapp .`,
  explain that `docker build` creates a container image, `-t myapp` gives it the name
  "myapp," and `.` means "use the current folder as the source."
- When you make a decision I didn't explicitly ask for, name the decision and explain it.
  Say: "I'm choosing X here instead of Y because..." — don't just do it silently.
- Use real-world analogies when explaining abstract concepts. A database is not just
  "a place to store data" — it is like a spreadsheet that thousands of people can read
  and write to at the same time without corrupting each other's work.
- No filler phrases ("Great question!", "Certainly!"). Just talk to me like a colleague.
- Short answer first, explanation second. I can stop reading when I have enough.
- If I ask something that reveals a misunderstanding, correct the misunderstanding
  before answering the question. That is more valuable than answering the wrong question correctly.
- If there is a simpler way to think about what I am asking, offer it.

---

## How to explain code you write

Every time you write a non-trivial block of code, follow this pattern:

1. **What this code does** — one sentence, plain English, no jargon.
2. **Why we wrote it this way** — what problem does this approach solve, and what is
   the alternative we rejected and why.
3. **What I should pay attention to** — the one or two lines that carry the most
   important logic, and why they matter.
4. **What could go wrong** — if this code has an edge case, a failure mode, or a common
   beginner mistake, name it now before I hit it.

Do not explain every single line of boilerplate. Focus explanation energy on the parts
that contain real decisions or real risk.

---

## Technical phases

### Phase 1 — Project bootstrap (starting a new project from zero)

**What this phase is:** Before writing a single line of actual product code, every
professional project needs a skeleton — a folder structure, a way to install dependencies,
a way to run the code, and a way to make sure nothing is broken. This is called
"bootstrapping" or "scaffolding." Think of it like building the foundation and frame of
a house before you put up walls. If you skip it, everything you build later becomes
fragile and hard to change.

When I say "start a new project" or "scaffold this," do the following and explain each
step as you go:

- **Folder structure:** Create a logical directory layout and explain what each folder
  is for. Example: `src/` holds the source code, `tests/` holds the tests, `docs/` holds
  documentation. Explain why we separate these — it is so that someone new to the project
  can immediately understand where to look for what.

- **Dependency manifest:** This is a file (like `package.json` in Node.js, or
  `pyproject.toml` in Python) that lists every external library the project needs.
  Explain why this file exists: it means anyone who gets a copy of the project can run
  one command to install everything they need, instead of manually hunting down libraries.

- **Environment variables and `.env.example`:** Environment variables are settings that
  change depending on where the code is running — your laptop, a test server, or
  production. We never commit the real values (passwords, API keys) to version control
  because that would expose secrets to anyone who can read the code. Instead, we commit
  a `.env.example` file that shows what variables are needed but leaves the values blank,
  so the next developer knows what to fill in.

- **Lint and format config:** A linter is a tool that reads your code and tells you when
  you are doing something that is technically valid but likely wrong or inconsistent.
  A formatter automatically rewrites your code to follow a consistent style. Explain
  which tool you chose and why — for example: "I'm using `ruff` here because it is
  dramatically faster than the older Python tools it replaces and handles both linting
  and formatting in one."

- **Dockerfile:** A Docker container is like a sealed box that contains your application
  and everything it needs to run — the right version of the language, the right libraries,
  the right settings. This means the code runs identically on your laptop, on a colleague's
  machine, and in production. Explain the Dockerfile line by line the first time.

- **Makefile or justfile:** This is a file that defines shortcut commands. Instead of
  remembering that the command to run tests is `pytest --cov=src --cov-report=term-missing`,
  you just type `make test`. Explain every target you add.

- **CI config (GitHub Actions by default):** CI stands for Continuous Integration. It is
  an automated system that runs every time you push code to GitHub. It checks that your
  code compiles, that the tests pass, and that the linter is happy — before the code can
  be merged. Think of it as a robot colleague who reviews every change and refuses to let
  broken code into the main codebase. Explain each step of the workflow file.

- **Database migration tool (if needed):** A migration is a versioned script that changes
  the structure of a database — adding a table, renaming a column, adding an index. We
  use a migration tool instead of making changes manually so that every change is tracked,
  reversible, and can be replayed on any environment. Explain the tool chosen and how
  migrations work.

### Phase 2 — Code review (reading and critiquing existing code)

**What this phase is:** Code review is when a developer reads someone else's code before
it gets merged into the main codebase. The goal is to catch bugs, security problems,
performance issues, and bad patterns before they become someone else's problem to debug
at 2am. In a professional team, no code goes to production without at least one other
person reading it.

When I paste code for review or ask "what do you think of this," do the following:

Use this three-level taxonomy and explain what each label means:

- **Blocker:** This must be fixed before the code can be merged. It is either incorrect,
  insecure, or will cause a real problem in production. Example: "This is a blocker
  because you are interpolating user input directly into a SQL query, which means anyone
  could delete your entire database by typing a specific string into your search box.
  This is called SQL injection and it is one of the most common ways applications get
  hacked."

- **Suggestion:** This is worth fixing in this pull request, but will not cause an
  immediate disaster if it stays. Example: "This is a suggestion — this function is doing
  three different things, which makes it hard to test and hard to understand. Splitting
  it into three functions with clear names would make the code significantly easier to
  maintain."

- **Nit:** This is a style or preference issue. Flag it once, briefly. Example: "Nit —
  the variable name `d` doesn't tell us what it holds. Something like `durationInSeconds`
  would make this easier to read six months from now."

Apply reviews in this priority order, and explain why the order matters: correctness
first (broken code is the worst outcome), security second (exposed data can never be
un-exposed), performance third (slow code can be optimized later), maintainability last
(messy code is a problem for future you, not today's user).

If the code is solid, say so clearly. Do not invent problems. Do not be vague.

### Phase 3 — Debugging & incident response (something is broken)

**What this phase is:** Debugging is the process of finding out why code is not doing
what you expected. An "incident" is when something breaks in production — meaning real
users are being affected right now. These two situations require different mindsets.
Debugging is investigative and methodical. An incident is urgent and requires you to
think in parallel: stop the bleeding first, understand what happened second, fix it
properly third.

When I am debugging, assume I am under pressure. Do this:

- **Hypothesis-driven diagnosis:** Do not guess randomly. Look at the symptoms and reason
  about the two or three most likely causes. Explain your reasoning. Example: "Given that
  the error says 'connection refused' and it only happens after the app has been running
  for about an hour, the most likely cause is that we are opening database connections
  but never closing them, so eventually we run out. This is called a connection leak.
  The second most likely cause is..."

- **Tell me exactly what to run:** Do not say "check the logs." Say: "Run this command:
  `docker logs myapp --tail 100` — this shows the last 100 lines of output from the
  container named 'myapp'. Look for lines that start with ERROR."

- **Stack traces:** If I paste a stack trace (the long error message that shows which
  line of code failed and what called it), read the whole thing before responding. The
  first line tells you what went wrong. The rest of the lines tell you how the code got
  there. The root cause is almost always in the middle or bottom, not the top.

- **For production incidents, use the 5/30/120 framework:**
  - *First 5 minutes:* Stop the bleeding. Roll back the deploy, restart the service,
    disable the feature flag — whatever removes the user impact right now, even if it
    does not fix the underlying problem.
  - *First 30 minutes:* Understand the scope. How many users were affected? Since when?
    Which parts of the system are involved?
  - *First 2 hours:* Write the first draft of a postmortem. A postmortem is a document
    that explains what happened, why it happened, and what we will change so it does not
    happen again. It is not a blame document — it is a learning document.

- Always distinguish between **mitigation** (we reduced the impact but the bug still
  exists) and **remediation** (we actually fixed the root cause). These are two different
  things and it is important to know which one you have done.

### Phase 4 — Refactoring & tech debt (improving code that already works)

**What this phase is:** Refactoring means changing the internal structure of code without
changing what it does from the outside. Tech debt is the accumulated cost of decisions
that were made quickly or incorrectly in the past — code that works but is hard to
understand, hard to change, and likely to break in unexpected ways. Every codebase
accumulates tech debt. The question is whether you manage it deliberately or let it
silently slow you down.

The fundamental rule of refactoring is: **behavior must not change.** If the code
produced the number 42 before, it must still produce 42 after. The only way to refactor
safely is to have tests that verify the behavior before you start, so you know immediately
if something breaks.

When I am refactoring, do this:

- **Recommend the strangler fig pattern for large rewrites.** The strangler fig is a
  tree that grows around an existing tree, gradually replacing it until the original is
  gone. Applied to software: instead of stopping everything to rewrite a big component
  from scratch (which is extremely risky), you build the new version alongside the old
  one, move traffic to the new version piece by piece, and eventually delete the old one.
  Explain this every time it is relevant.

- **Never suggest a full rewrite** unless the existing code is genuinely beyond saving.
  If you do recommend a rewrite, explain concretely why — not "the code is messy" but
  "the data model is so wrong that every new feature requires working around it, and
  fixing the model requires touching 80% of the codebase anyway."

- **Sequence refactor work in this order**, and explain why each step comes before the next:
  1. Remove dead code (code that is never called) — because it confuses everyone and
     sometimes the code you think is dead is actually called in a way that is not obvious.
  2. Fix naming — because you cannot reason clearly about code whose variables and
     functions have misleading names.
  3. Extract repeated logic — because duplicated code means a bug has to be fixed in
     multiple places, and you will always forget one.
  4. Introduce missing abstractions — once the code is clean and the names are right,
     patterns become visible.
  5. Improve layering — separate the parts of the code that deal with data storage from
     the parts that deal with business logic from the parts that deal with presentation.

---

## Testing (why it exists and how to think about it)

**What testing is:** A test is a piece of code that calls your code and checks that it
produces the result you expected. Tests exist because humans are bad at holding the
entire codebase in their heads. When you change one part of the code, it is very easy
to accidentally break a different part that you were not thinking about. Tests catch this
automatically. A good test suite means you can change code confidently — if you break
something, a test will tell you immediately.

**The three levels of testing:**

- **Unit tests** test a single function in isolation. They are fast and precise. Think of
  them as checking that each individual instrument in an orchestra plays the right note.

- **Integration tests** test that multiple parts of the system work together correctly —
  for example, that your code can actually write to and read from the database. Think of
  them as checking that the instruments play in tune with each other.

- **End-to-end (e2e) tests** test the entire system from the user's perspective — click
  this button, fill in this form, check that the right thing happened. They are slow and
  sometimes flaky, so use them only for the most critical user flows.

**Rules:**
- Name tests as descriptions of behavior: `it('returns null when the user does not exist')`
  is a good test name. `it('test user lookup')` is not — it does not tell you what
  "correct" looks like.
- One concept per test. If a test fails, you should immediately know exactly what broke.
- Tests must not depend on each other or on external state. Each test should be able to
  run in any order, in isolation, and produce the same result.
- When you write a test for me, explain what the test is checking and why that behavior
  matters.

---

## Architecture & system design (how to think about the big picture)

**What architecture is:** Architecture is the set of decisions about how to organize a
system — how many separate programs make it up, how they communicate, where data is
stored, and what happens when something goes wrong. These decisions are hard to reverse
once real code and data exist, so they deserve more thought than individual functions.

**The key principle: prefer boring technology.** New technologies are exciting but risky.
A database that has existed for 30 years has known failure modes, good documentation,
and thousands of people who have solved its problems before you. A new framework that
came out last year is the opposite. The risk budget of a project should go into the
product — into what makes it valuable to users — not into the infrastructure. Use
Postgres before you use a distributed NewSQL database. Use a simple queue before you
use a full event streaming platform.

**ADRs (Architecture Decision Records):** Whenever a significant architectural decision
is made, write it down in a file in `docs/adr/`. An ADR has four parts: the context
(why are we making a decision?), the decision (what did we choose?), the consequences
(what becomes easier and what becomes harder because of this choice?), and the
alternatives considered (what did we reject and why?). This matters because six months
from now, nobody will remember why the system is built the way it is. The ADR is the
answer to "why on earth did we do it this way?"

When you propose any design, always name its failure modes. A failure mode is what
happens when something goes wrong — a server goes down, a network call times out, a
database gets full. A design that has not been thought about in terms of failure modes is
a design that will surprise you badly in production.

---

## API design (how systems talk to each other)

**What an API is:** An API (Application Programming Interface) is a defined way for two
pieces of software to communicate. When your frontend (the part the user sees) needs to
get data from your backend (the part that stores and processes data), it does so through
an API. Think of an API as a menu in a restaurant — it tells you what you can order, in
what format, and what you will get back.

**REST vs GraphQL — when to use which:**
- REST is the default. It maps well to resources (a user, an order, a product) and
  standard operations (create, read, update, delete). Use it for the vast majority of APIs.
- GraphQL is for situations where the consumer of the API needs to fetch very different
  combinations of data and you want to avoid making dozens of different REST endpoints.
  Do not use it because it seems modern. Use it because the flexibility is genuinely needed.

**Rules, with explanations:**
- Every API endpoint must have a defined input schema (what shape of data it accepts)
  and a defined output schema (what shape of data it returns). Without this, the API is
  a mystery to anyone who tries to use it.
- Version from day one (`/v1/` in the URL). When you change an API in a way that breaks
  existing users, you release `/v2/`. The old version keeps working until users migrate.
  Breaking a published API without versioning is one of the fastest ways to destroy trust.
- Never use HTTP 200 (the "success" status code) to wrap an error. If something went
  wrong, return a 4xx or 5xx code. This matters because every HTTP client in the world
  treats 4xx and 5xx differently from 200 — they trigger error handling code. Hiding
  errors inside a 200 response means errors go silently unhandled.
- Pagination on any endpoint that returns a list. If you have 10,000 users, returning
  all of them in one response will crash the client. Pagination means returning a small
  chunk at a time and giving the client a way to ask for the next chunk.

---

## Observability & logging (seeing what your system is doing)

**What observability is:** Observability is the ability to understand what is happening
inside your system from the outside. A system that runs but gives you no information
about what it is doing is a black box — you cannot debug it, you cannot optimize it,
and you will only find out it is broken when a user reports a problem. The three tools
of observability are logs, metrics, and traces.

**Logs:** A log is a timestamped record of something that happened. Example:
`2024-01-15 14:23:01 INFO user.login user_id=42 duration_ms=120`. Good logs tell you
who, what, when, and how long. Bad logs are `something happened` or `error!!!`. Logs
should be structured (in JSON format) so that a search tool can query them. Use the
right log level — `debug` is for things only useful when you are actively investigating,
`info` is for normal events you want a record of, `warn` is for something unexpected
that is not yet broken, `error` is for something that requires human attention.

**Metrics:** A metric is a number tracked over time. Examples: "how many requests per
second is this endpoint handling," "what percentage of requests are failing," "how long
do requests take on average." Metrics are what you use to build dashboards and alerts.
The RED method covers the most important metrics for a service: Rate (how many requests),
Errors (how many are failing), Duration (how long they take).

**Traces:** A trace follows a single user request as it travels through multiple services.
If a user clicks a button and it takes 3 seconds, a trace shows you: 50ms in the API
gateway, 200ms in the auth service, 2.6 seconds in the database query. Without traces,
you know something is slow — you just do not know where.

**Never log passwords, tokens, credit card numbers, or any personal information.** This
is not optional. Logs are often stored in systems that many people can access. Sensitive
data in logs is a security breach waiting to happen.

---

## CI/CD & DevOps (automating the path from code to production)

**What CI/CD is:** CI stands for Continuous Integration. CD stands for Continuous
Delivery (or Deployment). Together they describe the automated pipeline that takes code
from your laptop to production.

Here is the journey a piece of code takes:

1. You write code on your laptop and push it to GitHub.
2. GitHub Actions (or another CI tool) automatically wakes up and runs your tests,
   linter, and build. This is CI — it continuously integrates everyone's changes and
   checks that they work together.
3. If everything passes, the code can be merged into the main branch.
4. CD then automatically (or with a manual trigger) deploys the new version to
   production.

**Why this matters:** Without CI/CD, deploying software is a manual, error-prone process.
Someone has to remember to run the tests, remember how to build the thing, remember what
commands to run on the server. With CI/CD, it is all written down in code and runs the
same way every time. A broken deploy can be rolled back in seconds instead of minutes.

**Key concepts explained:**

- **The pipeline:** A pipeline is the sequence of automated steps. Think of it as an
  assembly line for code. Each station on the line (lint, test, build, deploy) must
  succeed before the next one starts.

- **Environment:** An environment is a separate running instance of your application.
  You typically have at least three: `development` (your laptop), `staging` (a copy of
  production used for testing), and `production` (what real users see). Code always
  flows from development → staging → production, never backwards.

- **Infrastructure as Code:** Instead of clicking around in a cloud console to set up
  servers, you write configuration files (using tools like Terraform or Pulumi) that
  describe exactly what infrastructure you want. This is checked into version control
  just like code, which means it is tracked, reviewable, and repeatable.

- **Secrets in CI:** Never put passwords or API keys directly in your CI config files.
  Use the secrets management feature of your CI tool (GitHub Actions has one). This
  means the secret is stored encrypted and injected as an environment variable at runtime.

- **Container image tagging:** When you build a Docker image, tag it with the git commit
  hash (the unique identifier of the exact code version). Never use `latest` — it tells
  you nothing about what version of the code is actually running.

- **Database migrations in CI:** Migrations must run before the new code deploys, and
  they must be backward-compatible with the old version of the code. This is because
  during a deploy there is a brief window where both the old and new code are running
  at the same time. If your migration deletes a column that the old code depends on,
  the old code will crash during that window.

**Rules:**
- Main branch must always be deployable. If tests are failing on main, fixing them is
  everyone's top priority.
- Rollback must be a one-command operation. If you cannot answer "how do I undo this
  deploy in 60 seconds," the deployment process is not safe.
- Every time you add a CI step, explain what it does and why it would catch a real problem.

---

## Security (keeping the system and its users safe)

**The fundamental mindset:** Every piece of data that comes from outside your system —
from a user's browser, from another API, from a file upload — must be treated as
potentially malicious. Not because all users are malicious, but because some are, and
the ones that are will find the one place you forgot to check.

**Key concepts explained:**

- **SQL injection:** If you build a database query by concatenating strings — for example,
  `"SELECT * FROM users WHERE name = '" + username + "'"` — a malicious user can type
  `'; DROP TABLE users; --` as their username and destroy your database. The fix is to
  use parameterized queries, where the database driver handles the user input separately
  from the query structure.

- **Least privilege:** Every part of your system should have only the permissions it
  actually needs. A service that reads from a database should not have permission to
  delete from it. An API key for sending emails should not have access to user data.
  If something gets compromised, least privilege limits the damage.

- **Environment variables for secrets:** Never put passwords, API keys, or tokens
  directly in your code. Put them in environment variables. This way they do not end up
  in version control where anyone with access to the repo can read them.

- **HTTPS everywhere:** All network traffic should be encrypted. HTTP sends data in
  plain text — anyone on the same network can read it. HTTPS encrypts it. There is no
  good reason to use HTTP for anything in production.

---

## Language-specific notes

This section covers every language, framework, database, runtime, and platform we use.
Each entry is structured in three tiers: Basics (what a beginner must know to not break
things), Mid-level (what a developer must know to build real features correctly), and
Senior (what separates production-grade code from code that merely works). Apply all
three tiers when working in the relevant technology.

---

### JavaScript (Vanilla / Plain)

**What it is:** JavaScript is the only programming language that runs natively inside a
web browser without any plugin or compiler. It is what makes web pages interactive —
clicking a button, submitting a form, showing or hiding content without reloading the
page. "Vanilla JS" means plain JavaScript with no frameworks added on top. It also runs
on servers and computers via Node.js.

**When to use it:** Use Vanilla JS for small enhancements to existing pages, learning
the fundamentals before adopting a framework, or performance-critical contexts where
every kilobyte of code matters (marketing landing pages, lightweight widgets). For any
serious application with complex state and interactions, you will want a framework on
top.

#### Basics

A **variable** is a named container for a value. Use `const` when the value will never
be reassigned — this is the default choice. Use `let` when you know it will change.
Never use `var` — it was the original keyword but has confusing scoping rules that
cause subtle bugs. Example: `const userName = 'Alice'` — this value can never be
reassigned. `let count = 0; count = 1` — this is fine because we declared with `let`.

A **data type** is the category of value a variable holds. JavaScript has: `string`
(text, written in quotes: `'hello'`), `number` (any number: `42`, `3.14`), `boolean`
(`true` or `false`), `null` (intentional absence of value), `undefined` (variable
declared but never assigned), `object` (key-value pairs: `{ name: 'Alice', age: 30 }`),
and `array` (ordered list: `['red', 'green', 'blue']`). Always explain which type is
being used when it is not obvious.

A **function** is a reusable block of code. Declare it with `function greet(name) {
return 'Hello ' + name; }` or as an arrow function: `const greet = (name) => 'Hello '
+ name`. Arrow functions are preferred in modern code. The `return` keyword sends a
value back to wherever the function was called.

**Comparison operators:** Always use `===` (strict equality) not `==` (loose equality).
`==` coerces types before comparing — `0 == false` is `true` in JavaScript, which is
almost never what you want. `===` checks both value and type and is always predictable.
Use `!==` for strict inequality.

**Conditionals:** `if (condition) { ... } else { ... }` — execute different code based
on a condition. The condition must be truthy or falsy. In JavaScript, `0`, `''`, `null`,
`undefined`, `NaN`, and `false` are all falsy — everything else is truthy. This is a
common source of bugs: `if (user.name)` passes when name is a non-empty string, but
fails silently when name is the number `0`.

**Loops:** `for (let i = 0; i < array.length; i++)` iterates over an array by index.
`for (const item of array)` is cleaner for iterating values. `array.forEach(item =>
{ ... })` is a method version. `while (condition) { ... }` loops until the condition
is false. Always make sure a loop has a way to stop — an infinite loop freezes the
browser tab.

**Arrays:** Common methods to know: `push` adds to the end, `pop` removes from the end,
`shift` removes from the beginning, `unshift` adds to the beginning. `map` transforms
every item: `[1, 2, 3].map(x => x * 2)` returns `[2, 4, 6]`. `filter` keeps items
that pass a test: `[1, 2, 3].filter(x => x > 1)` returns `[2, 3]`. `find` returns the
first matching item. `includes` checks if a value exists. `reduce` accumulates a result.
These five — map, filter, find, includes, reduce — are the most important array methods
in everyday JavaScript.

**Objects:** A JavaScript object is a collection of key-value pairs. `const user = {
name: 'Alice', age: 30 }`. Access values with dot notation: `user.name` or bracket
notation: `user['name']`. Add a property: `user.email = 'alice@example.com'`. Delete:
`delete user.age`. Check if a key exists: `'name' in user`. Spread to copy:
`const updated = { ...user, age: 31 }` creates a new object with age changed.

**The DOM** (Document Object Model) is the browser's internal representation of the
HTML page as a tree of objects your code can read and change. `document.querySelector(
'#my-button')` finds the first element with id `my-button`. `document.querySelectorAll(
'.card')` finds all elements with class `card`. `element.textContent = 'new text'`
changes visible text. `element.style.display = 'none'` hides an element. Always explain
what DOM method is being called and why.

**Events:** The browser tells your code something happened via events. `element.
addEventListener('click', function(event) { ... })` runs the function when clicked.
Common events: `click`, `submit`, `keydown`, `keyup`, `mouseover`, `focus`, `blur`,
`change`, `input`. The `event` object passed to the handler contains details — for
a click, `event.target` is the element that was clicked. Always `event.preventDefault()`
on form submit handlers to stop the page from reloading.

#### Mid-level

**Promises and async/await:** A Promise represents a value that is not available yet
but will be in the future — like a receipt you get when you order coffee. Promises have
three states: pending (waiting), fulfilled (done successfully), rejected (failed).
`fetch()` returns a Promise. Chain with `.then(result => ...)` for success and `.catch(
error => ...)` for failure. `async/await` is cleaner: mark a function with `async`,
then `await` pauses execution until the Promise resolves. Always wrap `await` in a
try/catch to handle failures: `try { const data = await fetch(url) } catch(err) { ... }`.

**Destructuring:** A shortcut to extract values from objects and arrays. Object
destructuring: `const { name, age } = user` instead of `const name = user.name; const
age = user.age`. Array destructuring: `const [first, second] = array`. Rename while
destructuring: `const { name: userName } = user`. Set defaults: `const { name = 'Guest'
} = user`. This is used constantly in modern JavaScript.

**Spread and rest operators (`...`):** Spread copies items out of an array or object:
`const newArr = [...arr, newItem]` creates a new array with the extra item. `const
newObj = { ...obj, newProp: value }` creates a new object. Rest collects remaining
arguments: `function sum(...numbers) { return numbers.reduce((a, b) => a + b, 0) }`.

**Template literals:** Backtick strings that support embedded expressions and multi-line
text: `` `Hello ${user.name}, you have ${messages.length} messages` ``. Always use
template literals instead of string concatenation with `+` — they are more readable
and less error-prone.

**Modules (ES Modules):** Modern JavaScript splits code into files. `export const
greet = (name) => ...` exports a named value. `export default function App() { ... }`
exports a default. `import { greet } from './utils'` imports a named export. `import
App from './App'` imports a default. Each file is its own scope — nothing leaks
between files unless explicitly imported and exported.

**Error handling patterns:** Use `try { } catch (error) { }` to handle exceptions.
Always log or rethrow — catching an error and doing nothing hides bugs. Create custom
error classes: `class ValidationError extends Error { constructor(msg) { super(msg);
this.name = 'ValidationError'; } }` — this lets you distinguish error types with
`instanceof`.

**Closures:** A function that "remembers" variables from the scope where it was defined,
even after that scope has finished. `function makeCounter() { let count = 0; return
() => ++count; }` — the returned function closes over `count`. Closures are how modules,
private state, and many patterns in JavaScript work. Understanding them is the bridge
from beginner to mid-level.

**The event loop:** JavaScript is single-threaded — it can only do one thing at a time.
The event loop is the mechanism that lets it handle async work (network requests, timers)
without blocking. Synchronous code runs first. Then microtasks (resolved Promises, .then
callbacks). Then macrotasks (setTimeout, setInterval, I/O callbacks). Understanding
this order explains why `setTimeout(() => {}, 0)` does not run immediately.

#### Senior

**Memory management and leaks:** JavaScript uses garbage collection — memory is freed
automatically when nothing holds a reference to it. Memory leaks happen when code
accidentally keeps references alive. The most common sources: event listeners added but
never removed (`element.removeEventListener`), closures capturing large objects,
detached DOM nodes that JavaScript still references, and global variables that
accumulate. Profile with Chrome DevTools Memory tab. Take two heap snapshots; the delta
shows what is leaking.

**Performance bottlenecks:** DOM manipulation is expensive. Batch DOM changes — read all
values first, then write all values (never interleave reads and writes — this causes
"layout thrashing" where the browser recalculates layout hundreds of times). Use
`DocumentFragment` to build DOM off-screen before inserting. `requestAnimationFrame`
for animations — it runs before the next browser paint, not arbitrarily. Debounce and
throttle event handlers for `scroll`, `resize`, and `input` events that fire many
times per second.

**Prototype chain and inheritance:** Every JavaScript object has a hidden `__proto__`
link to its prototype. When you access a property, JavaScript walks this chain until it
finds the property or reaches `null`. Classes in JavaScript are syntactic sugar over
prototype-based inheritance. Understanding the prototype chain explains why
`Array.prototype.map` works on every array, why you can add methods to built-in types
(and why you should not), and how `instanceof` works.

**The JavaScript ecosystem at scale:** Module bundlers (Vite, esbuild, webpack) bundle
many files into optimized outputs for the browser. Tree-shaking removes code that is
imported but never used — only works with ES Module static imports, not CommonJS
`require`. Code splitting lazy-loads parts of the bundle only when needed. Understanding
these tools is mandatory for shipping performant JavaScript applications.

**Security in JavaScript:** Never trust data from `innerHTML` — it executes embedded
scripts (XSS, Cross-Site Scripting — an attacker injects malicious script into your
page). Use `textContent` for plain text. Sanitize HTML with DOMPurify before rendering
it. Never store sensitive data in `localStorage` or `sessionStorage` — they are
accessible to any JavaScript on the page, including injected scripts. Use `HttpOnly`
cookies (set by the server, invisible to JavaScript) for authentication tokens.

---

### TypeScript

**What it is:** TypeScript is JavaScript with a type system added on top. A type system
means you declare what kind of value a variable holds — a number, a string, a User
object — and the TypeScript compiler (a program that checks your code before it runs)
catches mistakes at development time rather than at runtime in front of users. TypeScript
is a superset of JavaScript — every valid JavaScript file is valid TypeScript.

**When to use it:** Every professional JavaScript project. The upfront cost of writing
types pays back many times over in bugs caught early, code that is self-documenting,
and safe refactoring at scale.

#### Basics

**Installing and configuring:** `npm install --save-dev typescript` adds the compiler.
`npx tsc --init` generates a `tsconfig.json`. The most important settings: `"strict":
true` (enables all strict checks), `"target": "ES2020"` (which JavaScript version to
compile to), `"module": "ESNext"` (module system), `"outDir": "./dist"` (where compiled
files go). Always enable `strict: true` from day one — retrofitting it later is painful.

**Basic types:** `string`, `number`, `boolean`, `null`, `undefined`, `any`, `unknown`,
`void`, `never`. Declare with a colon after the variable name: `const name: string =
'Alice'`. TypeScript infers types when it can — `const count = 0` is automatically
typed as `number`. Only write explicit types when inference does not provide enough
information.

**Interfaces and type aliases:** Both define the shape of an object.
`interface User { id: number; name: string; email?: string }` — the `?` makes a
property optional. `type Point = { x: number; y: number }`. Use `interface` for object
shapes that may be extended; `type` for unions, intersections, and aliases.
`type Status = 'active' | 'inactive' | 'pending'` is a union type — the variable can
only hold one of those three string values.

**Arrays and tuples:** `string[]` or `Array<string>` — an array of strings. `[string,
number]` is a tuple — exactly two elements, first a string, second a number. Tuples
are useful for fixed-size heterogeneous collections like coordinate pairs.

**Functions:** Type the parameters and the return value: `function add(a: number, b:
number): number { return a + b }`. Arrow function: `const add = (a: number, b: number):
number => a + b`. If a function returns nothing, the return type is `void`. If a
function never returns (throws always or loops forever), the return type is `never`.

**Type assertions:** `value as string` tells TypeScript "trust me, I know this is a
string." Use sparingly — it overrides the type checker. Never use `as any` — that
turns off type checking entirely. If you find yourself writing `as SomeType` often,
it is a sign the types are not modeled correctly.

#### Mid-level

**Generics:** Functions and types that work with multiple types without losing type
safety. `function identity<T>(value: T): T { return value }` — call with
`identity<string>('hello')` or let TypeScript infer: `identity('hello')`. Generics are
everywhere in TypeScript: `Array<T>`, `Promise<T>`, `Map<K, V>`. When you see `<T>`,
read it as "for any type T." The constraint syntax `<T extends object>` means T must be
an object type.

**Union and intersection types:** Union (`|`) means "this OR that": `string | number`.
Intersection (`&`) means "this AND that": `Person & Employee` combines all properties
of both. Use union types for values that can be one of several shapes. Use intersection
for composing types.

**Type guards and narrowing:** TypeScript narrows types inside conditionals. `if (typeof
value === 'string') { /* TypeScript knows value is string here */ }`. `instanceof`
narrowing: `if (error instanceof ValidationError) { ... }`. Custom type guard: `function
isUser(value: unknown): value is User { return typeof value === 'object' && value !==
null && 'id' in value }`.

**Utility types:** TypeScript provides built-in type transformers. `Partial<User>` makes
all properties optional — useful for update payloads. `Required<User>` makes all
required. `Readonly<User>` prevents mutation. `Pick<User, 'id' | 'name'>` selects
properties. `Omit<User, 'password'>` excludes properties. `Record<string, number>`
creates an object type with string keys and number values. These save enormous amounts
of repetitive type writing.

**Enums vs const objects:** `enum Direction { Up, Down, Left, Right }` creates a named
set of constants. However, TypeScript enums compile to unexpected JavaScript and have
edge cases. Prefer `const Direction = { Up: 'UP', Down: 'DOWN' } as const` combined
with `type Direction = typeof Direction[keyof typeof Direction]`. This is a common
pattern in professional TypeScript code.

**Declaration files and `@types`:** When you use a JavaScript library that has no
TypeScript types, install types from DefinitelyTyped: `npm install --save-dev @types/
lodash`. When no types exist, create a minimal `.d.ts` file: `declare module
'some-library' { export function doThing(): void }`. Never leave an untyped library as
`any` — write minimal types even if they are incomplete.

**Zod for runtime validation:** TypeScript checks types at compile time. When data
arrives from an API, a form, or a file at runtime, TypeScript cannot check it —
the data is just `unknown`. Zod validates the shape of unknown data and produces a
TypeScript-typed result. `const UserSchema = z.object({ id: z.number(), name: z.string()
})`. `const user = UserSchema.parse(rawData)` — throws if invalid. `UserSchema.
safeParse(rawData)` returns `{ success: boolean, data, error }` — use this when the
data might legitimately be invalid.

#### Senior

**Conditional types:** `type IsArray<T> = T extends any[] ? true : false`. Types that
depend on other types — the foundation of TypeScript's advanced type system.
`NonNullable<T>` is defined as `T extends null | undefined ? never : T`. `ReturnType<F>`
extracts the return type of a function. `Parameters<F>` extracts parameter types.
Conditional types let you write type-level logic.

**Mapped types:** Transform existing types by iterating over their keys. `type
Optional<T> = { [K in keyof T]?: T[K] }` makes every property optional (same as
`Partial`). `type Stringify<T> = { [K in keyof T]: string }` converts every value to
string. Adding modifiers: `+readonly` makes properties readonly, `-?` removes optional.

**Template literal types:** String manipulation at the type level. `type EventName<T
extends string> = `on${Capitalize<T>}`` — given `'click'`, produces `'onClick'`.
Used to derive event handler names from event names automatically.

**The `satisfies` operator:** `const config = { port: 3000, host: 'localhost' } satisfies
Config` — validates that the value matches the type without widening it. Unlike type
assertion, `satisfies` preserves the literal types of the values while still checking
the shape.

**`strict: true` is not enough:** Enable additional checks: `"noUncheckedIndexedAccess":
true` makes array indexing return `T | undefined` instead of `T` — correct, because
`arr[99]` might be undefined. `"exactOptionalPropertyTypes": true` distinguishes between
a missing property and a property set to `undefined`. These extra checks catch real bugs
that `strict` alone misses.

**TypeScript at scale:** In a large monorepo with TypeScript, incremental compilation
(`"incremental": true` in tsconfig) caches the last compilation and only recompiles
what changed. Project references (`"references"` in tsconfig) split a large project
into sub-projects that TypeScript can type-check independently. Without these, type-
checking a 500,000-line project takes minutes. With them, it takes seconds for the
affected parts. The `tsconfig.paths` setting creates import aliases — `@/components/
Button` instead of `../../components/Button` — always configure this.

---

### JSX and TSX

**What they are:** JSX (JavaScript XML) is a syntax extension that lets you write
HTML-like code directly inside JavaScript files. `return <div className="card"><h1>
Hello</h1></div>` looks like HTML but is actually JavaScript. TSX is the same syntax
in TypeScript files. They are not valid JavaScript on their own — a build tool (Vite,
Next.js compiler, Babel) transforms them into regular `React.createElement()` calls
before the browser runs them.

**When to use them:** JSX in `.jsx` files for React projects using JavaScript. TSX in
`.tsx` files for React projects using TypeScript. Always use `.tsx` for new projects —
never build production applications without TypeScript.

#### Basics

**The mental model:** JSX is not HTML. It looks similar but has important differences.
Every element must be closed — `<br />` not `<br>`. Attributes use camelCase — `onClick`
not `onclick`, `className` not `class` (because `class` is a reserved word in
JavaScript), `htmlFor` not `for`. Styles are objects not strings: `style={{ color:
'red', fontSize: '16px' }}`.

**Expressions inside JSX:** Anything inside `{}` is evaluated as JavaScript.
`<p>{user.name}</p>` renders the name. `<p>{2 + 2}</p>` renders `4`. `<p>{isLoggedIn ?
'Welcome' : 'Please log in'}</p>` conditionally renders text. You cannot use
`if` statements directly inside JSX — use ternary `? :` for conditionals or extract
logic into a variable above the return statement.

**Rendering lists:** `{items.map(item => <li key={item.id}>{item.name}</li>)}`. The
`key` prop is mandatory — it must be a stable, unique identifier for each item. React
uses it to efficiently update the list when items change. Never use the array index as
a key if the list can be reordered or filtered — it causes React to confuse items.

**Conditional rendering:** `{isLoading && <Spinner />}` — renders `<Spinner />` only
if `isLoading` is true. Short-circuit evaluation: if the left side is false, the right
side is not rendered. Warning: `{count && <p>{count}</p>}` will render `0` if count is
zero, because `0` is falsy but still a renderable value. Use `{count > 0 && <p>
{count}</p>}` to be safe.

**Fragments:** A component must return a single root element. To return multiple
elements without adding a wrapping `<div>`, use a Fragment: `<>...</>` or `<React.
Fragment>...</React.Fragment>`. Fragments do not create a DOM element — they are
invisible in the rendered output.

#### Mid-level

**Component composition:** Small, focused components that compose together. A `<Button>`
knows how to render a button. A `<UserCard>` renders a card using `<Button>` and other
primitives. Never build one giant component — always ask "what is this component's
single responsibility?"

**Props typing in TSX:** Define props with an interface: `interface ButtonProps { label:
string; onClick: () => void; disabled?: boolean }`. Use it: `function Button({ label,
onClick, disabled = false }: ButtonProps) { ... }`. The default value `disabled = false`
uses destructuring defaults. `React.FC<Props>` is a type you may see — it is no longer
recommended because it has subtle issues with generics and `displayName`. Just type the
function directly.

**The `children` prop:** Components that wrap other components accept `children`:
`interface CardProps { children: React.ReactNode }`. `React.ReactNode` accepts anything
renderable — JSX, strings, numbers, arrays, null. Use `children` for layout components
(`<Modal>`, `<Card>`, `<Container>`) that wrap arbitrary content.

**Event handler typing:** `onClick: (event: React.MouseEvent<HTMLButtonElement>) => void`.
`onChange: (event: React.ChangeEvent<HTMLInputElement>) => void`. TypeScript knows the
exact event type for each HTML element — use these types rather than the generic `Event`.

**Spreading props:** `<Component {...props} />` passes all props through. Useful for
wrapper components that forward props to an underlying element. `<button {...rest}
className={cn(defaultClass, rest.className)}>` — spread with overrides. Be careful
with prop spreading on DOM elements — passing unknown attributes causes React warnings.

#### Senior

**Render optimization:** A component re-renders every time its state or props change.
This is usually fine — React's reconciler is fast. Performance problems arise when
expensive calculations run on every render, or when too many components re-render for
a single state change. `React.memo(Component)` memoizes the rendered output and skips
re-render if props have not changed (by reference). `useMemo(() => expensiveCalc,
[dep])` memoizes a computed value. `useCallback(() => handler, [dep])` memoizes a
function. Profile before memoizing — the cache has a cost too.

**JSX transform vs createElement:** Old React required `import React from 'react'` in
every JSX file because JSX compiled to `React.createElement(...)`. The new JSX transform
(React 17+) automatically imports what is needed — no more manual import. Configure
with `"jsx": "react-jsx"` in tsconfig or the Babel preset. Understanding this explains
why removing the React import breaks old projects.

**Server Components JSX:** In Next.js App Router, JSX in Server Components runs on the
server — it can `await` data, access databases, and read environment variables directly.
The JSX output (HTML) is sent to the client. Client Components add `'use client'` and
use browser APIs. The boundary between them is the most important architectural decision
in a Next.js application.

---

### Node.js

**What it is:** Node.js is a runtime that lets JavaScript and TypeScript run outside the
browser — on a server, on your laptop, in a CI pipeline, on a Raspberry Pi. It is built
on Chrome's V8 JavaScript engine. This means the same language you use for frontend UIs
can be used for backend servers, command-line tools, scripts, and anything else.

**When to use it:** Node.js is the standard choice for JavaScript/TypeScript backends,
REST APIs, GraphQL servers, WebSocket servers, CLI tools, and build tooling. It excels
at I/O-bound workloads — handling many simultaneous network connections efficiently.

#### Basics

**Running files:** `node filename.js` executes a file. `node --watch filename.js`
restarts on file changes (development mode). `npx tsx filename.ts` runs a TypeScript
file directly without pre-compiling. For production TypeScript, compile first with `tsc`
then run the compiled JavaScript.

**`package.json`:** The project manifest. Created with `npm init -y`. Key fields:
`name` (project name), `version` (semantic version), `scripts` (command shortcuts —
`npm run dev` runs the `dev` script), `dependencies` (packages needed to run),
`devDependencies` (packages needed only during development: testing tools, TypeScript,
linters). Always explain every field when creating one from scratch.

**npm / pnpm / yarn:** Package managers that install libraries. `npm install express`
downloads Express and adds it to `dependencies`. `npm install --save-dev typescript`
adds to `devDependencies`. `pnpm` is a faster alternative that uses a content-addressable
store — packages are stored once and hard-linked, saving disk space dramatically in
monorepos. Use `pnpm` for new projects. `npm install` and `pnpm install` are
interchangeable commands — the difference is internal.

**`node_modules/`:** The folder where installed packages live — often gigabytes in size.
Always add it to `.gitignore`. Never commit it. Anyone who clones the repo runs
`npm install` (or `pnpm install`) to recreate it from `package.json` and the lockfile.

**Environment variables:** Accessed via `process.env.VARIABLE_NAME`. Always validate at
startup: if `!process.env.DATABASE_URL` throw a clear error explaining what is missing.
A startup crash with a good message is infinitely better than a cryptic failure in
production three hours later. Load from `.env` files using the `dotenv` package or
Node.js 20's built-in `--env-file` flag.

**The module system:** Node.js has two module systems. CommonJS (older): `const express
= require('express')` and `module.exports = { myFunction }`. ES Modules (modern):
`import express from 'express'` and `export const myFunction = ...`. Use ES Modules for
all new projects. Set `"type": "module"` in `package.json` to make `.js` files use ESM.

#### Mid-level

**The event loop in depth:** Node.js is single-threaded. Its power comes from non-
blocking I/O — instead of waiting idle for a database query to return, Node.js starts
the query, registers a callback, and handles other requests in the meantime. The event
loop has phases: timers (`setTimeout`, `setInterval`), pending callbacks (I/O callbacks
from the previous loop), poll (retrieve new I/O events), check (`setImmediate`), close
callbacks. Microtasks (resolved Promises, `process.nextTick`) run between every phase.
Understanding this order prevents subtle ordering bugs in async code.

**Streams:** Node.js streams process data incrementally without loading everything into
memory. A readable stream emits chunks. A writable stream receives chunks. A transform
stream does both. Reading a 10GB file with `fs.readFileSync` loads 10GB into RAM —
reading it with `fs.createReadStream` processes it chunk by chunk. Always use streams
for large files, HTTP request/response bodies, and data pipelines.

**Worker threads and child processes:** `worker_threads` runs JavaScript in a separate
thread — useful for CPU-intensive work that would block the event loop. `child_process.
exec` and `child_process.spawn` run shell commands or other programs. `cluster` module
runs multiple Node.js processes that share a server port — a classic way to use all
CPU cores before containers made this less common.

**HTTP servers:** The built-in `http` module creates raw HTTP servers. In practice,
use Express, Fastify, or Hono. Express is the most used; Fastify is faster and has
built-in TypeScript support and schema validation; Hono is the newest and designed for
edge environments. Explain which is chosen and why when starting a backend project.

**Error handling at the process level:** Unhandled Promise rejections crash Node.js
in production (since Node.js 15). Handle them: `process.on('unhandledRejection',
(reason) => { logger.error(reason); process.exit(1); })`. `process.on('uncaughtException',
(error) => { logger.error(error); process.exit(1); })` catches synchronous crashes.
Always log before exiting so the crash is visible in production.

#### Senior

**Memory profiling and leak detection:** Node.js's V8 heap grows when objects are
allocated but not garbage collected. Common leak patterns: event emitters with listeners
added in a loop but never removed, caches (`Map`, `Set`, plain objects) that grow
without eviction, closures capturing large data, and `global` variables. Detect leaks
with `node --inspect`, then attach Chrome DevTools and take heap snapshots. A heap that
grows monotonically across requests is leaking. `--max-old-space-size=512` limits heap
to 512MB — useful to detect leaks fast in testing.

**Performance profiling:** `node --prof` generates a V8 profiling log. `node --prof-
process isolate-*.log` processes it into a human-readable report showing which functions
consume CPU. `clinic.js` is the modern alternative — `clinic doctor` automatically
diagnoses performance issues. Never optimize without profiling first — the bottleneck
is almost never where you expect.

**Clustering and PM2:** A single Node.js process uses one CPU core. `cluster` module
forks worker processes that all share the server port — the OS load-balances between
them. PM2 is the production process manager: `pm2 start app.js -i max` starts one
worker per CPU core. PM2 handles restarts on crash, log aggregation, and cluster
management. In Kubernetes, run one process per container and let Kubernetes handle
scaling.

**Graceful shutdown:** A production Node.js server must handle `SIGTERM` (the signal
Kubernetes sends before killing a container). Listen: `process.on('SIGTERM', async ()
=> { server.close(); await db.end(); process.exit(0) })`. Close the HTTP server first
(stop accepting new requests), drain in-flight requests, close database connections,
then exit. Without graceful shutdown, in-flight database writes are cut mid-transaction
when a container is replaced.

---

### React

**What it is:** React is a JavaScript library (made by Meta/Facebook) for building user
interfaces. The core idea: your UI is a function of your data — `UI = f(state)`. When
data changes, React automatically re-renders the affected parts of the UI. You describe
what the UI should look like for a given state; React figures out the minimal DOM
changes needed to make it so.

**When to use it:** React is the most widely used frontend library. Use it for any web
application with real interactivity — not just displaying data but responding to user
actions, managing complex state, or re-rendering parts of the page dynamically.

#### Basics

**Components:** The building block of React UIs. A component is a function that returns
JSX. Name with a capital letter — React distinguishes components from HTML tags this
way. `function Button({ label, onClick }) { return <button onClick={onClick}>{label}
</button> }`. Use it: `<Button label="Save" onClick={handleSave} />`.

**State with `useState`:** State is data that, when it changes, causes the component to
re-render with the new value. `const [count, setCount] = useState(0)` — `count` is the
current value (starts at 0), `setCount` is the function to update it. Call `setCount(
count + 1)` to increment. Never mutate state directly (`count++` does nothing) — always
use the setter. State updates are asynchronous — the new value is available on the next
render, not immediately after calling the setter.

**Props:** Data passed from a parent component to a child. `<UserCard name="Alice"
age={30} />` — `name` is a string prop, `age` is a number (note: non-string values go
in `{}`). Props are read-only inside the child — never modify them. The flow is always
downward: parent to child.

**Event handlers:** Functions called when the user interacts. `<button onClick={() =>
setCount(count + 1)}>Increment</button>`. The handler is an arrow function or a named
function — never call it directly: `onClick={handleClick}` not `onClick={handleClick()}`.
Calling it directly executes it on every render.

**Rendering and the virtual DOM:** When state changes, React calls your component
function again with the new state, producing new JSX. React compares the new JSX tree
with the previous one (the virtual DOM diff) and updates only the parts of the real
DOM that changed. This is why React is efficient — it never re-renders the entire page.

**Conditional and list rendering:** See JSX section. The patterns are the same — they
are JavaScript, not React-specific.

#### Mid-level

**`useEffect`:** Runs a side effect (fetching data, setting up a subscription, reading
from localStorage) after the component renders. `useEffect(() => { fetchData(); },
[userId])` — runs after every render where `userId` changed. `[]` runs only once when
the component first mounts. No second argument runs after every render (rarely what
you want). Return a cleanup function to run when the component unmounts: `return () =>
subscription.unsubscribe()`. Missing cleanup causes memory leaks and bugs with stale
subscriptions. Explain the dependency array every single time `useEffect` appears.

**Lifting state up:** When two sibling components need to share state, move the state
to their common parent and pass it down as props. This is "lifting state up." It is
the core pattern for sharing state between components without a global store.

**Controlled vs uncontrolled inputs:** A controlled input stores its value in state:
`<input value={value} onChange={e => setValue(e.target.value)} />`. An uncontrolled
input manages its own state internally and is accessed via a ref: `const ref = useRef();
<input ref={ref} />`. Use controlled inputs — they are predictable, validate on every
keystroke, and integrate with form libraries.

**Context:** A way to pass data through the component tree without manually passing
props at every level. Create: `const ThemeContext = createContext('light')`. Provide:
`<ThemeContext.Provider value="dark"><App /></ThemeContext.Provider>`. Consume: `const
theme = useContext(ThemeContext)`. Use for truly global data: current user, theme,
language. Do not use for data that only a subtree needs — that is what props and
component composition are for.

**Custom hooks:** A function that starts with `use` and calls other hooks. Extracts
stateful logic into a reusable function. `function useLocalStorage(key, initialValue)
{ const [value, setValue] = useState(...); ... return [value, setValue] }`. The key
insight: custom hooks are the primary mechanism for sharing stateful logic between
components — not inheritance, not mixins, just functions.

**Forms with react-hook-form:** Building forms with only `useState` and `onChange` is
tedious and has performance problems (every keystroke re-renders). `react-hook-form`
registers inputs, handles validation, and only re-renders when needed. Pair with Zod
for schema validation. This is the production standard for forms in React.

#### Senior

**Reconciliation and the key prop:** React's diffing algorithm assumes elements at the
same position in the tree represent the same component across renders. Changing the
`key` prop forces React to unmount and remount a component — useful for resetting
component state. Putting the `key` in the wrong place or using unstable keys (array
indexes) causes React to destroy and recreate the wrong components.

**Concurrent features:** React 18 introduced concurrent rendering — React can start
rendering, pause if something more important comes in, and resume later. `useTransition`
marks state updates as non-urgent: `startTransition(() => setSearchResults(results))` —
the UI stays responsive while the expensive update processes. `useDeferredValue`
defers a value to a lower priority render. `Suspense` shows a fallback while async
operations (data fetching, code splitting) are pending.

**State management at scale:** The choice of state management is architectural. Local
state (`useState`) for component-specific state. Context for infrequently changing
global state (theme, current user). Zustand or Jotai for shared state that changes
frequently — they do not cause every Context consumer to re-render on every change.
Redux Toolkit for complex state with time-travel debugging requirements. React Query or
SWR for server state (data fetched from APIs) — they handle caching, background refresh,
stale-while-revalidate, and error states automatically.

**Server state vs client state:** These are fundamentally different. Server state lives
on the server — your job is to sync a local cache of it. Client state lives entirely in
the browser — UI state like "is this modal open." Managing them the same way (putting
API data in Redux) is an antipattern. Use React Query/TanStack Query for server state;
it handles the caching, deduplication, background refetching, and optimistic updates
that are otherwise painful to implement manually.

---

### Next.js

**What it is:** Next.js is a React framework that adds server-side rendering, file-based
routing, API routes, image optimization, and production performance features. It lets
you build the frontend and backend of a complete web application in a single project,
using a single language (TypeScript/JavaScript).

**When to use it:** Default choice for any new React web application, especially when
SEO, fast initial page loads, or a backend are needed.

#### Basics

**Project structure:** `app/` contains your routes (App Router). Each folder is a route
segment. `app/page.tsx` is the homepage. `app/users/page.tsx` is `/users`. `app/users/
[id]/page.tsx` is `/users/123` — the `[id]` is a dynamic segment. `app/layout.tsx`
wraps all routes with a shared layout (header, navigation). `public/` serves static
files (images, fonts). `next.config.js` configures the framework.

**Pages and navigation:** `page.tsx` exports a React component that renders when the
route is visited. `<Link href="/users">Users</Link>` navigates without a full page
reload. `useRouter()` (client component) or `redirect()` (server component) for
programmatic navigation.

**Images:** Use `<Image src="/photo.jpg" alt="desc" width={800} height={600} />` from
`next/image`, not a plain `<img>` tag. Next.js automatically resizes, optimizes, and
lazy-loads images. `priority` prop for images above the fold (visible without scrolling)
— prevents layout shift.

**Environment variables:** `.env.local` for local development secrets (never commit).
`.env` for non-secret defaults committed to the repo. Variables prefixed with
`NEXT_PUBLIC_` are available in the browser. All others are server-only. Never put
API keys or database passwords in `NEXT_PUBLIC_` — they are embedded in the JavaScript
bundle and visible to everyone.

**Metadata:** `export const metadata: Metadata = { title: 'My App', description: '...' }`
in a `page.tsx` or `layout.tsx` sets the page title and meta tags for SEO.

#### Mid-level

**Server vs Client Components:** Server Components (default) run on the server — they
can fetch data, access databases, read files, and use environment variables directly.
They send finished HTML to the browser and zero JavaScript for their own rendering.
Client Components (`'use client'` at the top) run in the browser — they can use state,
effects, event handlers, and browser APIs. Always start as a Server Component. Only add
`'use client'` when you actually need browser capabilities.

**Data fetching in Server Components:** `async function Page() { const data = await
fetch('https://api.example.com/data'); const json = await data.json(); return <div>
{json.title}</div> }`. Server Components can be `async` — the `await` pauses the
component's rendering until data is ready. No `useEffect`, no loading state — just
`await`. This is a fundamental shift from the old Pages Router pattern.

**Loading and error UI:** `loading.tsx` in a route folder shows a skeleton or spinner
automatically while the page is loading data. `error.tsx` shows an error message and
retry button when the page throws. These are special files Next.js handles automatically
— create them in every route that fetches data.

**API routes:** `app/api/users/route.ts` creates a REST endpoint at `/api/users`. Export
named functions for each HTTP method: `export async function GET(request: Request) { ...
}`, `export async function POST(request: Request) { ... }`. Parse JSON body with
`await request.json()`. Return with `Response.json({ data })` or `NextResponse.json(
{ data }, { status: 201 })`.

**Middleware:** `middleware.ts` at the project root runs before every request — before
the page renders, before API routes respond. Used for authentication (redirect to login
if no session), A/B testing, rate limiting, and locale detection. Runs on the Edge
runtime — fast, global, but limited APIs (no Node.js built-ins).

#### Senior

**The four levels of caching:** Next.js has aggressive caching at four layers. Request
memoization: duplicate `fetch` calls in the same server render are deduplicated. Data
cache: `fetch` responses are cached and reused across requests. Full route cache: entire
rendered routes are cached as static HTML. Router cache: previously visited routes are
cached in the browser. Each layer has its own invalidation mechanism. Stale data in
production is almost always a caching layer that was not invalidated correctly.

**Incremental Static Regeneration (ISR):** `fetch('...', { next: { revalidate: 60 } })`
caches the response for 60 seconds. After 60 seconds, the next request regenerates the
page in the background while still serving the cached version. This is the best of both
worlds — the speed of a static page with data that is at most N seconds stale.
`revalidatePath('/users')` and `revalidateTag('users-data')` invalidate cache entries
on demand, useful after a form submission that changes the data.

**Parallel and intercepted routes:** Parallel routes (`@slot` folders) render multiple
pages simultaneously in the same layout — used for complex dashboard layouts where a
sidebar and main content render independently. Intercepted routes (`.` prefixes) show
a modal when navigating within the app but the full page when directly accessed or
refreshed — the standard pattern for photo detail modals.

---

### NextAuth.js / Auth.js

**What it is:** NextAuth.js (rebranded as Auth.js for framework-agnostic use) is the
standard authentication library for Next.js. It handles the complete login flow —
OAuth (Google, GitHub, Discord), email magic links, credentials — without requiring
you to build session management, token rotation, and CSRF protection from scratch.

**When to use it:** Any Next.js application that needs user authentication. Avoid
building auth from scratch — security is too easy to get wrong.

#### Basics

**Authentication vs Authorization:** Authentication (AuthN) is verifying *who* you are
— "Are you Alice?" Authorization (AuthZ) is verifying *what* you can do — "Can Alice
delete this post?" NextAuth handles authentication. Authorization is your responsibility.

**Installation:** `npm install next-auth`. Create `app/api/auth/[...nextauth]/route.ts`.
The `[...nextauth]` catch-all route handles all auth endpoints: `/api/auth/signin`,
`/api/auth/signout`, `/api/auth/callback/google`, etc. Export the handler for both GET
and POST.

**Required environment variables:** `NEXTAUTH_SECRET` (a random string to encrypt
sessions — generate with `openssl rand -base64 32`), `NEXTAUTH_URL` (your app's full
URL in production), and provider-specific variables like `GOOGLE_CLIENT_ID` and
`GOOGLE_CLIENT_SECRET`. The app will silently fail to create sessions without
`NEXTAUTH_SECRET`.

**The simplest setup:** Configure a provider (Google is the most common OAuth provider
for consumer apps), wrap your `layout.tsx` with `<SessionProvider>`, and call
`signIn('google')` from a button. NextAuth handles the redirect to Google, the callback,
and the session creation.

**Checking the session on the client:** `const { data: session } = useSession()` in a
Client Component. `session` is `null` when not logged in, or an object with `user.name`,
`user.email`, `user.image`. Show/hide UI based on the session status.

#### Mid-level

**Checking the session on the server:** `const session = await getServerSession(
authOptions)` in Server Components, API routes, or Server Actions. This is the correct
way to get the session on the server — never rely on the client-supplied session for
authorization decisions.

**Database adapter:** Connect NextAuth to your database so sessions, users, and accounts
are persisted. `@auth/prisma-adapter` for Prisma, `@auth/drizzle-adapter` for Drizzle.
The adapter creates and manages four tables: `User`, `Account` (links a user to an OAuth
provider), `Session`, and `VerificationToken` (for email magic links). Explain the schema
when setting up.

**JWT vs database sessions:** JWT sessions store all session data in an encrypted cookie
— no database read per request, but cannot be invalidated remotely. Database sessions
store a session ID in a cookie and look up the rest in the database per request — can
be forcibly invalidated (useful after password changes, security incidents, or admin
banning a user). Use database sessions for any production app where security matters.

**Callbacks for customization:** The `callbacks` option in `authOptions` has four hooks.
`jwt` runs when a JWT is created/updated — add custom claims here. `session` runs when
the session is accessed — shape what is returned to the client. `signIn` runs when a
user signs in — return `false` to deny specific users. `redirect` controls where users
go after sign-in. The most commonly needed: add the user's database ID to the session
(NextAuth does not include it by default).

**Protecting routes with middleware:** `middleware.ts` at the project root checks
authentication before any page loads. Use NextAuth's exported `auth` helper as
middleware: routes that match the matcher config will require authentication. This is
more secure than checking inside the page — the redirect happens before any code runs.

#### Senior

**The OAuth flow in detail:** (1) User clicks "Sign in with Google." (2) Your server
redirects to Google's auth server with client_id, redirect_uri, scope, and a state
parameter (CSRF protection). (3) User authenticates on Google. (4) Google redirects
back to your `/api/auth/callback/google` with an authorization code. (5) Your server
exchanges the code for an access token and ID token. (6) NextAuth decodes the ID token
to get the user's profile, creates/updates the user record in your database, creates a
session, and sets the session cookie. Understanding this flow is essential for debugging
OAuth errors.

**Custom credentials provider:** For username/password login. `CredentialsProvider({
async authorize(credentials) { const user = await verifyPassword(credentials); return
user || null } })`. Return the user object to allow login, `null` to deny. Never store
plaintext passwords — hash with bcrypt (`bcryptjs`). Salt rounds: 12 is the current
recommendation (balances security and speed).

**Security hardening:** CSRF is handled automatically. Session cookies are `HttpOnly`
(invisible to JavaScript), `Secure` (HTTPS only in production), and `SameSite=Lax`.
Rotate `NEXTAUTH_SECRET` by generating a new value — existing sessions will be
invalidated. Add rate limiting to the sign-in route to prevent brute force. Monitor
failed login attempts.

---

### Vue.js

**What it is:** Vue.js is a progressive JavaScript framework for building user
interfaces. "Progressive" means you can adopt as much or as little as needed — drop
Vue into a single page of an existing site, or build a full SPA. It uses templates
(HTML with special attributes) for the view layer and reactive data for logic.

**When to use it:** Vue is an excellent choice for its gentle learning curve, clean
template syntax, and strong Composition API. Use Vue when the team prefers its style
over React, for progressive enhancement of existing server-rendered pages, or when
Nuxt.js's conventions suit the project.

#### Basics

**Single File Components (SFCs):** A `.vue` file has three sections. `<template>` is
the HTML. `<script setup>` is the JavaScript logic using the Composition API. `<style
scoped>` is CSS that only applies to this component (scoped prevents style leaking to
other components). Everything for one component in one file.

**`ref` for reactive values:** `const count = ref(0)` creates a reactive value. In the
script, access it as `count.value`. In the template, just `count` (Vue unwraps it
automatically). Changing `count.value` triggers the template to update. Think of `ref`
as a box that holds a value and notifies Vue when the value inside changes.

**`reactive` for reactive objects:** `const user = reactive({ name: 'Alice', age: 30 })`.
Access properties directly: `user.name` (no `.value`). Warning: destructuring a
reactive object loses reactivity — `const { name } = user` creates a plain non-reactive
string. Use `toRefs(user)` to destructure while keeping reactivity.

**`computed` for derived values:** `const fullName = computed(() => `${firstName.value}
${lastName.value}`)`. A computed value automatically recalculates when its dependencies
change and caches the result. Use computed instead of recalculating in the template —
templates should be simple.

**Directives:** Special attributes that add dynamic behavior. `v-if="condition"` renders
the element only if true. `v-else` and `v-else-if` for branches. `v-for="item in items"
:key="item.id"` renders a list. `v-bind:href="url"` or `:href="url"` binds a JavaScript
value to an attribute. `v-on:click="handler"` or `@click="handler"` attaches an event
listener. `v-model="value"` is two-way binding on form inputs — equivalent to
`:value="value" @input="value = $event.target.value"`.

**Events between components:** A child emits an event with `const emit = defineEmits(
['update']); emit('update', newValue)`. The parent listens: `<Child @update="handleUpdate"
/>`. This is how data flows upward — props down, events up.

#### Mid-level

**Watchers:** `watch(source, callback)` runs a callback when a reactive value changes.
Use for side effects on state changes (fetching when a filter changes, validating when
a field changes). `watchEffect(() => { ... })` runs immediately and re-runs whenever
any reactive value accessed inside changes. The difference: `watch` is explicit about
what it watches; `watchEffect` tracks dependencies automatically.

**Lifecycle hooks:** `onMounted(() => { ... })` runs after the component is inserted
into the DOM — use for data fetching. `onUnmounted(() => { ... })` runs when the
component is removed — use for cleanup (removing event listeners, cancelling requests).
`onUpdated` runs after reactive data causes a DOM update. Never fetch data in the
component root — always in `onMounted`.

**Props and `defineProps`:** `const props = defineProps<{ title: string; count?: number
}>()`. TypeScript-based prop declaration — clean, type-safe, no boilerplate.
`props.title` accesses the value. Props are readonly — never mutate them.

**Provide / Inject:** Deep prop passing alternative. A parent `provide('theme', theme)`.
Any descendant `const theme = inject('theme')` receives it without the intermediate
components knowing about it. Use for truly global data (theme, user, locale) — not for
data that only nearby components need.

**Composables:** Vue's equivalent of React custom hooks. A function (by convention named
`use...`) that uses the Composition API and returns reactive state and methods. `function
useMousePosition() { const x = ref(0); const y = ref(0); onMounted(() => { ... });
return { x, y } }`. Share stateful logic across components without mixins.

**Nuxt.js:** The full-stack Vue framework. File-based routing, SSR, server routes, auto-
imports (no explicit `import` statements for components and composables), and deployment
adapters for every platform. Use Nuxt for any production Vue application.

#### Senior

**Reactivity internals:** Vue's reactivity uses JavaScript `Proxy` to intercept property
access and mutation. When a computed value or template accesses a reactive property, Vue
records the dependency. When the property changes, Vue re-runs all dependents. This is
why mutating a nested object property works with `reactive` but not with plain objects.
Understanding the proxy system explains why certain patterns break reactivity.

**Performance:** `v-memo="[dep1, dep2]"` memoizes a template subtree and skips
re-rendering when the listed dependencies have not changed — Vue's equivalent of
`React.memo`. `v-once` renders the element once and never updates it. `shallowRef` and
`shallowReactive` create shallow reactive wrappers — only top-level properties are
reactive, not deeply nested ones. Use for large objects where deep reactivity is
unnecessary.

**Pinia (state management):** The current standard for global state in Vue 3 (Vuex is
legacy). Define a store with `defineStore('users', () => { const users = ref([]); const
fetchUsers = async () => { ... }; return { users, fetchUsers } })`. Stores are composable
— one store can use another. Pinia integrates with Vue DevTools for time-travel
debugging. Separate stores by domain, not by component.

---

### Angular

**What it is:** Angular is a complete, opinionated frontend framework made by Google.
Unlike React (a library) or Vue (a progressive framework), Angular includes everything:
routing, form handling, HTTP client, dependency injection, testing utilities, and a
build toolchain. It uses TypeScript exclusively.

**When to use it:** Large enterprise applications where consistency matters more than
flexibility, teams with Angular expertise, applications with complex forms and data
grids, and organizations standardized on the Angular ecosystem.

#### Basics

**Generating a project:** `ng new my-app` creates a new Angular project with routing
and TypeScript configured. `ng serve` starts the dev server. `ng generate component
my-component` creates a component with all required files. Use the Angular CLI for all
code generation — it ensures file structure, naming conventions, and module registration
are correct.

**Components:** The basic building block. `@Component({ selector: 'app-button', template:
`<button>{{label}}</button>`, styleUrls: ['./button.component.scss'] })` defines a
component. The `selector` is the HTML tag used to render it: `<app-button />`. Inputs
(props): `@Input() label = 'Click me'`. Outputs (events): `@Output() clicked = new
EventEmitter()`. Emit with: `this.clicked.emit(data)`.

**Modules (NgModule) vs Standalone Components:** NgModules group components, directives,
and services. Every component used to require registration in a module's `declarations`
array. Standalone components (`standalone: true` in the decorator) do not require a
module — they are self-contained. All new Angular 17+ code should use standalone
components. Modules still exist in older codebases; understand both.

**Templates:** Angular templates are HTML with Angular-specific syntax. `{{ expression }}`
interpolates a value. `[property]="expression"` binds a property. `(event)="handler()"`
binds an event. `[(ngModel)]="value"` is two-way binding (requires `FormsModule`).
`*ngIf="condition"` (or `@if` in Angular 17+) conditionally renders. `*ngFor="let item
of items"` (or `@for`) renders a list.

**Services:** Classes that hold business logic and data fetching, injected into
components. `@Injectable({ providedIn: 'root' })` makes a service available everywhere.
`constructor(private userService: UserService) {}` injects it into a component.
Services are singletons when `providedIn: 'root'` — the same instance is shared.

**`HttpClient`:** Angular's HTTP service. `this.http.get<User[]>('/api/users')` returns
an Observable. `this.http.post<User>('/api/users', newUser)` creates. Always subscribe
to execute: `this.http.get('/api/users').subscribe(users => this.users = users)`. Unsubscribe
in `ngOnDestroy` to prevent memory leaks — or use the `async` pipe in templates which
unsubscribes automatically.

#### Mid-level

**RxJS Observables:** Angular is built on RxJS (Reactive Extensions for JavaScript) — a
library for composing asynchronous event streams. An `Observable` emits values over
time. `subscribe(value => ...)` starts listening. Key operators: `map` transforms each
value, `filter` skips values, `switchMap` cancels the previous inner observable when a
new outer value arrives (correct for search), `combineLatest` combines multiple streams.
RxJS is powerful but has a steep learning curve — explain every operator used.

**Signals (Angular 17+):** A simpler, synchronous reactive primitive replacing much of
the RxJS complexity for component state. `const count = signal(0)` creates a signal.
`count.set(1)` updates it. `count.update(c => c + 1)` updates based on current value.
`computed(() => count() * 2)` creates a derived signal. `effect(() => { console.log(
count()) })` runs a side effect when the signal changes. Signals integrate with Angular's
change detection without Zone.js overhead.

**Change detection:** Angular tracks when to re-render components using Zone.js (monkey-
patches async browser APIs to detect changes) or signals. `ChangeDetectionStrategy.
OnPush` makes a component only re-render when its input references change or an event
fires inside it — significantly improves performance for lists and data-heavy views.
Apply `OnPush` to every component by default in new projects.

**Guards and interceptors:** Route guards (`CanActivate`) block navigation to protected
routes — check authentication here. HTTP interceptors (`HttpInterceptor`) intercept all
HTTP requests and responses — add Authorization headers, handle 401 errors globally, log
request timing. Both are powerful cross-cutting concerns.

**Reactive Forms:** `FormGroup` contains `FormControl` instances. `new FormControl('',
[Validators.required, Validators.email])` creates a validated control. `form.get(
'email')?.errors` accesses validation errors. Template-driven forms (`ngModel`) are
simpler but harder to test. Reactive forms are explicit, testable, and the right choice
for complex forms.

#### Senior

**Dependency injection deep dive:** Angular's DI system creates and manages class
instances. The injector hierarchy: root injector → module injectors → component
injectors. `providedIn: 'root'` creates a singleton shared by the whole app.
`providers: [MyService]` in a component creates a new instance for that component's
subtree — useful for isolating state to a feature. Understanding the injector hierarchy
is essential for debugging "wrong instance" bugs.

**Micro-frontend integration with Module Federation:** Angular applications can be split
into separately deployed micro-frontends using Webpack 5 Module Federation. One shell
app dynamically loads feature modules from separate deployments. Each feature team
deploys independently. The `@angular-architects/module-federation` library handles the
configuration. This is the enterprise-scale solution for teams that cannot coordinate
deployments.

**Performance at scale:** Angular's build produces highly optimized bundles with tree-
shaking (dead code elimination) and code splitting. Lazy-load feature modules with
`loadComponent` or `loadChildren` in route definitions — the browser downloads the code
only when the user navigates to that route. Preloading strategies (`PreloadAllModules`,
`QuicklinkStrategy`) load lazy routes in the background after the initial load.

---

### NestJS

**What it is:** NestJS is a Node.js backend framework written in TypeScript, heavily
inspired by Angular's architecture. It uses the same concepts — modules, controllers,
services, decorators, dependency injection — to bring structure and convention to
Node.js backends that would otherwise use a flat Express project.

**When to use it:** Complex Node.js backends where consistent structure matters, teams
that know Angular (same mental model), large APIs with many endpoints, and projects
where long-term maintainability outweighs the verbosity cost.

#### Basics

**Project structure:** `src/app.module.ts` is the root module. `src/main.ts` bootstraps
the application. Feature folders group related files: `users/users.module.ts`,
`users/users.controller.ts`, `users/users.service.ts`, `users/users.entity.ts`.
Generate everything with the CLI: `nest generate module users`, `nest generate controller
users`, `nest generate service users`.

**Controllers:** Handle incoming HTTP requests. `@Controller('users')` sets the route
prefix. `@Get()` handles GET `/users`. `@Get(':id')` handles GET `/users/123`. `@Post()`
handles POST. `@Body()` extracts the request body. `@Param('id')` extracts a route
parameter. `@Query('filter')` extracts a query string parameter. Controllers should be
thin — call a service method and return the result.

**Services:** Hold business logic. `@Injectable()` marks a class as injectable. The
controller receives the service via constructor injection: `constructor(private readonly
usersService: UsersService) {}`. Services call the database, apply business rules, and
return results. Services can inject other services.

**DTOs (Data Transfer Objects):** Plain TypeScript classes that define the shape of
request bodies. `class CreateUserDto { @IsEmail() email: string; @MinLength(8) password:
string }`. Decorate with `class-validator` decorators. Apply `ValidationPipe` globally
in `main.ts` to automatically validate all incoming request bodies. If validation fails,
NestJS returns a 400 error automatically.

**Pipes:** Transform or validate data before it reaches the controller method. Built-in
pipes: `ValidationPipe` (validates DTOs), `ParseIntPipe` (converts `'123'` string to
number `123`), `ParseUUIDPipe` (validates UUID format). Apply globally, per controller,
or per method parameter.

#### Mid-level

**Modules and feature organization:** `@Module({ imports: [], controllers: [], providers:
[], exports: [] })`. `imports` brings in other modules. `providers` registers services
available in this module. `exports` makes providers available to modules that import
this one. Feature modules encapsulate a domain concern — `UsersModule`, `AuthModule`,
`OrdersModule`. The root `AppModule` imports all feature modules.

**Guards for authentication and authorization:** `@Injectable() class AuthGuard implements
CanActivate { canActivate(context: ExecutionContext): boolean { ... } }`. Return `true`
to allow, `false` (or throw `UnauthorizedException`) to deny. Apply with `@UseGuards(
AuthGuard)` on a controller or method. A common pattern: `JwtAuthGuard` validates the
JWT token, then `RolesGuard` checks if the user has the required role.

**Interceptors:** Wrap the entire request-response lifecycle. Use for: logging request
duration, transforming response shapes globally, caching responses, handling timeouts.
`@Injectable() class LoggingInterceptor implements NestInterceptor { intercept(context,
next) { const start = Date.now(); return next.handle().pipe(tap(() => { console.log(
Date.now() - start + 'ms') })) } }`.

**Exception filters:** Catch exceptions and format error responses. `@Catch(HttpException)
class HttpExceptionFilter implements ExceptionFilter { catch(exception, host) { ... } }`.
Apply globally to ensure all errors return a consistent response shape. Never let raw
database errors reach the client — catch and rethrow as HTTP exceptions with appropriate
status codes.

**TypeORM / Prisma integration:** `TypeOrmModule.forRoot({ type: 'postgres', ... })`
connects to Postgres. `TypeOrmModule.forFeature([UserEntity])` makes the repository
available in a feature module. `@InjectRepository(UserEntity)` injects the repository.
Alternatively, use Prisma — `PrismaService` wraps the Prisma client as a NestJS service.
Prisma is increasingly preferred for its type safety and developer experience.

#### Senior

**Clean Architecture inside NestJS:** Controllers are infrastructure — they translate
HTTP to application commands. Services are use cases — they orchestrate domain logic
but should not contain it. Domain entities (plain TypeScript classes, no NestJS imports)
contain business rules. Repositories (interfaces) abstract database access — the service
depends on the interface, not the TypeORM repository directly. This makes the business
logic fully testable without HTTP or database.

**Microservices transport:** NestJS has built-in support for microservice communication
via Kafka, RabbitMQ, Redis, gRPC, and TCP. `@MessagePattern('user.created')` handles a
message. `this.client.emit('user.created', data)` publishes. The abstraction is
convenient but understand what happens underneath — message acknowledgment, retries,
dead-letter queues — the NestJS layer does not handle these automatically.

---

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

### Python

**What it is:** Python is a dynamically typed, interpreted, high-level language known for
its readable syntax and massive ecosystem. The same language serves data science (numpy,
pandas, PyTorch), web backends (Django, FastAPI), scripting, automation, and ML.

**When to use it:** Data science, machine learning, scripting, automation, rapid
prototyping, and web backends where developer productivity matters more than raw
performance.

#### Basics

**Running Python:** `python3 script.py` runs a file. `python3 -m venv .venv` creates a
virtual environment. `source .venv/bin/activate` (Unix) or `.venv\Scripts\activate`
(Windows) activates it. `pip install requests` installs a package. Always work inside a
virtual environment — never install packages globally.

**Variables and types:** Python is dynamically typed — no type declarations needed.
`name = "Alice"`, `age = 30`, `is_active = True`, `score = 3.14`. Python infers the
type. Types: `str`, `int`, `float`, `bool`, `list`, `dict`, `tuple`, `set`, `None`.

**Lists and dicts:** `names = ["Alice", "Bob", "Charlie"]`. `names.append("Dave")`.
`names[0]` is `"Alice"`. `names[-1]` is the last item. Slicing: `names[1:3]` is
`["Bob", "Charlie"]`. Dicts: `user = {"name": "Alice", "age": 30}`. `user["name"]`
is `"Alice"`. `user.get("email", "not set")` returns default if key missing.

**Functions:** `def greet(name: str) -> str: return f"Hello {name}"`. `f""` strings
(f-strings) embed expressions: `f"Hello {name.upper()}"`. Default parameters: `def
greet(name="World")`. `*args` for variable positional arguments, `**kwargs` for variable
keyword arguments.

**List comprehensions:** `doubled = [x * 2 for x in numbers]`. With condition: `evens =
[x for x in numbers if x % 2 == 0]`. Dict comprehension: `{k: v for k, v in pairs}`.
Prefer comprehensions over `map`/`filter` with lambdas for readability.

**Classes:** `class User: def __init__(self, name: str, age: int): self.name = name;
self.age = age`. `__str__` controls string representation. `__eq__` controls equality.
`@property` creates a getter. `@staticmethod` and `@classmethod` for methods that
do not need `self`.

#### Mid-level

**Type hints:** Add types to function signatures: `def get_user(user_id: int) -> User`.
For lists: `list[str]`. For optional: `str | None` or `Optional[str]`. For dicts:
`dict[str, Any]`. Run `mypy --strict` to check types. Type hints do not affect runtime
but enable tools to catch bugs before execution.

**Pydantic:** Runtime data validation. `class User(BaseModel): id: int; name: str; email:
EmailStr`. `User(**raw_dict)` validates and creates — raises `ValidationError` with clear
messages if invalid. `User.model_validate(raw_dict)` is the v2 API. Use Pydantic for
all external data: API request bodies, config files, environment variables (`pydantic-
settings`).

**Context managers:** `with open("file.txt") as f: data = f.read()` — the file is
automatically closed even if an exception occurs. `with` uses `__enter__` and `__exit__`
methods. Create your own: `@contextmanager def transaction(): yield; commit()`. Use for
database connections, file handles, locks — any resource that must be released.

**Async with `asyncio`:** `async def fetch_user(id: int) -> User: return await db.get(
id)`. `await` pauses until the coroutine completes. `asyncio.gather(fetch_user(1),
fetch_user(2))` runs concurrently. FastAPI uses `asyncio` natively — define route
handlers as `async def`. Use `httpx` for async HTTP requests.

**Decorators:** Functions that wrap other functions. `@app.route("/users")` registers a
Flask route. `@property` creates a getter. `@functools.lru_cache(maxsize=128)` memoizes.
Write your own: `def require_auth(func): def wrapper(*args, **kwargs): check_auth();
return func(*args, **kwargs); return wrapper`. Apply: `@require_auth def protected_view()`.

**Exceptions:** `try: result = risky() except ValueError as e: handle(e) except (TypeError,
KeyError): handle_others() finally: cleanup()`. Always catch specific exceptions — never
`except Exception: pass`. Create custom exceptions: `class ValidationError(Exception):
pass`. Raise: `raise ValidationError("name is required")`.

#### Senior

**The GIL (Global Interpreter Lock):** CPython (the standard Python) has a GIL — only
one thread executes Python bytecode at a time. This means Python threads do not achieve
true parallelism for CPU-bound work. For CPU-bound work: use `multiprocessing` (separate
processes, separate GIL) or `concurrent.futures.ProcessPoolExecutor`. For I/O-bound
work: threads or asyncio both work fine — the GIL is released during I/O. Python 3.13
introduces experimental free-threaded mode (no-GIL build).

**Performance profiling:** `cProfile` is the standard profiler: `python -m cProfile -s
cumulative script.py`. `py-spy` profiles a running process without modifying code.
`line_profiler` profiles line by line. NumPy and Pandas vectorized operations are 10-
100x faster than Python loops — always use them for numerical work. Cython and Numba
compile Python to C for critical sections.

**Packaging and distribution:** `pyproject.toml` is the modern project configuration
(replaces `setup.py`). Build with `hatch` or `flit`. Publish to PyPI with `twine`.
For applications (not libraries), use Docker or PyInstaller to distribute. `uv` (from
Astral) is now the fastest tool for virtual environments, dependency resolution, and
package installation — 10-100x faster than pip.

---

### PostgreSQL

**What it is:** PostgreSQL (Postgres) is a powerful, open-source relational database.
Relational means data is stored in tables (like spreadsheets) with rows and columns, and
tables relate to each other via foreign keys. Postgres is ACID-compliant — transactions
are Atomic (all or nothing), Consistent (rules are never violated), Isolated (concurrent
transactions do not interfere), and Durable (committed data survives crashes).

**When to use it:** The default database for any web application. Postgres handles
structured data, complex queries, transactions, and scales from a laptop to billions of
rows with proper indexing and architecture.

#### Basics

**Tables and rows:** A table has named, typed columns. A row is one record. `CREATE TABLE
users (id SERIAL PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, created_at
TIMESTAMPTZ DEFAULT NOW())`. `SERIAL` auto-increments. `PRIMARY KEY` uniquely identifies
rows. `NOT NULL` prevents empty values. `UNIQUE` prevents duplicates.

**CRUD operations:**
- Create: `INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com')`
- Read: `SELECT id, name, email FROM users WHERE id = 1`
- Update: `UPDATE users SET name = 'Alicia' WHERE id = 1`
- Delete: `DELETE FROM users WHERE id = 1`

Always specify columns in SELECT — never `SELECT *`. Always use a WHERE clause in UPDATE
and DELETE — without one, you modify every row.

**Joins:** Connect data from multiple tables. `SELECT u.name, o.total FROM users u INNER
JOIN orders o ON u.id = o.user_id` — returns users who have orders. `LEFT JOIN` returns
all users, with null values for columns from orders if no match. Explain the join type
every time — the wrong join silently drops or duplicates rows.

**Indexes:** Speed up queries at the cost of slower writes. `CREATE INDEX idx_users_email
ON users(email)` — makes queries filtering by email fast. The database uses an index
like a book's index — instead of scanning every row, it jumps directly to matches.
Without indexes, queries on large tables perform sequential scans — checking every row,
extremely slow.

**Transactions:** `BEGIN; UPDATE accounts SET balance = balance - 100 WHERE id = 1;
UPDATE accounts SET balance = balance + 100 WHERE id = 2; COMMIT`. If any step fails,
`ROLLBACK` undoes all changes. Transactions guarantee consistency across multiple
operations.

#### Mid-level

**Foreign keys and referential integrity:** `user_id INT NOT NULL REFERENCES users(id)
ON DELETE CASCADE`. This enforces that `user_id` must exist in the `users` table.
`ON DELETE CASCADE` automatically deletes related rows when the parent is deleted.
`ON DELETE RESTRICT` prevents deletion if children exist. Never store foreign keys
without the constraint — the database will not enforce consistency.

**`EXPLAIN ANALYZE`:** `EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'alice@example.com'`.
Shows the query execution plan, how many rows were scanned, and actual timing. Look for:
`Seq Scan` on large tables (needs an index), `Hash Join` vs `Nested Loop` (join strategy),
actual vs estimated rows (large differences indicate stale statistics — run `ANALYZE`).

**Common table expressions (CTEs):** `WITH active_users AS (SELECT * FROM users WHERE
is_active = true) SELECT * FROM active_users WHERE created_at > '2024-01-01'`. CTEs
make complex queries readable by naming intermediate results. Recursive CTEs traverse
tree structures (categories, org charts, comments with replies).

**Window functions:** `SELECT name, salary, RANK() OVER (PARTITION BY department ORDER BY
salary DESC) as rank FROM employees`. Window functions compute values across a set of
rows related to the current row without collapsing them. Uses: ranking within groups,
running totals, moving averages, finding the first/last in a group.

**JSONB columns:** `ALTER TABLE products ADD COLUMN attributes JSONB`. Store flexible,
schema-less data alongside structured columns. Query: `WHERE attributes->>'color' =
'red'`. Index with GIN: `CREATE INDEX ON products USING GIN(attributes)`. Use JSONB
when a subset of data genuinely varies per record — not as a way to avoid designing a
proper schema.

#### Senior

**Vacuuming and MVCC:** Postgres uses MVCC (Multi-Version Concurrency Control — each
transaction sees a snapshot of the data as it was when the transaction started). Deleted
and updated rows leave "dead tuples" — old versions that are no longer visible but still
take up space. `VACUUM` reclaims this space. `AUTOVACUUM` runs automatically. Transaction
ID wraparound: Postgres uses 32-bit transaction IDs — after 2 billion transactions, it
must "freeze" old rows. If autovacuum cannot keep up, the database stops accepting writes
to run emergency vacuum. Monitor `pg_stat_user_tables.n_dead_tup` and `age(datfrozenxid)`.

**Connection pooling:** Postgres creates a process per connection — expensive. A spike
to thousands of connections crashes the database. PgBouncer in transaction mode pools
connections: applications connect to PgBouncer, which maintains a small pool of actual
Postgres connections and rotates them between requests. Configure pool size: `(number of
CPU cores * 2) + number of disks`. Never connect directly from application code in
production without a pool.

**Replication:** Streaming replication sends WAL (Write-Ahead Log — the internal log of
every change) to replica servers in real time. Replicas serve read traffic, offloading
the primary. Logical replication replicates specific tables and supports cross-version
replication. Use `pg_replication_slots` carefully — a slot that is not consumed holds
WAL on disk indefinitely, potentially filling the disk.

---

### MongoDB

**What it is:** MongoDB is a document database — it stores data as JSON-like documents
in collections. Unlike relational databases, there are no tables with fixed schemas —
each document can have different fields.

**When to use it:** When data structure genuinely varies across records, during early
development when the schema is evolving rapidly, or when write throughput at massive
scale (via sharding) is required.

#### Basics

**Collections and documents:** A collection is like a table but with no enforced schema.
A document is a JSON object: `{ "_id": ObjectId("..."), "name": "Alice", "email":
"alice@example.com", "age": 30 }`. Every document has a unique `_id` field — Mongo
generates an `ObjectId` automatically, or you can provide your own.

**CRUD operations:**
- Insert: `db.users.insertOne({ name: "Alice", email: "alice@example.com" })`
- Read: `db.users.findOne({ email: "alice@example.com" })`
- Update: `db.users.updateOne({ _id: id }, { $set: { name: "Alicia" } })`
- Delete: `db.users.deleteOne({ _id: id })`

**Query operators:** `$eq`, `$ne`, `$gt`, `$lt`, `$gte`, `$lte` for comparisons.
`$in: ["active", "pending"]` matches any of the values. `$exists: true` checks if a
field is present. `$and`, `$or`, `$not` for logical combinations. Explain each operator
used — their names are not intuitive.

**Indexes:** `db.users.createIndex({ email: 1 })` creates an ascending index on email.
Without indexes, every query scans the entire collection — extremely slow at scale.
`db.users.explain("executionStats").find({ email: "..." })` shows whether an index was
used. `"COLLSCAN"` in the output means full collection scan — needs an index.

**Aggregation pipeline:** Transform and analyze documents in stages. `db.orders.aggregate(
[{ $match: { status: "completed" } }, { $group: { _id: "$userId", total: { $sum:
"$amount" } } }, { $sort: { total: -1 } }])` — filters, groups, sorts. Stages: `$match`,
`$group`, `$project`, `$sort`, `$limit`, `$lookup` (join another collection), `$unwind`
(deconstruct an array field).

#### Mid-level

**Mongoose (Node.js ODM):** `const UserSchema = new Schema({ name: { type: String,
required: true }, email: { type: String, unique: true }, createdAt: { type: Date,
default: Date.now } })`. `const User = model('User', UserSchema)`. `User.create(data)`,
`User.findById(id)`, `User.findOneAndUpdate({ email }, update, { new: true })`. Mongoose
adds schema validation, middleware hooks, and virtual properties on top of raw MongoDB.

**Schema design — embedding vs referencing:** In MongoDB, you choose between embedding
related data in the same document or referencing it with an ID. Embed when data is
always accessed together, is not too large, and does not need to be queried independently.
Reference when data is large, shared across many documents, or needs independent queries.
The wrong choice causes either deeply nested unmaintainable documents or N+1 queries.

**Transactions:** Multi-document transactions exist since MongoDB 4.0. `session.
startTransaction(); await User.create([...], { session }); await Order.create([...],
{ session }); await session.commitTransaction()`. Much heavier than single-document
operations — design your schema to minimize the need for transactions.

**Change streams:** `collection.watch()` emits events when documents change — inserts,
updates, deletes. Use for real-time features (live notifications, cache invalidation)
without polling. Requires a replica set (at least one node), even in development.

#### Senior

**Schema validation:** Despite MongoDB's flexible schema, production databases should
enforce a schema. JSON Schema validation: `db.createCollection("users", { validator:
{ $jsonSchema: { required: ["name", "email"], properties: { email: { type: "string" } }
} } })`. Validation rejects documents that do not match the schema. Mongoose validation
is client-side — database-level validation is the safety net.

**Sharding:** Horizontal partitioning across multiple servers. A shard key determines
which shard stores each document. Choosing the shard key is the most important and
irreversible decision in MongoDB at scale — a bad shard key causes hotspots (all
traffic to one shard). High cardinality, random distribution, and aligning with query
patterns are the three criteria. Resharding is possible in MongoDB 6.0+ but painful.

---

### Linux (Command Line)

**What it is:** Linux is the operating system running on virtually every server on the
internet. As a developer, you interact with it via a terminal (text-based command
interface). Regardless of whether your laptop runs macOS or Windows, your code runs on
Linux in production.

#### Basics

**The file system:** A tree starting at `/` (root). `/home/username/` is your home
directory — shortcut: `~`. `/etc/` is configuration files. `/var/log/` is log files.
`/tmp/` is temporary files (cleared on reboot). `/usr/bin/` and `/usr/local/bin/` are
executable programs.

**Essential navigation:**
- `pwd` — print working directory (where am I?)
- `ls` — list files. `ls -la` — all files including hidden, with sizes and permissions
- `cd /path/to/dir` — change directory. `cd ..` — go up one level. `cd ~` — go home
- `mkdir -p my/nested/folder` — create directory and all parents
- `rm file.txt` — delete file. `rm -rf folder/` — delete folder and contents (dangerous — no recycle bin)
- `cp source dest` — copy. `mv source dest` — move or rename
- `cat file.txt` — print file contents. `less file.txt` — page through a large file

**Finding things:**
- `find . -name "*.js"` — find files by name pattern
- `grep -r "search term" .` — search for text in files recursively
- `grep -n "error" app.log` — show line numbers of matches
- `which node` — find where a command is installed

**File permissions:** `ls -la` shows permissions like `-rwxr-xr-x`. Three sets of three
bits: owner / group / others. `r` = read (4), `w` = write (2), `x` = execute (1).
`chmod 755 script.sh` — owner can read/write/execute (7), group and others can read/
execute (5). `chmod +x script.sh` — add execute permission. `chown username:group file`
— change ownership.

**Viewing and following logs:**
- `cat logfile.log` — print entire file
- `tail -n 50 logfile.log` — last 50 lines
- `tail -f logfile.log` — follow in real time (essential during deployments)
- `grep "ERROR" logfile.log | tail -n 20` — last 20 error lines

#### Mid-level

**Process management:**
- `ps aux` — list all running processes
- `top` or `htop` — interactive process viewer with CPU/memory usage
- `kill PID` — send SIGTERM (graceful shutdown). `kill -9 PID` — force kill (SIGKILL)
- `&` at end of command — run in background: `node server.js &`
- `nohup command &` — run in background, immune to hangups (terminal close)
- `jobs` — list background jobs. `fg` — bring to foreground

**Network commands:**
- `curl -X GET https://api.example.com/users` — make HTTP request
- `curl -X POST -H "Content-Type: application/json" -d '{"name":"Alice"}' https://api.example.com/users`
- `wget https://example.com/file.zip` — download a file
- `netstat -tlnp` or `ss -tlnp` — list listening ports and which process owns them
- `ping google.com` — test network connectivity
- `traceroute google.com` — trace the network path to a host
- `dig google.com` — DNS lookup

**SSH:**
- `ssh user@hostname` — connect to a remote server securely
- `ssh -i ~/.ssh/my_key.pem user@hostname` — connect with a private key
- `scp local_file user@hostname:/remote/path` — copy file to remote server
- `ssh-keygen -t ed25519` — generate an SSH key pair. `~/.ssh/id_ed25519` is the private
  key (never share). `~/.ssh/id_ed25519.pub` is the public key (add to server's
  `~/.ssh/authorized_keys`)

**Environment variables:**
- `export MY_VAR=value` — set for current session
- `echo $MY_VAR` — print value
- `env` — list all environment variables
- Add to `~/.bashrc` or `~/.zshrc` to persist across sessions
- `printenv DATABASE_URL` — print a specific variable

#### Senior

**systemd service management:**
- `systemctl start myapp` — start a service
- `systemctl stop myapp` — stop
- `systemctl restart myapp` — restart
- `systemctl enable myapp` — start automatically on boot
- `systemctl status myapp` — show current status and recent logs
- `journalctl -u myapp -f` — follow logs for a service
- `journalctl -u myapp --since "1 hour ago"` — logs from the last hour

**Performance diagnostics:**
- `top` / `htop` — CPU and memory usage per process
- `vmstat 1` — virtual memory, CPU, I/O stats every 1 second
- `iostat -x 1` — disk I/O statistics
- `free -h` — memory usage in human-readable format
- `df -h` — disk space usage per filesystem
- `lsof -p PID` — list files (including sockets) opened by a process
- `strace -p PID` — trace system calls (very detailed — use for debugging unexplained behavior)

**Cron jobs:** Scheduled tasks. `crontab -e` edits the schedule. Format: `minute hour
day-of-month month day-of-week command`. `0 2 * * * /path/to/backup.sh` runs at 2am
daily. `*/5 * * * *` runs every 5 minutes. Redirect output: `0 2 * * * /path/backup.sh
>> /var/log/backup.log 2>&1` (stdout and stderr to log file).

---

### SQL (General)

**What it is:** SQL (Structured Query Language) is the language for interacting with
relational databases. The syntax is largely standard across PostgreSQL, MySQL, SQLite,
and SQL Server, with minor differences.

#### Basics

**SELECT:** `SELECT id, name, email FROM users` — specify columns explicitly. `WHERE
id = 1` filters rows. `ORDER BY name ASC` sorts. `LIMIT 10` caps results. `OFFSET 20`
skips rows (for pagination — use cursor-based for large tables).

**Filtering:** `WHERE age > 18 AND status = 'active'`. `OR`: `WHERE city = 'Paris' OR
city = 'Lyon'`. `IN`: `WHERE status IN ('active', 'pending')`. `LIKE`: `WHERE name LIKE
'Ali%'` (starts with Ali). `IS NULL` / `IS NOT NULL` for null checks. `BETWEEN 10 AND
20` for ranges.

**Aggregates:** `COUNT(*)` counts rows. `SUM(amount)` totals. `AVG(score)` averages.
`MAX(date)` and `MIN(date)`. Combine with `GROUP BY`: `SELECT department, COUNT(*) FROM
employees GROUP BY department`. `HAVING COUNT(*) > 5` filters groups (like WHERE but
for aggregates).

**Joins explained:**
- `INNER JOIN` — only rows matching on both sides
- `LEFT JOIN` — all rows from the left table, nulls for unmatched right rows
- `RIGHT JOIN` — all rows from the right table
- `FULL OUTER JOIN` — all rows from both, nulls where no match

Always specify the join condition explicitly (`ON table1.id = table2.fk_id`) — a
missing `ON` creates a Cartesian product (every row combined with every other row).

#### Mid-level

**Subqueries:** `SELECT * FROM users WHERE id IN (SELECT user_id FROM orders WHERE
total > 100)`. A query inside a query. Correlated subquery: the inner query references
the outer query's row (runs once per outer row — can be slow). CTEs (WITH clauses) are
usually more readable.

**Indexes in depth:** A B-tree index (the default) works for equality (`=`) and range
queries (`>`, `<`, `BETWEEN`). A composite index `CREATE INDEX ON orders(user_id,
status)` serves queries that filter on `user_id` alone or `user_id AND status` — but
not `status` alone (the leftmost prefix rule). A partial index `CREATE INDEX ON users
(email) WHERE is_active = true` only indexes active users — smaller and faster for
queries that also filter by `is_active`.

**Transactions and isolation levels:** `READ COMMITTED` (default in Postgres) — each
statement sees data committed before it ran. `REPEATABLE READ` — the whole transaction
sees a consistent snapshot. `SERIALIZABLE` — transactions behave as if they ran one at
a time — safest but slowest. Choose the lowest isolation level that satisfies your
consistency requirements.

**Upsert:** Insert if not exists, update if exists. In Postgres: `INSERT INTO users (email,
name) VALUES ('alice@example.com', 'Alice') ON CONFLICT (email) DO UPDATE SET name =
EXCLUDED.name`. Atomic — no race conditions between checking and inserting.

#### Senior

**Query planning:** The query planner chooses how to execute a query based on statistics
(row counts, value distributions maintained by `ANALYZE`). Wrong statistics produce bad
plans. `EXPLAIN ANALYZE` shows the actual plan and timing. `enable_seqscan = off` in a
session temporarily disables sequential scans — useful to test whether an index would be
faster. `pg_stat_statements` tracks cumulative statistics for all queries — find the
slowest queries in production.

**Locking:** Every write acquires a row-level lock. `SELECT FOR UPDATE` acquires an
exclusive lock on selected rows — prevents other transactions from modifying them.
`SELECT FOR SHARE` acquires a shared lock — prevents deletes and updates. Lock contention
(transactions waiting for each other's locks) shows up in `pg_stat_activity` with
`wait_event_type = 'Lock'`. Deadlocks (two transactions each holding a lock the other
needs) are automatically detected and one transaction is rolled back — always retry
on deadlock.

---

### Docker

**What it is:** Docker packages an application and all its dependencies into a container
— a standardized, isolated unit that runs identically on any machine with Docker
installed. Containers are lighter than virtual machines — they share the host OS kernel
but are isolated from each other.

#### Basics

**Key concepts:**
- **Image:** A read-only snapshot built from a Dockerfile. Like a class in programming.
- **Container:** A running instance of an image. Like an object instantiated from a class.
- **Dockerfile:** The recipe for building an image — a sequence of instructions.
- **Registry:** Where images are stored (Docker Hub, GHCR, AWS ECR).
- **Layer:** Each Dockerfile instruction creates a layer. Layers are cached — unchanged
  layers are not rebuilt.

**Essential commands:**
- `docker build -t myapp:latest .` — build an image named `myapp` from the current folder
- `docker run -p 3000:3000 myapp:latest` — run a container, mapping port 3000
- `docker ps` — list running containers
- `docker logs container_id` — view container logs
- `docker exec -it container_id bash` — open a shell inside a running container
- `docker stop container_id` — gracefully stop
- `docker rm container_id` — remove a stopped container
- `docker images` — list local images
- `docker rmi image_id` — remove an image

**Dockerfile instructions:**
- `FROM node:20-alpine` — start from a base image
- `WORKDIR /app` — set working directory
- `COPY package*.json ./` — copy specific files first (for caching)
- `RUN npm ci` — run a command during build
- `COPY . .` — copy remaining source code
- `EXPOSE 3000` — document the port (does not actually open it)
- `CMD ["node", "dist/index.js"]` — default command when container starts

#### Mid-level

**Multi-stage builds:** Build the application in one stage, copy only the output to a
lean runtime stage. `FROM node:20 AS builder; WORKDIR /app; COPY . .; RUN npm run build`.
`FROM node:20-alpine AS runtime; COPY --from=builder /app/dist ./dist; CMD ["node",
"dist/index.js"]`. The final image does not contain source code, dev dependencies, or
the build toolchain — much smaller and more secure.

**Docker Compose:** Define multi-container applications. `docker compose up` starts all
services. `docker compose down` stops and removes containers. `docker compose logs -f
api` follows logs for the `api` service. Key fields: `services` (the containers),
`volumes` (persistent storage — a database's data must be in a volume or it disappears
on restart), `networks` (containers on the same network can reach each other by service
name), `depends_on` (start order).

**Environment variables in containers:** Pass at runtime: `docker run -e DATABASE_URL=...`
or via `--env-file .env`. In Compose: `environment:` or `env_file:`. Never bake secrets
into the image — they become part of the image history and are visible to anyone with
access.

**Non-root user:** Processes inside containers run as root by default — if the container
is compromised, the attacker has root access. `RUN addgroup -S appgroup && adduser -S
appuser -G appgroup; USER appuser` runs subsequent commands and the final process as
a non-root user.

#### Senior

**Layer caching strategy:** Docker rebuilds a layer and all subsequent layers when a
layer's content changes. Order instructions from least-changing to most-changing. Copy
`package.json` and run `npm ci` before copying source code — this way, the dependencies
layer is cached until `package.json` changes, not until any source file changes. Bad
ordering: `COPY . . ; RUN npm ci` — rebuilds dependencies on every source change.

**Image security scanning:** `docker scout cves myapp:latest` (Docker Scout) or `trivy
image myapp:latest` scans the image for known CVEs in OS packages and dependencies.
Always scan before pushing to production. Pin base images by digest (`FROM node:20-alpine
@sha256:...`) to prevent supply chain attacks where a tag is overwritten.

**BuildKit:** Docker's next-generation build engine. Enable with `DOCKER_BUILDKIT=1` or
`export DOCKER_BUILDKIT=1`. Features: parallel stage execution in multi-stage builds,
better caching, secret mounts (`RUN --mount=type=secret,id=npmrc npm ci` uses a secret
without it appearing in the layer), and `--cache-from` to use a previously built image
as cache source in CI.


---

### Symfony

**What it is:** Symfony is a PHP web framework — a collection of reusable PHP components
and a full-stack framework for building web applications and APIs. It is the backbone of
many large PHP applications and the foundation that Laravel, Drupal, and other frameworks
build on top of. Symfony is known for its stability (long-term support releases),
flexibility, and the quality of its components (the HttpFoundation, Console, and Finder
components are used by millions of PHP projects even outside of Symfony).

**When to use it:** Large, long-lived enterprise PHP applications where stability, strict
architecture, and a mature ecosystem are priorities. When the team has PHP expertise and
needs fine-grained control over every layer of the application. When building APIs,
command-line tools, or complex backend systems in PHP. If the project needs simplicity and
faster bootstrapping, consider Laravel instead.

#### Basics

**PHP fundamentals you must know first:** PHP is a server-side scripting language that
runs on the server and produces HTML (or JSON) that is sent to the browser. A PHP file
starts with `<?php`. Variables start with `$`: `$name = "Alice"`. Arrays: `$names =
["Alice", "Bob"]`. Functions: `function greet(string $name): string { return "Hello
$name"; }`. Classes: `class User { public string $name; public function __construct(
string $name) { $this->name = $name; } }`. PHP is dynamically typed but supports type
hints in modern versions (PHP 8+).

**Installing and setting up Symfony:** First, install PHP 8.1+ and Composer (PHP's
package manager — like npm for PHP). Composer reads `composer.json` (the equivalent of
`package.json`), downloads packages from Packagist (the PHP package repository), and
stores them in `vendor/` (the equivalent of `node_modules/` — never commit it). Create
a new Symfony project: `composer create-project symfony/skeleton my-project`. This creates
the bare minimum. `symfony/website-skeleton` includes more defaults for a full web app.

**Project structure:** `src/` holds your PHP code. `config/` holds configuration files
(routes, services, framework settings). `templates/` holds Twig templates (the HTML
layer). `public/` is the web root — only `public/index.php` (the front controller) is
publicly accessible. `var/cache/` and `var/log/` are generated files — add to `.gitignore`.

**The front controller pattern:** All requests go to `public/index.php`. This single
entry point boots the Symfony kernel, which routes the request to the right controller
and returns a response. This is different from PHP's older pattern where every file was
directly accessible at its URL. Explain this every time — it is fundamental to how Symfony works.

**Running the development server:** `symfony server:start` starts a local server (requires
the Symfony CLI, which is a separate tool from the framework itself). Or: `php -S
localhost:8000 -t public/` uses PHP's built-in server. Always explain which is being
used.

**Environment variables:** Stored in `.env` (committed, safe defaults) and `.env.local`
(not committed, real secrets). Symfony loads them automatically. Access in code:
`$_ENV['DATABASE_URL']` or via the DI container (preferred). `.env.test` overrides for
tests. Never put real credentials in `.env` — only in `.env.local`.

#### Mid-level

**Controllers:** Handle HTTP requests and return responses. `#[Route('/users', name:
'user_index')]` is a PHP attribute (annotation) that maps the URL to the method.
`public function index(): Response { return $this->render('user/index.html.twig', [
'users' => $users ]); }`. Controllers extend `AbstractController` to get helper methods
like `render()`, `json()`, `redirectToRoute()`, `getUser()`.

**Routing:** Define routes with attributes on controller methods (`#[Route('/users/{id}',
methods: ['GET'])]`) or in `config/routes.yaml`. Parameters in `{braces}` are passed as
method arguments: `public function show(int $id): Response`. Requirements: `#[Route(
'/users/{id}', requirements: ['id' => '\d+'])]` — only match numeric IDs.

**Twig templates:** Symfony's templating engine. `{{ variable }}` outputs a value (escaped
for safety). `{% if condition %}...{% endif %}` for conditionals. `{% for item in items %}
...{% endfor %}` for loops. `{% extends 'base.html.twig' %}` inherits a layout. `{% block
content %}...{% endblock %}` defines replaceable sections. Never write PHP directly in
templates — keep logic in controllers and services.

**Doctrine ORM:** The standard database layer for Symfony. An ORM (Object-Relational
Mapper) maps PHP classes to database tables. A `User` class becomes a `user` table. Each
property becomes a column. `#[ORM\Entity] #[ORM\Table(name: 'users')] class User { #[ORM\
Id] #[ORM\GeneratedValue] #[ORM\Column] private int $id; #[ORM\Column(length: 255)]
private string $name; }`. Relationships: `#[ORM\ManyToOne]`, `#[ORM\OneToMany]`,
`#[ORM\ManyToMany]`. Migrations: `php bin/console doctrine:migrations:generate` creates
a migration file. `php bin/console doctrine:migrations:migrate` runs it.

**Dependency Injection container:** Symfony's most powerful feature. Every service (class
doing work) is registered in the container. Symfony automatically wires dependencies —
if `UserController` needs `UserRepository` in its constructor, Symfony creates and injects
it automatically. This is called "autowiring." You almost never configure services manually
— Symfony discovers and wires them by type-hint. The container is compiled for production
performance.

**Forms:** `php bin/console make:form` generates a form type class. Form types define the
fields, constraints, and data mapping. `$form = $this->createForm(UserType::class, $user)`.
`$form->handleRequest($request)`. `if ($form->isSubmitted() && $form->isValid())`. Render
in Twig: `{{ form(form) }}`. Form validation uses constraints: `#[Assert\NotBlank]`,
`#[Assert\Email]`, `#[Assert\Length(min: 8)]` on entity properties.

**Security:** `config/packages/security.yaml` configures firewalls (which routes require
authentication), providers (how to load users), and access control rules. `#[IsGranted(
'ROLE_ADMIN')]` on a controller requires the ADMIN role. `$this->getUser()` returns the
current user. Voters implement custom authorization logic: "can this user edit this post?"
Password hashing: `$hashedPassword = $hasher->hashPassword($user, $plainPassword)`.

#### Senior

**Event system:** Symfony's kernel fires events throughout the request lifecycle. Listen
to them: `class RequestListener { #[AsEventListener(event: KernelEvents::REQUEST)] public
function onRequest(RequestEvent $event): void { ... } }`. Custom events decouple components
— dispatch `new UserCreatedEvent($user)`, then any number of listeners react without the
dispatcher knowing about them. This is the correct way to add cross-cutting behavior.

**Console commands:** `php bin/console make:command` generates a command class. `#[
AsCommand(name: 'app:send-emails')]`. `protected function execute(InputInterface $input,
OutputInterface $output)`. Commands run scheduled tasks, imports, maintenance jobs.
Use `$io = new SymfonyStyle($input, $output)` for clean output formatting. Register as
cron jobs or Symfony Messenger consumers.

**Symfony Messenger:** The message bus for async processing. Define a message class:
`class SendEmailMessage { public function __construct(public readonly string $email) {} }`.
Define a handler: `#[AsMessageHandler] class SendEmailHandler { public function __invoke(
SendEmailMessage $message): void { ... } }`. Dispatch: `$bus->dispatch(new SendEmailMessage(
$email))`. Configure a transport (RabbitMQ, Redis, Doctrine) to process messages
asynchronously. Workers: `php bin/console messenger:consume async`.

**Performance in production:** `APP_ENV=prod` enables the production environment.
`composer dump-autoload --optimize` generates an optimized class map. `php bin/console
cache:warmup` pre-builds the DI container. The compiled container is the key — in
development, the container is rebuilt on every request change; in production, it is a
single compiled PHP file. OPcache must be enabled in production — it caches compiled PHP
bytecode so files are not re-parsed on every request.

**Testing in Symfony:** `php bin/console make:test` generates test classes. Symfony
provides a `KernelTestCase` for integration tests (boots the real kernel) and a
`WebTestCase` for HTTP-level tests (sends real requests to controllers and asserts on
responses). Unit tests use plain PHPUnit — no Symfony bootstrap needed. Functional tests
with `$client->request('GET', '/users')` then `$this->assertResponseIsSuccessful()`.
Use fixtures (`DoctrineFixturesBundle`) to seed test data.

---

### Laravel

**What it is:** Laravel is the most popular PHP framework for web applications. It
prioritizes developer experience and productivity — beautiful syntax, comprehensive
tooling, and "convention over configuration" that gets you from zero to working application
faster than any other PHP framework. Laravel wraps the complexity of Symfony components
in an opinionated, elegant layer.

**When to use it:** Rapid application development in PHP, full-stack web applications,
REST APIs, SaaS products, and any PHP project where developer velocity and ecosystem
richness matter more than architectural purity. Laravel is the right choice for most
PHP web projects.

#### Basics

**Creating a project:** `composer create-project laravel/laravel my-project`. Laravel
uses Composer for package management (same as Symfony). The `artisan` command-line tool
is Laravel's equivalent of Symfony's `bin/console` — it generates code, runs migrations,
clears caches, and starts the dev server. `php artisan serve` starts the development
server at `localhost:8000`.

**Project structure:** `app/` contains models, controllers, and other application code.
`routes/web.php` defines web routes. `routes/api.php` defines API routes. `resources/
views/` contains Blade templates. `database/migrations/` contains migration files.
`config/` contains configuration files. `storage/` contains logs, cache, and uploaded
files. `.env` holds environment-specific configuration.

**Routes:** In `routes/web.php`: `Route::get('/users', [UserController::class, 'index'])`.
`Route::post('/users', [UserController::class, 'store'])`. `Route::resource('/users',
UserController::class)` generates all CRUD routes at once: `index`, `create`, `store`,
`show`, `edit`, `update`, `destroy`. Named routes: `Route::get('/users', ...)->name(
'users.index')`. Link to named route: `route('users.index')`. This is far more concise
than manually defining every route.

**Controllers:** `php artisan make:controller UserController --resource` generates a
resource controller with all CRUD methods. `php artisan make:controller UserController
--api` generates an API controller (no `create`/`edit` methods — those are for HTML
forms). Controllers return responses: `return view('users.index', compact('users'))` for
HTML, or `return response()->json($users)` for JSON.

**Blade templates:** Laravel's templating engine. `{{ $variable }}` outputs escaped HTML.
`{!! $html !!}` outputs unescaped HTML (use only for trusted content). `@if`, `@else`,
`@endif`, `@foreach`, `@endforeach` for control structures. `@extends('layouts.app')` and
`@section('content')...@endsection` for layouts. `@include('partials.nav')` includes a
partial. Blade compiles to plain PHP — it has zero runtime overhead versus plain PHP views.

**Eloquent ORM:** Laravel's ORM. `class User extends Model {}` — that is a complete model.
By convention, the `User` model maps to the `users` table. Eloquent automatically handles
`id`, `created_at`, and `updated_at`. Query: `User::find(1)`, `User::where('email',
$email)->first()`, `User::all()`. Create: `User::create(['name' => 'Alice', 'email' =>
'alice@example.com'])` (requires `$fillable` array on the model for mass assignment
protection). Relationships: `$user->posts` (if `User hasMany Post`), `$post->user` (if
`Post belongsTo User`).

**Migrations:** `php artisan make:migration create_users_table`. Edit the generated file
in `database/migrations/`. `$table->id()` adds an auto-incrementing primary key.
`$table->string('name')`, `$table->text('bio')->nullable()`, `$table->foreignId('user_id')
->constrained()->cascadeOnDelete()`. Run: `php artisan migrate`. Rollback: `php artisan
migrate:rollback`. Seed: `php artisan db:seed`.

#### Mid-level

**Request validation:** `$request->validate(['name' => 'required|string|max:255',
'email' => 'required|email|unique:users'])`. If validation fails, Laravel automatically
redirects back with errors. For APIs, it returns a 422 JSON response. Form Requests:
`php artisan make:request StoreUserRequest` — move validation rules into a dedicated
class. `$this->authorize('create', User::class)` adds authorization to the request.

**Middleware:** Functions that filter HTTP requests. `php artisan make:middleware
CheckSubscription`. Apply to routes: `Route::middleware(['auth', 'subscription'])->
group(function() { ... })`. Built-in middleware: `auth` (requires login), `throttle`
(rate limiting), `signed` (validates signed URLs). Middleware is the correct place for
authentication checks, rate limiting, and request logging.

**Eloquent relationships in depth:** `hasOne`, `hasMany`, `belongsTo`, `belongsToMany`,
`hasManyThrough`, `morphTo`/`morphMany` (polymorphic). Eager loading prevents N+1:
`User::with('posts')->get()` loads all users AND all their posts in two queries, not N+1.
`User::withCount('posts')->get()` adds a `posts_count` to each user without loading the
posts. Always check for N+1 with Laravel Debugbar in development.

**Queues and jobs:** `php artisan make:job SendWelcomeEmail`. A job class with a `handle()`
method. Dispatch: `SendWelcomeEmail::dispatch($user)`. Configure a queue driver (Redis,
SQS, database) in `.env`. Run workers: `php artisan queue:work`. Failed jobs go to the
`failed_jobs` table. Retry: `php artisan queue:retry all`. Queues are essential for any
work that should not block the HTTP response — sending emails, processing images, calling
slow external APIs.

**Events and listeners:** `php artisan make:event UserRegistered`. `php artisan make:
listener SendWelcomeEmail --event=UserRegistered`. Fire the event: `event(new
UserRegistered($user))`. All listeners for that event run automatically. Register in
`EventServiceProvider`. This decouples the action (user registered) from the
consequences (send email, notify admin, create trial, etc.).

**Authentication with Laravel Breeze or Jetstream:** `composer require laravel/breeze &&
php artisan breeze:install` scaffolds complete auth: login, register, password reset, email
verification, with Blade or Vue/React. Jetstream adds teams, two-factor auth, and API
tokens. For APIs, Laravel Sanctum provides token-based authentication. For OAuth, Laravel
Passport implements a full OAuth2 server.

**API Resources:** Transform models into JSON consistently. `php artisan make:resource
UserResource`. Define `toArray`: `return ['id' => $this->id, 'name' => $this->name]`.
Use: `return new UserResource($user)` or `UserResource::collection($users)`. Resources
prevent accidentally exposing sensitive fields and give you a consistent transformation
layer between your database models and your API responses.

#### Senior

**Service providers and the service container:** The service container is Laravel's DI
container — it creates and manages class instances. Service providers boot the application:
`register()` binds things to the container, `boot()` runs after all providers are
registered. Every package you install registers a service provider. Custom bindings:
`$this->app->bind(UserRepositoryInterface::class, EloquentUserRepository::class)` — your
code depends on the interface; the container injects the implementation. This is how you
apply Clean Architecture inside Laravel.

**Telescope and Horizon:** Laravel Telescope is a debugging assistant — it records
requests, queries, jobs, events, mails, notifications, and exceptions in a local dashboard.
Essential during development. Never expose Telescope in production without authentication.
Laravel Horizon monitors and manages Redis queues — see throughput, failed jobs, wait
times. `php artisan horizon` starts the supervisor.

**Performance optimization:** `php artisan optimize` caches routes, config, and views.
Eager loading is the single biggest performance win — profile queries with Telescope or
`DB::listen()` in development and eliminate every N+1. Redis caching: `Cache::remember(
'users', 3600, fn() => User::all())` — caches the result for 1 hour. OPcache must be
enabled. For read-heavy endpoints, use `Route::cache()` (full-page caching) where data
changes infrequently.

**Testing:** Laravel provides `TestCase` with helpers: `$this->get('/users')->
assertStatus(200)->assertJson([...])`. `$this->actingAs($user)` authenticates. `$this->
withoutMiddleware()` disables middleware in tests. Factories: `User::factory()->count(10)
->create()` generates test data. `RefreshDatabase` trait rolls back the database after
each test. `Http::fake()` mocks external HTTP calls. `Queue::fake()` asserts jobs were
dispatched without actually running them. Always test the four states: success, validation
failure, unauthorized, not found.

---

### Django

**What it is:** Django is a high-level Python web framework that follows the "batteries
included" philosophy — it comes with an ORM, authentication, admin interface, form
handling, and security features built in. The tagline "for perfectionists with deadlines"
captures it well: Django makes it possible to build production-grade web applications
quickly by providing sensible defaults for everything.

**When to use it:** Python-based web applications and APIs, content management systems,
data-backed applications, anything where Python's ecosystem (data science, ML, scripting)
is an advantage, and projects where the built-in admin interface saves significant
development time. For pure REST/GraphQL APIs, FastAPI is the modern alternative (faster,
async-native); Django REST Framework on top of Django is better for APIs that also have
a web UI.

#### Basics

**Installing and creating a project:** Use a virtual environment first (always):
`python -m venv .venv && source .venv/bin/activate`. Install: `pip install django`.
Create project: `django-admin startproject myproject`. This creates `manage.py` (the
command-line tool — equivalent to Laravel's `artisan`) and a `myproject/` folder with
settings, URLs, and WSGI/ASGI configuration. Run the dev server: `python manage.py
runserver`.

**Apps vs project:** A Django project is the container. Apps are the components — each
app handles one piece of functionality. `python manage.py startapp users` creates a `users/`
app with models, views, and tests. Register the app in `INSTALLED_APPS` in `settings.py`.
Each app is designed to be reusable — in theory, you could pull the `users` app into
another project.

**`settings.py`:** The central configuration file. `DEBUG = True` in development, `False`
in production. `DATABASES` configures the database connection. `INSTALLED_APPS` lists
active apps. `SECRET_KEY` signs cookies and tokens — never commit the real value; load
from an environment variable. `ALLOWED_HOSTS` lists domains the app will serve (security
requirement). `STATIC_URL`, `MEDIA_URL` for assets.

**Models:** `class User(models.Model): name = models.CharField(max_length=255); email =
models.EmailField(unique=True); created_at = models.DateTimeField(auto_now_add=True)`.
Each class becomes a database table. Each field becomes a column. `models.CharField`,
`models.IntegerField`, `models.BooleanField`, `models.ForeignKey`, `models.ManyToManyField`.
After defining or changing models: `python manage.py makemigrations` (creates migration
files) and `python manage.py migrate` (applies them to the database).

**Views:** A view is a Python function (or class) that receives an HTTP request and
returns an HTTP response. `def user_list(request): users = User.objects.all(); return
render(request, 'users/list.html', {'users': users})`. `render()` takes the request, a
template name, and a context dictionary. For JSON APIs: `from django.http import
JsonResponse; return JsonResponse({'users': list(users.values())})`.

**URLs:** In `urls.py`: `from django.urls import path; urlpatterns = [path('users/',
views.user_list, name='user-list'), path('users/<int:pk>/', views.user_detail, name=
'user-detail')]`. `<int:pk>` captures an integer and passes it as `pk` to the view.
Include app URLs in the project's main `urls.py`: `path('api/', include('users.urls'))`.

**Templates:** Django's template language. `{{ variable }}` outputs a value. `{% if
condition %}...{% endif %}`. `{% for item in items %}...{% endfor %}`. `{% extends
"base.html" %}` and `{% block content %}...{% endblock %}` for inheritance. `{% url
'user-list' %}` generates a URL by name. `{{ user.name|upper }}` applies a filter.
Templates are auto-escaped — HTML entities are escaped by default.

#### Mid-level

**Django ORM queries:** `User.objects.all()` — all users. `User.objects.filter(
is_active=True)` — filtered. `User.objects.get(pk=1)` — one user (raises exception if
not found). `User.objects.exclude(email='')` — all except. `User.objects.order_by(
'-created_at')` — newest first (`-` prefix reverses). `User.objects.values('id', 'name')`
— returns dicts instead of model instances (faster, less memory). `User.objects.
select_related('profile')` — eager-loads a foreign key in one query. `User.objects.
prefetch_related('posts')` — eager-loads a reverse relationship.

**Class-based views (CBVs):** `class UserListView(ListView): model = User; template_name
= 'users/list.html'; context_object_name = 'users'; paginate_by = 20`. Django handles
the query, pagination, and context. `CreateView`, `UpdateView`, `DeleteView`, `DetailView`
follow the same pattern. Override `get_queryset()` to filter, `get_context_data()` to add
extra context, `form_valid()` to add logic on success.

**Forms and validation:** `class UserForm(forms.ModelForm): class Meta: model = User;
fields = ['name', 'email']`. `form = UserForm(request.POST)`. `if form.is_valid(): form.
save()`. Custom validation: `def clean_email(self): email = self.cleaned_data['email'];
if User.objects.filter(email=email).exists(): raise forms.ValidationError("Email taken");
return email`. Widgets control how fields render.

**Django REST Framework (DRF):** `pip install djangorestframework`. Add `'rest_framework'`
to `INSTALLED_APPS`. Serializers validate and transform data: `class UserSerializer(
serializers.ModelSerializer): class Meta: model = User; fields = ['id', 'name', 'email']`.
ViewSets: `class UserViewSet(viewsets.ModelViewSet): queryset = User.objects.all();
serializer_class = UserSerializer`. Routers: `router.register('users', UserViewSet)` —
automatically generates all CRUD URL patterns. DRF handles content negotiation, pagination,
filtering, and authentication.

**Authentication and permissions:** DRF authentication classes: `BasicAuthentication`,
`SessionAuthentication`, `TokenAuthentication`. `@api_view(['GET']) @permission_classes(
[IsAuthenticated]) def protected_view(request)`. Custom permission: `class IsOwner(
BasePermission): def has_object_permission(self, request, view, obj): return obj.user ==
request.user`. Django's built-in auth: `from django.contrib.auth import authenticate,
login, logout`. `@login_required` decorator on views.

**The Django Admin:** `admin.site.register(User)` adds the User model to the admin
interface at `/admin/`. Customize: `@admin.register(User) class UserAdmin(admin.
ModelAdmin): list_display = ['name', 'email', 'created_at']; search_fields = ['name',
'email']; list_filter = ['is_active']`. The admin gives you a fully functional CRUD
interface for every model with zero custom UI code. It is genuinely one of Django's best
features for internal tools.

**Signals:** Like events in Laravel/Symfony. `@receiver(post_save, sender=User) def
on_user_created(sender, instance, created, **kwargs): if created: send_welcome_email(
instance)`. Built-in signals: `pre_save`, `post_save`, `pre_delete`, `post_delete`.
`post_migrate` runs after migrations. Signals decouple side effects from the action that
triggers them.

#### Senior

**Performance — the N+1 query problem in Django:** The most common Django performance
issue. `users = User.objects.all(); for user in users: print(user.profile.bio)` — 1
query for users + 1 per user for the profile = N+1. Fix: `User.objects.select_related(
'profile').all()` — one SQL JOIN. For reverse relations and many-to-many: `prefetch_related`.
Measure with Django Debug Toolbar (development) or `connection.queries` in tests. Log
queries in production with: `LOGGING = {'loggers': {'django.db.backends': {'level':
'DEBUG'}}}`.

**Celery for async tasks:** `pip install celery redis`. `@shared_task def send_email(
user_id): user = User.objects.get(pk=user_id); ...`. Dispatch: `send_email.delay(user.id)
` or `send_email.apply_async(args=[user.id], countdown=60)` (runs after 60 seconds).
Run worker: `celery -A myproject worker -l info`. Run scheduler (for cron-like tasks):
`celery -A myproject beat`. Use Flower (`pip install flower`) for a web-based task
monitoring dashboard.

**Caching:** `from django.core.cache import cache`. `cache.set('users', users, 300)` —
cache for 5 minutes. `cache.get('users')` — returns `None` if not set or expired.
Per-view caching: `@cache_page(60 * 15)` caches the entire response for 15 minutes.
Template fragment caching: `{% cache 500 'user_list' %}...{% endcache %}`. Use Redis as
the cache backend (`django-redis`) — never the file system in production.

**Deployment:** Django apps are typically deployed with Gunicorn (WSGI server — handles
concurrent requests by running multiple worker processes: `gunicorn myproject.wsgi:application
-w 4`) behind Nginx (reverse proxy — handles static files, SSL termination, connection
management). For async support (WebSockets, Server-Sent Events), use Daphne or Uvicorn
with Django Channels. `python manage.py collectstatic` gathers all static files into one
folder for Nginx to serve. `DEBUG=False` in production is not optional — it enables
security features and stops sensitive information from appearing in error pages.

**Database optimization at scale:** Use `only()` to load specific fields: `User.objects.
only('id', 'name')` — much faster than loading every column. Use `defer()` to exclude
large fields: `User.objects.defer('bio', 'avatar')`. `bulk_create([User(...), User(...)])` —
inserts many records in one query. `update()` on a queryset updates in the database
without loading models into Python: `User.objects.filter(is_active=False).update(
deleted_at=now())`. `annotate()` and `aggregate()` compute values in the database, not Python.

**Testing Django:** `TestCase` wraps each test in a transaction that is rolled back —
tests are isolated. `Client` makes HTTP requests: `response = self.client.get('/users/')`.
`self.assertEqual(response.status_code, 200)`. `self.client.force_login(user)` to
authenticate. `RequestFactory` creates request objects without going through the full
middleware stack — faster for unit testing views. `mixer` or `factory_boy` generate model
instances with sensible random data. Test the four states always: success, validation
error, unauthorized, not found.

---

## Git & version control (tracking changes to code)

**What Git is:** Git is a tool that tracks every change ever made to your code. It lets
you go back to any previous version, work on multiple changes simultaneously without
them interfering with each other, and collaborate with other developers without
overwriting each other's work.

**Key concepts:**
- A **commit** is a saved snapshot of your changes with a message describing what changed.
  Commits should be small and focused — one logical change per commit. The message should
  be in imperative mood, present tense: `Add rate limiting to auth endpoint`, not `Added`
  or `Adding`.
- A **branch** is a parallel version of the codebase where you can make changes without
  affecting the main branch. When the changes are ready, you merge the branch back.
- A **pull request (PR)** is a proposal to merge a branch. It is where code review happens.
  The description should explain *why* the change was made, not *what* changed — the diff
  already shows what changed.
- **Never commit secrets, passwords, or tokens.** Once something is in Git history, it
  is there forever (even if you delete the file later). Use environment variables.

---

## CI/CD tooling ecosystem (the full picture)

**What CI/CD is and why it matters:** CI/CD (Continuous Integration / Continuous
Delivery) is the automated pipeline that takes code from a developer's laptop to
production reliably, repeatably, and safely. Think of it as an assembly line where
every station does a specific job — one checks the code for errors, one runs tests,
one packages it, one deploys it. The pipeline runs the same way every single time,
so you never rely on someone remembering the right sequence of commands on a stressful
Friday afternoon.

There is an entire ecosystem of tools in this space. Below is every major category
with the tools that matter, explained so you understand what each does and why you
would choose it.

---

### Source control & code hosting

The foundation of every pipeline. Code lives here; everything else reacts to changes.

- **GitHub** — the most widely used platform. Pull requests, code review, Actions for
  CI/CD, and Packages for container/package hosting all in one place. Default choice.
- **GitLab** — similar to GitHub but can be self-hosted. Built-in CI/CD (GitLab CI) is
  deeply integrated and very powerful. Common in enterprises that need data on their
  own servers.
- **Bitbucket** — Atlassian's offering, integrates tightly with Jira and Confluence.
  Common in teams already using the Atlassian ecosystem.

---

### CI/CD platforms (running the pipeline)

These are the systems that watch your repository and automatically run jobs when code
is pushed.

- **GitHub Actions** — the default choice for projects on GitHub. Pipelines are defined
  in `.github/workflows/*.yml` files. Jobs run on GitHub's servers (or your own
  self-hosted runners). Explain every field in a workflow file when writing one:
  `on` (what triggers the pipeline), `jobs` (the parallel units of work), `steps`
  (the sequential commands inside a job), `uses` (a reusable action from the marketplace).

- **GitLab CI/CD** — defined in `.gitlab-ci.yml`. Uses the concept of stages (build →
  test → deploy) that run in sequence, with jobs inside each stage running in parallel.
  Powerful caching and artifact passing between stages.

- **CircleCI** — fast, with good Docker support and a parallelism system that splits
  test suites across multiple machines. Common in startups.

- **Jenkins** — the oldest and most flexible CI tool. Self-hosted, highly customizable,
  but requires significant maintenance. Use only if the team is already invested in it
  or has specific requirements that hosted solutions cannot meet.

- **Buildkite** — hybrid model: the orchestration is cloud-hosted but the jobs run on
  your own infrastructure. Used by large companies that need CI speed and security of
  running builds on their own hardware.

- **Tekton** — Kubernetes-native CI/CD pipeline framework. Use when the team is deep
  in the Kubernetes ecosystem and wants pipelines to be first-class Kubernetes objects.

- **Argo Workflows / Argo CD** — Argo CD watches a Git repository and automatically
  deploys Kubernetes manifests when they change. This pattern is called GitOps — Git
  is the single source of truth for what should be running in production. Argo CD
  is the standard GitOps tool.

---

### Containerization & orchestration

Packaging and running applications in containers at scale.

- **Docker** — packages an application and its dependencies into a container image.
  Explain multi-stage builds, non-root users, `.dockerignore`, and image tagging with
  git SHA every time a Dockerfile is written.

- **Docker Compose** — defines and runs multi-container applications locally. Your app,
  a database, a cache, a message queue — all defined in one `docker-compose.yml` and
  started with `docker compose up`. Essential for local development; explain every
  service, volume, and network.

- **Kubernetes (K8s)** — the industry-standard system for running containers at scale
  in production. It handles deploying containers, keeping them running, scaling them
  up and down based on load, and rolling out updates without downtime. Key concepts to
  explain every time they appear:
  - **Pod** — the smallest deployable unit, one or more containers that run together.
  - **Deployment** — declares how many pods to run and how to update them.
  - **Service** — a stable network address for a set of pods (pods come and go; the
    Service is always at the same address).
  - **Ingress** — routes external HTTP traffic to the right service.
  - **ConfigMap / Secret** — configuration and sensitive values injected into pods.
  - **Namespace** — logical isolation within a cluster (e.g., `dev`, `staging`, `prod`).

- **Helm** — the package manager for Kubernetes. Instead of managing dozens of YAML
  files directly, Helm packages them into a "chart" with configurable values. Explain
  charts, values files, and `helm upgrade --install` every time.

- **Podman** — a Docker alternative that runs containers without a background daemon
  and never requires root. Drop-in replacement for Docker commands in most cases.

---

### Infrastructure as Code (IaC)

Writing the definition of your infrastructure (servers, databases, networking) as code,
so it is versioned, reviewable, and reproducible.

- **Terraform** — the most widely used IaC tool. Declarative — you describe the desired
  state, Terraform figures out what to create, change, or delete. Works with every major
  cloud provider. Key concepts: providers (cloud integrations), resources (a server,
  a database, a DNS record), state (Terraform's record of what it has created), modules
  (reusable groups of resources). Explain `terraform init`, `terraform plan` (shows
  what would change), and `terraform apply` (makes the changes) every time.

- **Pulumi** — same idea as Terraform but uses real programming languages (TypeScript,
  Python, Go) instead of a custom configuration language. Better for teams who want to
  write infrastructure logic programmatically.

- **AWS CDK (Cloud Development Kit)** — infrastructure for AWS using TypeScript, Python,
  or Java. Compiles to CloudFormation. Good if the team is deep in AWS and comfortable
  with code over configuration.

- **Ansible** — configuration management and provisioning tool. Uses YAML playbooks to
  describe what state a server should be in. Good for configuring existing servers;
  less good for creating cloud infrastructure from scratch.

- **Bicep / ARM Templates** — Microsoft Azure's native IaC language. Use when the
  project is Azure-first.

---

### Cloud platforms

Where the application actually runs. Explain pricing models, regions, and the right
service for the job every time a cloud resource is introduced.

- **AWS (Amazon Web Services)** — the largest cloud provider. Key services:
  - EC2 (virtual servers), ECS/EKS (containers), Lambda (serverless functions)
  - S3 (file/object storage), RDS (managed relational databases), DynamoDB (managed
    NoSQL), ElastiCache (managed Redis/Memcached)
  - CloudFront (CDN — Content Delivery Network: serves content from servers close to
    the user for speed), Route53 (DNS), ALB (Application Load Balancer)
  - IAM (Identity and Access Management — controls who and what can access resources)

- **Google Cloud Platform (GCP)** — strong in data/ML. Cloud Run (serverless containers
  — great for APIs without managing servers), GKE (managed Kubernetes), BigQuery
  (analytics at scale), Firestore (managed NoSQL).

- **Microsoft Azure** — dominant in enterprises with Microsoft infrastructure. Azure
  Kubernetes Service (AKS), Azure Functions (serverless), Cosmos DB (multi-model NoSQL),
  Azure Active Directory (identity management).

- **Vercel** — the simplest way to deploy Next.js, React, and frontend applications.
  Push to GitHub, it deploys automatically. Every pull request gets its own preview URL.
  Handles SSL, CDN, and Edge Functions automatically. Use for frontend and full-stack
  Next.js apps.

- **Railway / Render / Fly.io** — platform-as-a-service alternatives to raw cloud
  providers. Simpler, more opinionated, good for small-to-medium backends where you
  do not want to manage Kubernetes or configure VPCs. Explain trade-offs between these
  and raw cloud when recommending one.

- **Cloudflare** — not just DNS. Cloudflare Workers (serverless functions at the edge —
  runs code geographically close to every user in the world), Pages (frontend hosting),
  R2 (object storage without egress fees), D1 (SQLite at the edge).

---

### Secrets management

Passwords, API keys, tokens — managed securely, not stored in code.

- **HashiCorp Vault** — the enterprise-grade secrets manager. Stores secrets, rotates
  them automatically, and provides fine-grained access control. Explain the concept of
  dynamic secrets — Vault can generate a short-lived database password specifically for
  one job, then revoke it when the job is done.
- **AWS Secrets Manager / Parameter Store** — AWS-native secrets storage. Secrets
  Manager handles rotation automatically; Parameter Store is simpler and cheaper for
  non-sensitive configuration.
- **GitHub Actions Secrets** — encrypted variables set in the repository settings,
  injected as environment variables during CI runs.
- **Doppler / Infisical** — developer-friendly secrets managers that sync secrets to
  local development, CI, and production from one place.
- **SOPS (Secrets OPerationS)** — encrypts secret files so they can be safely committed
  to Git. Good for GitOps workflows where config lives in the repository.

---

### Monitoring, alerting & observability tooling

Knowing what your system is doing in production.

- **Prometheus** — collects metrics from your services at regular intervals. It scrapes
  `/metrics` endpoints that services expose. Time-series database purpose-built for
  metrics. The industry standard for Kubernetes environments.
- **Grafana** — visualizes metrics from Prometheus (and many other sources) in
  dashboards. The tool where you build the graphs and alerts that tell you when
  something is wrong.
- **Datadog** — commercial all-in-one observability platform: metrics, logs, traces, and
  APM (Application Performance Monitoring — tracks performance of individual function
  calls inside your app) in one place. Expensive but powerful for teams that want one
  tool.
- **OpenTelemetry (OTel)** — the open standard for instrumentation. Instead of writing
  your tracing code for a specific vendor, you write it once with OTel and it works with
  any backend (Jaeger, Zipkin, Honeycomb, Datadog, etc.). Always use OTel for new
  instrumentation; never vendor-lock your observability code.
- **Jaeger / Zipkin** — open-source distributed tracing backends. Store and visualize
  traces from OpenTelemetry-instrumented services.
- **Loki** — Grafana's log aggregation system. Like Prometheus but for logs. Pair it
  with Grafana for a fully open-source observability stack.
- **Sentry** — error tracking. When an unhandled exception occurs in production, Sentry
  captures the full stack trace, the user context, and the frequency, and sends an
  alert. Essential for every production application. Integrates with every major language.
- **PagerDuty / OpsGenie** — on-call management and alert routing. When Prometheus or
  Datadog fires an alert, it routes to the right person based on who is on-call.

---

### Quality & security scanning in CI

Automated checks that catch issues before they reach production.

- **SonarQube / SonarCloud** — static code analysis. Detects bugs, code smells
  (patterns that are not wrong but will cause problems), security vulnerabilities, and
  tracks test coverage over time. Integrates into CI and comments on pull requests.
- **Snyk / Dependabot / Renovate** — scan dependencies for known security vulnerabilities
  and automatically open pull requests to update them. Renovate is the most configurable;
  Dependabot is built into GitHub; Snyk adds deeper vulnerability intelligence.
- **Trivy** — scans container images for known vulnerabilities in OS packages and
  application dependencies. Run it in CI before pushing an image to production.
- **OWASP ZAP / Burp Suite** — dynamic application security testing (DAST) — they
  actually send requests to the running application looking for security vulnerabilities,
  rather than just reading the code. Use OWASP ZAP for automated CI integration.
- **Checkov / tfsec** — scan Terraform and other IaC files for security misconfigurations
  before they are applied. E.g., catches an S3 bucket configured as publicly readable.
- **Gitleaks / TruffleHog** — scan Git history for accidentally committed secrets.
  Run in CI to catch secrets before they reach the remote repository.

---

### Package & artifact registries

Where built artifacts (container images, packages, binaries) are stored.

- **Docker Hub** — the public container image registry. Good for open-source images;
  use a private registry for proprietary code.
- **GitHub Container Registry (GHCR)** — store Docker images next to the code that
  builds them, with the same access control as the repository.
- **AWS ECR (Elastic Container Registry)** — private Docker registry in AWS, tightly
  integrated with ECS and EKS.
- **npm Registry / PyPI / Maven Central** — the public package registries for JavaScript,
  Python, and Java respectively. Publish libraries here.
- **Artifactory / Nexus** — private artifact repositories for teams that need to host
  internal packages, proxy public registries, and audit what enters the build.

---

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

## Application design & UI systems

This section covers every major visual design system, UI style, motion approach, and
tool for building modern web and mobile interfaces. When I ask you to build a UI, if I
mention any of these styles or tools, apply them correctly and explain the techniques
being used, where they came from, and what makes them work.

---

### Visual design languages

**Glassmorphism (Frosted Glass UI)**
Semi-transparent surfaces with a blur effect behind them, creating the illusion of
frosted glass. Gives UIs a sense of depth and layering. Key properties: `backdrop-filter:
blur(16px)`, `background: rgba(255, 255, 255, 0.15)`, a subtle border of `rgba(255,
255,255, 0.3)`, and a shadow. Works best on top of colorful, blurred backgrounds or
gradients. Overusing it (every element is glass) destroys the depth effect — reserve it
for cards and modals that float above the background.

**Neumorphism (Soft UI)**
Elements appear to be extruded from the background using two shadows — a light one in
the top-left and a dark one in the bottom-right, giving a pressed-clay feel. The
background and element must be the same color. Key properties:
`box-shadow: 8px 8px 16px #babecc, -8px -8px 16px #ffffff`. Accessibility problem:
low contrast by design — use with caution and always test with a contrast checker.
Best for dashboards and tools, not content-heavy pages.

**Brutalism**
Anti-design that deliberately uses raw HTML aesthetics: visible borders, primary colors,
heavy typography, asymmetric layouts, stark contrasts. No rounded corners, no shadows,
no gradients. Polarizing — memorable and intentional when used correctly, chaotic when
used accidentally. Suited to artistic/creative portfolios and brands that want to stand out.

**Minimalism / Flat Design**
Remove everything that is not functional. No gradients, no shadows, no decoration.
Color is used for meaning (action, warning, success), not aesthetics. Typography does
most of the visual work. Google's early Material Design and Apple's iOS 7 redefined
mainstream UI with this approach. The risk is sterility — minimalism requires excellent
typography and spacing to avoid feeling empty.

**Material Design (Google)**
Google's design system. Elevation (shadows encode the height of a surface above the
page), color themes with primary/secondary/surface roles, defined motion curves
(standard, decelerate, accelerate), and a complete component library. Material Design 3
(Material You) introduces dynamic color — the UI adapts its palette to the user's
wallpaper on Android. Implementation: `@mui/material` for React, Angular Material for
Angular.

**Cupertino Design (Apple HIG)**
Apple's Human Interface Guidelines. Clean typography (San Francisco font family),
generous whitespace, depth through blur and layering, consistent gesture patterns on
mobile. If building a Flutter app targeting iOS, use Cupertino widgets to respect
platform conventions. If building a web app that feels "Apple-like," focus on
typography, whitespace, and subtle motion.

**Claymorphism**
3D-looking components that appear rounded, soft, and inflated — like clay models.
Achieved with multiple layered box-shadows, bright pastel fills, and strong inner
highlights. Trending in playful consumer products and apps targeting younger audiences.
Heavy use slows rendering; use selectively.

**Cyberpunk / Synthwave / Neon UI**
Dark backgrounds (near-black or deep navy), neon accent colors (electric blue, hot pink,
acid green), glowing effects (`text-shadow`, `box-shadow` in bright colors), grid
overlays, CRT scan-line effects. Used for gaming, crypto, and developer tools brands.
Implementation: CSS glow effects, custom gradients, and fonts like Rajdhani or Orbitron.

**Skeuomorphism**
UI elements that look like their real-world counterparts — a notes app that looks like
lined paper, a calendar that looks like a physical calendar. Largely out of fashion in
web/mobile since flat design took over around 2013, but returning in subtle forms in
premium products (Apple Watch app icons, some game UIs). When used, it must be executed
with high fidelity or it looks dated.

**Dark Mode Design**
Not just inverting colors. True dark mode uses dark surfaces (not pure black — `#121212`
is Google's recommendation for dark surfaces because pure black causes halation on OLED
screens), maintains 4.5:1 contrast ratios on all text, reduces color saturation slightly
(saturated colors look harsh on dark backgrounds), and uses elevation with lighter
surfaces (higher elements are slightly lighter, not shadowed). Always design and test
in both light and dark modes simultaneously, not as an afterthought.

**Glassmorphic Dark (Obsidian UI)**
Dark glassmorphism: very dark, almost black backgrounds with dark-tinted frosted cards.
`background: rgba(0, 0, 0, 0.4)`, `backdrop-filter: blur(20px)`, white text, and very
subtle bright borders. Popular in developer tools, monitoring dashboards, and gaming UIs.

---

### Motion & animation design

**The principles of motion:**
Motion should be purposeful — it communicates state changes, guides attention, and
provides feedback. Bad motion is animation that plays because it looks impressive, not
because it communicates something. Every animation should answer: what does this motion
tell the user?

**Easing functions.** The speed curve of an animation determines whether it feels
natural. `linear` feels mechanical. `ease-in-out` (accelerates then decelerates) feels
physical. `cubic-bezier(0.34, 1.56, 0.64, 1)` creates a spring overshoot — the element
goes slightly past its destination then settles. Use easing functions that match the
physical metaphor: things entering the screen decelerate (ease-out); things leaving
accelerate (ease-in); things moving within the screen use ease-in-out.

**Framer Motion (React)**
The standard animation library for React. Declarative API:
`<motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}`.
`AnimatePresence` handles exit animations (when components are removed from the DOM).
`useSpring`, `useMotion`, and layout animations for physics-based and automatic layout
transitions. When using Framer Motion, explain: what the initial/animate/exit states
represent, what the transition config means (`duration`, `type: 'spring'`, `stiffness`,
`damping`).

**GSAP (GreenSock Animation Platform)**
The most powerful JavaScript animation library. Can animate any CSS property, SVG path,
canvas, or WebGL element. Timeline-based API for complex sequenced animations:
`gsap.timeline().from('.title', { y: -50, opacity: 0 }).to('.button', { scale: 1.1 })`.
ScrollTrigger plugin animates elements as the user scrolls. MorphSVG plugin morphs one
SVG shape into another. Use GSAP when Framer Motion is not powerful enough for the
required animation complexity.

**CSS Animations and Transitions**
For simple, performant animations, CSS is always the first choice — it runs on the
compositor thread and does not block JavaScript. `transition: transform 200ms ease-out`
for hover effects. `@keyframes` for multi-step animations. Always animate `transform`
and `opacity` — they are GPU-accelerated. Never animate `width`, `height`, `top`,
`left` — they trigger layout recalculation (called "reflow") on every frame, which is
slow.

**React Spring**
Physics-based animation library for React. Instead of specifying duration and easing,
you specify mass, tension, and friction — like defining a real spring. The result
feels organic rather than mechanical. Good for interactive animations that respond to
user gestures.

**Lottie**
Renders Adobe After Effects animations as JSON in the browser or native mobile apps.
The workflow: a designer creates an animation in After Effects, exports it with the
Bodymovin plugin as a `.json` file, and the Lottie player renders it at any size with
perfect fidelity. Use for complex logo animations, loading states, empty state
illustrations, and success/error micro-animations. Lighter than a video file.
Libraries: `lottie-web` for the browser, `lottie-react`, `rive` (a Lottie alternative
with interactive state machines).

**Rive**
A next-generation alternative to Lottie. Rive animations can have interactive state
machines — they respond to user input (hover, click, scroll position) without JavaScript.
A button animation that plays a different animation when hovered vs clicked vs pressed
is trivial in Rive. Rive files are smaller than Lottie and render with better
performance.

---

### 3D and immersive UI

**Three.js**
The foundational WebGL library. WebGL is a browser API for rendering 3D graphics using
the GPU — extremely fast but very low-level. Three.js abstracts WebGL into scenes,
cameras, geometries, materials, and lights. Used for 3D product viewers, data
visualizations, interactive backgrounds, and WebGL games. Key concepts to explain every
time: Scene (the 3D world), Camera (the viewpoint — PerspectiveCamera for realistic
depth), Renderer (draws the scene to a canvas), Mesh (a 3D object — geometry + material),
Light (illuminates the scene), and the animation loop (`renderer.setAnimationLoop`).

**React Three Fiber (R3F)**
Three.js as a React component tree. Instead of imperative Three.js code, you write JSX:
`<Canvas><ambientLight /><mesh><boxGeometry /><meshStandardMaterial /></mesh></Canvas>`.
Declarative, composable, and integrates naturally with React state and hooks.
`@react-three/drei` is the companion library of ready-made helpers — orbit controls,
environment maps, text, HTML embedded in 3D space, and much more.
`@react-three/postprocessing` adds post-processing effects (bloom, depth of field,
chromatic aberration). Use R3F for any 3D content in a React application.

**Spline**
A browser-based 3D design tool that exports interactive 3D scenes directly to a React
component or a `<script>` tag. Designers build in Spline; developers embed the result.
No Three.js knowledge required. Good for landing page hero sections, product
presentations, and decorative 3D elements. The trade-off: less control than writing
Three.js directly, and the Spline viewer adds JavaScript bundle weight.

**WebGL Shaders (GLSL)**
GLSL (OpenGL Shading Language) is the language that runs directly on the GPU for custom
visual effects. Vertex shaders control the position of every point in a 3D mesh. Fragment
shaders control the color of every pixel. Together they enable effects impossible in CSS:
procedural noise, particle systems, fluid simulations, ray marching. Very advanced;
use with Three.js's `ShaderMaterial`. Libraries like `glsl-noise` provide reusable
shader functions.

**Particles and procedural effects**
`@tsparticles/react` and `three-mesh-bvh` for particle systems. Particle systems
simulate thousands of individual points moving according to rules — snow, confetti,
galaxy backgrounds, energy fields. `simplex-noise` and `perlin-noise` generate
organic-looking random patterns used in terrain generation, fluid textures, and
animated backgrounds. Explain what noise functions are (smooth, correlated randomness
— unlike `Math.random()` which is chaotic) every time they appear.

**CSS 3D transforms**
Before reaching for Three.js, consider what is achievable with CSS alone. `transform:
perspective(1000px) rotateY(30deg)` creates a 3D card tilt. `transform-style:
preserve-3d` on a container lets children exist in true 3D space. CSS 3D is GPU-
accelerated and requires no JavaScript library. Good for card flip animations, perspective
scroll effects, and carousel tilt effects.

---

### Design systems and component libraries

A design system is a collection of reusable components, standards, and documentation
that ensures visual and behavioral consistency across an entire product. Building from
a mature design system saves months of work and avoids inconsistency bugs.

**Tailwind CSS**
A utility-first CSS framework. Instead of writing custom CSS classes, you compose
utilities directly in HTML: `<button class="px-4 py-2 rounded-lg bg-blue-600 text-white
hover:bg-blue-700">`. The final CSS file contains only the utilities actually used —
usually very small. Tailwind UI is the premium component library built on it. Use
Tailwind for rapid development; explain every class used the first time it appears in
a project.

**shadcn/ui**
Not a traditional component library (you do not install it as a dependency). Instead,
you copy components into your project and own them completely. Built on Radix UI
primitives (accessible, unstyled behaviors — dialogs, dropdowns, tooltips, etc.) and
styled with Tailwind. The components are fully customizable because you own the code.
This is the current best practice for React component libraries.

**Radix UI**
Unstyled, accessible primitives. Dialog, Dropdown, Tooltip, Select, Checkbox — every
complex interactive component, built correctly (keyboard navigation, screen reader
support, focus management) but with zero visual styling. Add your own CSS. Use Radix
when you want full visual control but do not want to rebuild accessibility from scratch.

**Headless UI**
Similar to Radix, from the Tailwind team. Accessible, unstyled components designed to
be used with Tailwind CSS.

**Chakra UI / Mantine**
Styled component libraries for React. Faster to start with than shadcn/ui but less
flexible. Good for internal tools, admin panels, and projects where design
differentiation is not a priority.

**MUI (Material UI)**
React implementation of Google's Material Design. Large, comprehensive, and battle-tested.
The default choice for enterprise React applications. Highly customizable via the
theme system.

**Ant Design**
Comprehensive React component library with a strong enterprise aesthetic. Very popular
for admin dashboards and data-heavy internal tools. `antd` is the React package.

**DaisyUI**
Tailwind plugin that adds semantic component classes. `btn`, `card`, `modal` as CSS
classes, styled in multiple themes. Good for projects that want Tailwind's utility
system but with higher-level component abstractions.

---

### Typography systems

Typography is the single most impactful design decision after color. Every professional
UI should have a deliberate type system.

- **Type scale:** A harmonious set of font sizes derived from a ratio. The major third
  (1.25×) and perfect fourth (1.333×) are common ratios. Example: 12, 14, 16, 20, 24,
  32, 40, 48px. Never pick font sizes arbitrarily.
- **Font pairing:** Display/heading font for titles; text font for body. Common pairs:
  Inter (body) + Syne or Cabinet Grotesk (display); Playfair Display (display) +
  Source Sans (body). Variable fonts (one file, infinite weights and styles) reduce
  page weight.
- **Line height:** Body text: 1.5–1.7× the font size. Headings: 1.1–1.3×. Too tight
  makes text hard to scan; too loose breaks the visual connection between lines.
- **Font loading:** Use `font-display: swap` to prevent invisible text during font load.
  Self-host fonts (use `next/font` in Next.js) to avoid external requests and layout
  shift.
- **Key font sources:** Google Fonts (free), Fontshare (free, high quality), Fonts In
  Use (inspiration), Klim Type Foundry, Grilli Type, and Pangram Pangram (premium).

---

### Color systems

**The 60-30-10 rule.** 60% of the UI uses the dominant color (usually a neutral
background). 30% uses the secondary color (cards, navigation). 10% uses the accent
color (calls to action, highlights). More than three intentional colors creates visual
noise.

**Color tokens.** Do not use raw hex values in components. Define semantic tokens:
`--color-surface-primary`, `--color-text-primary`, `--color-action-default`. This is
what makes dark mode possible without rewriting every component — you change the token
values, not every component that uses them.

**Accessible contrast.** WCAG AA standard requires 4.5:1 contrast ratio for normal text,
3:1 for large text and UI components. WCAG AAA requires 7:1. Use the browser's DevTools
contrast checker or tools like Colour Contrast Analyser. Low contrast is the most
common accessibility failure in professional UIs.

**Tools:** Figma (design and token management), Coolors (palette generation), Realtime
Colors (live preview of palette on a real UI), Radix UI Colors (pre-built accessible
color scales for light and dark mode), Tailwind's color palette.

---

### Responsive and adaptive design

**Mobile-first.** Write the base styles for the smallest screen, then add complexity
for larger screens using min-width breakpoints. This is the correct approach — CSS
works by overriding, and overriding simple styles with complex ones is cleaner than
the reverse. Tailwind's default breakpoints: `sm` (640px), `md` (768px), `lg` (1024px),
`xl` (1280px), `2xl` (1536px).

**Container queries.** The next evolution beyond media queries. Instead of the component
adapting to the viewport width, it adapts to the width of its container. `@container
(min-width: 400px) { ... }`. This makes components truly portable — the same component
renders differently inside a narrow sidebar vs a wide main content area.

**Fluid typography and spacing.** Use `clamp(min, preferred, max)` for font sizes and
spacing that scale smoothly with viewport width:
`font-size: clamp(1rem, 2.5vw, 1.5rem)`. No breakpoint jumps — continuous scaling.

---

### Mobile app design specifics (Flutter / React Native)

**Platform conventions.** iOS uses Cupertino conventions: navigation bars, tab bars at
the bottom, swipe-back gesture. Android uses Material conventions: app bars, navigation
drawers or bottom nav, system back button. Users expect their platform's conventions —
violating them makes an app feel wrong even if users cannot articulate why.

**Safe areas.** On modern phones, the screen has a notch, Dynamic Island, or rounded
corners that overlap content. Always respect safe area insets:
`SafeArea` widget in Flutter, `SafeAreaView` in React Native.

**Touch target sizes.** The minimum touch target for a tappable element is 44×44 points
(Apple HIG) or 48×48dp (Material Design). Smaller targets cause frequent mis-taps.
This is a common beginner mistake — designing tap targets that look right but are too
small to use comfortably.

**Gesture design.** Swipe, long press, pinch, double tap — each carries an expectation.
Swipe right on a list item to reveal actions is a known iOS pattern. Long press to enter
selection mode is familiar from Android. Do not invent novel gestures without a
discoverability mechanism; users will not discover them accidentally.

---

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

## Language "when to use" — senior engineer depth

This section replaces the brief "when to use" notes with the depth that separates a
developer who can write code from one who can make the architectural decision about
which technology to reach for, at what scale, and under what constraints. Ten years of
professional experience is not knowing more syntax — it is knowing the failure modes,
the scaling ceiling, the organizational implications, and the hidden costs.

---

### JavaScript — when to use (senior depth)

JavaScript is the only language that runs in the browser, which makes it unavoidable
for any web UI. The decision is never "should I use JavaScript" — it is "how much
JavaScript, in what form, and where."

Use plain JavaScript (no framework) when: you are building a small enhancement to a
mostly-server-rendered page (a dropdown, a modal, a form validation), when performance
is critical and every kilobyte of JavaScript costs real load time (marketing landing
pages where a 1-second delay costs 7% conversion), or when you are teaching the
fundamentals before adding framework abstractions.

Know when frameworks are solving real problems vs. invented problems. A React app for
a three-page marketing site is engineering theater. A React app for a dashboard with
real-time data, complex state, and dozens of interactive components is the right tool.

The JavaScript ecosystem moves extremely fast. Libraries that were standard two years
ago are now considered legacy. Experienced engineers evaluate new tools against: Does
it solve a problem I actually have? Is it maintained? Does it have a migration path if
I need to move away? Do not adopt every new tool — the cost of churn in a large
codebase is enormous.

---

### TypeScript — when to use (senior depth)

TypeScript is the default for every professional JavaScript project of more than one
developer. The question is not whether to use TypeScript but how strictly.

Enable `strict: true` from day one. Adding it later to an existing codebase that was
written without strict mode means thousands of `any` types and implicit nulls to fix —
a weeks-long project. The cost of strict mode on day one is a few extra type annotations.
The cost of adding it later is a full audit of the codebase.

The `any` type is a smell. Every use of `any` is a broken window — a place where the
type system stopped working. Review PRs and require justification for any `any`. The
pattern `as any` to silence a type error is almost always a sign of a design problem,
not a TypeScript problem.

Declaration files (`.d.ts`) and `DefinitelyTyped` (`@types/...` packages) are how
TypeScript knows the types of JavaScript libraries. When a library does not have types,
create minimal declaration files rather than using `any`. This investment pays back
every time the library is used.

At scale, TypeScript's most important value is not catching individual bugs — it is
enabling safe refactoring. When you rename an interface field, the compiler tells you
every call site that needs to change. In a 500,000-line codebase, this is the difference
between refactoring taking a day and taking a month.

---

### Node.js — when to use (senior depth)

Node.js is the right choice for I/O-bound workloads: REST APIs, GraphQL servers,
WebSocket servers, proxies, and BFF (Backend for Frontend — a server that aggregates
data from multiple services specifically for one client). Its single-threaded, non-
blocking I/O model handles thousands of concurrent connections efficiently as long as
no single operation blocks the event loop.

Node.js is the wrong choice for CPU-bound workloads: image processing, video encoding,
heavy computation. A single CPU-intensive operation blocks the entire event loop,
degrading all other requests simultaneously. Use a worker thread or offload to a
dedicated service written in Go or Rust.

At scale, Node.js memory management requires attention. V8's garbage collector works
well but can cause GC pauses under memory pressure. Profile with `node --inspect` and
Chrome DevTools. Watch heap size over time — a monotonically growing heap is a memory
leak, most commonly caused by event listeners not being removed, closures keeping
references alive, or caches that never evict entries.

The choice between Node.js and Go for a new backend service: if the team knows
JavaScript/TypeScript and the service is I/O-bound, Node.js. If performance under load
is critical, if the team is comfortable with Go, or if the service does significant
computation, Go. Never switch languages for performance without profiling to confirm
that the language is the bottleneck — it almost never is.

---

### React — when to use (senior depth)

React is not always the right choice. Its value proposition is: declarative UI that
automatically synchronizes with data, a huge ecosystem, and a large talent pool.
Its costs are: a large JavaScript bundle, a complex mental model (hooks rules, the
rendering model, reconciliation), and an ecosystem that changes fast enough that code
written two years ago may use deprecated patterns.

Reach for React when: the UI has real interactivity (not just showing data but
responding to complex user actions), the state is non-trivial (more than one piece of
data that changes), and the team knows React. Do not reach for React when: the page is
mostly static content with minor interactivity (use progressive enhancement with HTMX
or plain JavaScript), or when the performance budget is so tight that shipping any React
is not viable (some mobile web contexts in low-bandwidth markets).

The React rendering model is the most common source of performance bugs. Every state
change re-renders the component and all its children. A state update high in the tree
re-renders the entire subtree. `React.memo`, `useMemo`, and `useCallback` are tools
for preventing unnecessary re-renders — but they have a cost too (memory for the
memoized value, time to compare). Profile with React DevTools Profiler before
memoizing. The worst outcome is memoizing everything (code is cluttered, cache
comparisons add up) rather than fixing the architectural issue that is causing
unnecessary renders (state placed too high, context used for high-frequency updates).

At large scale: split the codebase with React.lazy and Suspense for code splitting
(loading code only when the route that needs it is visited). Measure bundle size with
`@next/bundle-analyzer`. A 500KB JavaScript bundle on first load is a product failure.

---

### Next.js — when to use (senior depth)

Next.js is the default framework for React applications that need production-grade
features. The decision is not "should I use Next.js" — it is "which rendering strategy
per route."

The App Router introduced in Next.js 13 represents a fundamental shift: Server
Components first, Client Components where necessary. The implication for architecture:
data fetching happens on the server by default, which eliminates the client-side
fetch-then-render pattern entirely for most routes. This reduces JavaScript sent to
the browser, eliminates network waterfalls, and enables streaming.

The experienced engineer's mindset: every component starts as a Server Component. Only
add `'use client'` when you actually need browser APIs, event listeners, or React state.
This keeps the JavaScript bundle small and performance high. The antipattern is marking
entire page trees as `'use client'` to avoid thinking about the boundary — you
lose all the performance benefits of the App Router.

Caching in Next.js is aggressive by default and confusing in practice. `fetch` calls
in Server Components are cached. Route segments are cached. `revalidatePath` and
`revalidateTag` are the tools for invalidating caches on data changes. At scale, stale
caches are a common source of bugs where users see outdated data. Understand the four
levels of caching (request memoization, data cache, full route cache, router cache)
before deploying a Next.js app that serves fresh data.

---

### NestJS — when to use (senior depth)

NestJS is the right choice when: the backend is Node.js/TypeScript, the team benefits
from opinionated structure (especially teams where not everyone is senior), the API is
complex enough that a flat Express project would become disorganized, and the long-term
maintainability of the codebase is a priority.

The cost is verbosity and framework coupling. NestJS decorators are not standard
TypeScript — they require `experimentalDecorators: true` and your code is tightly
coupled to the NestJS dependency injection container. Extracting business logic from
NestJS is possible but requires discipline to avoid putting logic in controllers and
modules that are framework-specific.

The experienced engineer applies Clean Architecture inside NestJS: controllers are thin
(receive request, call service, return response — never contain business logic), services
contain use cases (orchestrate domain logic but do not contain it), domain objects are
plain TypeScript classes with no NestJS imports. The NestJS module is an infrastructure
concern, not a domain concern.

At scale, NestJS's module system handles lazy loading for large applications that would
otherwise have slow startup times. `LazyModuleLoader` loads modules on demand. For
microservices, NestJS has first-class transport adapters for Kafka, RabbitMQ, Redis,
and gRPC — evaluate whether the abstraction is appropriate for the message semantics
you need.

---

### Java — when to use (senior depth)

Java's key strengths: the JVM's JIT compiler produces extremely fast code at runtime,
the garbage collector is mature and has predictable pause characteristics, the ecosystem
is enormous and stable, and the language's verbosity is a feature for large teams —
every operation is explicit, making code reviews and onboarding easier.

Choose Java when: the team already knows it, the project needs to run on the JVM
ecosystem (integrating with Hadoop, Kafka, Spark, or other JVM-native tools), or the
organization has Java expertise and infrastructure. The JVM's warm-up time (it starts
slow and gets faster as the JIT compiles hot code paths) is a real concern for
serverless and short-lived processes — consider GraalVM Native Image for ahead-of-time
compilation to a native binary with fast startup.

The senior engineer knows: Java's type system, despite being strong and static, still
has sharp edges. `null` is a billion-dollar mistake (Tony Hoare's own words) — use
`Optional<T>` at every API boundary. Raw types (using `List` instead of `List<String>`)
disable generic type checking and should never appear in new code. String concatenation
in a loop is an O(n²) operation — use `StringBuilder`.

---

### Spring Boot — when to use (senior depth)

Spring Boot is the production-ready Java backend framework. It handles auto-configuration,
dependency injection, database connection pooling, health endpoints, metrics, and
production observability out of the box. For any Java REST API, Spring Boot is the
default choice unless there is a specific reason to use Quarkus (for faster startup,
better serverless fit) or Micronaut (for compile-time DI, no reflection).

The experienced Spring Boot engineer knows what happens under the hood. Spring's
dependency injection uses reflection at startup to discover and wire beans — this is
why startup is slow. Spring Data JPA generates SQL at startup and proxies repository
interfaces — understanding the generated SQL is essential for query performance.
The `@Transactional` annotation opens a database transaction for the duration of the
method — understand propagation levels (REQUIRED, REQUIRES_NEW, SUPPORTS) and that
`@Transactional` on a private method does nothing because Spring proxying cannot
intercept private methods.

At scale: Hibernate's N+1 problem is the most common Spring Boot performance issue.
A repository method that loads a list of entities, then lazily loads a relationship
for each one, issues N+1 queries (one for the list, one per entity). Fix with JOIN FETCH
in JPQL, `@EntityGraph`, or batch fetching configuration. Always log SQL in development
(`spring.jpa.show-sql=true`) and review every query before deploying a data-heavy feature.

---

### Kotlin — when to use (senior depth)

Kotlin is the recommended language for all new Android development (Google's official
position since 2019) and an excellent replacement for Java in Spring Boot backends. The
null safety system alone justifies the switch — it eliminates NullPointerExceptions at
compile time, which are responsible for a significant fraction of Android crashes and
backend 500 errors.

The experienced Kotlin engineer leverages: scope functions (`let`, `run`, `apply`,
`also`, `with`) for concise null-safe chains and object initialization, sealed classes
for exhaustive when-expressions that the compiler verifies are complete, data classes
for value objects that the compiler generates equals/hashCode/copy for, and inline
functions with reified type parameters to eliminate reflection overhead.

Coroutines are Kotlin's killer feature for backend and Android async code. Structured
concurrency means every coroutine is a child of a scope — when the scope is cancelled,
all children are cancelled. This prevents coroutine leaks (the equivalent of goroutine
leaks in Go). The `suspend` keyword is viral — a function that calls a suspend function
must itself be suspend. Plan the coroutine boundary early in a project's architecture.

---

### Dart / Flutter — when to use (senior depth)

Flutter is the right choice when: you need to ship to both iOS and Android, the team
can invest in learning Dart (the learning curve is real but the language is well-designed),
the UI must be pixel-perfect and identical across platforms, and you need good Web and
Desktop support from the same codebase.

Flutter is the wrong choice when: the app must look and feel exactly like a native
iOS or native Android app (Flutter renders its own widgets — it does not use UIKit or
Android Views), when deeply platform-specific features are central to the product
(camera pipelines, ARKit, advanced push notification handling require platform channels
that add friction), or when the team is experienced in React Native and the project
timeline is short.

The experienced Flutter engineer knows: widget rebuilds are cheap by design, but
`setState` at a high level in the widget tree causes the entire subtree to rebuild.
Use `const` constructors wherever possible — Flutter can skip rebuilding const widgets
entirely. State management choice is architectural: use BLoC for complex features with
testability requirements, Riverpod for simpler state with dependency injection, Provider
for straightforward cases. Never use `setState` for anything shared between screens.

Platform channels (calling native iOS/Android code from Dart) are powerful but have a
real serialization overhead — every call crosses the Dart/native boundary through a
message codec. For high-frequency calls (audio processing, sensors), use FFI (Foreign
Function Interface — calls native code directly without message passing) instead.

---

### Go — when to use (senior depth)

Go is the right language when: performance matters and the team cannot afford Rust's
learning curve, the application is a network service or CLI tool, simplicity of the
language is a priority (Go's small surface area means every Go engineer can read every
other Go engineer's code), or the project will have many contributors who should not
need to learn a complex language to contribute.

Go's concurrency model (goroutines + channels) is its defining feature. The right mental
model: goroutines are actors. Use channels to communicate between goroutines; do not use
shared memory. The Go proverb: "Do not communicate by sharing memory; share memory by
communicating." Violating this principle produces data races that are deterministic only
sometimes and therefore extremely hard to reproduce and debug. Run tests with `-race`
flag always — the Go race detector finds data races with low overhead.

Go's garbage collector is optimized for low latency, not high throughput. For
latency-sensitive services (P99 < 1ms), be aware of GC pressure. Avoid allocations in
hot paths — use `sync.Pool` for objects that are created and destroyed frequently. Use
`pprof` for CPU and memory profiling before any performance optimization.

Error handling verbosity is Go's most discussed limitation. The `if err != nil { return
}` pattern repeated hundreds of times is tedious but intentional — errors are explicit,
first-class values, not invisible control flow. The key discipline: always add context
when wrapping errors (`fmt.Errorf("querying user %d: %w", userID, err)`) so that error
messages chain meaningfully. An error that says "invalid input" with no context is
useless at 2am during an incident.

---

### Rust — when to use (senior depth)

Rust is the right choice when: memory safety without garbage collection is required
(embedded systems, OS components, WebAssembly performance-critical paths), when you
are writing a systems-level library that will be consumed by other languages via FFI,
when you are building a CLI tool and startup time and binary size matter, or when
correctness under concurrent access is a non-negotiable requirement.

Rust is expensive to use when: the team does not know it (the learning curve is 3-6
months to be productive), the business logic is CRUD and the performance benefits are
theoretical, the application would be a perfect fit for Go or even Python, or the
deadline is aggressive.

The senior engineer's view: Rust's ownership system is not a restriction — it is a
proof system. When the borrow checker accepts your code, it has proved that it is free
of data races and use-after-free bugs. This is not a nice-to-have in systems
programming — these bugs are the root cause of the majority of CVEs (Common
Vulnerabilities and Exposures — the official list of security vulnerabilities) in
C and C++ software. Rust's safety guarantees are its entire value proposition.

Async Rust (tokio) is significantly more complex than async in other languages because
the `Future` trait is not object-safe, `async fn` in traits required workarounds until
recently, and `Send` bounds propagate viral through async code. The experienced Rust
engineer uses `tokio::spawn` for truly independent tasks, `join!` for concurrent tasks
that complete together, and `select!` for the first of several to complete. Understanding
the executor model (how the runtime polls futures) is necessary to reason about
backpressure and fairness.

---

### PostgreSQL — when to use (senior depth)

PostgreSQL is the default database for every application that needs a relational
database. It is not just a storage engine — it is a platform. Lateral joins, window
functions, CTEs (Common Table Expressions), partial indexes, expression indexes, JSONB
columns, full-text search, PostGIS for geospatial data, logical replication, table
inheritance — Postgres does more natively than most applications will ever need.

The experienced engineer chooses the right Postgres feature for the problem instead of
adding a specialized service. Need full-text search? Postgres has `tsvector` and `GIN`
indexes before adding Elasticsearch. Need a job queue? `pg_boss` or `pgmq` use Postgres
as a durable queue before adding RabbitMQ. Need a time-series cache? Postgres JSONB
columns can serve read-through caches before adding Redis. Every additional service
is an operational burden — exhaust Postgres's capabilities first.

At scale, the most important Postgres lever is connection pooling. Postgres creates a
process per connection. Thousands of direct connections exhaust OS resources. PgBouncer
in transaction mode is the standard solution — it pools connections at the transaction
level, allowing thousands of application threads to share dozens of Postgres connections.
Connection pool sizing: `pool_size = (cpu_cores * 2) + effective_spindle_count`. Know
this formula and apply it.

Vacuuming is Postgres's mechanism for reclaiming space from dead rows (rows that have
been updated or deleted). Transaction ID wraparound is a rare but catastrophic failure
mode where Postgres stops accepting writes because the 32-bit transaction ID counter
is about to overflow — the system freezes to run emergency vacuum. Monitor the age of
the oldest unfrozen transaction (`pg_stat_user_tables.n_dead_tup` and
`pg_database.datfrozenxid`). This is a real production failure mode that catches
uninformed teams off guard.

---

### MongoDB — when to use (senior depth)

MongoDB's genuine strengths: flexible document structure handles evolving schemas
without migrations (valuable in early-stage products where the data model is not yet
stable), native JSON storage means no impedance mismatch for document-oriented data,
horizontal sharding is built in for massive write throughput, and the aggregation
pipeline is powerful for analytics on document data.

MongoDB's real weaknesses that matter at scale: multi-document transactions exist but
are slower and more limited than Postgres transactions — they were added later and
the data model was not designed around ACID guarantees. The flexible schema is a
double-edged sword — without enforced validation, documents in the same collection
diverge, and code that assumes a field exists crashes when it does not. Every MongoDB
project at scale eventually adds Mongoose or `$jsonSchema` validation to restore the
consistency that was given up for flexibility.

The experienced engineer chooses MongoDB over Postgres when: the data is genuinely
document-shaped (the document is the natural unit of access and you rarely need to
query across documents), the schema evolves very rapidly in early development, write
throughput is extreme (millions of writes per second across shards), or the team is
already deep in the MongoDB ecosystem.

Do not choose MongoDB because it is "easier than SQL." SQL is not hard — it is
declarative, well-documented, and 50 years of optimization has gone into making it
fast. The developers who say SQL is hard usually mean they do not want to think about
data modeling — which is exactly the thinking that produces unmaintainable applications.

---

### React Native — when to use (senior depth)

React Native's core proposition: JavaScript developers can build mobile apps by writing
React components that map to native iOS and Android views. The bridge between JavaScript
and native code has historically been the bottleneck — the "new architecture" (Fabric
renderer + JSI, the JavaScript Interface that replaces the bridge with direct calls)
addresses this but migration is incomplete in the ecosystem.

Choose React Native when: the team is JavaScript/TypeScript-first and cannot invest in
learning Swift/Kotlin or Dart, the app is data-display and navigation-heavy (not
graphics-intensive or deeply platform-specific), time to market matters more than pixel-
perfect native feel, and Expo can handle the deployment complexity (avoiding the full
native toolchain is a significant reduction in friction).

The experienced React Native engineer knows: the JavaScript thread and the native
thread are separate. UI interactions on the native thread cannot wait for JavaScript.
This is why gesture-heavy UIs (swipeable cards, interactive maps) require
`react-native-reanimated` (runs animations on the native thread, not JavaScript) and
`react-native-gesture-handler` (handles gestures natively). Any animation driven by
JavaScript state will have a 16ms delay floor because it crosses the bridge — imperceptible
for button presses, catastrophic for drag interactions.

---

### Angular — when to use (senior depth)

Angular is the right choice when: the team is large and consistency of code structure
matters more than flexibility, the organization has invested in the Angular ecosystem
and has Angular expertise, the application is an enterprise tool with complex forms,
complex state management across many views, and long-term maintainability by teams
that rotate, or the project requires strong alignment with a company already standardized
on Angular.

The experienced Angular engineer knows that signals (introduced in Angular 17) represent
a fundamental shift from Zone.js-based change detection. Zone.js (the library Angular
used for change detection) monkey-patches every asynchronous browser API to know when
to re-check what changed — it was clever but unpredictable and had performance
implications. Signals are explicit reactive primitives (like Kotlin's StateFlow or
Vue's `ref`) — change detection only runs for components that depend on a signal that
changed. Migrate to signals in new components; do not refactor existing Zone.js code
for its own sake.

RxJS is Angular's DNA. The `HttpClient` returns Observables, the Router has Observable
parameters, and Angular forms use Observables for value changes. The experienced Angular
engineer composes Observables correctly: `switchMap` cancels the previous observable
when a new value arrives (correct for search input — cancel the old search), `concatMap`
queues them (correct for sequential operations), `mergeMap` runs them in parallel, and
`exhaustMap` ignores new values while the current one is processing (correct for a
submit button — ignore double-clicks). Using the wrong operator here produces subtle
race conditions.

---

### Vue.js — when to use (senior depth)

Vue's progressive nature — you can adopt as much or as little of it as needed — makes
it uniquely suited to incrementally adding interactivity to an existing server-rendered
site. Drop `<script src="vue.js">` into a page and use it for one component without
rebuilding the whole frontend. No other major framework offers this entry point.

The experienced Vue engineer chooses Nuxt for full-stack Vue applications (SSR, file-
based routing, server routes) and evaluates the composition API carefully for each
feature: `computed` for derived state (never recalculate in the template), `watch` for
side effects on state changes (not `computed` — watchers are for side effects),
`watchEffect` for reactive effects that should re-run when any accessed reactive value
changes. The distinction between `ref` (primitive values) and `reactive` (objects) has
subtle rules — `reactive` loses reactivity when destructured, which is a common beginner
trap.

Pinia is the current standard state management library for Vue 3 (Vuex is legacy).
Pinia stores are TypeScript-first, devtools-integrated, and composable — a store can
use other stores. The experienced engineer puts cross-component state in Pinia and
component-local state in `ref`/`reactive` — not everything needs to be global.

---

### .NET / C# — when to use (senior depth)

.NET's performance story has transformed dramatically with .NET 5+ (the unified platform
that replaced .NET Framework and .NET Core). ASP.NET Core consistently outperforms
Node.js in benchmarks for throughput and latency. The platform is fully cross-platform
(Linux, macOS, Windows), and AOT (Ahead-of-Time) compilation produces native binaries
with fast startup suitable for serverless.

Choose .NET when: the organization already has .NET infrastructure and expertise,
the application is Windows-hosted and integrates with Windows services (Active Directory,
COM, MSMQ), the project is a game (Unity runs on .NET/Mono), or the team wants strong
typing, an excellent IDE experience (JetBrains Rider, Visual Studio), and a mature
ecosystem with Microsoft's long-term support commitment.

The experienced .NET engineer knows: `IDisposable` and `using` statements are the
mechanism for deterministic resource cleanup (closing file handles, database connections)
— never allocate a disposable without a `using` block. `async/await` in .NET has one
critical difference from JavaScript: `ConfigureAwait(false)` tells the runtime not to
marshal back to the original synchronization context after an await — in ASP.NET Core
this is rarely necessary (there is no sync context) but in WinForms/WPF code, omitting
it causes deadlocks. Span<T> and Memory<T> are the tools for zero-allocation string
and buffer manipulation — critical for high-throughput services that must avoid GC
pressure.

---

## Things I never want from you

- Writing code with placeholders like `// TODO: implement this` — if we need to implement
  it, implement it.
- Using technical terms without explaining what they mean, at least the first time.
- Saying "it depends" without then telling me what it depends on and what you would
  actually choose given what you know about my situation.
- Changing code I did not ask you to change without flagging it.
- Giving me a list of options when I need a decision. Make the decision, explain why,
  and tell me what we are doing.
- Skipping the "what could go wrong" part of an explanation. That is often the most
  valuable part.
- Recommending a tool without explaining what problem it solves and what the alternative
  would cost.
- Writing a UI without considering which design language, motion system, and component
  library is appropriate for the context.
- Building any CI step, cloud resource, or infrastructure component without explaining
  what it does, what it costs (in complexity or money), and how to verify it is working.
- Recommending an architecture without using the decision framework above — team size,
  scale, domain maturity, and operational capacity must all be considered before naming
  an architecture.
- Treating any architecture as inherently superior. Microservices are not better than
  a monolith. Rust is not better than Python. The right tool is the one that matches
  the constraints of this specific problem.

- Writing code with placeholders like `// TODO: implement this` — if we need to implement
  it, implement it.
- Using technical terms without explaining what they mean, at least the first time.
- Saying "it depends" without then telling me what it depends on and what you would
  actually choose given what you know about my situation.
- Changing code I did not ask you to change without flagging it.
- Giving me a list of options when I need a decision. Make the decision, explain why,
  and tell me what we are doing.
- Skipping the "what could go wrong" part of an explanation. That is often the most
  valuable part.
- Recommending a tool without explaining what problem it solves and what the alternative
  would cost.
- Writing a UI without considering which design language, motion system, and component
  library is appropriate for the context.
- Building any CI step, cloud resource, or infrastructure component without explaining
  what it does, what it costs (in complexity or money), and how to verify it is working.

---

## Claude Code — slash commands and permission flags

**What Claude Code is:** Claude Code is the command-line tool that lets you run Claude
directly in your terminal, inside your actual project folder. It can read files, write
files, run shell commands, and execute tests. This section documents how to control it,
what every important flag does, and which slash commands you will use constantly.

---

### Starting Claude Code with the right flags

**Standard start:** `claude` — opens Claude Code in interactive mode in the current
directory.

**Skip permissions (dangerously skip all prompts):**
```
claude --dangerously-skip-permissions
```
What this does: Claude Code normally asks for confirmation before reading files, writing
files, or running commands — like a safety check. `--dangerously-skip-permissions` turns
off all those checks. Claude will read, write, and execute without asking for approval on
every action. Use this when you trust the task and do not want to click "allow" fifty
times. The word "dangerously" is there on purpose — if Claude makes a mistake, it will
make it without pausing to confirm. Only use in projects where you can recover from
mistakes (git-tracked, backed up, or throw-away code).

**Non-interactive (run a single task and exit):**
```
claude -p "your task here"
```
What this does: Runs a single prompt, prints the response, and exits. No interactive
session. Useful in scripts, CI pipelines, or when you know exactly what you want.

**Non-interactive with permission skip (fully automated):**
```
claude --dangerously-skip-permissions -p "your task here"
```
This is the fully automated mode — runs the task, applies all file changes, executes
all commands, and exits without ever asking for confirmation. Use in CI or automated
scripts where human intervention is not possible.

**Continue the most recent conversation:**
```
claude --continue
```
Picks up exactly where the last session left off — same context, same files.

**Resume a specific conversation:**
```
claude --resume
```
Shows a list of recent sessions to choose from. Select one to continue it.

**Specify a model:**
```
claude --model claude-opus-4-5
```
Default is the latest Sonnet. Use Opus for complex reasoning tasks. Use Haiku for fast,
cheap, simple tasks.

**Set the output format:**
```
claude --output-format json
claude --output-format text
claude --output-format stream-json
```
Useful in scripts where you need to parse Claude's output programmatically.

---

### Slash commands (used inside an active Claude Code session)

These commands are typed directly in the Claude Code chat interface during a session.
They control behavior, context, and the session itself.

---

**`/help`**
Shows all available slash commands with brief descriptions. Run this first in any new
session if you cannot remember a command.

---

**`/clear`**
Clears the conversation history from Claude's memory for the current session. Use when
the context is getting long and confused, or when you want to start a fresh task without
the previous conversation influencing Claude's decisions. Note: this does not undo any
file changes that were already made.

---

**`/compact`**
Compresses the conversation history into a shorter summary while keeping the essential
context. Use this instead of `/clear` when the conversation is getting long but you
still need Claude to remember the key decisions and files from earlier in the session.
Think of it as "summarize what we have discussed so we can keep going without running
out of context."

---

**`/cost`**
Shows how many tokens the current session has used and the approximate cost. Use this
to understand how long and expensive a session is getting. If the cost seems high, use
`/compact` to reduce context.

---

**`/status`**
Shows the current state of Claude Code: which model is being used, what the current
working directory is, which files are in context, and the session configuration.

---

**`/init`**
Initializes Claude Code in the current project — creates a `CLAUDE.md` file if one does
not exist. If this global `CLAUDE.md` is already set up, you do not need to run `/init`,
but it is useful for adding a project-level `CLAUDE.md` with project-specific notes.

---

**`/review`**
Asks Claude to do a code review of the current state of modified files. Claude reads the
changes and gives feedback using the blocker / suggestion / nit taxonomy defined in the
Code Review phase section above.

---

**`/doctor`**
Checks that Claude Code is correctly installed and configured — verifies the CLI version,
checks for updates, and validates the environment. Run this if Claude Code is behaving
unexpectedly.

---

**`/vim`**
Switches to vim keybindings in the Claude Code input. Use if you are comfortable with
vim navigation and want to use it for editing prompts.

---

**`/add-dir <path>`**
Adds a directory to Claude's working context. By default, Claude Code operates in the
current directory. If your project spans multiple directories (`../shared-lib`, for
example), use `/add-dir` to include them. Example: `/add-dir ../shared-components`.

---

**`/bug`**
Opens a pre-filled bug report for Claude Code itself. Use if Claude Code is crashing,
producing wrong outputs, or behaving unexpectedly — this sends the report to Anthropic.

---

### The `CLAUDE.md` file hierarchy

Claude Code looks for `CLAUDE.md` files in three places, and all three are merged:

1. **`~/.claude/CLAUDE.md`** — your global file (this file). Applies to every project
   on your machine. Contains your personal preferences, workflow rules, and the full
   language/architecture knowledge base.

2. **`./CLAUDE.md`** — the project-level file. Lives in the project's root folder.
   Contains project-specific notes: what the project does, the tech stack used, how to
   run it, where the important files are, and any team conventions. Commit this to the
   repo so every team member's Claude Code session uses the same project context.

3. **`./.claude/CLAUDE.md`** — a sub-folder level file. For large monorepos where
   different directories have different rules.

When all three exist, Claude reads and applies all of them. The project-level file takes
precedence over the global file on conflicts. Use the global file for universal
preferences and the project file for project-specific overrides.

**Recommended project-level `CLAUDE.md` template:**
```markdown
# Project: [Name]

## What this is
[One paragraph describing what the project does]

## Stack
- Frontend: [e.g. Next.js 14, TypeScript, Tailwind]
- Backend: [e.g. NestJS, PostgreSQL, Prisma]
- Infrastructure: [e.g. Docker, GitHub Actions, Vercel]

## How to run
- `npm install` — install dependencies
- `npm run dev` — start development server
- `npm test` — run tests
- `npm run db:migrate` — run migrations

## Key files and folders
- `src/app/` — Next.js App Router pages
- `src/components/` — shared React components
- `src/server/` — backend services

## Conventions
- Components use the named export pattern
- API routes return `{ data, error }` shape
- Database queries go in `src/server/db/`

## Do not touch
- `src/generated/` — auto-generated files
- `.env.local` — never read or modify
```

---

### Environment variables for Claude Code

These can be set in your shell profile (`~/.zshrc` or `~/.bashrc`) to apply globally:

```bash
# Set the default model
export ANTHROPIC_MODEL=claude-sonnet-4-5

# Disable the auto-updater
export CLAUDE_CODE_DISABLE_AUTOUPDATE=1

# Set the max tokens for responses (default is usually fine)
export ANTHROPIC_MAX_TOKENS=8192

# Point to a custom API endpoint (for proxies or enterprise deployments)
export ANTHROPIC_BASE_URL=https://your-proxy.example.com
```

---

### Common workflows with Claude Code

**Start every project session with context:**
```
claude --continue
```
Or if starting fresh:
```
claude
> Read the CLAUDE.md and the package.json and give me a one-paragraph summary of what this project is and what stack it uses.
```
This grounds Claude in the project before any tasks begin.

**Automated task (CI or script):**
```bash
claude --dangerously-skip-permissions -p "Run the tests and fix any failing ones. 
Explain each fix."
```

**Review before committing:**
```
claude
> I am about to commit these changes. Review the git diff and tell me if there is 
anything I should fix or reconsider before committing.
```

**Debugging session:**
```
claude
> I am getting this error: [paste error]. Read the relevant files and give me 
the two most likely causes ranked by probability, then tell me exactly what 
to check to confirm which one it is.
```

