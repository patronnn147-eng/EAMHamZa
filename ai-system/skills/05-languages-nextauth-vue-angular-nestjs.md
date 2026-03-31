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

