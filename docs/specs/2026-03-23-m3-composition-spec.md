# M3: Composition & Capabilities — Security Spec

**Date**: 2026-03-23
**Status**: Draft
**Companion to**: [Loom Design Spec](2026-03-21-loom-design.md) · [Implementation Milestones](implementation-milestones.md) · [M2 Quality & Trust Spec](2026-03-23-m2-quality-trust-spec.md)

---

## 1. Overview

### 1.1 Thesis

Loom can compose atomic skills into higher-order capabilities and resolve them as single coherent execution plans. No other skill platform offers first-class composition with validated data flow, dependency aggregation, and trust propagation.

### 1.2 Why This Spec Exists

M3 introduces capabilities: multi-step execution plans that chain skills together. This creates a new attack surface that does not exist in M1/M2. When skills are composed, trust decisions become transitive, data flows between steps can carry injection payloads, and the extends mechanism gains a second dimension (capabilities extending capabilities). A naive implementation would allow attackers to launder trust through composition, inject via data flow, or substitute steps through extends overlays.

This spec defines the capability data model, resolution semantics, extends behaviour for capabilities, and — critically — the composition security model that prevents these attacks.

### 1.3 Design Principles

1. **Minimum trust propagation** — a composed result is only as trustworthy as its least trustworthy component. Trust never flows upward through composition.
2. **Explicit source binding** — step skill references use URI prefixes (`loom://`, `corp://`) and resolve strictly from the declared source. No implicit resolution or shadowing.
3. **Append-only extends** — capability extends can add steps but cannot replace or remove existing steps. Override requires a new version, not an extends overlay.
4. **Data flow classification** — every flow edge between steps has a declared classification. Steps consuming external data are evaluated with that context.
5. **Fail-safe resolution** — if any step in a capability fails to resolve, the entire plan resolution fails with a clear per-step error report (unless the step is marked `required: false`).

---

## 2. Capability Data Model

### 2.1 Core Models

Capabilities are first-class objects alongside skills. They share the same versioning, trust tier, and eval infrastructure but add multi-step composition.

```python
class CapabilityStep(BaseModel):
    """A single step in a capability's execution plan."""
    skill_ref: str                     # URI: "loom://slug" or "corp://slug"
    role: str                          # Human-readable purpose of this step
    inputs: dict[str, str] = {}        # Input mapping: param -> "$input.x" or "$steps[n].output"
    outputs: dict[str, str] = {}       # Output mapping: name -> "$result"
    required: bool = True              # If false, skip when deps unmet
    data_classification: str = "internal"  # "internal" | "external" | "confidential"

class DataFlowEdge(BaseModel):
    """Declared data flow between steps."""
    from_step: str                     # Slug of source step's skill
    to_step: str                       # Slug of destination step's skill
    classification: str                # "internal" | "external" | "confidential"

class CapabilityCreate(BaseModel):
    slug: str
    name: str
    description: str
    category_slug: str
    version: str
    tags: list[str] = []
    scope: Scope = Scope.COMMUNITY
    trust_tier: TrustTier = TrustTier.EXPERIMENTAL
    steps: list[CapabilityStep]
    preconditions: list[str] = []
    expected_outcome: str = ""
    data_flow: list[DataFlowEdge] = []
    dependencies: DependencyDeclaration = DependencyDeclaration()
    cost_profile: CostProfile = CostProfile.FREE
    cost_drivers: list[str] = []
    estimated_duration: EstimatedDuration | str = EstimatedDuration.SLOW
    eval_spec: EvalSpec = EvalSpec()
    extends: str | None = None

class Capability(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    description: str
    category_id: uuid.UUID
    tags: list[str]
    scope: str
    version: str
    author_id: uuid.UUID
    trust_tier: TrustTier
    steps: list[CapabilityStep]
    preconditions: list[str]
    expected_outcome: str
    data_flow: list[DataFlowEdge]
    dependencies: DependencyDeclaration = DependencyDeclaration()
    cost_profile: CostProfile
    cost_drivers: list[str]
    estimated_duration: str
    eval_spec: EvalSpec = EvalSpec()
    extends: str | None = None
    embedding: list[float] | None = Field(default=None, exclude=True)
    eval_status: str | None = None
    composite_score: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class CapabilitySummary(BaseModel):
    """Lightweight capability representation for search results."""
    id: uuid.UUID
    slug: str
    name: str
    description: str
    category_id: uuid.UUID
    tags: list[str]
    version: str
    trust_tier: TrustTier
    cost_profile: CostProfile
    estimated_duration: str
    step_count: int
```

### 2.2 Resolved Models

```python
class ResolvedStep(BaseModel):
    """A step with its skill fully resolved and embedded."""
    index: int
    skill_ref: str
    role: str
    skill: Skill                       # Full resolved skill content
    inputs: dict[str, str]
    outputs: dict[str, str]
    required: bool
    data_classification: str
    dependencies_satisfied: list[str] = []
    dependencies_missing: list[str] = []

class ResolvedCapability(BaseModel):
    """A fully resolved capability with all steps' skills embedded."""
    capability: Capability
    resolved_steps: list[ResolvedStep]
    effective_trust_tier: TrustTier    # Minimum across all steps
    trust_warnings: list[str] = []     # Warnings about experimental steps, etc.
    all_dependencies_satisfied: list[str] = []
    all_dependencies_missing: list[str] = []
    data_flow: list[DataFlowEdge]
    alternatives: list[Alternative] = []
    selection_rationale: list[str] = []
```

### 2.3 Type Discrimination

The unified `resolve()` response needs a type indicator so the agent knows whether it received a skill or a capability:

```python
class ResolvedResult(BaseModel):
    """Union result from resolve() — either a skill or a capability."""
    type: Literal["skill", "capability"]
    skill: ResolvedSkill | None = None
    capability: ResolvedCapability | None = None
```

---

## 3. Database Schema

### 3.1 New Tables

**`capabilities`** — mirrors skills table structure for capability metadata.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK, `gen_random_uuid()` |
| slug | TEXT | UNIQUE, NOT NULL |
| name | TEXT | NOT NULL |
| description | TEXT | NOT NULL |
| category_id | UUID | FK → categories |
| tags | TEXT[] | GIN index |
| scope | VARCHAR(20) | `community` default |
| version | TEXT | NOT NULL |
| author_id | UUID | FK → users |
| trust_tier | VARCHAR(20) | `experimental` default |
| steps | JSONB | NOT NULL — serialised `list[CapabilityStep]` |
| preconditions | JSONB | `[]` default |
| expected_outcome | TEXT | |
| data_flow | JSONB | `[]` default — serialised `list[DataFlowEdge]` |
| dependencies | JSONB | `{}` default — aggregated from steps |
| cost_profile | VARCHAR(20) | `free` default |
| cost_drivers | TEXT[] | |
| estimated_duration | VARCHAR(20) | `slow` default |
| eval_spec | JSONB | `{}` default |
| extends | TEXT | Nullable — extends URI |
| embedding | vector(1536) | For semantic search |
| eval_status | VARCHAR(20) | Nullable |
| composite_score | FLOAT | Nullable |
| created_at | TIMESTAMPTZ | `now()` |
| updated_at | TIMESTAMPTZ | `now()` |

Indexes: `idx_capabilities_category`, `idx_capabilities_trust_tier`, `idx_capabilities_scope`, `idx_capabilities_tags` (GIN).

**`capability_versions`** — version history, mirrors `skill_versions`.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| capability_id | UUID | FK → capabilities, CASCADE |
| version | TEXT | NOT NULL |
| steps | JSONB | NOT NULL |
| preconditions | JSONB | |
| expected_outcome | TEXT | |
| data_flow | JSONB | |
| dependencies | JSONB | |
| cost_profile | VARCHAR(20) | |
| cost_drivers | TEXT[] | |
| estimated_duration | VARCHAR(20) | |
| eval_spec | JSONB | |
| extends | TEXT | |
| author_id | UUID | FK → users |
| changelog | TEXT | |
| created_at | TIMESTAMPTZ | |

Unique constraint: `(capability_id, version)`.

### 3.2 No New Columns on Existing Tables

Capabilities are a parallel entity to skills, not an extension. The `skills` table is unchanged. The `eval_jobs` table gains an optional `capability_id` column (nullable) to support capability evaluation in the future, but this is deferred to M3iv.

---

## 4. Resolution

### 4.1 `resolve_capability(task_description, context?)`

When a capability matches better than an atomic skill, `resolve()` returns a `ResolvedCapability` containing the full execution plan with all steps' skills embedded.

**Resolution algorithm:**

1. Embed the task description (same embedder as skills).
2. Vector-search capabilities alongside skills (combined candidate pool).
3. Apply constraint-aware ranking (trust floor, cost budget, dependency satisfaction).
4. If the best candidate is a capability:
   a. For each step, resolve the referenced skill via its URI (`loom://slug` or `corp://slug`).
   b. Check each step's skill against the trust floor and dependency context.
   c. Compute `effective_trust_tier` = minimum trust tier across all steps' skills.
   d. If `effective_trust_tier` < context trust floor, reject with explanation.
   e. Aggregate dependencies: union of all steps' required dependencies.
   f. Mark per-step `dependencies_satisfied` / `dependencies_missing` based on `available_tools`.
   g. For `required: false` steps where dependencies are unmet, mark as skippable.
   h. Embed full skill content in each `ResolvedStep`.
5. Return `ResolvedCapability` with the complete plan.

### 4.2 Full Plan Resolution

The resolved plan is self-contained. The agent does not need further Loom lookups to execute it. Each step contains:
- The complete skill content (instructions the agent follows)
- Dependency satisfaction status for that specific step
- Data flow classification for the step's inputs/outputs
- Whether the step is required or skippable

### 4.3 Unified `resolve()` Return

The existing `resolve()` MCP tool returns either a `ResolvedSkill` or a `ResolvedCapability` wrapped in a `ResolvedResult` with a `type` discriminator:

```json
{
  "type": "capability",
  "capability": {
    "capability": { "slug": "vendor-risk-briefing", ... },
    "resolved_steps": [ ... ],
    "effective_trust_tier": "community",
    "trust_warnings": [],
    ...
  }
}
```

Agents that do not understand capabilities can fall back to treating the response as opaque instructions. The `type` field enables capability-aware agents to execute step-by-step with proper data passing.

---

## 5. Extends for Capabilities

### 5.1 Capability Extends

Capabilities can use `extends` to layer on top of other capabilities. The same URI scheme applies: `loom://capability-slug@version` or `corp://capability-slug@version`.

### 5.2 Merge Strategy: Append-Only

**Critical security decision:** capability extends is append-only.

When capability B extends capability A:
- B inherits all of A's steps in their original order.
- B can ADD new steps after A's steps.
- B can ADD new preconditions.
- B can ADD new data flow edges (from B's new steps to/from inherited steps).
- B CANNOT replace, remove, or reorder A's existing steps.
- B CANNOT modify A's existing data flow edges.

This prevents step substitution attacks (Threat 5 below).

If a capability needs to change inherited steps, it must create a new version (new slug or new version number) rather than using extends. This is by design: extends is for refinement and extension, not for mutation.

### 5.3 Resolution Chain

The extends resolver for capabilities follows the same pattern as skills:

```
local://my-briefing-workflow
    ↓ extends
corp://acme-vendor-briefing
    ↓ extends
loom://vendor-risk-briefing
```

Resolution proceeds bottom-up: resolve the community base, apply corporate additions, apply local additions. The result is a flat list of steps from all layers.

### 5.4 Trust Propagation in Extends Chains

The effective trust tier of the composed capability is the minimum across:
- The base capability's trust tier
- All extending capabilities' trust tiers
- All individual steps' referenced skills' trust tiers

If any link in the chain is `experimental`, the entire composed result is `experimental`.

---

## 6. Composition Security Model

This is the core security analysis for M3. Composition introduces attack vectors that do not exist in atomic skill resolution.

### 6.1 Threat 1: Injection via Extends Chain

**Vector:** A malicious corporate overlay extends a trusted community capability and injects adversarial content. When the agent resolves the chain, the injected content gets merged into the final result. The community capability's trust score is "inherited" by the composed result, lending false credibility.

**Impact:** Agent executes injected instructions believing they come from a trusted source. Trust laundering: experimental content masquerades as community/verified.

**Defence: Minimum trust tier across all layers.**

The resolved capability's `effective_trust_tier` is the minimum trust tier across every layer in the extends chain AND every referenced skill in every step. If the community base is `verified` but the corporate overlay is `experimental`, the composed result is `experimental`.

Implementation:
- `resolve_capability()` computes `effective_trust_tier = min(tier for tier in all_layers + all_step_skills)`.
- If any layer's trust tier is below the context's `trust_floor`, resolution fails with an explicit error naming the offending layer.
- The `trust_warnings` field in `ResolvedCapability` lists every layer/step that reduced the effective tier.

### 6.2 Threat 2: Dependency Confusion (Source Shadowing)

**Vector:** A capability references `loom://web-search` in step 1. An attacker publishes a `corp://web-search` skill with the same slug. If step resolution falls back to implicit source matching, the agent gets the corporate skill instead of the expected community one.

**Impact:** Step substitution via namespace shadowing. Attacker-controlled skill content executed in a capability context that appears community-trusted.

**Defence: Explicit source prefixes are mandatory.**

All skill references in capability steps MUST include a URI scheme prefix (`loom://`, `corp://`). Steps without a prefix are rejected at validation time (creation and update).

Implementation:
- `CapabilityStep.skill_ref` is validated on creation: must contain `://`.
- Resolution is strict: `loom://web-search` resolves ONLY from the public registry. `corp://web-search` resolves ONLY from the corporate instance. There is no fallback or cross-source resolution for step references.
- If a `corp://` reference is encountered on the public Loom registry (which has no corporate context), it resolves to a structured "not available" placeholder rather than attempting cross-source lookup.

### 6.3 Threat 3: Data Flow Injection

**Vector:** Step 1 produces output that step 2 consumes. Step 1's skill is an external data retrieval task (e.g., web search). A malicious website returns content containing prompt injection. Step 2's skill (e.g., synthesis) receives this output and interprets the injected content as instructions.

**Impact:** Prompt injection propagated through data flow. The capability's structure amplifies the attack surface because data flows are declared and automatic.

**Defence: Data flow classification with safety context.**

Every `DataFlowEdge` has a `classification` field:
- `internal` — data originates from controlled sources (e.g., local files, internal APIs)
- `external` — data originates from uncontrolled sources (e.g., web search, user input)
- `confidential` — data contains sensitive information that should not be exposed

Implementation:
- Data flow classification is declared upfront in the capability definition.
- The resolved plan includes classification per flow edge.
- Steps that consume `external` classified data have their `data_classification` field set to `external`.
- During capability evaluation (M2 pipeline applied to capabilities), steps consuming external data are assessed with awareness that their inputs may contain adversarial content.
- The selection rationale in the resolved plan warns when external data flows exist: "Step 2 (risk-synthesis) consumes external data from step 1 (web-search); treat inputs as untrusted."

**Note:** Loom does not enforce runtime data flow isolation — that is the agent runtime's responsibility. Loom's role is to declare and warn. The resolved plan provides sufficient information for a capable agent runtime to apply appropriate sandboxing.

### 6.4 Threat 4: Privilege Escalation via Composition

**Vector:** A capability chains a low-trust skill (`experimental`) with a high-trust skill (`verified`). The composition could be used to launder trust — an attacker publishes an experimental skill and composes it with a verified one, hoping the capability inherits the higher tier.

**Impact:** Trust laundering. Experimental content gains implicit endorsement by association with verified skills.

**Defence: Minimum trust across all steps + explicit warnings.**

Same mechanism as Threat 1, applied at the step level rather than the extends chain level:

- `effective_trust_tier = min(step.skill.trust_tier for step in capability.steps)`
- If ANY step references an `experimental` skill, the resolved capability includes a warning: "Capability contains experimental skill 'slug' at step N. Effective trust tier reduced to experimental."
- Capabilities submitted for evaluation are scored with awareness of their constituent trust tiers. A capability composed entirely of `verified` skills scores higher on the safety dimension than one containing `experimental` components.

### 6.5 Threat 5: Step Substitution via Extends

**Vector:** Capability B extends capability A. B replaces A's step 2 (which references a trusted `loom://web-search`) with a malicious alternative (`corp://fake-search`). Because extends is supposed to be a refinement, the substitution might not be obvious.

**Impact:** Trusted capability's steps replaced with attacker-controlled alternatives through the extends mechanism.

**Defence: Append-only merge for capability extends.**

Capabilities that extend other capabilities can ADD steps but CANNOT REPLACE or REMOVE existing steps.

Implementation:
- The `ExtendsResolver` for capabilities enforces append-only semantics.
- When merging, the resolver verifies that the base capability's steps are preserved exactly (same `skill_ref`, same `role`, same `inputs`/`outputs`).
- If the extending capability defines a step with the same index or role as a base step, the merge is rejected with error: "Capability extends cannot replace existing steps. Create a new version instead."
- The extending capability's steps are appended after the base capability's steps, with step indices adjusted accordingly.
- Data flow edges from the extending capability can reference both inherited and new steps.

### 6.6 Threat 6: Circular Extends

**Vector:** Capability A extends B, B extends C, C extends A. Resolution enters an infinite loop.

**Impact:** Resource exhaustion. Resolution hangs or crashes.

**Defence: Cycle detection via visited URI tracking.**

Implementation:
- The extends resolver maintains a set of visited URIs during chain resolution.
- Before resolving each `extends` target, the URI is checked against the visited set.
- If a cycle is detected, resolution fails immediately with error: "Circular extends chain detected: A -> B -> C -> A. Remove the cycle."
- Maximum chain depth limit: 10 levels. Chains deeper than this are rejected regardless of cycles.

### 6.7 Threat Matrix

| # | Threat | Impact | Defence | Verification |
|---|--------|--------|---------|-------------|
| 1 | Injection via extends chain | Trust laundering | Min trust across all layers | Adversarial test: compose experimental + verified, verify effective tier = experimental |
| 2 | Dependency confusion | Step substitution | Mandatory URI prefixes, strict source resolution | Test: step without `://` rejected; `loom://x` never resolves from corp |
| 3 | Data flow injection | Prompt injection propagation | Classification per edge, safety warnings | Test: external flow edge produces warning in resolved plan |
| 4 | Privilege escalation | Trust laundering | Min trust across steps + warnings | Test: capability with mixed tiers reports minimum |
| 5 | Step substitution | Trusted steps replaced | Append-only extends merge | Test: extends that modifies base step is rejected |
| 6 | Circular extends | Resource exhaustion | Visited set + depth limit | Test: A->B->C->A produces cycle error |

---

## 7. API Endpoints

### 7.1 Capability CRUD

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/capabilities` | Create a new capability |
| GET | `/api/v1/capabilities` | List capabilities (with filters) |
| GET | `/api/v1/capabilities/search` | Semantic search for capabilities |
| GET | `/api/v1/capabilities/{slug}` | Get capability by slug |
| PUT | `/api/v1/capabilities/{slug}` | Update capability (version bump) |

### 7.2 Resolution

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/capabilities/resolve` | Resolve a capability from task description |

### 7.3 Unified Resolution

The existing `POST /api/v1/skills/resolve` endpoint is extended to search both skills and capabilities. The response includes a `type` field (`"skill"` or `"capability"`) so the consumer knows which shape to expect. A query parameter `?type=skill|capability|any` allows filtering (default: `any`).

---

## 8. MCP Tools

### 8.1 New Tools

**`resolve_capability(task_description, context?)`** — resolve the best capability for a task. Returns a `ResolvedCapability` with full execution plan.

**`get_capability(slug, version?)`** — fetch a specific capability by slug.

### 8.2 Modified Tools

**`resolve(task_description, context?)`** — now returns either a `ResolvedSkill` or a `ResolvedCapability` wrapped in a `ResolvedResult` with `type` discriminator.

**`search(query, ...)`** — now includes capabilities in results. A `type` filter parameter is added (`skill`, `capability`, `any`).

---

## 9. Seed Capabilities

Three seed capabilities that compose existing seed skills:

### 9.1 `comprehensive-code-review`

Composes: `review-pull-request` + `review-security` + `review-performance`

```yaml
slug: "comprehensive-code-review"
name: "Comprehensive Code Review"
description: "Full code review combining structural review, security analysis, and performance assessment"
steps:
  - skill: "loom://review-pull-request"
    role: "Perform structural code review of the pull request"
    inputs: { diff: "$input.diff" }
    outputs: { structural_review: "$result" }
  - skill: "loom://review-security"
    role: "Analyse code changes for security vulnerabilities"
    inputs: { diff: "$input.diff" }
    outputs: { security_review: "$result" }
  - skill: "loom://review-performance"
    role: "Assess performance implications of code changes"
    inputs: { diff: "$input.diff" }
    outputs: { performance_review: "$result" }
preconditions:
  - "Pull request diff available"
expected_outcome: "Combined review covering structure, security, and performance with prioritised findings"
data_flow:
  - from: "review-pull-request"
    to: "review-security"
    classification: "internal"
  - from: "review-pull-request"
    to: "review-performance"
    classification: "internal"
```

### 9.2 `release-documentation`

Composes: `release-notes-enriched` + `changelog-update` + `api-docs-generate`

```yaml
slug: "release-documentation"
name: "Release Documentation"
description: "Generate complete release documentation including enriched notes, changelog, and API docs"
steps:
  - skill: "loom://release-notes-enriched"
    role: "Generate enriched release notes from git history"
    inputs: { version: "$input.version" }
    outputs: { release_notes: "$result" }
  - skill: "loom://changelog-update"
    role: "Update CHANGELOG.md with new version entry"
    inputs: { version: "$input.version", notes: "$steps[0].release_notes" }
    outputs: { changelog: "$result" }
  - skill: "loom://api-docs-generate"
    role: "Regenerate API documentation reflecting changes"
    inputs: {}
    outputs: { api_docs: "$result" }
    required: false
preconditions:
  - "Git repository with tagged releases"
  - "Version number for the release"
expected_outcome: "Complete release documentation package: release notes, updated changelog, and refreshed API docs"
data_flow:
  - from: "release-notes-enriched"
    to: "changelog-update"
    classification: "internal"
```

### 9.3 `accessibility-security-review`

Composes: `review-accessibility` + `review-security`

```yaml
slug: "accessibility-security-review"
name: "Accessibility & Security Review"
description: "Combined review for accessibility compliance and security vulnerabilities"
steps:
  - skill: "loom://review-accessibility"
    role: "Assess code changes for accessibility compliance"
    inputs: { diff: "$input.diff" }
    outputs: { accessibility_review: "$result" }
  - skill: "loom://review-security"
    role: "Analyse code changes for security vulnerabilities"
    inputs: { diff: "$input.diff" }
    outputs: { security_review: "$result" }
preconditions:
  - "Pull request diff available"
expected_outcome: "Combined review covering both accessibility and security with prioritised remediation steps"
data_flow: []
```

---

## 10. Configuration

### 10.1 New Settings

```python
class CapabilityConfig(BaseModel):
    """Configuration for capability composition."""
    max_steps: int = 20                    # Maximum steps per capability
    max_extends_depth: int = 10            # Maximum extends chain depth
    max_data_flow_edges: int = 50          # Maximum data flow declarations
    allow_cross_source_refs: bool = True   # Allow loom:// + corp:// in same capability
    require_uri_prefix: bool = True        # Require explicit source prefix on all step refs
```

Add `capability: CapabilityConfig` to `LoomSettings`.

### 10.2 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOOM_CAPABILITY__MAX_STEPS` | 20 | Max steps per capability |
| `LOOM_CAPABILITY__MAX_EXTENDS_DEPTH` | 10 | Max extends chain depth |
| `LOOM_CAPABILITY__REQUIRE_URI_PREFIX` | true | Enforce URI prefixes on step refs |
