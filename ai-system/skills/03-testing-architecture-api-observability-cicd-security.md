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

