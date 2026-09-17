# Technical Defense — Narration Script

Total budget: 20:00 including the demo. Demo video = 6:47. Remaining ≈ 14:03 across 29 content slides, weighted by how much each needs. Paced ~120–140 wpm. (Sequence diagram slide + the new checkpoints slide push this ~50s past the original 20:00 target — trim a line somewhere if you need it exact.)

Note: slides 30 and 31 in the current deck are identical ("Live Demonstration" / "DEMO", both page "27") — an accidental duplicate. Say the cue once; delete one of the two slides when convenient.

---

### 3 — Host Company *(~15s)*
> "SagemCom builds high-value communication equipment — set-top boxes, internet boxes, smart meters. Seven months here, in Software Engineering and Innovation, building internal digital tools for maintenance across four production lines: SMT assembly, functional testing, automated quality control."

### 4 — General Context *(~30s)*
> "Maintenance has three stages. Reactive: you fix it after it breaks, at maximum cost. Preventive: fixed calendar intervals, regardless of real condition — parts replaced too early, or failures slip through between visits. Predictive, the target here: continuously reading a machine's own signals — temperature, torque, wear — to catch degradation before the stoppage, because in most cases, that degradation is already visible in the data."

### 5 — Problem Statement *(~30s)*
> "So the real question: how do you cover, in one platform, both classic operational management and predictive maintenance? That means three things at once — the EAM foundation: users, machines, work orders, scheduling; the ML layer: failure risk, remaining life, anomalies, prioritization; and intelligent field support: alerts that explain themselves, and an assistant that combines documentation with real-time machine status."

### 6 — Existing Solutions *(~30s)*
> "I looked at what's already out there. SAP PM — full EAM coverage, but heavy licensing. IBM Maximo — mature, with a predictive add-on, strong on documents. GE Digital's Predix — built for IoT and large-scale reliability analytics. And at the other end, generic CMMS tools or plain spreadsheets, for when there's no budget for a full suite."

### 7 — Critique *(~30s)*
> "These tools are proven, but not built for this context. Predictive ML shows up as a costly add-on, poorly explained to technicians. None of them tie a conversational assistant to real-time machine status. That's the gap this fills: one platform tailored to SagemCom's fleet, no heavy licensing, and automation that's always guarded — nothing fires without human approval."

### 8 — Proposed Solution *(~30s)*
> "So here's what I built: a full EAM foundation underneath, seven predictive models on top, fused through Dempster-Shafer evidence theory into one honest health score. Every prediction ships with a plain-language explanation. A RAG assistant merges documentation with live machine status into every answer. And automation stays guarded — parts get proposed, never auto-ordered, without a human signing off."

### 9 — Actors *(~30s)*
> "Four roles, four different views of the system. The Operations Manager just needs a quick read on machine status. The Head Technician plans interventions, arbitrates priority, and approves procurement. The Technician executes work orders, checks health status, and can ask the assistant directly. And the Administrator manages users, machines, and the whole document base — the overall view."

### 10 — Use Case Diagram *(~15s)*
> "This use case diagram maps every one of those actions back to a role — who can trigger what, across the whole system."

### 11 — Functional Requirements *(~30s)*
> "Nine functional areas, end to end: authentication, machine management, order management, scheduling, the seven ML predictions, alerts, the conversational assistant, dashboards, and archiving with full traceability. Two rules cut across all nine: every prediction explains itself in plain language, and the system degrades honestly — it reports missing data instead of inventing a number."

### 12 — Non-Functional Requirements *(~30s)*
> "Seven non-functional requirements shaped every decision. Performance: under two seconds for normal operations, under five for full ML inference. Availability: the classic EAM features keep working even if the ML service goes down. Clean separation of layers, versioned migrations, full Docker deployment, a role-adapted interface, and role-scoped data access with an intervention history that can't be altered after the fact. And it's OWASP-hardened, scanned every commit."

### 13 — Methodology *(~30s)*
> "I ran this like a small Scrum team. My SagemCom supervisor as product owner, prioritizing and validating every deliverable. Me as both scrum master and the development team, paired with an AI assistant for implementation and testing. Seven monthly sprints, and every single feature went through the same disciplined loop — specify, plan, build, verify — before any code shipped, so every technical decision stays traceable."

### 14 — Component Diagram *(~44s)*
> "This is the logical architecture. Everything's a container on one Docker network. The Next.js frontend talks to a FastAPI backend, which is the hub — it owns Postgres with pgvector, MinIO for files, and it's the only thing that calls out to the ML microservice, the RAG service, and Celery workers running behind RabbitMQ for anything asynchronous. External calls — the Groq LLM, SMTP for email — go out over HTTPS. It's a clean separation: presentation, business logic, and data access never blur into each other."

### 15 — Request Flow *(~44s)*
> "Here's what actually happens on one request. The frontend asks for a machine's unified health. The backend pulls the latest real sensor data — if there's none, it stops right there and returns 'telemetry unavailable,' no fabrication. If there is data, it calls the ML microservice, which runs all seven models in parallel, while the Wave 2 models process the telemetry trend concurrently. Dempster-Shafer fusion combines every signal into one score and verdict, it gets logged for audit and future retraining, and the frontend renders it."

### 16 — Sequence Diagram — Unified Health Request *(~30s)*
> "This sequence diagram traces that same request end to end — a machine's unified health check. Frontend asks the backend, the backend pulls real sensor data — and if there's none, it stops honestly right there. Otherwise, it calls the ML microservice for all seven models, runs the Wave 2 signals in parallel, fuses everything through Dempster-Shafer, logs it, and returns the score."

### 17 — Deployment Diagram *(~30s)*
> "Physically, it's four independent stacks on one Docker host. The application stack — frontend, backend, ML, RAG, Postgres, RabbitMQ, MinIO, Celery. A SonarQube stack for static analysis, self-hosted on demand. A monitoring stack — Prometheus, Grafana, Pushgateway. And a notebooks stack for offline model research, not part of the running app. Each one starts, stops, and rebuilds independently, without ever touching the live application."

### 18 — Security Pipeline *(~44s)*
> "Every push runs through five security stages. Gitleaks scans for hard-coded secrets across the git history. Dependency scanning cross-references every package against known CVEs. SonarQube's static analysis flags injection flaws and weak crypto. Trivy checks all five Docker images for CVEs. And OWASP ZAP logs in as all four roles and actively probes the running app. All five stages are non-blocking — but the gate is genuinely green: zero new violations, duplication down to 2.6%, coverage at 74.8%, above target."

### 19 — Security Live Evidence *(~15s)*
> "These are live dashboards, not mockups — SonarQube's quality gate, Trivy's image scan, and the ZAP DAST run, all pulled straight from the running project."

### 20 — Production on AKS *(~30s)*
> "And it's not just local. I provisioned an AKS cluster in Poland Central through Terraform, with a managed Postgres and pgvector, secrets in Key Vault, and the Terraform state itself on a live HCP dashboard. Staging is genuinely live — eight out of eight pods verified internally. The one open item is the public load balancer, blocked by a subscription-level quota, not the platform."

### 21 — Machine Learning Pipeline *(~20s — overview only, detail moved to slide 22)*
> "This is the heart of the ML pipeline — two layers of models running in parallel on live sensor data, fused into one honest verdict. Let's walk through it, checkpoint by checkpoint."

### 22 — ML Pipeline Checkpoints *(~44s, new)*
> "Checkpoint one: five raw sensors feed a feature pipeline reading heat and workload. Checkpoint two: seven models, P1 through P7, each running in parallel on one question — will it fail, what kind, how long, is it acting strange, how urgent, when to fix it, what parts. Checkpoint three: four Wave 2 signals reading the machine's full history — PINN, Cox PH survival, Mahalanobis distance, CUSUM-Kalman drift. Checkpoint four: Dempster-Shafer fusion combines all eleven, and says 'not sure' if they disagree. Checkpoint five: one health score, one plain-language verdict, logged for retraining."

### 23 — RAG Assistant Pipeline *(~30s)*
> "This is the RAG assistant's pipeline — how a question gets answered. Documents get chunked and embedded once at ingestion; at query time, the same embedding model retrieves the most relevant chunks, real-time machine status gets merged in, and everything goes to the LLM together, so the answer is grounded in both the documentation and what the machine is actually doing right now."

### 24 — ML Model Definitions *(~30s)*
> "This table is the full model reference — all seven predictive models plus the four Wave 2 signals, with their type, what question they answer, and the key technical detail behind each. I won't read every row, but it's here for exactly the kind of question you'd expect in a defense."

### 25 — Why These Models *(~30s)*
> "And this is why each one was chosen over the alternative — XGBoost over Random Forest for the non-linear, imbalanced sensor data; censoring-aware survival models over naive regression, which measurably improves the concordance index; a four-method ensemble for anomalies, because a single method alone misses shapes the others catch; and Croston's method for parts demand, built specifically for bursty, intermittent demand instead of a simple reorder point."

### 26 — Class Diagram *(~15s)*
> "And this is the class diagram underneath it all — the actual data model connecting machines, work orders, predictions, and every role."

### 27 — Gantt Chart *(~15s)*
> "And here's how those seven months actually broke down, sprint by sprint, against the roadmap."

### 28 — Technologies Used *(~15s)*
> "On the stack: Next.js and TypeScript, FastAPI and PostgreSQL, Flask and XGBoost for ML, pgvector and Groq for RAG, and Docker, Terraform, and AKS underneath it all."

### 29 — Progress / Features Delivered *(~30s)*
> "Here's a preview of what's actually running — the Head Technician's dashboard, per-machine ML intelligence, the conversational assistant, and the login screen behind all of it. But screenshots only go so far. Let's look at the real thing."

### 30/31 — Live Demonstration *(~10s cue, say once)*
> "This next part is live — everything I'm about to show follows the same nine areas from the requirements slide, walked through end-to-end, across all four roles."

**→ play the 6:47 narrated demo video here**

### 32 — Conclusion *(~30s)*
> "So, where this lands: a complete platform — operational management, seven ML models, a RAG assistant — tested and secured by a five-stage DevSecOps pipeline. Every feature followed the same specify-plan-build-verify discipline. And I stayed honest about model quality — label leakage got detected and reported, not hidden. Thank you — happy to take questions."
