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

