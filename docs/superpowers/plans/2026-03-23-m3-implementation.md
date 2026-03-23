# M3: Composition & Capabilities — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build first-class capability composition: multi-step execution plans that chain atomic skills, with validated data flow, dependency aggregation, trust propagation, secure extends, and unified resolution returning either skills or capabilities.

**Architecture:** Capabilities are parallel entities to skills with their own DB tables, repository, and registry service. Resolution is unified: vector search spans both skills and capabilities, ranking them in a single candidate pool. The extends resolver is extended to support append-only capability merging with cycle detection. Composition security is enforced through minimum-trust propagation, mandatory URI prefixes, and data flow classification.

**Tech Stack:**
- Same as M1/M2: FastAPI, asyncpg, pgvector, Pydantic, MCP SDK
- No new infrastructure dependencies

**Spec references:**
- [M3 Composition Security Spec](../../specs/2026-03-23-m3-composition-spec.md)
- [Loom Design Spec](../../specs/2026-03-21-loom-design.md)
- [Implementation Milestones](../../specs/implementation-milestones.md)

**Note on naming:** This plan follows existing codebase conventions: repos use raw asyncpg SQL, services are stateless with injected dependencies, models are Pydantic, factories are wired through `ServiceContainer`.

---

## Chunk 1: Infrastructure — Database Schema & Domain Models

---

### Task 1: DB Tables + Alembic Migration

**Files:**
- Modify: `src/loom/db/tables.py`
- Create: Alembic migration

- [ ] **Step 1: Add capability tables to tables.py**

Add `capabilities` and `capability_versions` table definitions following the schema in [M3 Spec §3](../../specs/2026-03-23-m3-composition-spec.md). The `capabilities` table mirrors `skills` in structure but replaces `content` with `steps` (JSONB), and adds `preconditions` (JSONB), `expected_outcome` (TEXT), and `data_flow` (JSONB). Include all the same metadata columns: tags, scope, version, author_id, trust_tier, cost_profile, cost_drivers, estimated_duration, dependencies, eval_spec, extends, embedding, eval_status, composite_score. Add indexes for category, trust_tier, scope, tags (GIN).

The `capability_versions` table follows `skill_versions` pattern with `capability_id` FK (CASCADE), version, steps, preconditions, expected_outcome, data_flow, dependencies, cost_profile, cost_drivers, estimated_duration, eval_spec, extends, author_id, changelog. Unique constraint on `(capability_id, version)`.

- [ ] **Step 2: Generate and run migration**

Run: `uv run alembic revision --autogenerate -m "m3 capability tables"`
Run: `uv run alembic upgrade head`
Expected: Migration creates `capabilities` and `capability_versions` tables.

- [ ] **Step 3: Verify schema**

Run: `docker exec loom-db-1 psql -U loom -c "\dt"`
Expected: `capabilities` and `capability_versions` both present.

Run: `docker exec loom-db-1 psql -U loom -c "\d capabilities"`
Expected: All columns present with correct types.

- [ ] **Step 4: Commit**

```bash
git add src/loom/db/tables.py alembic/
git commit -m "feat(m3): database tables for capabilities and capability versions"
```

---

### Task 2: Domain Models

**Files:**
- Create: `src/loom/models/capability.py`
- Modify: `src/loom/models/resolution.py`

- [ ] **Step 1: Create capability models**

Create `src/loom/models/capability.py` with these Pydantic models:

- `CapabilityStep` — skill_ref (str, must contain `://`), role (str), inputs (dict[str, str]), outputs (dict[str, str]), required (bool, default True), data_classification (str, default "internal")
- `DataFlowEdge` — from_step (str), to_step (str), classification (str)
- `CapabilityCreate` — slug, name, description, category_slug, version, tags, scope, trust_tier, steps (list[CapabilityStep]), preconditions, expected_outcome, data_flow (list[DataFlowEdge]), dependencies, cost_profile, cost_drivers, estimated_duration, eval_spec, extends
- `Capability` — full model with id, category_id, author_id, embedding, eval_status, composite_score, created_at, updated_at. Include `to_summary()` method.
- `CapabilitySummary` — id, slug, name, description, category_id, tags, version, trust_tier, cost_profile, estimated_duration, step_count
- `CapabilityUpdate` — steps, description, version (required), tags, preconditions, expected_outcome, data_flow, dependencies, cost_profile, cost_drivers, estimated_duration, eval_spec, extends, changelog
- `CapabilityVersion` — id, capability_id, version, steps, preconditions, expected_outcome, data_flow, dependencies, cost_profile, cost_drivers, estimated_duration, eval_spec, extends, author_id, changelog, created_at

Add a field validator on `CapabilityStep.skill_ref` to enforce the `://` prefix requirement.

- [ ] **Step 2: Add resolved models to resolution.py**

Add to `src/loom/models/resolution.py`:

- `ResolvedStep` — index (int), skill_ref (str), role (str), skill (Skill), inputs, outputs, required, data_classification, dependencies_satisfied (list[str]), dependencies_missing (list[str])
- `ResolvedCapability` — capability (Capability), resolved_steps (list[ResolvedStep]), effective_trust_tier (TrustTier), trust_warnings (list[str]), all_dependencies_satisfied (list[str]), all_dependencies_missing (list[str]), data_flow (list[DataFlowEdge]), alternatives (list[Alternative]), selection_rationale (list[str])
- `ResolvedResult` — type (Literal["skill", "capability"]), skill (ResolvedSkill | None), capability (ResolvedCapability | None)

- [ ] **Step 3: Verify imports**

Run: `uv run python -c "from loom.models.capability import Capability, CapabilityCreate, CapabilityStep, DataFlowEdge; from loom.models.resolution import ResolvedStep, ResolvedCapability, ResolvedResult; print('Models OK')"`
Expected: `Models OK`

- [ ] **Step 4: Commit**

```bash
git add src/loom/models/capability.py src/loom/models/resolution.py
git commit -m "feat(m3): domain models for capabilities and resolved plans"
```

---

### Task 3: CapabilityRepo

**Files:**
- Create: `src/loom/db/repositories/capability_repo.py`
- Create: `tests/unit/test_capability_repo.py`

- [ ] **Step 1: Write tests for CapabilityRepo**

Test cases (use real DB via `db_conn` fixture, same pattern as `test_skill_repo.py`):
- Create capability and verify all fields returned
- Get by slug returns correct capability
- Get by slug returns None for missing
- Update capability creates version record
- List capabilities with trust_tier filter
- Vector search returns capabilities ranked by similarity
- Version history retrieval

- [ ] **Step 2: Implement CapabilityRepo**

Follow existing `SkillRepo` patterns:
- Raw asyncpg SQL with parameterised queries (`$1`, `$2`, etc.)
- `_row_to_capability()` and `_row_to_summary()` converter functions
- Methods: `create`, `get_by_slug`, `get_by_id`, `update`, `list_all`, `vector_search_summary`, `get_versions`, `get_version`
- JSONB fields (`steps`, `preconditions`, `data_flow`, `dependencies`, `eval_spec`) serialised via `json.dumps` on write and `json.loads` on read
- Embedding stored as pgvector on create/update
- `step_count` computed from `steps` JSONB length for summary

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/unit/test_capability_repo.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/loom/db/repositories/capability_repo.py tests/unit/test_capability_repo.py
git commit -m "feat(m3): capability repository with CRUD, versioning, and vector search"
```

---

## Chunk 2: Capability Registry

---

### Task 4: CapabilityRegistryService

**Files:**
- Create: `src/loom/services/capability_registry.py`
- Create: `tests/unit/test_capability_registry.py`

- [ ] **Step 1: Write tests**

Test cases:
- Create capability with valid steps succeeds
- Create capability with step missing `://` fails with ValueError
- Get capability by slug
- Update capability creates version
- List capabilities
- Create with non-existent category fails

- [ ] **Step 2: Implement CapabilityRegistryService**

Constructor takes `capability_repo`, `category_repo`, `embedder`. Methods:
- `create_capability(data: CapabilityCreate, author_id: UUID) -> Capability` — validate category exists, validate steps, generate embedding, persist
- `get_capability(slug: str, version: str | None = None) -> Capability | None`
- `update_capability(slug: str, data: CapabilityUpdate, author_id: UUID) -> Capability`
- `list_capabilities(trust_tier: TrustTier | None = None) -> list[CapabilitySummary]`

- [ ] **Step 3: Run tests and commit**

Run: `uv run pytest tests/unit/test_capability_registry.py -v`
Expected: PASS.

```bash
git add src/loom/services/capability_registry.py tests/unit/test_capability_registry.py
git commit -m "feat(m3): capability registry service with CRUD and validation"
```

---

### Task 5: Step Reference Validation

**Files:**
- Modify: `src/loom/services/capability_registry.py`
- Create: `tests/unit/test_step_validation.py`

- [ ] **Step 1: Write tests**

Test cases:
- Step with `loom://slug` passes URI validation
- Step with `corp://slug` passes URI validation
- Step with bare `slug` (no prefix) fails validation
- Step with empty `skill_ref` fails
- Step referencing non-existent skill produces warning (not hard failure — skill may exist at resolution time)
- Step referencing skill below trust floor produces warning
- All referenced skills' trust tiers collected for minimum computation

- [ ] **Step 2: Implement step validation**

Add `_validate_steps(steps: list[CapabilityStep]) -> list[str]` method to `CapabilityRegistryService`:
- Check each step's `skill_ref` contains `://`
- Parse source and slug from URI
- Return list of warnings (non-existent skills, trust floor violations)
- Raise `ValueError` for structural issues (missing prefix, empty slug)

- [ ] **Step 3: Run tests and commit**

Run: `uv run pytest tests/unit/test_step_validation.py -v`
Expected: PASS.

```bash
git add src/loom/services/capability_registry.py tests/unit/test_step_validation.py
git commit -m "feat(m3): step reference validation with mandatory URI prefixes"
```

---

### Task 6: Dependency Aggregation

**Files:**
- Modify: `src/loom/services/capability_registry.py`
- Add tests to: `tests/unit/test_capability_registry.py`

- [ ] **Step 1: Write tests**

Test cases:
- Two steps with same MCP server dependency → aggregated to one entry
- Two steps with different dependencies → both present
- Per-step dependency satisfaction check with available_tools
- `required: false` step's dependencies don't block capability

- [ ] **Step 2: Implement dependency aggregation**

Add `aggregate_dependencies(steps: list[CapabilityStep], skill_deps: list[DependencyDeclaration]) -> DependencyDeclaration` method:
- Union of all steps' MCP server dependencies (deduplicated by URI)
- Union of all steps' API dependencies (deduplicated by name)
- Trust requirements: highest data_classification across steps, network_access = any step needs it

- [ ] **Step 3: Run tests and commit**

Run: `uv run pytest tests/unit/test_capability_registry.py -v`
Expected: PASS.

```bash
git add src/loom/services/capability_registry.py tests/unit/test_capability_registry.py
git commit -m "feat(m3): dependency aggregation across capability steps"
```

---

### Task 7: Data Flow Validation

**Files:**
- Modify: `src/loom/services/capability_registry.py`
- Create: `tests/unit/test_data_flow_validation.py`

- [ ] **Step 1: Write tests**

Test cases:
- Valid data flow: step 0 output consumed by step 2 input → passes
- Invalid data flow: references non-existent step slug → fails
- Forward-only data flow: step 2 output consumed by step 0 → fails (backward reference)
- Self-referencing data flow → fails
- Data flow edge classification must be one of "internal", "external", "confidential"

- [ ] **Step 2: Implement data flow validation**

Add `_validate_data_flow(steps: list[CapabilityStep], data_flow: list[DataFlowEdge]) -> list[str]` method:
- Build slug-to-index map from steps
- Validate `from_step` and `to_step` reference existing step slugs
- Validate `from_step` index < `to_step` index (forward-only)
- Validate classification values
- Return list of errors

- [ ] **Step 3: Run tests and commit**

Run: `uv run pytest tests/unit/test_data_flow_validation.py -v`
Expected: PASS.

```bash
git add src/loom/services/capability_registry.py tests/unit/test_data_flow_validation.py
git commit -m "feat(m3): data flow validation for capability step graphs"
```

---

## Chunk 3: Resolution

---

### Task 8: CapabilityDiscoveryService

**Files:**
- Create: `src/loom/services/capability_discovery.py`
- Create: `tests/unit/test_capability_discovery.py`

- [ ] **Step 1: Write tests**

Test cases:
- Resolve returns ResolvedCapability with embedded skill content per step
- Resolve with trust floor filters capabilities by effective tier (min across steps)
- Resolve with cost budget filters
- Search returns CapabilitySummary list
- No match returns ResolutionError

- [ ] **Step 2: Implement CapabilityDiscoveryService**

Constructor takes `capability_repo`, `skill_repo`, `embedder`, `embed_cache`. Methods:

- `resolve(task_description, context?) -> ResolvedCapability | ResolutionError`
  1. Embed query
  2. Vector-search capabilities
  3. Apply trust floor and cost budget filters
  4. For best match: resolve each step's skill via `skill_repo.get_by_slug(parsed_slug)`
  5. Compute effective_trust_tier = min across all step skills
  6. Check effective tier against trust floor
  7. Aggregate dependencies, compute per-step satisfied/missing
  8. Build ResolvedCapability with all ResolvedSteps

- `search(query, category_id?, trust_tier?, cost_budget?) -> list[CapabilitySummary]`

- [ ] **Step 3: Run tests and commit**

Run: `uv run pytest tests/unit/test_capability_discovery.py -v`
Expected: PASS.

```bash
git add src/loom/services/capability_discovery.py tests/unit/test_capability_discovery.py
git commit -m "feat(m3): capability discovery service with full plan resolution"
```

---

### Task 9: Full Plan Resolution

**Files:**
- Modify: `src/loom/services/capability_discovery.py`
- Add tests to: `tests/unit/test_capability_discovery.py`

- [ ] **Step 1: Write tests**

Test cases:
- Each resolved step contains complete skill content (not just metadata)
- `required: false` step with unmet deps marked as skippable
- `required: true` step with unmet deps → resolution still succeeds but deps reported
- Trust warnings generated when experimental skills present
- Data flow classification carried through to resolved plan
- External data flow produces safety warning in selection_rationale

- [ ] **Step 2: Enhance resolve() with full plan details**

In `resolve()`, after resolving each step's skill:
- Populate `ResolvedStep.dependencies_satisfied` and `dependencies_missing` from context's `available_tools`
- Set `trust_warnings` listing any step with `experimental` skill
- Add data flow warnings to `selection_rationale`
- For external data flow edges, add: "Step N (slug) consumes external data from step M (slug); treat inputs as untrusted."

- [ ] **Step 3: Run tests and commit**

Run: `uv run pytest tests/unit/test_capability_discovery.py -v`
Expected: PASS.

```bash
git add src/loom/services/capability_discovery.py tests/unit/test_capability_discovery.py
git commit -m "feat(m3): full plan resolution with trust warnings and data flow classification"
```

---

### Task 10: Unified resolve() — Skills + Capabilities

**Files:**
- Modify: `src/loom/services/discovery.py`
- Create: `src/loom/services/unified_resolver.py`
- Create: `tests/unit/test_unified_resolver.py`

- [ ] **Step 1: Write tests**

Test cases:
- Resolve returns `ResolvedResult` with `type="skill"` when a skill matches best
- Resolve returns `ResolvedResult` with `type="capability"` when a capability matches best
- Type filter `skill` excludes capabilities from search
- Type filter `capability` excludes skills from search
- Type filter `any` (default) includes both

- [ ] **Step 2: Implement UnifiedResolver**

Constructor takes `discovery_service` (skills) and `capability_discovery_service` (capabilities). Method:

- `resolve(task_description, context?, type_filter?) -> ResolvedResult | ResolutionError`
  1. If type_filter is "skill" or "any": resolve via DiscoveryService
  2. If type_filter is "capability" or "any": resolve via CapabilityDiscoveryService
  3. If both return results: compare match scores, pick the best
  4. Wrap in `ResolvedResult` with appropriate `type` field
  5. If neither returns results: return `ResolutionError`

- `search(query, type_filter?, ...) -> list[SkillSummary | CapabilitySummary]`

- [ ] **Step 3: Run tests and commit**

Run: `uv run pytest tests/unit/test_unified_resolver.py -v`
Expected: PASS.

```bash
git add src/loom/services/unified_resolver.py tests/unit/test_unified_resolver.py
git commit -m "feat(m3): unified resolver returning skills or capabilities with type discriminator"
```

---

## Chunk 4: Extends & Composition Security

---

### Task 11: Capability Extends Support in ExtendsResolver

**Files:**
- Modify: `src/loom/extends/resolver.py`
- Create: `tests/unit/test_capability_extends.py`

- [ ] **Step 1: Write tests**

Test cases:
- Capability B extends capability A: result has A's steps followed by B's steps
- Step indices adjusted correctly after merge
- A's step fields preserved exactly (skill_ref, role, inputs, outputs)
- B's data flow edges referencing both inherited and new steps are valid
- Preconditions merged (A's + B's)
- Expected outcome uses B's if provided, else A's

- [ ] **Step 2: Implement capability extends in ExtendsResolver**

Add `merge_capability_layers(layers: list[dict]) -> ResolvedChain` method:
- First layer's steps are the base
- Each subsequent layer's steps are appended
- Validate no step replacement (see Task 14)
- Preconditions are merged (concatenated)
- Data flow edges are merged (base + extension)
- Expected outcome: last layer's value if non-empty, else base

- [ ] **Step 3: Run tests and commit**

Run: `uv run pytest tests/unit/test_capability_extends.py -v`
Expected: PASS.

```bash
git add src/loom/extends/resolver.py tests/unit/test_capability_extends.py
git commit -m "feat(m3): capability extends support with append-only merge"
```

---

### Task 12: Minimum-Trust-Across-Chain Rule

**Files:**
- Modify: `src/loom/services/capability_discovery.py`
- Add tests to: `tests/unit/test_capability_discovery.py`

- [ ] **Step 1: Write tests**

Test cases:
- Capability with all verified steps → effective_trust_tier = verified
- Capability with one experimental step → effective_trust_tier = experimental
- Extends chain: verified base + experimental overlay → effective_trust_tier = experimental
- Trust warning lists the specific step/layer that caused the reduction
- Resolution with trust_floor = community rejects capability containing experimental step

- [ ] **Step 2: Implement minimum trust computation**

In `resolve()`:
- Collect trust tiers from: capability's own tier, all step skills' tiers, all extends chain layers' tiers
- `effective_trust_tier = min(all_tiers, key=lambda t: t.rank)`
- Generate `trust_warnings` for each element below the maximum tier
- Check effective tier against context trust floor

- [ ] **Step 3: Run tests and commit**

Run: `uv run pytest tests/unit/test_capability_discovery.py -v`
Expected: PASS.

```bash
git add src/loom/services/capability_discovery.py tests/unit/test_capability_discovery.py
git commit -m "feat(m3): minimum trust propagation across composition chains"
```

---

### Task 13: Cycle Detection

**Files:**
- Modify: `src/loom/extends/resolver.py`
- Add tests to: `tests/unit/test_capability_extends.py`

- [ ] **Step 1: Write tests**

Test cases:
- A extends B extends C (no cycle) → resolves successfully
- A extends B extends A → raises ValueError with cycle description
- A extends B extends C extends A → raises ValueError listing full chain
- Chain depth = max_extends_depth → succeeds
- Chain depth = max_extends_depth + 1 → raises ValueError

- [ ] **Step 2: Implement cycle detection**

Add `_resolve_extends_chain(uri: str, visited: set[str], depth: int) -> list[dict]` method:
- Before resolving each URI, check if it's in `visited`
- If yes, raise `ValueError(f"Circular extends chain detected: {' -> '.join(visited)} -> {uri}")`
- Add current URI to `visited` before recursing
- Check `depth <= max_extends_depth`, raise if exceeded

- [ ] **Step 3: Run tests and commit**

Run: `uv run pytest tests/unit/test_capability_extends.py -v`
Expected: PASS.

```bash
git add src/loom/extends/resolver.py tests/unit/test_capability_extends.py
git commit -m "feat(m3): cycle detection and depth limiting for extends chains"
```

---

### Task 14: Append-Only Merge Enforcement

**Files:**
- Modify: `src/loom/extends/resolver.py`
- Add tests to: `tests/unit/test_capability_extends.py`

- [ ] **Step 1: Write tests**

Test cases:
- Extending capability adds 2 new steps → merge succeeds, result has base steps + 2 new
- Extending capability defines step with same skill_ref as base step → rejected with error
- Extending capability defines step with same role as base step → rejected with error
- Base steps are in original order in merged result
- Extension steps follow base steps in merged result

- [ ] **Step 2: Implement append-only enforcement**

In `merge_capability_layers()`:
- After computing base steps from first layer, for each subsequent layer's steps:
  - Check that no step's `skill_ref` matches any base step's `skill_ref`
  - Check that no step's `role` matches any base step's `role`
  - If match found: raise `ValueError("Capability extends cannot replace existing steps. Create a new version instead. Conflicting step: {role}")`
- Append validated extension steps after base steps

- [ ] **Step 3: Run tests and commit**

Run: `uv run pytest tests/unit/test_capability_extends.py -v`
Expected: PASS.

```bash
git add src/loom/extends/resolver.py tests/unit/test_capability_extends.py
git commit -m "feat(m3): append-only merge enforcement prevents step substitution"
```

---

### Task 15: Cross-Source URI Validation

**Files:**
- Modify: `src/loom/services/capability_discovery.py`
- Add tests to: `tests/unit/test_capability_discovery.py`

- [ ] **Step 1: Write tests**

Test cases:
- Step with `loom://slug` resolves from skill_repo (public registry)
- Step with `corp://slug` on public Loom → resolves to "not available" placeholder
- Step with `loom://slug` never accidentally resolves from corp source
- Step with no `://` prefix → rejected at validation (already enforced in Task 5)

- [ ] **Step 2: Implement source-strict resolution**

In `resolve()`, when resolving each step's skill:
- Parse source from `skill_ref` via `ExtendsResolver.parse_extends_uri()`
- If source is `loom`: resolve from `skill_repo`
- If source is `corp`: in public Loom context, return structured placeholder `{"error": "corp_not_available", "message": "Corporate skill 'slug' requires a corporate Loom instance"}`
- Never cross-source resolve

- [ ] **Step 3: Run tests and commit**

Run: `uv run pytest tests/unit/test_capability_discovery.py -v`
Expected: PASS.

```bash
git add src/loom/services/capability_discovery.py tests/unit/test_capability_discovery.py
git commit -m "feat(m3): strict cross-source URI validation prevents dependency confusion"
```

---

## Chunk 5: API & MCP

---

### Task 16: API Routes

**Files:**
- Create: `src/loom/api/routes/capabilities.py`
- Modify: `src/loom/api/app.py`
- Modify: `src/loom/api/deps.py`
- Create: `tests/unit/test_capability_routes.py`

- [ ] **Step 1: Add dependency injection**

Add to `src/loom/api/deps.py`:
- `get_capability_repo` — following existing `get_skill_repo` pattern
- `get_capability_registry_service` — following existing `get_registry_service` pattern
- `get_capability_discovery_service` — following existing `get_discovery_service` pattern

- [ ] **Step 2: Create capability routes**

Create `src/loom/api/routes/capabilities.py` following `skills.py` patterns:

- `POST /api/v1/capabilities` — create capability (validates steps, generates embedding)
- `GET /api/v1/capabilities` — list with optional trust_tier filter
- `GET /api/v1/capabilities/search` — semantic search with query, trust_tier, cost_budget filters
- `GET /api/v1/capabilities/{slug}` — get by slug with optional version
- `PUT /api/v1/capabilities/{slug}` — update (version bump)
- `POST /api/v1/capabilities/resolve` — resolve capability from task description

Request/response models follow the same patterns as skill routes.

- [ ] **Step 3: Update unified resolve endpoint**

Modify `POST /api/v1/skills/resolve` to accept optional `type` query parameter (`skill`, `capability`, `any`, default `any`). When `type=any`, use `UnifiedResolver` to search both. Response model becomes `ResolvedResult`.

- [ ] **Step 4: Register routes in app.py**

Add `capabilities.router` to the FastAPI app.

- [ ] **Step 5: Write route tests**

Test: create capability, list, get by slug, update, resolve. Follow patterns from existing skill route tests.

- [ ] **Step 6: Run tests and commit**

Run: `uv run pytest tests/unit/test_capability_routes.py -v`
Expected: PASS.

```bash
git add src/loom/api/routes/capabilities.py src/loom/api/app.py src/loom/api/deps.py tests/unit/test_capability_routes.py
git commit -m "feat(m3): API routes for capability CRUD and resolution"
```

---

### Task 17: MCP Tools

**Files:**
- Modify: `src/loom/mcp/server.py`

- [ ] **Step 1: Add resolve_capability tool**

```python
@mcp.tool()
async def resolve_capability(task_description: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve the best capability (multi-step execution plan) for a task."""
    # Similar to resolve() but uses CapabilityDiscoveryService
```

- [ ] **Step 2: Add get_capability tool**

```python
@mcp.tool()
async def get_capability(slug: str, version: str | None = None) -> dict[str, Any]:
    """Retrieve a capability by slug and optional version."""
```

- [ ] **Step 3: Update resolve() tool**

Update the existing `resolve()` tool to use `UnifiedResolver` and return `ResolvedResult` with type discriminator. Add optional `type` parameter (default: `"any"`).

- [ ] **Step 4: Update search() tool**

Add `type` parameter to `search()` tool (default: `"any"`). When `type="capability"` or `type="any"`, include capabilities in results.

- [ ] **Step 5: Commit**

```bash
git add src/loom/mcp/server.py
git commit -m "feat(m3): MCP tools for capability resolution and retrieval"
```

---

### Task 18: Service Container Wiring

**Files:**
- Modify: `src/loom/services/container.py`

- [ ] **Step 1: Update ServiceContainer**

Add to the frozen dataclass:
- `capability_repo_factory: Callable[[asyncpg.Connection], CapabilityRepo]`
- `capability_registry_factory: Callable[[CapabilityRepo, CategoryRepo], CapabilityRegistryService]`
- `capability_discovery_factory: Callable[[CapabilityRepo, SkillRepo], CapabilityDiscoveryService]`
- `unified_resolver_factory: Callable[[SkillRepo, CapabilityRepo], UnifiedResolver]`

- [ ] **Step 2: Wire factories in create_container()**

Add factory functions:
```python
def _capability_repo(conn): return CapabilityRepo(conn)
def _capability_registry(cap_repo, cat_repo): return CapabilityRegistryService(cap_repo, cat_repo, embedder)
def _capability_discovery(cap_repo, skill_repo): return CapabilityDiscoveryService(cap_repo, skill_repo, embedder, embed_cache)
def _unified_resolver(skill_repo, cap_repo): return UnifiedResolver(...)
```

- [ ] **Step 3: Verify imports**

Run: `uv run python -c "from loom.services.container import ServiceContainer; print('Container OK')"`
Expected: `Container OK`

- [ ] **Step 4: Commit**

```bash
git add src/loom/services/container.py
git commit -m "feat(m3): wire capability services into service container"
```

---

## Chunk 6: Seed Capabilities + Integration Tests

---

### Task 19: Seed Capabilities

**Files:**
- Create: `seeds/capabilities/comprehensive-code-review.yaml`
- Create: `seeds/capabilities/release-documentation.yaml`
- Create: `seeds/capabilities/accessibility-security-review.yaml`
- Modify: `scripts/seed.py` (if it handles capability seeding)

- [ ] **Step 1: Create seed capability files**

Create three YAML files following the capability format defined in the design spec. Each must:
- Reference existing seed skills via `loom://` URI prefix
- Define steps with role, inputs, outputs
- Declare data flow edges with classification
- Include preconditions and expected_outcome
- Include eval_spec with at least 2 scenarios

See [M3 Spec §9](../../specs/2026-03-23-m3-composition-spec.md) for the full definitions.

- [ ] **Step 2: Update seed script**

If `scripts/seed.py` handles loading seed data, add capability loading logic. Follow the existing pattern for skill loading.

- [ ] **Step 3: Verify seed loading**

Run: `uv run python scripts/seed.py` (or equivalent)
Expected: 3 capabilities loaded without errors.

- [ ] **Step 4: Commit**

```bash
git add seeds/capabilities/ scripts/seed.py
git commit -m "feat(m3): 3 seed capabilities composing existing seed skills"
```

---

### Task 20: Adversarial Test Suite for Composition Attacks

**Files:**
- Create: `tests/adversarial/test_composition_attacks.py`

- [ ] **Step 1: Write adversarial tests**

Test cases covering all 6 threats from [M3 Spec §6](../../specs/2026-03-23-m3-composition-spec.md):

**Trust laundering (Threats 1 & 4):**
- Create capability with experimental + verified skills → effective_trust_tier = experimental
- Create extends chain: verified base + experimental overlay → effective tier = experimental
- Resolve with trust_floor=community → rejected when capability contains experimental step

**Dependency confusion (Threat 2):**
- Create step with `skill_ref="web-search"` (no prefix) → rejected at creation
- Create step with `loom://web-search` → resolves only from public registry, never corp

**Data flow injection (Threat 3):**
- Create capability with external data flow edge → resolved plan includes warning
- Verify warning text references specific steps and classification

**Step substitution (Threat 5):**
- Extend capability and attempt to replace a step's skill_ref → rejected
- Extend capability and attempt to redefine a step's role → rejected
- Extend capability with only new steps → succeeds

**Circular extends (Threat 6):**
- A extends B extends A → cycle error
- A extends B extends C extends A → cycle error with full chain
- Chain depth exceeding limit → depth error

- [ ] **Step 2: Run adversarial tests**

Run: `uv run pytest tests/adversarial/test_composition_attacks.py -v`
Expected: All PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/adversarial/test_composition_attacks.py
git commit -m "test(m3): adversarial test suite for composition security attacks"
```

---

### Task 21: Integration Tests + E2E Demo

**Files:**
- Create: `tests/integration/test_capability_integration.py`

- [ ] **Step 1: Write integration tests**

Test cases:
- **CRUD round-trip:** Create capability → get by slug → update → verify version history
- **Full plan resolution:** Create 3 skills, create capability referencing them, resolve → each step has full skill content embedded
- **Unified resolve:** Seed both skills and capabilities, resolve a task → verify type discriminator correct
- **Extends chain:** Create base capability, create extending capability, resolve → verify merged steps
- **Dependency aggregation:** Capability with steps requiring different MCP servers → aggregated deps correct
- **API round-trip:** POST capability via API, GET via API, resolve via API

- [ ] **Step 2: Run integration tests**

Run: `uv run pytest tests/integration/test_capability_integration.py -v`
Expected: PASS.

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest tests/ -v --tb=short`
Run: `uv run ruff check src/loom/ tests/`
Run: `uv run mypy src/loom/`
Expected: All clean.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_capability_integration.py
git commit -m "test(m3): integration tests and E2E capability resolution demo"
```

---

## Final Verification

- [ ] **Step 1: Verify all new services importable**

Run: `uv run python -c "from loom.models.capability import Capability, CapabilityCreate, CapabilityStep; from loom.services.capability_registry import CapabilityRegistryService; from loom.services.capability_discovery import CapabilityDiscoveryService; from loom.services.unified_resolver import UnifiedResolver; from loom.models.resolution import ResolvedCapability, ResolvedResult; print('All M3 services importable')"`
Expected: `All M3 services importable`

- [ ] **Step 2: Verify API starts with new routes**

Run: `uv run python -m loom.api &`
Run: `curl -s localhost:8000/openapi.json | python3 -c "import sys,json; paths=json.load(sys.stdin)['paths']; [print(p) for p in paths if 'capabilit' in p]"`
Expected: Lists all capability routes.

Kill the server.

- [ ] **Step 3: Run full test suite one final time**

Run: `uv run pytest tests/ -v`
Run: `uv run ruff check src/loom/ tests/`
Run: `uv run mypy src/loom/`
Expected: All clean.

---

## New Files Summary

| File | Purpose |
|------|---------|
| `src/loom/models/capability.py` | Domain models for capabilities, steps, data flow |
| `src/loom/db/repositories/capability_repo.py` | Persistence for capabilities and versions |
| `src/loom/services/capability_registry.py` | CRUD, validation, dependency aggregation |
| `src/loom/services/capability_discovery.py` | Resolution with full plan embedding |
| `src/loom/services/unified_resolver.py` | Unified skill + capability resolution |
| `src/loom/api/routes/capabilities.py` | Capability API routes |
| `seeds/capabilities/*.yaml` | 3 seed capabilities |
| `tests/unit/test_capability_repo.py` | Repo unit tests |
| `tests/unit/test_capability_registry.py` | Registry service unit tests |
| `tests/unit/test_step_validation.py` | Step reference validation tests |
| `tests/unit/test_data_flow_validation.py` | Data flow validation tests |
| `tests/unit/test_capability_discovery.py` | Discovery/resolution unit tests |
| `tests/unit/test_capability_extends.py` | Extends merge and cycle detection tests |
| `tests/unit/test_unified_resolver.py` | Unified resolver tests |
| `tests/unit/test_capability_routes.py` | API route tests |
| `tests/adversarial/test_composition_attacks.py` | Adversarial security test suite |
| `tests/integration/test_capability_integration.py` | Integration and E2E tests |

## Modified Files Summary

| File | Changes |
|------|---------|
| `src/loom/db/tables.py` | Add capabilities and capability_versions tables |
| `src/loom/models/resolution.py` | Add ResolvedStep, ResolvedCapability, ResolvedResult |
| `src/loom/extends/resolver.py` | Add capability merge, cycle detection, append-only enforcement |
| `src/loom/services/container.py` | Wire capability services and factories |
| `src/loom/mcp/server.py` | Add resolve_capability, get_capability tools; update resolve/search |
| `src/loom/api/app.py` | Register capability routes |
| `src/loom/api/deps.py` | Add capability dependency injection functions |
| `src/loom/settings.py` | Add CapabilityConfig |
| `scripts/seed.py` | Add capability seed loading |
