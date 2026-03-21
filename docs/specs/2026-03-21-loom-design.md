# Loom: Capability Resolution for Agents

**Date**: 2026-03-21
**Status**: Design
**Author**: Adam Wielowieyski

---

## 1. Problem Statement

The Model Context Protocol (MCP) is standardising how agents access tools. But tools are not capabilities. "Search the web" is a tool. "Produce a competitive landscape briefing" is a composed capability requiring search, retrieval, ranking, synthesis, and document generation. Today, the gap between tools and capabilities is bridged by humans — developers manually install skill files, configure tool sets, and hope the agent figures out the rest.

Meanwhile, skill-sharing platforms (ClawHub, SkillsMP, community GitHub collections) are directories of files. A developer browses, picks, downloads, and drops a markdown file into a local folder. The agent sees whatever was installed. There is no runtime discovery, no evaluation of quality, no composition, no trust model, and no economic metadata. 26% of sampled skills on SkillsMP had vulnerabilities. ClawHub had 11% of its registry turn out to be malicious.

The fundamental problem: **agents cannot autonomously discover, evaluate, trust, and compose capabilities at runtime.** Everything requires a human in the loop at install time.

## 2. What Loom Is

Loom is a **capability resolution service for agents**. Not a file registry. Not a download marketplace.

When an agent encounters a task it doesn't have local instructions for, it asks Loom: "how do I do X?" Loom returns the current, evaluated, trust-scored instructions — resolved at the point of need, like a DNS lookup. The skill never touches the filesystem as a static install. It's a response, not a file.

Today, a frontier model with a few good local skills can often brute-force around missing capability descriptions. Loom is not claiming that every agent needs remote resolution for every task. It is designed for the harder case: environments with many tools, changing workflows, policy constraints, and non-trivial cost/latency trade-offs. In those settings, the key problem is not "can the model reason?" but "can the agent choose the right executable capability for this environment right now?"

Loom provides:

- **Semantic resolution** — agents describe what they need in natural language; Loom returns the best matching skills or capabilities for the task
- **Dependency-aware selection** — results are ranked and filtered based on available tools, required scopes, network needs, and other execution constraints
- **Evaluated quality** — every skill carries its own eval criteria; every amendment is scored against them
- **Composition** — multi-step capabilities that compose atomic skills into higher-order outcomes
- **Trust and provenance** — cryptographic signing, tiered trust levels, structured dependency declarations
- **Org-specific adaptation** — community capabilities can be refined by corporate policy and personal preference without forking the whole workflow
- **Economic metadata** — cost profiles and estimated duration so agents can route based on budget and latency
- **Continuous evaluation** — skills are re-evaluated automatically to ensure they remain effective as models and ecosystems evolve

### Positioning

> ClawHub and SkillsMP are skill directories for developers. Loom is a capability resolution service for agents.

| Dimension | ClawHub / SkillsMP | Loom |
|-----------|-------------------|------|
| Consumer | Developer browses, installs manually | Agent resolves at runtime |
| Discovery | Keyword / star count | Semantic search with context-aware ranking |
| Quality | GitHub stars, no formal eval | Eval engine with automated scoring and amendment comparison |
| Security | Afterthought (ClawHavoc incident) | Cryptographic signing + trust tiers from day one |
| Composition | None — flat list of atomic skills | First-class capabilities with data flow and dependency validation |
| Freshness | Stale until manually updated | Always-current resolution |
| Cost awareness | None | Cost profiles and duration metadata on every skill and capability |

The harder comparison is not a file directory but a strong model plus local curated skills. Loom wins when the runtime must choose among multiple semantically plausible paths under trust, dependency, policy, and budget constraints. The differentiator is not remote storage of instructions; it is better runtime choice.

## 3. Core Concepts

### 3.1 Skills

An atomic capability description. Not code — structured instructions that an agent follows.

```yaml
id: "uuid"
slug: "git-commit-conventional"
name: "Conventional Commit"
description: "Create git commits following the Conventional Commits specification with automatic scope detection"
category: "development/git"
tags: ["git", "commits", "conventions"]
scope: "community"          # community | corporate | personal
version: "2.3.1"
author_id: "uuid"
signature: "ed25519:..."    # over content + version
trust_tier: "verified"      # experimental | community | verified

content: |
  # Conventional Commit
  When creating git commits, follow the Conventional Commits specification...
  [full instructions]

dependencies:
  mcp_servers:
    - uri: "filesystem"
      required: true
      scopes: ["read"]
  apis: []
  trust_requirements:
    data_classification: "none"
    network_access: false

cost_profile: "free"
cost_drivers: []
estimated_duration: "fast"   # fast (<5s) | moderate (5-30s) | slow (>30s)

eval:
  scenarios:
    - description: "Agent needs to commit code changes"
      input_context: "Modified files in git repo, no staged changes"
      success_criteria: "Produces a valid conventional commit message with appropriate type and scope"
    - description: "Agent encounters merge conflict"
      input_context: "Git repo with unresolved conflicts"
      success_criteria: "Skill correctly identifies this as out-of-scope or handles gracefully"
  quality_dimensions:
    - clarity: "Instructions are unambiguous and followable"
    - completeness: "All common edge cases addressed"
    - minimalism: "No unnecessary steps or over-engineering"
```

### 3.2 Capabilities

A composed recipe that chains multiple skills into a higher-order outcome. First-class objects, not ad-hoc prompt engineering.

```yaml
id: "uuid"
slug: "vendor-risk-briefing"
name: "Vendor Risk Briefing"
description: "Produce a structured vendor risk assessment by combining financial data retrieval, public record search, and document synthesis"
version: "1.0.0"
trust_tier: "community"

steps:
  - skill: "loom://web-search-structured"
    role: "Gather public information about the vendor"
    inputs: { vendor_name: "$input.vendor_name" }
    outputs: { public_info: "$result" }

  - skill: "loom://financial-data-retrieval"
    role: "Pull financial filings and credit data"
    inputs: { company_name: "$input.vendor_name" }
    outputs: { financials: "$result" }
    required: false  # graceful degradation

  - skill: "loom://risk-synthesis"
    role: "Synthesise findings into structured risk assessment"
    inputs:
      public_info: "$steps[0].public_info"
      financials: "$steps[1].financials"
    outputs: { briefing: "$result" }

preconditions:
  - "Vendor name or identifier provided"
expected_outcome: "Structured risk briefing with financial health, public sentiment, and risk flags"

data_flow:
  - from: "web-search-structured"
    to: "risk-synthesis"
    classification: "external"  # data sourced externally
  - from: "financial-data-retrieval"
    to: "risk-synthesis"
    classification: "external"

dependencies:
  mcp_servers:
    - uri: "web-search-provider"
      required: true
    - uri: "financial-data-api"
      required: false
  trust_requirements:
    data_classification: "internal"  # output may contain internal assessments
    network_access: true

cost_profile: "moderate"
cost_drivers: ["external API calls", "LLM synthesis"]
estimated_duration: "slow"

eval:
  scenarios:
    - description: "Standard vendor assessment"
      input_context: "Well-known public company name"
      success_criteria: "Produces briefing covering financial health, public sentiment, key risks"
    - description: "Unknown or private company"
      input_context: "Small private company with limited public data"
      success_criteria: "Gracefully handles missing financial data, flags data gaps"
  quality_dimensions:
    - completeness: "All available data sources consulted"
    - accuracy: "No hallucinated financial figures"
    - actionability: "Risk flags are specific and decision-relevant"
```

### 3.3 Skill Sources & Resolution Chain

Skills exist at three levels, each with different scope, visibility, and hosting:

```
┌─────────────────────────────────────────────────────────────┐
│  Local (personal)                                            │
│  Lives on: user's machine                                    │
│  Scope: individual preferences, personal workflow tweaks     │
│  Examples: "always sign my commits", "use our team's Jira"   │
├─────────────────────────────────────────────────────────────┤
│  Corporate (org)                                             │
│  Lives on: private Loom instance (Loom-hosted or self-hosted)│
│  Scope: org-wide knowledge, internal tools, policies         │
│  Examples: "how to query our data warehouse",                │
│            "vendor onboarding per compliance policy",         │
│            "access the internal risk API"                     │
├─────────────────────────────────────────────────────────────┤
│  Community (public)                                          │
│  Lives on: public Loom registry                              │
│  Scope: general-purpose capabilities for any agent           │
│  Examples: "conventional commits", "web search + synthesis"  │
└─────────────────────────────────────────────────────────────┘
```

**Resolution priority:** Local > Corporate > Community. When an agent resolves a task, it checks sources in priority order. A corporate skill for "vendor risk assessment" takes precedence over a community one — the org has domain-specific knowledge. A personal skill takes precedence over both.

**Corporate skills are first-class.** They are not personal workarounds or community skills with caveats. They are org-specific capabilities maintained in a private registry, with the same versioning, signing, eval, and trust tier infrastructure as community skills. A corporate Loom instance runs the same eval engine, the same trust model, the same MCP interface — just scoped to an organisation.

**Cross-source capabilities.** Capabilities can compose skills from any source:

```yaml
# Corporate capability (lives in org's private Loom instance)
slug: "acme-vendor-onboarding"
scope: "corporate"
steps:
  - skill: "loom://web-search-structured"           # community skill
    role: "Gather public information about the vendor"

  - skill: "corp://acme-risk-db-query"               # corporate skill
    role: "Pull internal risk ratings from our database"

  - skill: "loom://risk-synthesis"                    # community skill
    role: "Synthesise findings into risk assessment"

  - skill: "corp://acme-compliance-formatter"         # corporate skill
    role: "Format per ACME compliance template and route to reviewers"
```

**URI scheme:** Skills reference their source via URI prefix:
- `loom://` — public Loom registry
- `corp://` — the agent's configured corporate Loom instance
- No prefix — local skill (resolved from disk)

### 3.3.1 The `extends` Mechanism

`extends` bridges layers. Any layer can extend a skill from any lower-priority layer (but not the reverse — higher-priority layers refine, they don't get refined by lower ones).

```
Local can extend → Corporate or Community
Corporate can extend → Community
Community cannot extend → Corporate or Local
```

`extends` is first-class — not a convenience feature but the architectural bridge between shared knowledge and local context.

**Example: personal extending corporate extending community**

```yaml
# Community skill (public Loom)
slug: "vendor-risk-briefing"
scope: "community"
# General-purpose vendor risk assessment instructions...
```

```yaml
# Corporate skill (org's private Loom) — extends community
slug: "acme-vendor-assessment"
scope: "corporate"
extends: "loom://vendor-risk-briefing@verified"
---

When using the vendor risk briefing:
- Always cross-reference against our approved vendor list via corp://acme-vendor-list
- Apply our risk threshold: flag any vendor with credit rating below BBB-
- Include GDPR compliance section (we're EU-based)
- Query our internal incident database for prior vendor issues
```

```yaml
# Local skill (on disk) — extends corporate
name: my-vendor-workflow
scope: personal
extends: "corp://acme-vendor-assessment@latest"
---

After completing the vendor assessment:
- Route to #procurement-review in Slack
- Create a Jira ticket in project VENDOR with the briefing attached
- CC me on the compliance notification email
```

**Resolution chain:**

```
Agent resolves "my-vendor-workflow" (local)
    ↓
Sees extends: "corp://acme-vendor-assessment@latest"
    ↓
Resolves corporate skill from org's Loom instance
    ↓
Corporate skill extends: "loom://vendor-risk-briefing@verified"
    ↓
Resolves community skill from public Loom
    ↓
Merges all three layers: community base → corporate refinements → personal preferences
    ↓
Agent receives the composed result
```

**Merge semantics:**

The `extends` merge is a defined operation, not ad-hoc concatenation. Layers are appended in priority order with clear delimiters:

```
[Community skill content]

---
## Corporate Context
[Corporate skill content]

---
## Local Overrides
[Personal skill content]
```

Each higher-priority layer refines the one below. If layers contradict (e.g., corporate says "use BBB- threshold" but personal says "use BB+"), the higher-priority layer wins. The agent treats sections in reverse priority — later sections override earlier ones.

This is intentionally simple: append with delimiters, not field-level merge. Complex merge strategies are fragile and model-dependent. A clear layered structure is unambiguous for any LLM.

**Rules:**
- Higher-priority layers can extend lower-priority layers. Never the reverse.
- `extends` supports version pinning (`@2.3.1`), trust tier pinning (`@verified`), or latest (`@latest`).
- `extends` chains are resolved recursively — if A extends B which extends C, all three are resolved and merged.
- The extended skill has no knowledge of its extenders. Extension is strictly a consumer-side operation.
- Local skills never transit any Loom instance. Corporate skills never transit the public Loom. Each layer resolves from its own source.

### 3.3.2 Corporate Loom Instances

A corporate Loom instance is a private deployment of the same Loom service, scoped to an organisation:

- **Same infrastructure**: registry, eval engine, MCP server, trust tiers, versioning, signing
- **Private skills**: only accessible to agents authenticated with the org's API keys
- **Cross-source resolution**: corporate instances can resolve `loom://` references against the public registry (configurable — air-gapped deployments can disable this)
- **Org-specific eval criteria**: corporate skills can have eval specs that reference internal standards or compliance requirements
- **Org-specific trust policies**: the org controls its own trust floor, approved categories, and promotion criteria

**Hosting models:**

| Model | Description | Target |
|-------|-------------|--------|
| **Loom-hosted** (SaaS) | Loom runs the private instance, org manages content | Mid-size orgs wanting managed infrastructure |
| **Self-hosted** | Org deploys Loom on their infrastructure | Enterprise with security/compliance requirements |
| **Loom-managed** | Loom deploys and maintains on org's cloud account | Enterprise wanting support without data leaving their environment |

This is the primary monetisation path: **Loom is free for community. Corporate instances are the paid product.** The public registry creates the ecosystem; corporate instances capture the value of org-specific knowledge management.

### 3.3.1 Capability Execution Model

Loom does **not** execute capabilities. It resolves them — returning a fully expanded execution plan that the agent runtime interprets.

When an agent calls `resolve_capability`, Loom returns:

```yaml
capability_id: "vendor-risk-briefing"
version: "1.0.0"
trust_tier: "community"
steps:
  - order: 1
    skill_slug: "web-search-structured"
    skill_version: "1.2.0"
    content: |
      # Full skill instructions, resolved and embedded
      ...
    role: "Gather public information about the vendor"
    inputs: { vendor_name: "$input.vendor_name" }
    outputs: ["public_info"]
    required: true
    dependencies: { satisfied: ["web-search"], missing: [] }

  - order: 2
    skill_slug: "financial-data-retrieval"
    skill_version: "3.0.1"
    content: |
      # Full skill instructions, resolved and embedded
      ...
    role: "Pull financial filings and credit data"
    inputs: { company_name: "$input.vendor_name" }
    outputs: ["financials"]
    required: false
    dependencies: { satisfied: [], missing: ["financial-data-api"] }

  - order: 3
    skill_slug: "risk-synthesis"
    skill_version: "1.0.0"
    content: |
      # Full skill instructions, resolved and embedded
      ...
    role: "Synthesise findings into structured risk assessment"
    inputs:
      public_info: "$steps[1].public_info"
      financials: "$steps[2].financials"
    outputs: ["briefing"]
    required: true

preconditions: "Vendor name or identifier provided"
expected_outcome: "Structured risk briefing with financial health, public sentiment, and risk flags"
```

Key design decisions:
- **Skills are fully resolved and embedded** — the agent runtime doesn't need to make additional Loom calls. Each step contains the complete instructions.
- **`$input` and `$steps[n]` are conventions, not executable code** — they tell the agent what to pass between steps. The agent runtime (or the LLM itself) interprets these naturally.
- **`required: false`** means the agent should skip the step if dependencies aren't met and continue with available data.
- **Execution is sequential by default** — steps are ordered. The agent runtime may parallelise independent steps (no inter-step data dependencies) if it chooses.
- **The agent is the executor** — Loom provides the plan; the agent follows it using whatever tools and MCP servers it has available.

### 3.4 Trust & Provenance

**Cryptographic signing:**
- Every skill/capability is signed by its author using ed25519 keypairs
- Keys are registered to Loom accounts at creation time
- Signatures cover `content + version + dependencies + eval_spec` — any change invalidates the signature. The eval_spec is included because it's the author's quality contract; tampering with it would allow a poor skill to pass evaluation without detection
- Consumers can verify signatures without trusting Loom itself (the public keys are available)

**Trust tiers (computed, not self-declared):**

| Tier | Criteria | How achieved |
|------|----------|-------------|
| `experimental` | Passes structural validation and basic eval | Automatic on submission |
| `community` | Passes full eval suite, >N successful usage reports, no security flags, signed | Automatic when thresholds met |
| `verified` | All of `community` + reviewed by category steward or partner org, signed by verified entity | Manual promotion |

**Dependency declarations:**
Skills declare what they need (MCP servers, APIs, network access, data classification). This is declarative — Loom validates the declarations, agent runtimes enforce them. Loom is a capability registry with rich auth metadata, not a credential broker.

**Dependency risk scoring:**
Skills requiring `network_access: true`, external APIs, or broad MCP scopes receive higher scrutiny. A skill needing network access cannot reach `verified` without explicit steward review. Risk score factors into search ranking.

**Scoped delegation (designed in, built later):**
Capabilities that chain steps can declare scope narrowing: "step 2 only needs read access to the output of step 1, not to the user's full context." The schema supports this; enforcement is deferred to agent runtimes and future delegation infrastructure.

### 3.5 Cost & Time Metadata

Every skill and capability carries economic metadata:

```yaml
cost_profile: "free" | "low" | "moderate" | "high"
cost_drivers: ["LLM API call", "external search API", "vision model", "database query"]
estimated_duration: "fast" | "moderate" | "slow"
```

For capabilities, these are aggregated from constituent skills but can be overridden if the composition introduces additional cost (e.g., an LLM synthesis step that isn't in any individual skill).

**Why this matters:** An agent choosing between two capabilities that achieve the same outcome can factor in cost and latency. A runtime with a budget constraint can filter results. This enables the economic routing layer the original design document argues for, without requiring a full billing or metering system on day one.

## 4. Architecture

### 4.1 System Overview

```
┌──────────────────────────────────────────────────────────┐
│  Agent Runtimes                                           │
│  (Claude Code, Codex, custom agents)                      │
│                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ Local skills │  │ Local skills │  │ Local skills │      │
│  │ (personal,   │  │ (personal,   │  │ (personal,   │      │
│  │  extends)    │  │  extends)    │  │  extends)    │      │
│  └──────┬───── ┘  └──────┬──────┘  └──────┬──────┘      │
│         │                │                │               │
│         └────────────────┼────────────────┘               │
│                          │ resolve / search               │
└──────────────────────────┼───────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  Loom MCP   │
                    │  Server     │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼────┐ ┌────▼─────┐ ┌───▼────────┐
        │ Registry  │ │ Discovery│ │ Eval       │
        │ Service   │ │ Service  │ │ Engine     │
        └─────┬────┘ └────┬─────┘ └───┬────────┘
              │            │            │
              └────────────┼────────────┘
                           │
                    ┌──────▼──────┐
                    │  PostgreSQL │
                    │  + pgvector │
                    └─────────────┘
```

### 4.2 Service Layer (Python / FastAPI)

**Registry Service:**
- Skill and capability CRUD with full version history
- Signature verification on all mutations
- Contribution workflows (new skill, amendment, new capability)
- Scope classification (community vs personal content detection)

**Discovery Service:**
- Semantic search via pgvector embeddings
- Constraint-aware ranking (semantic match, local/corporate precedence, trust tier, cost profile, dependency satisfaction, usage outcomes)
- Category browsing and filtering
- Alternative suggestions (when resolving, return the best match + ranked alternatives)
- Selection rationale and exclusion reasons for near matches

**Eval Engine:**
- New submission evaluation (structural, clarity, overlap, scope, dependency risk)
- Amendment comparison (run eval_spec against both versions, score delta)
- Capability end-to-end evaluation (reference validation, dependency compatibility, data flow analysis)
- Continuous re-evaluation (scheduled, covered in section 5)

**Contribution Service:**
- New skill pipeline: validate → eval → assign tier → index
- Amendment pipeline: scope check → eval comparison → auto-merge or human review
- New capability pipeline: reference validation → dependency check → data flow analysis → end-to-end eval

### 4.3 MCP Server (Primary Agent Interface)

```
resolve(task_description, context?) → ResolvedSkill
```

The core operation. Agent describes what it needs; Loom returns the best matching skill with full content, dependency status, and alternatives.

**Context** (optional, shapes resolution):
```yaml
trust_floor: "community"        # minimum tier accepted
cost_budget: "low"              # economic constraint
latency_budget: "fast"          # acceptable time to complete
data_classification: "internal" # affects which dependencies are allowed
available_tools:                # what the agent currently has
  - "filesystem"
  - "git"
  - "web-search"
approved_providers:
  - "internal-data-warehouse"
  - "public-web-search"
runtime: "claude-code"          # agent framework identifier
```

At resolution time, Loom does more than return a semantically similar result:

- It prefers the highest-priority applicable layer (local > corporate > community)
- It filters or downranks options whose dependencies, trust tier, or cost profile do not fit the current runtime context
- It returns alternatives with explicit trade-offs so the runtime can adapt when constraints change

**ResolvedSkill** response:
```yaml
skill_id: "git-commit-conventional"
version: "2.3.1"
trust_tier: "verified"
content: |
  # The actual skill instructions...
dependencies:
  satisfied: ["filesystem:read", "git"]
  missing: ["github-api"]
cost_profile: "free"
estimated_duration: "fast"
selection_rationale:
  - "Matched the requested task"
  - "All required dependencies are satisfied in the current runtime"
  - "Preferred over higher-cost alternatives because cost_budget='low'"
alternatives:
  - skill_id: "git-commit-ai-message"
    version: "1.1.0"
    trust_tier: "community"
    match_score: 0.82
    tradeoff: "Generates commit messages via LLM — higher quality but requires API call"
rejected_candidates:
  - skill_id: "git-commit-github-enriched"
    reason: "Requires github-api, which is not available in this runtime"
```

**Full MCP tool surface:**

| Tool | Purpose |
|------|---------|
| `resolve` | Resolve a single skill by task description — primary entry point. Returns full content, dependency status, alternatives |
| `resolve_capability` | Resolve a composed capability — returns full execution plan with all steps' content embedded |
| `search` | Browse/filter skills by category, tags, trust tier — returns summaries and metadata, not full content |
| `get_skill` | Fetch a specific skill by slug + version — for pinned references and `extends` |
| `report_usage` | Anonymous outcome feedback (success/partial/failure) — feeds quality signals |
| `list_categories` | Category taxonomy for browsing |

**Error and failure responses:**

All MCP tools return structured error responses when resolution fails:

```yaml
# No match found
error: "no_match"
message: "No skills matched 'quantum flux capacitor calibration' above the confidence threshold"
suggestions:
  - "Try broader terms: 'hardware calibration' or 'device configuration'"
  - "Lower trust_floor from 'verified' to 'community' for more results"

# Trust floor not met
error: "trust_floor_not_met"
message: "Found 3 matching skills but none meet trust_floor='verified'"
available_at_lower_tier:
  - skill_id: "flux-capacitor-setup"
    trust_tier: "community"
    match_score: 0.91

# Skill deprecated
error: "deprecated"
message: "Skill 'old-git-commit' is deprecated"
successor: "loom://git-commit-conventional@2.3.1"

# Skill removed (security/policy)
error: "removed"
message: "Skill 'compromised-skill' has been removed due to a security issue"
```

### 4.4 Web UI (Secondary, Human Interface)

For curation and governance, not primary consumption:

- Browse and search skills/capabilities with rich filtering
- Contribution workflow: submit, amend, review queue, diff view
- Quality dashboard: eval scores, usage trends, trust tier distribution, stale skill detection
- Org admin: configure trust floors, approved categories, usage analytics
- Category steward tools: review queue, tier promotion, dispute resolution

### 4.5 Caching & Offline

The default path is resolve-on-demand. Local caching is an optimisation, not the architecture.

**Prefetch manifest:** An org or agent runtime declares a base set of skill slugs. These are cached locally with a TTL. The runtime checks for updates on session start — fast, lightweight, just version comparison. If the network is down, cached versions work.

**Resolution caching:** Individual resolutions are cached by the runtime with ETags. Subsequent requests for the same capability are near-instant if the upstream version hasn't changed.

**Offline graceful degradation:** If Loom is unreachable, the agent falls back to cached resolutions, then to local skills, then to its own reasoning. The agent is never hard-blocked by a network outage.

## 5. Continuous Evaluation

Skills are not "publish and forget." Loom continuously re-evaluates to ensure quality doesn't degrade as models, ecosystems, and usage patterns evolve.

### 5.1 Evaluation Triggers

| Trigger | What happens |
|---------|-------------|
| **New submission** | Full eval pipeline: structural, clarity, overlap, scope, risk |
| **Amendment** | Comparative eval: original vs amended on skill's eval_spec |
| **Scheduled re-eval** | Periodic (configurable, default weekly): re-run eval on all `community` and `verified` skills with latest eval engine |
| **Usage signal** | When failure rate exceeds threshold (e.g., >30% of reports are "failure"), trigger re-eval and flag for review |
| **Model drift** | When the eval engine's underlying model is updated, re-score a sample and flag significant score changes |
| **Dependency change** | When a skill's declared MCP server or API changes status (deprecated, security advisory), re-evaluate and notify |

### 5.2 Eval Spec Contract

The eval_spec is the skill author's quality contract. It defines:

- **Scenarios**: concrete input/output situations the skill should handle
- **Quality dimensions**: named axes of quality (clarity, completeness, minimalism, etc.)
- **Regression threshold**: minimum score to maintain current trust tier

When the eval engine re-evaluates, it tests against the skill's own scenarios and scores against its own dimensions. A skill that was `community` but now scores below its regression threshold is flagged and demoted to `experimental` if not remediated.

### 5.3 Continuous Signals

Beyond formal eval, Loom collects continuous quality signals:

- **Usage outcome reports**: anonymous success/partial/failure from agent runtimes
- **Resolution frequency**: how often a skill is resolved (popularity signal)
- **Alternative selection**: when Loom returns alternatives, which one does the agent (or user) actually use? (preference signal)
- **Staleness detection**: skills with zero resolutions in 90 days are marked stale — deprioritised in search, not deleted

These signals feed into:
- Trust tier computation (high failure rate blocks promotion to `community`)
- Search ranking (usage success rate weights results)
- Amendment prioritisation (high-usage skills with declining scores are surfaced to stewards)

### 5.4 Eval Engine Resilience

The eval engine uses LLMs, which introduces non-determinism and availability risk. Mitigations:

**Deterministic baseline:** Every eval run includes deterministic structural checks (frontmatter validity, dependency schema, token count, overlap detection via embedding distance). These produce a hard pass/fail independent of LLM availability. A skill that fails structural checks is rejected regardless of LLM scores.

**LLM scoring with tolerance bands:** LLM-evaluated dimensions (clarity, completeness, minimalism) are scored on a 0-1 scale. To account for non-determinism:
- Each eval runs the LLM scorer 3 times and takes the median score per dimension
- Amendment auto-merge requires the amended version to score >= original minus a tolerance of 0.05 on every dimension (i.e., `B >= A - 0.05` per dimension, not strict `B >= A`)
- If the 3 scores for any dimension have a spread > 0.15, the result is flagged as low-confidence and sent to human review

**Provider fallback:** The eval engine supports multiple LLM providers. If the primary provider is unavailable, it falls back to a secondary. If all providers are down, submissions enter a "pending eval" queue and structural-only results are used for temporary tier assignment.

**Eval versioning:** Every eval result records the evaluator version (model + prompt + scoring logic). When the eval engine is updated, a sample of existing skills is re-scored. If the new engine disagrees with the old by more than 0.1 on average, the update is flagged for review before rollout.

### 5.5 Eval Engine Transparency

Eval results are public. For any skill, consumers can see:
- Current eval score and dimension breakdown
- Score history over time
- Usage outcome distribution
- Last eval date and evaluator version

This creates accountability: a skill's quality is observable, not asserted.

## 6. Community Model & Governance

### 6.1 Contribution Workflows

**New Skill:**
```
Contributor submits skill (content + eval_spec + dependencies)
    ↓
Automated eval pipeline
    ↓
Pass → enters registry as "experimental"
Borderline → human review queue
Fail → rejected with feedback
```

**Amendment:**
```
Contributor submits diff against existing skill
    ↓
Scope check: does the amendment change WHAT the skill does?
    → If yes: reject as amendment, suggest new skill submission
    → If no: proceed
    ↓
Run skill's eval_spec against both versions
    ↓
Improvement (B >= A all dimensions) → auto-merge, patch version bump
Mixed results → human review
Regression (B < A overall) → reject with explanation
    ↓
Anti-complexity gate: >20% token growth without proportional
eval improvement → flagged for review
```

**New Capability:**
```
Contributor submits composition recipe
    ↓
Reference validation (all skills exist, trust tiers met)
    ↓
Dependency compatibility check
    ↓
Data flow analysis (no internal data leaking to external without declaration)
    ↓
End-to-end eval against capability's eval_spec
    ↓
Pass → enters as "experimental"
```

### 6.2 User-Specific vs Community Boundary

Hard rules enforced at submission time:

- `community` skills must not contain: absolute file paths, hardcoded credentials, usernames, org-specific tool references, personal preferences
- `community` skills must be general-purpose — applicable across orgs and contexts
- `personal` skills can `extend` community skills. Never the reverse.
- An LLM classifier scans submissions for personal content; false positives go to contributor for confirmation

The `extends` mechanism is the designed bridge: community knowledge stays general, personal context stays local, and they compose cleanly at resolution time.

### 6.3 Governance Structure

**v1 (intentionally simple):**

- **Platform maintainers** — small team; responsible for eval engine, infrastructure, `verified` tier promotions, dispute resolution
- **Category stewards** — domain expert volunteers; review borderline submissions in their category, propose taxonomy changes
- **Contributors** — anyone with an account can submit; eval gating, not reputation gating

**Evolution path (not built in v1):**

- Reputation scores based on: eval scores of contributed skills, amendment acceptance rate, usage outcomes
- Higher reputation unlocks: faster review, direct merge for amendments, steward nomination
- Fork-and-prove: competing versions of a skill visible to consumers with comparative metrics

### 6.4 Abuse Prevention

Eval gating prevents low-quality skills but not high-volume noise. Additional measures:

- **Submission rate limiting**: New accounts are limited to 5 submissions per day. After 10 accepted skills, the limit increases to 20/day.
- **Duplicate detection at submission**: Before eval, embedding similarity check against existing skills. >0.90 similarity triggers a mandatory justification — contributor must explain why this isn't a duplicate.
- **Automated content scanning**: LLM classifier checks for prompt injection attempts, obfuscated instructions, credential harvesting patterns, and other adversarial content. Flagged submissions go to maintainer review, not the standard queue.
- **Account verification**: Email verification required. Submitting skills with `network_access: true` or external API dependencies requires additional verification (GitHub OAuth linking).
- **Reporting mechanism**: Any user can flag a skill. Flagged skills are deprioritised in search results and queued for maintainer review.

### 6.5 Skill Lifecycle & Deprecation

Skills have a defined lifecycle:

| State | Meaning |
|-------|---------|
| `active` | Normal state, appears in search results |
| `stale` | Zero resolutions in 90 days, deprioritised in search |
| `deprecated` | Author or steward has marked it as superseded |
| `removed` | Maintainer removal (security issue, policy violation) |

- Authors can deprecate their own skills and point to a successor: `deprecated_by: "loom://better-skill"`
- Deprecated skills still resolve (for pinned references) but include a `deprecated: true` flag and successor suggestion in the response
- `removed` skills return a 410 Gone with an explanation. Pinned references break intentionally — this is a security measure.
- Stewards can deprecate skills in their category. Only maintainers can remove.

### 6.6 Licensing

- All community skills: Apache 2.0 (permissive open source)
- Personal skills: private to the contributor's account
- Capabilities: inherit the most restrictive license of constituent skills

## 7. Authentication & Dependency Model

### 7.1 Platform Auth

- **Agent runtimes**: API keys tied to org/user accounts
- **Human users**: OAuth for web UI
- **Contributors**: ed25519 signing keypairs registered to accounts
- Built fully from day one

### 7.2 Skill Dependency Declarations

Skills declare external dependencies in structured frontmatter:

```yaml
dependencies:
  mcp_servers:
    - uri: "github.com/modelcontextprotocol/servers/filesystem"
      required: true
      scopes: ["read"]
    - uri: "some-org/slack-mcp-server"
      required: false
      scopes: ["channels:read", "messages:write"]
  apis:
    - name: "OpenAI API"
      auth_type: "api_key"
      env_var: "OPENAI_API_KEY"
    - name: "Jira"
      auth_type: "oauth2"
      scopes: ["read:jira-work"]
  trust_requirements:
    data_classification: "internal"
    network_access: true
    privacy_impact:
      external_data_sharing: true       # does this skill send data to third parties?
      input_logging: "unknown"          # none | anonymised | full | unknown
      data_retention: "unknown"         # none | transient | persistent | unknown
```

Privacy impact declarations follow the same principle as cost and dependency metadata: skills declare their privacy characteristics, runtimes enforce policy. An agent operating under GDPR constraints can filter out skills with `external_data_sharing: true` or `data_retention: "persistent"`. The `unknown` default ensures existing skills are not falsely marked as privacy-safe.

This is **declarative, not executable**. The skill says what it needs; the runtime decides whether to grant it. Loom validates declarations at ingest time; runtimes enforce at execution time.

### 7.3 Resolution-Time Dependency Checking

When an agent resolves a skill, the response includes dependency status:

```yaml
dependencies:
  satisfied: ["filesystem:read", "git"]
  missing: ["slack-mcp-server"]
```

The agent (or its runtime) can decide: proceed without optional dependencies, prompt the user, or choose an alternative with fewer requirements.

### 7.4 Delegation Model (Designed In, Built Later)

The schema supports but does not yet enforce:

- **Scoped delegation tokens**: a capability step can declare "this step only needs read access to the output of the previous step"
- **Data flow classifications**: each step declares what data flows in/out, enabling policy engines to check for leaks
- **Credential reference by role**: skills reference credentials by function ("a Slack token with channels:read") not by value; runtimes resolve roles to actual credentials

## 8. Data Model

### 8.1 Core Entities

**skills**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| slug | text | unique, human-readable |
| name | text | display name |
| description | text | short summary |
| content | text | full skill body (markdown) |
| category | text | hierarchical (e.g., "development/git") |
| tags | text[] | searchable tags |
| scope | enum | community (public Loom), corporate (private Loom instance). Personal skills are local-only, never stored in any Loom instance |
| version | text | semver |
| author_id | uuid | FK to users |
| signature | text | ed25519 over content+version+deps+eval_spec |
| trust_tier | enum | experimental, community, verified |
| cost_profile | enum | free, low, moderate, high |
| cost_drivers | text[] | what drives cost |
| estimated_duration | enum | fast, moderate, slow |
| dependencies | jsonb | structured dependency declarations |
| eval_spec | jsonb | scenarios + quality dimensions |
| embedding | vector(1536) | for semantic search |
| created_at | timestamptz | |
| updated_at | timestamptz | |

**skill_versions** — full version history (every mutation creates a new row)
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| skill_id | uuid | FK to skills |
| version | text | semver |
| content | text | skill body at this version |
| dependencies | jsonb | dependencies at this version |
| eval_spec | jsonb | eval criteria at this version |
| cost_profile | enum | |
| cost_drivers | text[] | |
| estimated_duration | enum | |
| signature | text | ed25519 over content+version+deps+eval_spec |
| author_id | uuid | FK to users |
| changelog | text | what changed from previous version |
| created_at | timestamptz | |

The `skills` table holds the **current/latest** version. `skill_versions` stores every historical version. Resolution defaults to latest; pinned references (`@2.3.1`) query `skill_versions` by `(skill_id, version)`.

**categories**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| slug | text | unique, hierarchical (e.g., "development/git") |
| name | text | display name |
| parent_id | uuid | FK to categories (null for root) |
| description | text | |
| created_at | timestamptz | |

Initial taxonomy is maintainer-curated. Stewards can propose additions. New skills can suggest a category; if it doesn't exist, it goes to a steward for approval.

**capabilities**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| slug | text | unique |
| name, description | text | |
| steps | jsonb | ordered skill references with data flow |
| preconditions | text | what inputs are needed |
| expected_outcome | text | what it produces |
| data_flow | jsonb | classification of data between steps |
| dependencies | jsonb | aggregated from steps + overrides |
| eval_spec | jsonb | end-to-end eval criteria |
| cost_profile, cost_drivers, estimated_duration | | aggregated |
| version, author_id, signature, trust_tier | | same as skills |
| embedding | vector(1536) | |

**eval_results**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| skill_id | uuid | FK |
| version | text | version evaluated |
| score | float | 0-1 composite |
| dimensions | jsonb | per-dimension scores |
| evaluator_version | text | eval engine version |
| trigger | enum | submission, amendment, scheduled, usage_signal, model_drift |
| created_at | timestamptz | |

**usage_reports**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| skill_id | uuid | FK |
| version | text | |
| outcome | enum | success, partial, failure |
| runtime | text | agent framework identifier |
| context_hash | text | anonymised task fingerprint |
| created_at | timestamptz | |

**users**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| handle | text | unique |
| email | text | |
| signing_public_key | text | ed25519 |
| role | enum | contributor, steward, maintainer |
| created_at | timestamptz | |

## 9. Privacy Considerations

Loom sees what agents ask for. This requires care at two levels: the privacy characteristics of skills themselves, and Loom's own data handling.

### 9.1 Skill-Level Privacy Metadata

Skills declare their privacy impact in structured frontmatter, alongside cost and dependency metadata:

- **`external_data_sharing`** — does executing this skill cause data to be sent to third-party services?
- **`input_logging`** — does the skill's dependency chain log the inputs it receives? (`none`, `anonymised`, `full`, `unknown`)
- **`data_retention`** — does the skill's dependency chain retain data beyond the immediate request? (`none`, `transient`, `persistent`, `unknown`)

This enables privacy-aware resolution: an agent with a `privacy_floor` constraint can filter or downrank skills whose privacy impact exceeds what the runtime allows. An enterprise agent handling PII can exclude skills with `external_data_sharing: true`. The `unknown` default ensures skills without explicit declarations are not falsely treated as privacy-safe.

Privacy metadata is validated at ingest (structural checks) but not verified by Loom — the same trust model as dependency declarations. Trust tier and community signals provide indirect verification over time.

### 9.2 Platform Query Privacy

- **Resolution queries are not logged with user identity** — the MCP server authenticates API keys for rate limiting and trust floor enforcement, but does not associate resolution queries with specific users or orgs
- **Resolution query text is not stored** — Loom logs skill IDs and outcomes for quality signals, not the natural language query text. Query embeddings are ephemeral (computed, used for vector search, discarded)
- **Usage reports are anonymous** — `context_hash` is a one-way hash of the task type, not the task content; runtime identifier is the framework, not the user
- **Personal skills are local-only** — neither the public Loom nor corporate instances store personal skills. Personal skills live on the user's machine. The `extends` mechanism resolves community/corporate parts from their respective Loom instances and merges with personal context locally. No Loom instance ever sees the personal layer
- **Corporate skills are org-scoped** — corporate Loom instances are isolated per-org. Cross-source resolution (`loom://` from a corporate instance) sends only the skill slug to the public registry, not the corporate context or the task description
- **Embedding queries** — semantic search sends a task description to Loom's embedding model. These should be treated as ephemeral (not stored) and should not contain sensitive task content. Runtimes should sanitise queries before sending

### 9.3 Tiered Observability (Designed In, Built Later)

Different consumers have fundamentally different privacy needs:

- **Corporate instances** typically want full audit trails — which skills were resolved, by which team, how often, with what outcomes. This is a selling point for compliance-heavy organisations.
- **Public registry users** want minimal telemetry — anonymous usage signals, no query logging, no activity profiling.

These are different privacy contracts, not different levels of the same contract. The architecture accommodates this naturally: corporate Loom instances control their own logging policy (including full audit when required), while the public registry defaults to privacy-preserving behaviour. The multi-tenancy split in M5 is the natural boundary for this divergence.

A future enhancement may introduce explicit **privacy tiers** on the public registry (e.g., opt-in to richer analytics for contributors who want skill performance data), but this is deferred beyond M5.

## 10. Multi-Runtime Compatibility

Loom is agent-framework agnostic. Skills are markdown instructions, not framework-specific code. However, different runtimes have different conventions:

- **Skill format**: Loom uses its own structured YAML frontmatter (richer than SKILL.md). A compatibility layer can export Loom skills as SKILL.md for runtimes that expect that format.
- **Tool references**: Skills reference tools by capability role ("filesystem read", "web search") not by framework-specific tool names. Runtimes map roles to their local tool implementations.
- **Migration**: Existing SKILL.md files from ClawHub/SkillsMP can be imported into Loom with automated frontmatter enrichment (add eval_spec, dependency declarations, cost metadata). The eval engine scores them normally.

## 11. Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| API | Python, FastAPI | Async, well-suited for LLM integration, strong typing with Pydantic |
| Database | PostgreSQL + pgvector | Relational + vector search in one store; proven at scale |
| MCP Server | Python, MCP SDK | Primary agent-facing interface |
| Eval Engine | LLM-powered (configurable provider) | Quality evaluation requires reasoning, not just pattern matching |
| Embeddings | Configurable (OpenAI, local) | For semantic search; swappable |
| Auth | API keys + OAuth + ed25519 signing | Platform auth + contributor signing |
| Web UI | React (SPA) | Secondary interface for curation/governance |
| Task Queue | Redis + background workers | For async eval pipeline, scheduled re-eval |

## 12. What We Build in v1

**Fully functional:**
- Skill registry with versioning, signing, structured frontmatter
- Capability registry with step references and data flow declarations
- MCP server with `resolve`, `resolve_capability`, `search`, `get_skill`, `report_usage`, `list_categories`
- Eval engine: submission eval, amendment comparison, anti-complexity gate
- Semantic search via pgvector
- Constraint-aware resolution that accounts for trust, dependency satisfaction, and cost/time constraints
- Trust tier computation (experimental → community automatic; verified manual)
- Platform auth (API keys, OAuth, signing keys)
- Dependency declarations validated at ingest
- Cost and time metadata on all skills/capabilities
- Usage report collection and quality signal aggregation
- Continuous scheduled re-evaluation
- Reference Python implementation of client-side `extends` resolution for local layering
- Web UI for browsing, contribution, and review

**Designed in, built later:**
- Corporate Loom instances (private registries, cross-source resolution)
- Credential brokering / token exchange
- Runtime scope enforcement
- Cross-service delegation chains
- Reputation scoring and reputation-gated workflows
- Fork-and-prove competitive versioning
- Full billing / metering integration
- Federated Loom nodes (decentralisation path)
- Privacy tiers on the public registry (opt-in analytics for contributors)
- Tiered observability policies (corporate audit vs public privacy-preserving defaults)

## 13. Monetisation Model

The public Loom registry is free. Corporate Loom instances are the paid product.

```
┌──────────────────────────────────────────────────────────┐
│  Free Tier (Community)                                    │
│  - Full access to public registry (resolve, search, etc.) │
│  - Submit and maintain community skills                   │
│  - Usage reporting                                        │
│  - Rate limited (generous for individual agents)          │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  Team Tier                                                │
│  - Corporate Loom instance (Loom-hosted SaaS)             │
│  - Private skill registry with full eval engine           │
│  - Cross-source resolution (corp:// + loom://)            │
│  - Org-level API keys, trust floor policies               │
│  - Usage analytics dashboard                              │
│  - Higher rate limits                                     │
│  - Category steward tools for internal curation           │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  Enterprise Tier                                          │
│  - Self-hosted or Loom-managed deployment                 │
│  - Air-gapped option (no public registry connectivity)    │
│  - SSO/SAML integration                                   │
│  - Custom eval criteria and compliance policies           │
│  - Audit logs and access controls                         │
│  - SLA and dedicated support                              │
│  - Multi-instance federation (e.g., per-division)         │
└──────────────────────────────────────────────────────────┘
```

**Why this works:**

1. **The community registry is the moat.** A rich, evaluated, always-current public skill ecosystem is what makes Loom valuable. Gating it behind payment would kill adoption.

2. **Corporate value is obvious.** Every org has internal knowledge that agents need — how to access internal systems, compliance policies, approved workflows. Today this knowledge lives in wikis, Confluence pages, and tribal knowledge. Corporate Loom turns it into agent-accessible, evaluated, maintained capabilities.

3. **The extends chain creates lock-in.** Once an org's corporate skills build on community skills via `extends`, and their employees' personal skills build on corporate skills, the resolution chain is deeply integrated. Switching costs are high because the value is in the composition, not just the individual skills.

4. **Metering is natural.** Corporate instances meter resolutions, eval runs, and storage. Usage-based pricing aligns cost with value delivered.

## 14. Open Questions

1. **Eval engine model selection**: The eval engine supports multiple LLM providers with fallback (see 5.4). Which model(s) should be the primary evaluator? Trade-off between cost and reasoning quality.
2. **Embedding model choice**: pgvector embeddings need a specific model. Should this be configurable per-deployment or standardised across all Loom instances?
3. **Resolution rate limiting**: How aggressive should rate limits be on `resolve`? Too tight hurts agent workflows; too loose invites abuse. Likely needs tiered limits by API key plan.
4. **Skill format versioning**: As the frontmatter schema evolves, how do we handle backward compatibility with older skills? Likely a `schema_version` field with migration support.
5. **Synthetic capability execution**: Should Loom ever verify that a capability *actually works* end-to-end (run it against synthetic inputs), or only validate structure and metadata? Powerful but expensive. Likely v2.
6. **Cross-Loom federation**: Corporate instances connecting to the public registry is straightforward (one-way pull). But should corporate instances be able to publish back to community? Should multiple corporate instances federate (e.g., supply chain partners sharing vendor assessment skills)? The URI scheme (`loom://`, `corp://`) supports this but the trust model for cross-org federation needs design.
7. **Skill format as open standard**: Should the Loom skill format (YAML frontmatter + markdown body + eval_spec) be proposed as an open standard independent of the Loom service? This would encourage adoption and make Loom the reference implementation rather than a proprietary format.
