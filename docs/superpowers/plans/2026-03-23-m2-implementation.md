# M2: Quality & Trust — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a defence-in-depth evaluation pipeline that scores skills using LLM evaluation with injection resistance, manages trust tier promotion/demotion, handles amendments with comparative evaluation, executes evaluation scenarios in Docker sandboxes, and provides cryptographic signing via ed25519.

**Architecture:** Five-phase pipeline (static analysis → content isolation → isolated LLM evaluation → sandboxed execution → score aggregation) with async job processing via Redis + arq. Each quality dimension (clarity, completeness, safety, correctness) is assessed in an isolated LLM call using the data-only protocol. Docker containers provide sandboxed scenario execution. ed25519 signing via PyNaCl provides provenance.

**Tech Stack:**
- Redis 7 + arq (async job queue)
- aiodocker (async Docker SDK for sandbox management)
- pydantic-ai Agent with structured output (LLM-based assessment)
- PyNaCl (ed25519 signing — already in deps)
- Docker (sandbox containers, `python:3.12-slim` base)

**Sandbox decision:** `python:3.12-slim` base image (~41MB) with ruff pre-installed. `aiodocker` for async container management. Create-per-request pattern (epicbox-style) for guaranteed isolation — no state leakage between runs. Security: `--network=none`, `--read-only`, `--cap-drop=ALL`, `--tmpfs /tmp:rw,noexec,size=64m`, `--memory=256m`, `--cpus=0.5`, `--pids-limit=64`, non-root user, 30s hard timeout.

**Spec references:**
- [M2 Security Spec](../../specs/2026-03-23-m2-quality-trust-spec.md)
- [Loom Design Spec](../../specs/2026-03-21-loom-design.md)
- [Implementation Milestones](../../specs/implementation-milestones.md)
- [Project Setup Design](../../specs/2026-03-21-project-setup-design.md)

**Note on naming:** This plan uses "evaluation" and "assessment" to describe the quality scoring pipeline. The services and modules use "eval" as shorthand (e.g., `EvalPipelineService`, `eval_jobs` table) consistent with the existing codebase conventions established in M1.

---

## Chunk 1: Infrastructure — Redis, Dependencies, Database Schema

---

### Task 1: Add M2 Dependencies

**Files:**
- Modify: `pyproject.toml`
- Modify: `docker-compose.yml`
- Modify: `src/loom/settings.py`

- [ ] **Step 1: Add Redis to Docker Compose**

Add a `redis` service to `docker-compose.yml`:

```yaml
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
```

- [ ] **Step 2: Add Python dependencies**

Add to `pyproject.toml` dependencies:

```toml
    "arq>=0.26",
    "redis[hiredis]>=5.0",
    "aiodocker>=0.23",
```

- [ ] **Step 3: Install and verify**

Run: `uv sync`
Expected: All dependencies resolve and install.

Run: `docker compose up -d`
Expected: Both `db` and `redis` containers healthy.

- [ ] **Step 4: Add Redis and pipeline settings**

Add to `src/loom/settings.py`:

```python
class RedisConfig(BaseModel):
    url: str = "redis://localhost:6379"

class PipelineConfig(BaseModel):
    """Configuration for the quality assessment pipeline."""
    pass_threshold: float = 0.50
    promotion_threshold: float = 0.70
    safety_floor: float = 0.60
    runs_per_dimension: int = 3
    low_confidence_spread: float = 0.25
    sandbox_timeout_seconds: int = 30
    sandbox_memory_mb: int = 256
    sandbox_image: str = "loom-eval-sandbox:latest"
    max_content_length: int = 50_000
    max_steps: int = 50
    max_dependencies: int = 15
```

Add `redis: RedisConfig` and `pipeline: PipelineConfig` to `LoomSettings`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock docker-compose.yml src/loom/settings.py
git commit -m "feat(m2): add Redis, arq, aiodocker deps and pipeline config"
```

---

### Task 2: M2 Database Tables and Migration

**Files:**
- Modify: `src/loom/db/tables.py`
- Create: Alembic migration

- [ ] **Step 1: Add M2 tables to tables.py**

Add `eval_jobs`, `eval_dimension_runs`, `trust_audit_log`, and `signing_keys` table definitions following the schemas defined in [M2 Security Spec §8](../../specs/2026-03-23-m2-quality-trust-spec.md). Add required imports (`Boolean`, `Float`, `Integer`, `LargeBinary`). Add `latest_eval_job_id`, `composite_score`, `eval_status`, `signature_key_fingerprint` columns to the `skills` table (use `use_alter=True` on the FK to break the circular reference).

- [ ] **Step 2: Generate and run migration**

Run: `uv run alembic revision --autogenerate -m "m2 eval tables"`
Run: `uv run alembic upgrade head`
Expected: Migration creates all 4 new tables and adds 4 new columns to `skills`.

- [ ] **Step 3: Verify schema**

Run: `docker exec loom-db-1 psql -U loom -c "\dt"`
Expected: `eval_jobs`, `eval_dimension_runs`, `trust_audit_log`, `signing_keys` all present.

- [ ] **Step 4: Commit**

```bash
git add src/loom/db/tables.py alembic/
git commit -m "feat(m2): database tables for eval jobs, dimension runs, trust audit, signing keys"
```

---

### Task 3: M2 Domain Models

**Files:**
- Create: `src/loom/models/eval.py`
- Create: `src/loom/models/signing.py`
- Modify: `src/loom/models/common.py`

- [ ] **Step 1: Add enums to common.py**

Add `EvalStatus` (pending/running/completed/failed), `TriggerType` (submission/amendment/scheduled/usage_signal), `EvalDimension` (clarity/completeness/safety/correctness) as `StrEnum` classes.

- [ ] **Step 2: Create eval models**

Create `src/loom/models/eval.py` with these Pydantic models:
- `InjectionIndicator` — line, pattern, matched_text
- `StructuralReport` — passed, errors, warnings, injection_indicators, complexity_score, content_hash
- `CodeBlock` — language, code, line_start
- `IsolatedFragments` — content_hash, metadata, step_outline, full_body, code_blocks, eval_scenarios, injection_indicators
- `DimensionResult` — dimension, score (0-1), evidence, injection_detected, injection_detail, confidence
- `SandboxResult` — passed, scenarios_run, scenarios_passed, errors, lint_warnings, duration_ms
- `EvalResult` — passed, composite_score, dimension_scores, dimension_confidence, overall_confidence, injection_flagged, sandbox_passed, content_hash, evaluator_version
- `ComparisonResult` — verdict, original_scores, amendment_scores, dimension_deltas, auto_merge, reason
- `EvalJob` — database record model (id, skill_id, status, scores, etc.)
- `EvalDimensionRun` — database record model (id, eval_job_id, dimension, run_index, score, etc.)
- `TrustAuditEntry` — database record model (id, skill_id, previous_tier, new_tier, reason, etc.)

- [ ] **Step 3: Create signing models**

Create `src/loom/models/signing.py` with:
- `SigningKey` — id, user_id, fingerprint, label, revoked_at
- `SigningKeyCreate` — public_key_base64, label
- `SignatureStatus` — signed, valid, fingerprint, signer_handle, revoked

- [ ] **Step 4: Commit**

```bash
git add src/loom/models/
git commit -m "feat(m2): domain models for eval pipeline, trust audit, and signing"
```

---

### Task 4: Repository Layer

**Files:**
- Create: `src/loom/db/repositories/eval_repo.py`
- Create: `tests/unit/test_eval_repo.py`
- Modify: `tests/conftest.py` (add `test_skill_id` and `test_category_id` fixtures)

- [ ] **Step 1: Write tests for EvalRepo**

Test: create/get eval job, update status, create dimension runs, get latest for skill, create trust audit entry. Use real DB via `db_conn` fixture (same pattern as existing repo tests).

- [ ] **Step 2: Implement EvalRepo**

Follow existing `SkillRepo` patterns:
- Raw asyncpg SQL with parameterised queries (`$1`, `$2`, etc.)
- `_row_to_*` converter functions
- Dynamic `UPDATE SET` builder for `update_eval_job`
- Methods: `create_eval_job`, `get_eval_job`, `update_eval_job`, `get_latest_eval_for_skill`, `create_dimension_run`, `get_runs_for_job`, `create_trust_audit_entry`, `get_trust_history`

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/unit/test_eval_repo.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/loom/db/repositories/eval_repo.py tests/unit/test_eval_repo.py tests/conftest.py
git commit -m "feat(m2): eval repository with job, dimension run, and trust audit persistence"
```

---

## Chunk 2: Static Analysis (Phase 1)

---

### Task 5: StaticAnalyser Service

**Files:**
- Create: `src/loom/services/static_analyser.py`
- Create: `tests/unit/test_static_analyser.py`

- [ ] **Step 1: Write tests (TDD)**

Test cases:
- Valid skill passes
- Empty/short content fails
- No eval scenarios fails
- Injection patterns detected (but NOT rejected — `injection_indicators` populated)
- Excessive content length rejected
- Complexity score computed (0-1 range)
- Content hash is SHA-256 (`sha256:` prefix + 64 hex chars)
- Empty MCP URI fails

- [ ] **Step 2: Implement StaticAnalyser**

Pure functions, no external dependencies. Includes:
- Content length bounds (`MIN_CONTENT_LENGTH=10`, `MAX_CONTENT_LENGTH=50_000`)
- Eval spec validation (≥1 scenario, ≤20)
- Dependency count limits (≤15)
- Step count from markdown headings (≤50)
- Nesting depth (warn >4, reject >6)
- Injection pattern scanning — regex catalogue:

```python
INJECTION_PATTERNS = [
    ("ignore_instructions", r"ignore\s+(previous|above|all)\s+(instructions?|prompts?|rules?)"),
    ("role_assignment", r"(system|assistant|user)\s*:"),
    ("special_tokens", r"<\|im_(start|end)\|>"),
    ("role_tags", r"<\|(system|user|assistant)\|>"),
    ("identity_override", r"you\s+are\s+(now|a|an)\s+"),
    ("new_instructions", r"(new|updated|real)\s+instructions?\s*:"),
    ("forget_instructions", r"forget\s+(everything|all|previous)"),
    ("important_override", r"IMPORTANT:\s*(ignore|override|disregard)"),
    ("prompt_tags", r"</?(system|instruction|prompt)>"),
]
```

- Content normalisation (NFC, zero-width char removal, RTL override removal) before hashing
- Complexity scoring (weighted: tokens 40%, deps 30%, steps 30%)
- Returns `StructuralReport` with content_hash binding

- [ ] **Step 3: Run tests and lint**

Run: `uv run pytest tests/unit/test_static_analyser.py -v`
Run: `uv run ruff check src/loom/services/static_analyser.py`
Run: `uv run mypy src/loom/services/static_analyser.py`
Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add src/loom/services/static_analyser.py tests/unit/test_static_analyser.py
git commit -m "feat(m2): static analyser — Phase 1 with injection pattern scanning"
```

---

## Chunk 3: Content Isolation (Phase 2)

---

### Task 6: ContentIsolator Service

**Files:**
- Create: `src/loom/services/content_isolator.py`
- Create: `tests/unit/test_content_isolator.py`

- [ ] **Step 1: Write tests**

Test: content_hash carried forward, step_outline contains only headings (not body), full_body is present (not raw markdown in prompt — it's JSON-encoded when used), code blocks extracted with language tags, injection indicators carried forward, metadata contains frontmatter fields, Unicode normalisation strips zero-width chars.

- [ ] **Step 2: Implement ContentIsolator**

Fragment extraction:
- `metadata` — name, description, tags, cost_profile, estimated_duration, scope, dependency_count
- `step_outline` — heading lines only (regex: `^#{1,6}\s+`)
- `full_body` — complete content after Unicode normalisation
- `code_blocks` — fenced code blocks with language and line_start
- `eval_scenarios` — from skill.eval_spec.scenarios
- `injection_indicators` — passed through from StructuralReport

Key: all fragments stored as strings/dicts. The LLMEvaluator JSON-encodes them when building prompts (Phase 3). ContentIsolator just provides the separation.

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/unit/test_content_isolator.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/loom/services/content_isolator.py tests/unit/test_content_isolator.py
git commit -m "feat(m2): content isolator — Phase 2 fragment extraction"
```

---

## Chunk 4: LLM Assessment (Phase 3)

---

### Task 7: Prompt Registry

**Files:**
- Create: `src/loom/services/prompt_registry.py`
- Create: `tests/unit/test_prompt_registry.py`

- [ ] **Step 1: Implement PromptRegistry**

Versioned prompt templates for each dimension. Key security invariant: **no skill data is interpolated into system prompts**. System prompts only define the assessment task and output format. Each variant includes:
- "UNTRUSTED" warning about data field
- Explicit instruction not to follow directives in the data
- `injection_detected` field requirement
- Dimension-specific assessment criteria

Start with 2 variants for clarity, 1 each for completeness/safety/correctness. More added via prompt rotation (§7.1 of spec).

- [ ] **Step 2: Write tests**

Test: all dimensions have variants, get by name works, all system prompts contain "UNTRUSTED" warning, all mention injection detection, no `{` interpolation markers in any prompt.

- [ ] **Step 3: Commit**

```bash
git add src/loom/services/prompt_registry.py tests/unit/test_prompt_registry.py
git commit -m "feat(m2): prompt registry with versioned templates per dimension"
```

---

### Task 8: LLMEvaluator Service

**Files:**
- Create: `src/loom/services/llm_evaluator.py`
- Create: `tests/unit/test_llm_evaluator.py`

- [ ] **Step 1: Write tests with mock LLM**

Test cases:
- Single dimension assessment produces valid `DimensionResult`
- `evaluate_all` produces results for all 4 dimensions with N runs each
- User message is JSON-encoded (data-only protocol) — verify `skill_fragment` key present
- No metadata leakage (no author, trust_tier, score in user message)
- Safety dimension receives `injection_indicators` from Phase 1
- Retry on malformed LLM response (up to 2 retries)
- Parse failure returns score=0.0, confidence=0.0

- [ ] **Step 2: Implement LLMEvaluator**

Constructor takes `agent_factory: Callable[[str], Agent]` (creates a pydantic-ai Agent per system prompt), `prompt_registry`, and `model_id`.

Fragment-to-dimension mapping (dimension isolation):
| Dimension | Fragment Seen |
|-----------|--------------|
| clarity | `step_outline` only |
| completeness | `metadata` + `step_outline` |
| safety | `full_body` + `injection_indicators` |
| correctness | `eval_scenarios` + `code_blocks` |

`_build_user_message()` creates JSON:
```json
{"skill_fragment": "<fragment>", "dimension": "clarity"}
```
Safety additionally includes `"injection_indicators": [...]`.

Response parsing validates score ∈ [0,1], evidence non-empty, confidence ∈ [0,1].

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/unit/test_llm_evaluator.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/loom/services/llm_evaluator.py tests/unit/test_llm_evaluator.py
git commit -m "feat(m2): LLM evaluator — Phase 3 with data-only protocol and dimension isolation"
```

---

## Chunk 5: Score Aggregation (Phase 5) + Pipeline Orchestration

---

### Task 9: ScoreAggregator Service

**Files:**
- Create: `src/loom/services/score_aggregator.py`
- Create: `tests/unit/test_score_aggregator.py`

- [ ] **Step 1: Write tests**

Test cases:
- Structural failure overrides all (returns passed=False, reason="structural_failure")
- Passing skill computes correct composite
- **Median not mean** — single outlier score ignored
- Injection flagged if any run on any dimension detects injection
- Confidence computed from score spread (wide spread → low confidence)
- Sandbox failure blocks pass
- Weighted composite: clarity 0.25, completeness 0.30, safety 0.25, correctness 0.20

- [ ] **Step 2: Implement ScoreAggregator**

Pure function, no external deps. Uses `statistics.median`. Confidence = `1.0 - (max - min)` per dimension. Overall confidence = min across dimensions. Pass requires composite ≥ `PASS_THRESHOLD` (0.50) and sandbox not failed.

- [ ] **Step 3: Run tests and commit**

```bash
git add src/loom/services/score_aggregator.py tests/unit/test_score_aggregator.py
git commit -m "feat(m2): score aggregator — Phase 5 with median consensus and confidence"
```

---

### Task 10: EvalPipelineService Orchestrator

**Files:**
- Create: `src/loom/services/eval_pipeline.py`
- Create: `tests/unit/test_eval_pipeline.py`

- [ ] **Step 1: Write tests with mocked phases**

Test cases:
- Full pipeline passes (all phases called in order, result returned)
- Structural failure short-circuits (LLM evaluator NOT called)
- Phases called in correct order (static → isolator → LLM → aggregator)
- Sandbox runner optional (None until M2iv)

- [ ] **Step 2: Implement EvalPipelineService**

Constructor takes all 5 phase services. `evaluate(skill)` method:
1. Convert Skill → SkillCreate for static analysis
2. Phase 1: StaticAnalyser.analyse() — short-circuit on failure
3. Phase 2: ContentIsolator.isolate()
4. Phase 3: LLMEvaluator.evaluate_all()
5. Phase 4: SandboxRunner.execute() (if not None)
6. Phase 5: ScoreAggregator.aggregate()

- [ ] **Step 3: Run tests and commit**

```bash
git add src/loom/services/eval_pipeline.py tests/unit/test_eval_pipeline.py
git commit -m "feat(m2): pipeline orchestrator — coordinates all assessment phases"
```

---

### Task 11: Arq Worker, Container Wiring, and API Routes

**Files:**
- Create: `src/loom/worker.py`
- Modify: `src/loom/services/container.py`
- Modify: `src/loom/api/deps.py`
- Create: `src/loom/api/routes/eval.py`
- Modify: `src/loom/api/app.py`

- [ ] **Step 1: Update ServiceContainer**

Add `prompt_registry`, `eval_repo_factory`, and `eval_pipeline_factory` to the frozen dataclass. In `create_container()`, instantiate `StaticAnalyser`, `ContentIsolator`, `ScoreAggregator`, `PromptRegistry`, `LLMEvaluator` (with agent_factory using pydantic-ai Agent + `create_llm_model`), and wire the pipeline factory.

- [ ] **Step 2: Add eval dependency injection**

Add `get_eval_repo` to `deps.py` following the existing pattern.

- [ ] **Step 3: Create API routes**

Create `src/loom/api/routes/eval.py`:
- `GET /api/v1/skills/{skill_id}/eval` → latest assessment result
- `GET /api/v1/eval/jobs/{job_id}` → job status and results
- `GET /api/v1/skills/{skill_id}/trust` → trust tier change history

Register in `app.py`.

- [ ] **Step 4: Create arq worker**

Create `src/loom/worker.py` with:
- `run_eval_job(ctx, skill_id, trigger)` — fetches skill, creates job record, runs pipeline, persists result, updates skill's eval_status and composite_score
- `startup(ctx)` — creates DB pool, LLM model, pipeline services
- `shutdown(ctx)` — closes DB pool
- `WorkerSettings` class for arq configuration

Worker started with: `uv run arq loom.worker.WorkerSettings`

- [ ] **Step 5: Run full test suite and lint**

Run: `uv run pytest tests/ -v --tb=short`
Run: `uv run ruff check src/loom/`
Run: `uv run mypy src/loom/`
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add src/loom/services/container.py src/loom/api/ src/loom/worker.py
git commit -m "feat(m2): arq worker, API routes, and service container wiring"
```

---

## Chunk 6: Sandboxed Execution (Phase 4)

---

### Task 12: Sandbox Docker Image

**Files:**
- Create: `sandbox/Dockerfile`
- Create: `sandbox/run_eval.py`

- [ ] **Step 1: Create sandbox runner script**

`sandbox/run_eval.py` — runs INSIDE the container:
- Reads JSON task from stdin (code_blocks + eval_scenarios)
- Checks Python code blocks for syntax errors (`ast.parse`)
- Validates eval scenarios have required fields and non-empty success_criteria
- Runs `ruff check` on Python code blocks (if ruff available)
- Writes JSON result to stdout: `{passed, scenarios_run, scenarios_passed, errors, lint_warnings}`
- Wraps everything in try/except to ensure JSON output on any failure

- [ ] **Step 2: Create Dockerfile**

```dockerfile
FROM python:3.12-slim AS base
RUN pip install --no-cache-dir ruff==0.8.6
RUN useradd --create-home --shell /bin/false sandbox
USER sandbox
WORKDIR /home/sandbox
COPY --chown=sandbox:sandbox run_eval.py /home/sandbox/run_eval.py
ENTRYPOINT ["python3", "/home/sandbox/run_eval.py"]
```

- [ ] **Step 3: Build and test**

Run: `docker build -t loom-eval-sandbox:latest sandbox/`
Expected: Image builds (~150MB).

Run: `echo '{"code_blocks":[],"eval_scenarios":[{"description":"test","input_context":"ctx","success_criteria":"pass"}]}' | docker run --rm -i --network=none --read-only --tmpfs /tmp:rw,noexec,size=64m --memory=256m --cpus=0.5 loom-eval-sandbox:latest`
Expected: `{"passed": true, "scenarios_run": 1, "scenarios_passed": 1, ...}`

- [ ] **Step 4: Commit**

```bash
git add sandbox/
git commit -m "feat(m2): sandbox Docker image for scenario execution"
```

---

### Task 13: SandboxRunner Service

**Files:**
- Create: `src/loom/services/sandbox_runner.py`
- Create: `tests/unit/test_sandbox_runner.py`

- [ ] **Step 1: Write tests with mock aiodocker**

Test cases:
- Successful execution returns SandboxResult with correct fields
- Container created with security flags (NetworkDisabled, CapDrop, ReadonlyRootfs, Memory, PidsLimit)
- Container deleted after execution (cleanup)
- Timeout produces failure result with "timeout" in errors

- [ ] **Step 2: Implement SandboxRunner**

Uses `aiodocker.Docker` client. Container config:
```python
{
    "Image": self._image,
    "OpenStdin": True, "StdinOnce": True,
    "NetworkDisabled": True,
    "HostConfig": {
        "Memory": self._memory * 1024 * 1024,
        "NanoCpus": 500_000_000,
        "ReadonlyRootfs": True,
        "Tmpfs": {"/tmp": "rw,noexec,size=64m"},
        "CapDrop": ["ALL"],
        "PidsLimit": 64,
        "SecurityOpt": ["no-new-privileges"],
    },
}
```

Task input JSON-serialised and sent to container stdin. Stdout parsed as JSON result. `asyncio.wait_for` with timeout. Container always deleted in `finally` block.

- [ ] **Step 3: Run tests and commit**

```bash
git add src/loom/services/sandbox_runner.py tests/unit/test_sandbox_runner.py
git commit -m "feat(m2): sandbox runner — Phase 4 Docker-based execution with aiodocker"
```

---

## Chunk 7: Trust Tiers & Signing

---

### Task 14: TrustService

**Files:**
- Create: `src/loom/services/trust_service.py`
- Create: `tests/unit/test_trust_service.py`

- [ ] **Step 1: Write tests**

Test cases:
- All criteria met → should_promote=True, target_tier=community
- Low score → no promotion (reason mentions "score")
- Unsigned → no promotion (reason mentions "sign")
- Injection flagged → no promotion
- Already community → no auto-promotion (reason mentions "manual")
- Insufficient usage → no promotion
- Low success rate → no promotion

- [ ] **Step 2: Implement TrustService**

`check_promotion(skill_id, current_tier, is_signed, usage_count, success_rate)` → `PromotionDecision`:

Criteria for `experimental` → `community`:
1. Composite score ≥ 0.70 (`promotion_threshold`)
2. Safety dimension ≥ 0.60 (`safety_floor`)
3. No injection flags
4. Signed (ed25519)
5. ≥10 usage reports (`min_usage_count`)
6. ≥80% success rate (`min_success_rate`)

`community` → `verified` always returns should_promote=False with "requires manual promotion by steward" message.

- [ ] **Step 3: Run tests and commit**

```bash
git add src/loom/services/trust_service.py tests/unit/test_trust_service.py
git commit -m "feat(m2): trust service — auto-promotion logic with criteria checks"
```

---

### Task 15: SigningService

**Files:**
- Create: `src/loom/services/signing_service.py`
- Create: `tests/unit/test_signing_service.py`

- [ ] **Step 1: Write tests**

Test cases:
- Generate keypair produces valid hex strings (64 chars each for seed+vk and vk)
- Sign and verify round-trip succeeds
- Verify fails on tampered content
- Verify fails with wrong public key
- Fingerprint is SHA-256 of public key (`sha256:` prefix + 64 hex)

- [ ] **Step 2: Implement SigningService**

Uses PyNaCl (`nacl.signing.SigningKey`, `nacl.signing.VerifyKey`):
- `generate_keypair()` → (private_key_hex, public_key_hex)
- `sign(content, version, dependencies_json, eval_spec_json, private_key_hex)` → signature_hex
- `verify(content, version, dependencies_json, eval_spec_json, signature_hex, public_key_hex)` → bool
- `fingerprint(public_key_hex)` → `sha256:...`

Canonical message: `SHA-256(content + "\n" + version + "\n" + deps_json + "\n" + eval_spec_json)`

- [ ] **Step 3: Run tests and commit**

```bash
git add src/loom/services/signing_service.py tests/unit/test_signing_service.py
git commit -m "feat(m2): signing service — ed25519 via PyNaCl"
```

---

## Chunk 8: Integration Tests & Final Verification

---

### Task 16: Integration Tests

**Files:**
- Create: `tests/integration/test_eval_integration.py`

- [ ] **Step 1: Write integration tests**

Test cases:
- Full pipeline with mock LLM: StaticAnalyser + ContentIsolator + LLMEvaluator (mock) + ScoreAggregator → result.passed, composite > 0.5, content_hash starts with sha256:
- Pipeline detects injection: skill with "Ignore previous instructions" → injection_flagged=True
- Repo round-trip: create eval job, add 12 dimension runs (4 dims × 3 runs), update to completed, verify retrieval

- [ ] **Step 2: Run integration tests**

Run: `uv run pytest tests/integration/test_eval_integration.py -v`
Expected: PASS.

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest tests/ -v --tb=short`
Run: `uv run ruff check src/loom/ tests/`
Run: `uv run mypy src/loom/`
Expected: All clean.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/
git commit -m "test(m2): integration tests for pipeline, injection detection, and repo round-trip"
```

---

### Task 17: Final Verification

- [ ] **Step 1: Verify all services importable**

Run: `uv run python -c "from loom.services.static_analyser import StaticAnalyser; from loom.services.content_isolator import ContentIsolator; from loom.services.llm_evaluator import LLMEvaluator; from loom.services.score_aggregator import ScoreAggregator; from loom.services.eval_pipeline import EvalPipelineService; from loom.services.trust_service import TrustService; from loom.services.signing_service import SigningService; from loom.services.sandbox_runner import SandboxRunner; print('All M2 services importable')"`
Expected: `All M2 services importable`

- [ ] **Step 2: Verify API starts with new routes**

Run: `uv run python -m loom.api &`
Run: `curl -s localhost:8000/health`
Expected: `{"status":"ok"}`

Run: `curl -s localhost:8000/openapi.json | python3 -c "import sys,json; paths=json.load(sys.stdin)['paths']; [print(p) for p in paths if 'eval' in p or 'trust' in p]"`
Expected: Lists `/api/v1/skills/{skill_id}/eval`, `/api/v1/eval/jobs/{job_id}`, `/api/v1/skills/{skill_id}/trust`.

Kill the server.

- [ ] **Step 3: Verify sandbox image**

Run: `echo '{"code_blocks":[{"language":"python","code":"def foo():\n    return 42","line_start":1}],"eval_scenarios":[{"description":"test","input_context":"repo","success_criteria":"functions return correct values"}]}' | docker run --rm -i --network=none --read-only --tmpfs /tmp:rw,noexec,size=64m --memory=256m --cpus=0.5 loom-eval-sandbox:latest`
Expected: `{"passed": true, "scenarios_run": 1, "scenarios_passed": 1, ...}`

- [ ] **Step 4: Run full test suite one final time**

Run: `uv run pytest tests/ -v`
Run: `uv run ruff check src/loom/ tests/`
Run: `uv run mypy src/loom/`
Expected: All clean.

---

## New Files Summary

| File | Purpose |
|------|---------|
| `src/loom/models/eval.py` | Domain models for pipeline results, jobs, runs |
| `src/loom/models/signing.py` | Signing key and signature models |
| `src/loom/services/static_analyser.py` | Phase 1: deterministic validation |
| `src/loom/services/content_isolator.py` | Phase 2: fragment extraction |
| `src/loom/services/prompt_registry.py` | Versioned prompt templates |
| `src/loom/services/llm_evaluator.py` | Phase 3: isolated LLM assessment |
| `src/loom/services/sandbox_runner.py` | Phase 4: Docker sandbox execution |
| `src/loom/services/score_aggregator.py` | Phase 5: consensus and confidence |
| `src/loom/services/eval_pipeline.py` | Pipeline orchestrator |
| `src/loom/services/trust_service.py` | Trust tier promotion/demotion |
| `src/loom/services/signing_service.py` | ed25519 signing via PyNaCl |
| `src/loom/db/repositories/eval_repo.py` | Persistence for jobs, runs, audit |
| `src/loom/api/routes/eval.py` | Assessment and trust API routes |
| `src/loom/worker.py` | Arq background worker |
| `sandbox/Dockerfile` | Sandbox container image |
| `sandbox/run_eval.py` | Container entry point |

## Modified Files Summary

| File | Changes |
|------|---------|
| `pyproject.toml` | Add arq, redis, aiodocker deps |
| `docker-compose.yml` | Add Redis service |
| `src/loom/settings.py` | Add RedisConfig, PipelineConfig |
| `src/loom/db/tables.py` | Add 4 tables, 4 columns to skills |
| `src/loom/models/common.py` | Add EvalStatus, TriggerType, EvalDimension enums |
| `src/loom/services/container.py` | Wire M2 services and factories |
| `src/loom/api/deps.py` | Add get_eval_repo |
| `src/loom/api/app.py` | Register eval routes |
| `tests/conftest.py` | Add test_skill_id, test_category_id fixtures |
