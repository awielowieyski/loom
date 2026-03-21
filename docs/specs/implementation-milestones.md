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

### Eval Engine

- [ ] Structural validation gate (hard pass/fail): required fields, dependency schema, eval_spec present
- [ ] LLM-powered quality scoring: clarity, completeness, minimalism (configurable dimensions)
- [ ] 3-run median scoring with tolerance bands (spread > 0.15 → low-confidence flag)
- [ ] Overlap detection: embedding similarity > 0.90 → duplicate flag with justification requirement
- [ ] Scope classification: LLM classifier detects personal content (paths, credentials, usernames) in community submissions
- [ ] Dependency risk scoring: network access, external APIs, broad MCP scopes → higher scrutiny
- [ ] Eval results stored with evaluator version, trigger type, dimension breakdown

### Trust Tiers

- [ ] `experimental`: automatic on passing structural + eval threshold
- [ ] `community`: automatic when thresholds met (>N successful usage reports, no security flags, signed)
- [ ] `verified`: manual promotion by maintainers (API endpoint + web UI in M4)
- [ ] Trust tier filters applied to `resolve` and `search` results
- [ ] Trust tier visible in all responses

### Signing & Provenance

- [ ] ed25519 keypair registration on user accounts
- [ ] Signature generation over `content + version + dependencies + eval_spec`
- [ ] Signature verification on all mutations
- [ ] Signature status included in resolve/get_skill responses
- [ ] Unsigned skills capped at `experimental` tier

### Amendments

- [ ] Amendment submission: diff against existing skill (new content, same slug)
- [ ] Scope check: LLM classifier determines if amendment changes WHAT vs HOW
- [ ] Comparative eval: run eval_spec against both versions, score delta
- [ ] Auto-merge: amended version scores >= original - 0.05 on all dimensions → patch version bump
- [ ] Mixed results → queued for review (stored as pending amendment)
- [ ] Regression → rejected with per-dimension explanation
- [ ] Anti-complexity gate: >20% token growth without proportional eval improvement → flagged

### Deliverable

- Quality-gated submission pipeline (submit → eval → tier assignment)
- Amendment workflow with automated comparison
- Signing and verification
- Eval results queryable for any skill (transparency)

---

## M3: Composition & Capabilities

**Thesis proved:** Loom can do something no other skill platform can — compose atomic skills into higher-order capabilities and resolve them as a single coherent execution plan.

**What you can demo:** Ask an agent to "produce a vendor risk briefing." Loom returns a multi-step execution plan with each step's full instructions embedded, dependencies pre-checked, data flow declared. The agent follows the plan step by step, passing outputs between steps. One request, one resolved plan, multi-skill execution.

### Capability Registry

- [ ] Capability data model: steps with skill references, data flow, preconditions, expected outcome
- [ ] Capability CRUD with versioning (same version model as skills)
- [ ] Step reference validation: all referenced skills exist and meet minimum trust tier
- [ ] Dependency aggregation: union of all steps' dependencies, with per-step satisfied/missing
- [ ] Data flow validation: outputs of step N are available as inputs to step N+1 where declared
- [ ] Cost/time aggregation from constituent skills (with override support)

### Resolution

- [ ] `resolve_capability(task_description, context?)` → ResolvedCapability
- [ ] Full plan resolution: each step contains the complete resolved skill content (no further lookups needed)
- [ ] Per-step dependency status based on agent's declared `available_tools`
- [ ] `required: false` steps marked as skippable when dependencies unmet
- [ ] Capability-level eval_spec storage and validation

### Semantic Integration

- [ ] Capabilities indexed with embeddings alongside skills
- [ ] `resolve` returns capabilities when they match better than atomic skills (with type indicator)
- [ ] `search` includes capabilities in results (filterable)

### Extends for Capabilities

- [ ] Capabilities can use `extends` to layer on top of other capabilities
- [ ] Cross-source skill references in steps: `loom://` and `corp://` URI prefixes validated (corp:// returns "not available" in public Loom, but the schema is valid)

### Layered Adaptation

- [ ] Reference Python implementation of `extends` chain resolution and merge semantics
- [ ] Demo: community capability + policy overlay + personal override merged client-side into one resolved result
- [ ] Tests for precedence, version pinning, and local override behavior

### Deliverable

- Full capability lifecycle: create, resolve, version, search
- End-to-end demo: agent resolves a multi-step capability and executes it
- Policy-overlay demo proving layered adaptation before full corporate deployment
- At least 3 seed capabilities composing existing seed skills

---

## M4: Living Registry

**Thesis proved:** The registry improves itself over time. Usage signals, continuous evaluation, and community curation create a flywheel that makes skills better without manual intervention.

**What you can demo:** Show the quality dashboard. A skill that was `experimental` last week is now `community` — enough successful usage reports crossed the threshold. Another skill's eval score dropped — it was flagged and a steward reviewed it. A third skill hasn't been resolved in 90 days — it's marked stale and deprioritised. An abusive submission was caught and blocked. The registry is alive.

### Usage Signals

- [ ] `report_usage(skill_id, version, outcome, runtime)` MCP tool
- [ ] Anonymous outcome aggregation (success/partial/failure rates per skill per version)
- [ ] Resolution frequency tracking (popularity signal)
- [ ] Alternative selection tracking (preference signal)
- [ ] `context_hash`: one-way hash of skill category + task type classification (not content)

### Continuous Evaluation

- [ ] Scheduled re-evaluation: background worker re-scores `community` and `verified` skills weekly
- [ ] Usage-signal-triggered re-eval: failure rate > 30% triggers immediate re-eval
- [ ] Model drift detection: when eval engine model is updated, re-score a sample and flag divergence > 0.1
- [ ] Dependency change monitoring: check declared MCP servers/APIs for deprecation or security advisories
- [ ] Staleness detection: skills with zero resolutions in 90 days marked stale
- [ ] Trust tier auto-promotion: `experimental` → `community` when thresholds met

### Lifecycle & Governance

- [ ] Deprecation workflow: author marks skill as deprecated with successor pointer
- [ ] Deprecated skills resolve with `deprecated: true` flag and successor suggestion
- [ ] Removal workflow: maintainer-only, returns 410 Gone
- [ ] Reporting mechanism: any user can flag a skill (deprioritised pending review)

### Abuse Prevention

- [ ] Submission rate limiting: 5/day for new accounts, 20/day after 10 accepted skills
- [ ] Content scanning: LLM classifier for prompt injection, credential harvesting, adversarial content
- [ ] Account verification: email required, GitHub OAuth for network-access skills
- [ ] Duplicate detection at submission (pre-eval embedding check)

### Web UI

- [ ] Browse and search skills/capabilities with filtering
- [ ] Skill detail view: content, eval scores, usage stats, version history, trust tier
- [ ] Contribution workflow: submit skill, submit amendment, review queue
- [ ] Quality dashboard: eval trends, usage heatmap, trust tier distribution, stale/deprecated skills
- [ ] Category steward tools: review queue, tier promotion interface
- [ ] OAuth login for humans

### Deliverable

- Self-improving registry with observable quality signals
- Web UI for human curation and governance
- Full community contribution workflow
- Anti-abuse measures active

---

## M5: Corporate Loom

**Thesis proved:** The business model works. Organisations pay for private Loom instances that compose with the public registry. The three-tier resolution chain (local → corporate → community) is operational.

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
- [ ] `extends` chain resolution across tiers: recursive resolution through corp → loom

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
                                    M4 (Living Registry)
                                               │
                                               ↓
                                    M5 (Corporate Loom)
```

M1 → M2 → M3 is the critical path. M4 can start in parallel with M3 (the usage reporting and continuous eval don't depend on capabilities). M5 depends on M4 because corporate instances need the governance and abuse prevention infrastructure.

---

## What's NOT in These Milestones

These are explicitly deferred beyond M5:

- **Credential brokering / token exchange** — Loom declares dependencies; runtimes handle auth
- **Runtime scope enforcement** — agent runtimes' responsibility
- **Cross-service delegation chains** — requires MCP ecosystem maturity
- **Reputation scoring** — needs enough contributor activity to be meaningful
- **Fork-and-prove** — competing skill versions visible to consumers
- **Cross-org federation** — corporate instances sharing skills between partner orgs
- **Skill format as open standard** — publish the spec independently of the implementation
- **Additional client-side `extends` libraries beyond the reference Python implementation** — e.g. TypeScript and framework-specific helpers
- **Public registry privacy tiers** — opt-in analytics for contributors who want richer skill performance data
