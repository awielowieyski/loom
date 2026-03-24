# Loom: Implementation Milestones

**Date**: 2026-03-21
**Companion to**: [Loom Design Spec](2026-03-21-loom-design.md)

---

## Guiding Principles

1. **Each milestone is independently demo-able and feedback-worthy.** You should be able to show it to someone and get a meaningful reaction.
2. **Each milestone proves a distinct part of the thesis.** M1 proves the concept; M2 proves it's better than alternatives; M3 proves it can do things no one else can; etc.
3. **Foundation work is front-loaded into M1.** Project structure, DB, auth, testing, CI — all in M1 so later milestones focus purely on features.
4. **The `extends` mechanism is a client-side convention.** Loom stores and returns the `extends` field; the agent runtime performs the merge. A reference implementation (Python library) is provided but the server doesn't execute merges.
5. **Milestones should beat the real baseline, not just weaker incumbents.** The relevant comparison is often "strong model + local skills," so demos must prove better runtime choice under constraints, not just hosted skill retrieval.

---

## M1: Constraint-Aware MCP Skill Resolution

**Thesis proved:** An agent can resolve the best executable skill for its current environment at runtime. The value is not remote skill hosting by itself; it is better constraint-aware choice than a static local skill list.

**What you can demo:** Connect Claude Code (or any MCP client) to the Loom MCP server. Ask it to find the best way to summarise recent code changes for release notes. Loom compares semantically similar skills with different trust, dependency, and cost profiles. In a runtime with only `git` and a low cost budget, it chooses the local-git path. In a runtime with richer dependencies and a higher quality budget, it returns a richer alternative. No file was installed, and the result changes for a concrete reason.

### Foundation

- [ ] Project scaffolding: Python package with `uv`, directory structure (`src/loom/`), pyproject.toml
- [ ] PostgreSQL + pgvector schema: `skills`, `skill_versions`, `users`, `categories` tables
- [ ] Alembic migrations setup
- [ ] FastAPI application with structured error handling
- [ ] API key authentication middleware
- [ ] Test infrastructure: pytest, fixtures, test database
- [ ] MCP server (Python MCP SDK) wired to FastAPI services
- [ ] CI: linting (ruff), type checking (mypy), tests

### Skill Registry

- [ ] Skill format: Pydantic model matching the design spec frontmatter (including `extends`, `dependencies`, `eval_spec`, cost/time metadata, `privacy_impact`)
- [ ] Skill CRUD: create, read, update (version bump), list
- [ ] Skill format validation on ingest (structural checks, required fields, dependency schema)
- [ ] Version history: every mutation creates a `skill_versions` row, `skills` table holds latest
- [ ] Category CRUD with hierarchical slugs

### Semantic Discovery

- [ ] Embedding generation on skill ingest (description + content → pgvector)
- [ ] Semantic search: query embedding → cosine similarity → ranked results
- [ ] Constraint-aware ranking: semantic match + trust tier + dependency satisfaction + cost/time fit
- [ ] Context-aware filtering: trust tier, cost profile, category, tags
- [ ] Alternative suggestions: top match + up to 3 ranked alternatives with tradeoff descriptions
- [ ] Selection rationale: explain why the chosen result beat nearby candidates

### MCP Server

- [ ] `resolve(task_description, context?)` → ResolvedSkill with content, dependency status, alternatives, and selection rationale
- [ ] `get_skill(slug, version?)` → specific skill by slug, supports version pinning for `extends`
- [ ] `search(query, category?, trust_tier?, cost_budget?)` → summaries without full content
- [ ] `list_categories()` → category taxonomy
- [ ] Structured error responses: no_match, trust_floor_not_met, deprecated, removed
- [ ] Runtime context support in `resolve`: `available_tools`, `trust_floor`, `cost_budget`, and latency hints

### Seed Content

- [ ] 15-20 seed skills across 3-4 categories (development/git, development/testing, documentation, code-review)
- [ ] Each with complete frontmatter: eval_spec, dependencies, cost/time metadata
- [ ] At least 3 seed clusters where multiple skills address the same task with different dependency/cost/trust trade-offs
- [ ] At least 2 skills with `extends` references (to validate the field is stored and returned correctly)
- [ ] At least 1 community skill designed to be extended locally, to prove layering before corporate multi-tenancy exists

### Deliverable

- Running MCP server that an agent can connect to
- Skills resolvable by natural language description and runtime constraints
- A demo where the same task resolves differently under different runtime contexts
- Reference Python `extends` resolver for local + community layering
- API documentation (auto-generated from FastAPI)
- README with setup instructions

---

## M2: Quality & Trust

**Thesis proved:** Loom is demonstrably better than static local skills or a GitHub repo of skill files in governed environments. Skills are evaluated, trust-scored, signed, and amendments are quality-gated. You can't ship a bad skill and expect the runtime to treat it as equivalent.

**What you can demo:** Submit a vague, low-quality skill — it gets rejected with specific feedback. Submit a good one — it enters as `experimental`. Propose an amendment that adds complexity without improving quality — it gets flagged. Propose a genuine improvement — it auto-merges with a version bump. Show the eval scores and trust tier for any skill.

**Full design:** [M2 Evaluation Security Spec](2026-03-23-m2-quality-trust-spec.md) — threat model, 5-phase eval pipeline, schemas, service architecture.

M2 is divided into four sub-milestones that sequence from deterministic checks through LLM evaluation to trust decisions and sandboxed execution:

```
M2i (Pipeline + Static) ──→ M2ii (LLM Eval + Aggregation)
                                      │
                                      ▼
                             M2iii (Trust + Amendments)
                                      │
                                      ▼
                             M2iv (Sandbox + Signing)
```

### M2i: Static Analysis + Pipeline Skeleton

**Proves:** The eval infrastructure exists and catches obviously bad submissions deterministically.

#### Infrastructure
- [ ] Redis + arq setup in Docker Compose
- [ ] `eval_jobs` table: tracks pipeline runs (status, scores, content_hash, evaluator_version)
- [ ] `eval_dimension_runs` table: individual LLM eval runs per dimension
- [ ] `trust_audit_log` table: tier change history
- [ ] Alembic migrations for all new tables
- [ ] `EvalRepo` repository following existing repo patterns (asyncpg, explicit SQL)
- [ ] Arq worker process for background eval job execution

#### Static Analyser (Phase 1)
- [ ] Schema validation: required frontmatter fields, field types, enum values
- [ ] Complexity bounds: content length, step count, dependency count, nesting depth
- [ ] Injection pattern scanning: regex catalogue for common prompt injection patterns
- [ ] Dependency resolution checks: extends target existence, circular dependency detection
- [ ] Cost/trust metadata sanity checks
- [ ] `StructuralReport` model: passed, errors, warnings, injection_indicators, content_hash

#### Pipeline Skeleton
- [ ] `EvalPipelineService` orchestrator (calls phases in sequence, saves results)
- [ ] Integration with `RegistryService.create_skill()` — auto-enqueue eval on submission
- [ ] API: `POST /skills/{id}/eval` (trigger re-eval), `GET /skills/{id}/eval` (get results)
- [ ] `eval_status` field on skills table (pending, running, completed, failed)

### M2ii: Isolated LLM Evaluation + Score Aggregation

**Proves:** Skills are quality-scored by LLM in an injection-resistant architecture.

#### Content Isolation (Phase 2)
- [ ] Fragment extraction: split skill into metadata, step_outline, full_body, code_blocks, eval_scenarios
- [ ] JSON encoding of all fragments (raw markdown never in LLM prompts)
- [ ] Unicode normalisation and injection vector stripping (zero-width chars, RTL overrides)
- [ ] Content hashing (SHA-256) bound to all eval results

#### LLM Evaluation (Phase 3)
- [ ] Data-only evaluation protocol: skill content as quarantined data field, never in system prompt
- [ ] Dimension isolation: one LLM call per dimension (clarity, completeness, safety, correctness)
- [ ] Each dimension sees only its relevant fragment (see [M2 Evaluation Security Spec](2026-03-23-m2-quality-trust-spec.md) §3.3.1 table)
- [ ] Structured output via tool_use: score, evidence, injection_detected, confidence
- [ ] Blind evaluation: no author, trust tier, or popularity metadata exposed to evaluator
- [ ] `PromptRegistry` with versioned prompt templates per dimension
- [ ] Multi-run consensus: N=3 independent runs per dimension, median score
- [ ] Injection detection: `injection_detected` field on every eval run
- [ ] Output validation: schema enforcement, malformed response retry (up to 2)

#### Score Aggregation (Phase 5)

> **Note:** Phase 5 is implemented here before Phase 4 (Sandbox, in M2iv). Until M2iv, `sandbox` result is always `None` and the composite score reflects LLM dimensions only. This is intentional — LLM eval provides immediate value; sandbox execution adds depth later.

- [ ] Weighted composite score (clarity 0.25, completeness 0.30, safety 0.25, correctness 0.20)
- [ ] Confidence computation from score spread (high/medium/low thresholds)
- [ ] Injection response protocol: quarantine on 2+ dimension flags, review on 1
- [ ] Composite score written back to `skills` table
- [ ] Canary skill infrastructure: reference skills with known scores, drift detection
- [ ] `evaluator_version` tracking on all results

### M2iii: Trust Tiers, Promotion, Amendments

**Proves:** Quality gates prevent bad submissions from gaining trust; good submissions are rewarded.

> **Dependency note:** Auto-promotion to `community` requires signing (M2iv). Until M2iv, promotion logic is implemented and tested but the signing criterion is deferred — skills can meet all other criteria and be queued for promotion pending signature.

#### Trust Tier Management
- [ ] `TrustService` with auto-promotion logic (`experimental` → `community` when thresholds met)
- [ ] Promotion criteria: composite score ≥ 0.70, no injection flags, safety ≥ 0.60, ≥10 usage reports with ≥80% success, signed, author account in good standing (no quarantined submissions in last 90 days)
- [ ] Demotion triggers: score regression, usage failure rate >30%, security flags, key revocation
- [ ] `trust_audit_log` population on all tier changes
- [ ] API: `GET /skills/{id}/trust` (tier + audit history)

#### Amendment Workflow
- [ ] Amendment submission: new content against existing slug
- [ ] Scope check: LLM classifier determines WHAT vs HOW change (data-only protocol)
- [ ] Comparative eval: both versions through full pipeline, per-dimension comparison
- [ ] Auto-merge: amendment ≥ original − 0.05 on all dimensions → patch version bump
- [ ] Mixed results → human review queue
- [ ] Regression → rejected with per-dimension explanation
- [ ] Anti-complexity gate: >20% token growth without proportional eval improvement → flagged
- [ ] Score jump detection: >0.3 composite jump → flagged regardless of absolute score

#### Human Review Queue
- [ ] Queue model: skills awaiting review with full eval context
- [ ] Queue population from low-confidence evals, injection flags, mixed amendments
- [ ] Queue item includes: eval fragments (what LLM saw), scores, indicators (no UI — UI is M4)

### M2iv: Sandboxed Execution + Signing

**Proves:** Eval scenarios are actually tested; skills have verifiable provenance.

#### Sandbox Execution (Phase 4)
- [ ] `loom-eval-sandbox` Docker image: minimal Python/Node runtime
- [ ] Container spec: no network, 512MB memory, 1 CPU, 30s timeout, read-only filesystem, non-root
- [ ] Eval scenario validation and execution in container
- [ ] Code block syntax checking and linting in container
- [ ] Output capture and pass/fail determination
- [ ] Warm container pool (3 pre-built containers for reduced cold start)

#### Signing & Provenance
- [ ] `signing_keys` table: user_id, public_key (ed25519), fingerprint, revocation status
- [ ] `SigningService`: key registration, signature generation, verification
- [ ] Signature covers: SHA-256(content + version + dependencies + eval_spec)
- [ ] Signature status in `resolve` and `get_skill` responses
- [ ] Unsigned skills capped at `experimental` tier
- [ ] Key revocation invalidates all signatures, triggers trust re-evaluation
- [ ] API: key registration, skill signing, signature verification

#### Overlap Detection
- [ ] Embedding similarity check on submission (threshold 0.90)
- [ ] Duplicate flag with justification requirement for near-matches

### Deliverable

- Quality-gated submission pipeline (submit → eval → tier assignment)
- Injection-resistant 5-phase eval with defence in depth
- Amendment workflow with automated comparison and anti-gaming
- Trust tier auto-promotion and demotion
- Signing and verification with ed25519
- Eval results queryable for any skill (transparency)

---

## M3: Composition & Capabilities

**Thesis proved:** Loom can do something no other skill platform can — compose atomic skills into higher-order capabilities and resolve them as a single coherent execution plan.

**What you can demo:** Ask an agent to "produce a vendor risk briefing." Loom returns a multi-step execution plan with each step's full instructions embedded, dependencies pre-checked, data flow declared. The agent follows the plan step by step, passing outputs between steps. One request, one resolved plan, multi-skill execution.

**Full design:** [M3 Composition Security Spec](2026-03-23-m3-composition-spec.md) — capability model, resolution semantics, extends merge strategy, and composition threat model with defences.

M3 is divided into four sub-milestones that sequence from data model through resolution to security hardening:

```
M3i (Model & Registry) ──→ M3ii (Resolution)
                                  │
                                  ▼
                           M3iii (Extends & Security)
                                  │
                                  ▼
                           M3iv (API, Seeds, Integration)
```

### M3i: Capability Model & Registry

**Proves:** Capabilities exist as first-class objects with validated structure and versioning.

#### Data Model
- [ ] `CapabilityStep` model: skill_ref (URI), role, inputs, outputs, required, data_classification
- [ ] `DataFlowEdge` model: from_step, to_step, classification
- [ ] `CapabilityCreate`, `Capability`, `CapabilitySummary`, `CapabilityUpdate`, `CapabilityVersion` models
- [ ] `ResolvedStep`, `ResolvedCapability`, `ResolvedResult` models (type-discriminated union)

#### Database
- [ ] `capabilities` table: mirrors skills structure with steps (JSONB), preconditions, expected_outcome, data_flow
- [ ] `capability_versions` table: version history with same pattern as skill_versions
- [ ] Alembic migration for both tables
- [ ] Indexes: category, trust_tier, scope, tags (GIN), embedding (ivfflat)

#### Registry
- [ ] `CapabilityRepo`: CRUD operations following `SkillRepo` patterns (asyncpg, explicit SQL)
- [ ] Capability CRUD with versioning (same version model as skills)
- [ ] Step reference validation: all skill_ref values contain `://` prefix
- [ ] Step reference existence check: all referenced skills exist and meet minimum trust tier
- [ ] Dependency aggregation: union of all steps' dependencies, with per-step satisfied/missing
- [ ] Data flow validation: outputs of step N are available as inputs to step N+M where declared
- [ ] Cost/time aggregation from constituent skills (with override support)

### M3ii: Capability Resolution

**Proves:** Capabilities are discoverable and resolvable with full execution plans.

#### Resolution Service
- [ ] `resolve_capability(task_description, context?)` → ResolvedCapability
- [ ] Full plan resolution: each step contains the complete resolved skill content (no further lookups needed)
- [ ] Per-step dependency status based on agent's declared `available_tools`
- [ ] `required: false` steps marked as skippable when dependencies unmet
- [ ] Effective trust tier computation: minimum across all steps' skills
- [ ] Trust warnings when experimental skills are present in a capability

#### Semantic Integration
- [ ] Capabilities indexed with embeddings alongside skills (combined vector search)
- [ ] `resolve` returns capabilities when they match better than atomic skills (with type indicator)
- [ ] `search` includes capabilities in results (filterable by type)

#### MCP Tools
- [ ] `resolve_capability(task_description, context?)` MCP tool
- [ ] Update `resolve()` to return `ResolvedResult` with type discriminator
- [ ] Update `search()` to include capabilities with type filter

### M3iii: Extends for Capabilities + Composition Security

**Proves:** Capabilities can be layered safely. Adversarial composition attacks are detected and blocked.

#### Extends Support
- [ ] Capability extends support in `ExtendsResolver`: parse `loom://` and `corp://` URIs for capabilities
- [ ] Append-only merge enforcement: extending capabilities can ADD steps but NOT replace or remove base steps
- [ ] Base step preservation validation: verify inherited steps are unchanged
- [ ] Data flow edge addition: extending capabilities can add edges referencing both inherited and new steps

#### Security Rules
- [ ] Minimum-trust-across-chain rule: composed result inherits LOWEST trust tier from all layers and all step skills
- [ ] Cycle detection: visited URI set during extends chain resolution, reject on cycle with clear error
- [ ] Maximum extends chain depth limit (10 levels)
- [ ] Cross-source URI validation: `loom://` resolves only from public registry, `corp://` only from corporate instance
- [ ] Mandatory URI prefix validation: step skill_ref without `://` rejected at creation

#### Adversarial Test Suite
- [ ] Test: experimental overlay + verified base → effective tier = experimental
- [ ] Test: step without URI prefix rejected
- [ ] Test: `loom://x` never resolves from corp source
- [ ] Test: external data flow edge produces warning in resolved plan
- [ ] Test: capability with mixed trust tiers reports minimum
- [ ] Test: extends that modifies base step is rejected
- [ ] Test: circular extends A→B→C→A produces cycle error
- [ ] Test: extends chain exceeding depth limit rejected

### M3iv: API, Seed Capabilities, Integration Tests

**Proves:** Full capability lifecycle works end-to-end.

#### API Routes
- [ ] `POST /api/v1/capabilities` — create capability
- [ ] `GET /api/v1/capabilities` — list capabilities with filters
- [ ] `GET /api/v1/capabilities/search` — semantic search
- [ ] `GET /api/v1/capabilities/{slug}` — get by slug
- [ ] `PUT /api/v1/capabilities/{slug}` — update (version bump)
- [ ] `POST /api/v1/capabilities/resolve` — resolve capability from task description
- [ ] Update `POST /api/v1/skills/resolve` to support `?type=skill|capability|any`

#### Seed Capabilities
- [ ] `comprehensive-code-review`: review-pull-request + review-security + review-performance
- [ ] `release-documentation`: release-notes-enriched + changelog-update + api-docs-generate
- [ ] `accessibility-security-review`: review-accessibility + review-security

#### Integration Tests
- [ ] Capability CRUD round-trip test
- [ ] Full plan resolution with embedded skill content
- [ ] Unified resolve() returning both skills and capabilities
- [ ] Extends chain resolution for capabilities
- [ ] E2E demo: agent resolves a multi-step capability and executes it

### Deliverable

- Full capability lifecycle: create, resolve, version, search
- Composition security model with adversarial test suite
- Append-only extends for capabilities with cycle detection
- Unified resolution returning skills or capabilities
- 3 seed capabilities composing existing seed skills
- End-to-end demo: agent resolves a multi-step capability

---

## M4: Living Registry (Backend)

**Thesis proved:** The registry improves itself through behavioral evaluation, comparative assessment, and usage feedback. Skills are continuously tested, compared, and informed by real-world outcomes. Quality signals compound over time and bad skills are detected and demoted without manual intervention.

**What you can demo:** Submit a skill that scores well on M2 eval but produces poor outputs when followed — behavioral eval catches it. Amend a skill — the triage pipeline classifies the change as refinement, regression, or variant with evidence. Show usage stats: a skill promoted from `experimental` to `community` based on 80%+ success rate. Another skill flagged for re-eval after failure rate spiked. A third marked stale after 90 days without resolution.

**Full design:** [M4 Living Registry Spec](2026-03-24-m4-living-registry-spec.md) — Runner-Judge architecture, comparative protocol, usage signals, continuous re-evaluation, abuse prevention.

M4 is divided into three sub-milestones:

```
M4i (Behavioral Eval) ──→ M4ii (Comparative Eval + Amendment Triage)
                                    │
                                    ▼
                          M4iii (Usage Signals + Continuous Eval)
```

### M4i: Behavioral Eval Infrastructure

**Proves:** Skills are evaluated not just on how they look, but on what happens when an LLM follows them.

#### Runner-Judge Services
- [ ] `BehavioralRunner` service: sends skill instructions + scenario `input_context` to Runner LLM, parses structured output (actions_taken, output, artifacts, notes)
- [ ] `BehavioralJudge` service: receives ONLY Runner output + success_criteria + quality_dimensions, scores on outcome quality/completeness/efficiency (0-1 each)
- [ ] Judge never sees skill instructions (prevents gaming)
- [ ] Both use data-only protocol (content as JSON in user message, never as system instructions)
- [ ] Different system prompts, configurable to use different models

#### Prompt & Orchestration
- [ ] Runner/Judge prompt variants registered in `PromptRegistry` with versioning
- [ ] `BehavioralEvalService` orchestrator: runs Runner N times per scenario, passes each output to Judge, aggregates scores
- [ ] `run_behavioral_eval_job` arq task: dispatched as post-pipeline phase after M2 passes
- [ ] `behavioral_eval` field on `eval_spec`: `auto` (default), `not_applicable`, `required`
- [ ] Auto-detection: scenarios with empty `input_context` → `not_applicable`

#### Storage & Trust
- [ ] `behavioral_eval_runs` table + Alembic migration (unique on eval_job_id + scenario_index + run_index)
- [ ] `behavioral_score` column on `skills` table (median across all scenario/run combinations)
- [ ] `behavioral_score` column on `eval_jobs` table
- [ ] `TrustService` updated: `behavioral_score >= 0.60` required for promotion to `community`

### M4ii: Comparative Eval + Amendment Triage

**Proves:** The system can objectively determine which of two skills is better and classify amendments automatically.

#### Head-to-Head Protocol
- [ ] `ComparativeEvalService`: same scenario → both skills via Runner → two outputs → blind Judge comparison
- [ ] Output anonymization: Judge receives "Output X" vs "Output Y" with randomized assignment per scenario
- [ ] Judge scores each on: outcome quality, completeness, efficiency, safety
- [ ] Preference declared only when confidence > 0.60 (below = tie)
- [ ] `comparative_eval_results` table + Alembic migration

#### Amendment Triage Pipeline
- [ ] Semantic diff: embedding similarity between old and new content
- [ ] Behavioral diff: head-to-head on SAME eval scenarios
- [ ] Classification matrix: refinement / regression / variant / extension / rejected (based on semantic similarity + behavioral result)
- [ ] Updated `PUT /api/v1/skills/{slug}`: amendment submission routes through triage pipeline

#### Breaking Change Detection
- [ ] Query capabilities referencing amended skill via `steps[].skill_ref`
- [ ] Run capability eval scenarios with both old and new versions
- [ ] Flag as breaking change if capability behavioral score drops
- [ ] Notify capability author with evidence

#### API
- [ ] `POST /api/v1/skills/{slug}/compare` endpoint (202 Accepted, async job)

#### Elo Ranking (stretch)
- [ ] `skill_rankings` table + Alembic migration (unique on skill_id + category_id)
- [ ] Baseline 1200, standard Elo calculation, per-category
- [ ] Inform resolution ordering within same trust tier (advisory, not decisive)

### M4iii: Usage Signals + Feedback Loop + Continuous Eval

**Proves:** Real-world outcomes feed back into the registry, driving promotion, demotion, staleness detection, and re-evaluation.

#### Usage Collection & Aggregation
- [ ] `usage_reports` table + Alembic migration (idempotent on `idempotency_key`)
- [ ] `usage_aggregates` table + Alembic migration (unique on skill_id + skill_version + window_type)
- [ ] `POST /api/v1/usage/report` endpoint (201 Created, idempotent)
- [ ] `report_usage()` MCP tool (same semantics as REST endpoint)
- [ ] Usage aggregation arq cron job (hourly): reads reports, upserts 7d/30d/90d window aggregates
- [ ] `GET /api/v1/skills/{slug}/usage` endpoint

#### Signal-Driven Actions
- [ ] Signal detection arq cron job: checks thresholds, triggers re-eval or alerts
- [ ] High failure rate (>30% over 7d, min 10 reports) → trigger behavioral re-eval
- [ ] Success rate drop (>20% vs previous 30d) → alert + re-eval
- [ ] Promotion eligibility: `success_rate >= 0.80`, count >= 10 → feed to TrustService
- [ ] Top 10% in category over 90d → `verified` tier candidate

#### Lifecycle
- [ ] `deprecated_at`, `successor_slug` columns on `skills` table
- [ ] `POST /api/v1/skills/{slug}/deprecate` endpoint with successor pointer
- [ ] Deprecated skills resolve with `deprecated: true` + successor info, sort below non-deprecated
- [ ] Capabilities get `trust_warnings` for deprecated step dependencies
- [ ] Removal: maintainer-only `DELETE`, returns 410 Gone
- [ ] `stale_since` column: set when `resolution_count` = 0 for 90d
- [ ] `resolution_count` column: incremented on each `resolve()` hit

#### Continuous Re-evaluation
- [ ] Scheduled weekly re-eval arq cron job: 20% sample of community/verified skills, oldest `last_eval_at` first
- [ ] `last_eval_at` column on `skills` table
- [ ] Drift detection: new score differs > 0.15 from stored → flag for steward review
- [ ] Model drift detection: compare `evaluator_version` across jobs, MAD > 0.10 → halt rollout

#### Abuse Prevention
- [ ] Rate limiting: Redis sliding window, 5/day unverified, 20/day verified
- [ ] Duplicate detection: embedding similarity at submission (>0.95 reject, 0.85-0.95 flag)
- [ ] Network-access skills require `community` tier author

#### Updated Resolution Response
- [ ] `resolve()` response gains: `deprecated`, `successor`, `stale`, `behavioral_score`, `usage_success_rate`

### Deliverable

- Behavioral evaluation pipeline: Runner-Judge architecture with blind scoring
- Comparative evaluation with head-to-head protocol and amendment triage
- Usage signal collection, aggregation, and signal-driven actions
- Continuous re-evaluation with drift detection
- Deprecation and staleness lifecycle
- Abuse prevention (rate limits, duplicate detection)
- All new REST endpoints and MCP tool updates

---

## M5: Web UI + Community

**Thesis proved:** Humans can browse, contribute, and curate the registry through a web interface. Category stewards have governance tools. The community contribution workflow is operational end-to-end.

**What you can demo:** Open the Loom web UI. Browse skills by category with filtering. Click into a skill and see its eval scores, behavioral eval results, usage stats, version history, and trust tier. Submit a new skill through the contribution form — it enters the eval pipeline. Review a flagged amendment in the steward queue. View the quality dashboard: eval trends, usage heatmap, trust tier distribution, stale/deprecated skills.

### Web Application

- [ ] React SPA with TypeScript
- [ ] OAuth login (GitHub, Google) for human contributors
- [ ] Responsive design for desktop and tablet

### Browse & Search

- [ ] Browse skills and capabilities with category filtering
- [ ] Full-text and semantic search
- [ ] Skill detail view: content, eval scores, behavioral eval results, usage stats, version history, trust tier
- [ ] Capability detail view: steps, data flow, resolved plan preview

### Contribution Workflow

- [ ] Submit new skill form with live validation
- [ ] Submit amendment to existing skill
- [ ] Amendment diff view: side-by-side comparison with triage classification
- [ ] Submission status tracking: eval pipeline progress, results

### Steward Tools

- [ ] Review queue: skills awaiting human review (low-confidence evals, injection flags, mixed amendments)
- [ ] Review interface: eval fragments, scores, indicators, approve/reject actions
- [ ] Tier promotion interface: override auto-promotion decisions with audit trail
- [ ] Flagged skill management: community-reported skills pending review

### Quality Dashboard

- [ ] Eval score trends over time (per skill, per category)
- [ ] Usage heatmap: resolution frequency by category and time
- [ ] Trust tier distribution: how many skills at each tier
- [ ] Stale and deprecated skills overview
- [ ] Behavioral eval coverage: percentage of skills with behavioral scores

### Deliverable

- Production-ready web UI for browsing, contributing, and curating skills
- Full community contribution workflow (submit, amend, review)
- Category steward governance tools
- Quality dashboard with observable metrics
- OAuth authentication for human users

---

## M6: Corporate Loom

**Thesis proved:** The business model works. Organisations pay for private Loom instances that compose with the public registry. The three-tier resolution chain (local -> corporate -> community) is operational.

**What you can demo:** An organisation's agent resolves `corp://acme-vendor-assessment`. The corporate Loom instance serves the org-specific skill. That skill `extends` `loom://vendor-risk-briefing@verified` from the public registry. The agent gets the merged result: community knowledge + corporate context. The org admin sees usage analytics in their dashboard. None of their corporate skills are visible to the public registry.

### Multi-Tenancy

- [ ] Org model: org accounts, org-level API keys, member management
- [ ] Tenant isolation: each org's skills are fully isolated in the database
- [ ] Org-level configuration: trust floor, approved categories, custom eval criteria, logging/audit policy
- [ ] Org admin dashboard: usage analytics, skill inventory, member access

### Cross-Source Resolution

- [ ] `corp://` URI scheme: corporate MCP server resolves `corp://` locally, `loom://` from public registry
- [ ] Public registry resolution from corporate instance: sends only slug + version, not corporate context
- [ ] Air-gapped mode: disable public registry connectivity (all `loom://` references return "unavailable")
- [ ] `extends` chain resolution across tiers: recursive resolution through corp -> loom

### Corporate Eval

- [ ] Same eval engine running against corporate skills
- [ ] Org-specific eval dimensions (compliance, internal standards)
- [ ] Corporate trust tiers (same model, org-scoped)
- [ ] Corporate amendment workflow

### Deployment

- [ ] Docker Compose for self-hosted deployment (API + MCP server + PostgreSQL + Redis)
- [ ] Helm chart for Kubernetes deployment
- [ ] Configuration for Loom-hosted SaaS (multi-tenant on shared infrastructure)
- [ ] SSO/SAML integration for enterprise auth

### Monetisation Infrastructure

- [ ] Usage metering: resolutions, eval runs, storage per org
- [ ] Plan management: free (community only), team, enterprise
- [ ] Rate limit tiers aligned with plans
- [ ] Billing integration (Stripe or similar)

### Privacy & Observability

- [ ] Tiered observability: corporate instances control their own audit/logging policy
- [ ] Corporate audit trails: full resolution logging (which skills, which teams, outcomes) when org policy requires it
- [ ] Public registry privacy defaults: anonymous usage signals only, no query text logging, no activity profiling
- [ ] Privacy-aware resolution: `privacy_floor` context parameter filters skills by `privacy_impact` metadata
- [ ] `privacy_impact` filtering in `resolve` and `search` constraint-aware ranking

### Deliverable

- Working corporate Loom instance (self-hosted or Loom-hosted)
- Three-tier resolution chain operational
- Org admin dashboard with analytics
- Metering and plan enforcement
- Tiered observability with corporate audit and public privacy defaults

---

## Milestone Dependencies

```
M1 (Resolution + MCP) ──→ M2 (Quality + Trust) ──→ M3 (Composition)
                                    │                      │
                                    └──────────┬───────────┘
                                               ↓
                                    M4 (Living Registry — Backend)
                                               │
                                               ↓
                                    M5 (Web UI + Community)
                                               │
                                               ↓
                                    M6 (Corporate Loom)
```

M1 -> M2 -> M3 is the critical path. M4 can start in parallel with M3 (usage reporting and behavioral eval don't depend on capabilities, though breaking change detection for capabilities requires M3). M5 depends on M4 because the web UI surfaces M4's behavioral scores, usage stats, and governance workflows. M6 depends on M5 because corporate instances need the governance, abuse prevention, and community infrastructure.

---

## What's NOT in These Milestones

These are explicitly deferred beyond M6:

- **Credential brokering / token exchange** — Loom declares dependencies; runtimes handle auth
- **Runtime scope enforcement** — agent runtimes' responsibility
- **Cross-service delegation chains** — requires MCP ecosystem maturity
- **Reputation scoring** — needs enough contributor activity to be meaningful
- **Fork-and-prove** — competing skill versions visible to consumers
- **Cross-org federation** — corporate instances sharing skills between partner orgs
- **Skill format as open standard** — publish the spec independently of the implementation
- **Additional client-side `extends` libraries beyond the reference Python implementation** — e.g. TypeScript and framework-specific helpers
- **Public registry privacy tiers** — opt-in analytics for contributors who want richer skill performance data
