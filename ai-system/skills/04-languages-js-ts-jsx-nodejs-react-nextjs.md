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

