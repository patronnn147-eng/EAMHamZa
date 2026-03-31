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

