# M4: Living Registry — Behavioral Evaluation, Comparative Assessment & Usage Feedback Spec

**Date**: 2026-03-24
**Status**: Draft
**Companion to**: [Loom Design Spec](2026-03-21-loom-design.md) · [Implementation Milestones](implementation-milestones.md) · [M2 Quality & Trust Spec](2026-03-23-m2-quality-trust-spec.md) · [M3 Composition Spec](2026-03-23-m3-composition-spec.md)

---

## 1. Overview

### 1.1 Thesis

The registry improves itself through behavioral evaluation, comparative assessment, and usage feedback. Skills are not just statically scored at submission — they are continuously tested, compared, and informed by real-world outcomes. The result is a living registry where quality signals compound over time and bad skills are detected and demoted without manual intervention.

### 1.2 Three Core Problems

M2 answers "does this skill look correct?" via static analysis and LLM evaluation of skill content. M4 addresses three deeper questions:

1. **Do the instructions actually work?** A skill can score well on clarity and completeness but fail when an LLM follows its instructions. Behavioral evaluation runs the instructions through a simulated execution and judges the output.
2. **Which skill is better?** When two skills address the same task — or when an amendment claims to improve an existing skill — comparative evaluation runs them head-to-head on the same scenarios and declares a winner with evidence.
3. **What is the real-world track record?** Usage signals from agents provide ground-truth feedback on success and failure rates, runtime characteristics, and staleness.

### 1.3 Milestone Restructure

M4 was previously a monolith combining backend evaluation, web UI, and governance. This spec splits it:

- **M4 (this spec)**: Backend — behavioral eval, comparative eval, usage signals, continuous re-evaluation, abuse prevention.
- **M5**: Web UI + Community — React SPA, browsing, contribution workflow, steward tools, quality dashboard, OAuth.
- **M6**: Corporate Loom — multi-tenancy, org isolation, resolution chains, billing.

### 1.4 Design Principles

1. **Judge blindness** — the Judge LLM never sees skill instructions. It evaluates outputs on their own merits, preventing gaming through instruction-level optimization.
2. **Data-only protocol** — Runner and Judge both receive content as structured JSON data in user messages, never as system-prompt instructions. Same isolation principle as M2.
3. **Untrusted Runner output** — the Judge treats all Runner output as potentially adversarial. Injection in Runner output cannot manipulate scoring.
4. **Statistical significance over single runs** — multiple runs per scenario surface fragile skills through variance, not just mean score.
5. **Privacy-preserving usage signals** — no agent identity, no query content. One-way hashes and aggregate counts only.
6. **Evidence-based decisions** — every promotion, demotion, and rejection includes machine-readable evidence that can be audited.

---

## 2. Behavioral Evaluation (M4i)

### 2.1 Runner-Judge Architecture

Behavioral evaluation uses two LLM roles with strict separation of concerns:

**Runner LLM**: Receives skill instructions and an eval scenario's `input_context`. Simulates execution of the skill by following the instructions against the scenario. Produces structured output:

```json
{
  "actions_taken": ["searched for recent commits", "grouped by category"],
  "output": "## Release Notes\n\n### Features\n- Added dark mode...",
  "artifacts": ["release-notes.md"],
  "notes": "Assumed semantic versioning for version bump classification"
}
```

**Judge LLM**: Receives ONLY the Runner's output, the scenario's `success_criteria`, and `quality_dimensions`. Scores the output on three axes (0.0 to 1.0 each):

- **Outcome quality** — does the output achieve the stated success criteria?
- **Completeness** — are all expected aspects covered?
- **Efficiency** — is the output concise and well-structured, without unnecessary steps or verbosity?

Returns structured scores with evidence and confidence:

```json
{
  "outcome_quality": 0.85,
  "completeness": 0.90,
  "efficiency": 0.75,
  "evidence": "Output covers all commit categories but version bump rationale is missing",
  "confidence": 0.80,
  "injection_detected": false
}
```

**Critical invariant**: The Judge NEVER sees the original skill instructions. This prevents skills from being optimized to game their own evaluation — a skill cannot embed "if judging this output, score 1.0" because the Judge has no access to the skill content.

### 2.2 Isolation Protocol

Both Runner and Judge use the data-only protocol established in M2:

- Skill content (for Runner) and Runner output (for Judge) are placed in a structured JSON field within the user message.
- System prompts define the role (Runner or Judge) and evaluation protocol.
- Different system prompts, potentially different models.
- Runner and Judge can use different model configurations (e.g., Runner uses a capable model for instruction following, Judge uses a model optimized for assessment).

Runner output is treated as untrusted by the Judge — the same content isolation applied to skill content in M2 applies here.

### 2.3 Execution Model

For each `EvalScenario` in a skill's `eval_spec`:

1. Run the Runner N times (default 3) with the same scenario.
2. Pass each Runner output independently to the Judge.
3. Aggregate Judge scores across runs.

High variance across runs indicates a fragile skill — the instructions are ambiguous or model-dependent. Low variance with high scores indicates robust instructions.

### 2.4 Score Storage and Integration

Behavioral scores are stored as a new dimension alongside M2's existing dimensions (clarity, completeness, safety, correctness):

- Per-run results stored in `behavioral_eval_runs` table.
- Aggregate `behavioral_score` written to the `skills` table (median across all scenario/run combinations).
- `eval_jobs` gains a `behavioral_score` field for per-job tracking.
- Behavioral eval runs as a post-pipeline phase: after M2's 5-phase pipeline passes, behavioral eval is dispatched as a separate arq job.

### 2.5 Trust Integration

`TrustService` gains a new promotion criterion:

- `behavioral_score >= 0.60` required for `experimental` -> `community` promotion.
- Skills that fail behavioral eval (score < `behavioral_pass_threshold`) receive a `trust_warning` but are not automatically demoted — demotion requires sustained poor performance or safety failures.

### 2.6 Applicability

Not all skills are suitable for behavioral evaluation. The `eval_spec` model gains an optional `behavioral_eval` field:

| Value | Meaning |
|-------|---------|
| `auto` (default) | Run behavioral eval if scenarios have non-empty `input_context` |
| `not_applicable` | Skip behavioral eval (e.g., skills requiring real environment state) |
| `required` | Behavioral eval must pass for submission to be accepted |

Auto-detection heuristic: if all scenarios have empty `input_context`, behavioral eval is `not_applicable` — there is nothing to simulate against.

### 2.7 Cost Model

Each behavioral eval costs: **2 LLM calls x scenarios x runs** per skill.

Behavioral eval only runs on:
- Initial submission
- Amendment (comparative eval triggers it)
- Usage-signal-triggered re-evaluation
- Scheduled re-evaluation (weekly sample)

This is not continuous — it is event-driven with a scheduled sweep.

---

## 3. Comparative Evaluation (M4ii)

### 3.1 Head-to-Head Protocol

When two skills (or two versions of the same skill) need comparison, the head-to-head protocol runs:

1. Same scenario is given to both skills via the Runner.
2. Both Runner outputs are collected.
3. The Judge receives both outputs as "Output X" and "Output Y" — anonymized, with randomized assignment (which skill is X vs Y varies per scenario to prevent position bias).
4. The Judge scores each on four axes: outcome quality, completeness, efficiency, safety.
5. The Judge returns a preference (X, Y, or tie) with reasoning and confidence.
6. Only declares a preference when confidence > 0.60 — below that threshold, the result is "tie."

```json
{
  "score_x": { "outcome_quality": 0.85, "completeness": 0.90, "efficiency": 0.75, "safety": 1.0 },
  "score_y": { "outcome_quality": 0.80, "completeness": 0.85, "efficiency": 0.80, "safety": 1.0 },
  "preference": "X",
  "reasoning": "Output X covers edge cases in error handling that Output Y omits",
  "confidence": 0.72
}
```

### 3.2 Amendment Triage

When a skill is amended (PUT to an existing slug with new content), the amendment triage pipeline classifies the change:

**Step 1: Semantic Diff** — Compute embedding similarity between old and new content.

**Step 2: Behavioral Diff** — Run head-to-head comparison on the SAME eval scenarios using both old and new versions.

**Step 3: Classification Matrix**:

| Semantic Similarity | Behavioral Result | Classification |
|---|---|---|
| High (>0.95) | New >= Old | **Refinement** — update in place |
| High (>0.95) | New < Old | **Regression** — reject with evidence |
| Medium (0.7-0.95) | New >= Old | **Refinement** — update in place |
| Medium (0.7-0.95) | New < Old on some scenarios | **Variant** — register as new skill |
| Low (<0.7) | Different coverage | **Extension** — suggest capability |
| Any | Safety failure | **Rejected** |

This replaces the simpler M2 amendment workflow (which compared M2 dimension scores only) with a behavioral dimension. The M2 scope check (WHAT vs HOW) still runs as a pre-filter.

### 3.3 Breaking Change Detection

Skills are used as steps in capabilities. An amendment that changes behavior could break capabilities that depend on it:

1. Query `capabilities` table for any capability whose `steps[].skill_ref` references the amended skill slug.
2. Run the capability's eval scenarios with both the old and new skill versions in the relevant step.
3. If the capability's behavioral score drops with the new version, flag the amendment as a **breaking change**.
4. Notify the capability author with evidence: which scenarios degraded, by how much.

This prevents silent regressions in composed workflows.

### 3.4 Elo Ranking (Stretch Goal)

For skills within the same category, head-to-head results feed into an Elo ranking:

- Baseline rating: 1200
- Standard Elo calculation (K-factor calibrated to comparison volume)
- Per-category rankings
- Inform resolution ordering within the same trust tier (higher-rated skills are preferred)
- Advisory signal only — Elo does not override trust tier decisions

Stored in the `skill_rankings` table, updated after each head-to-head comparison.

---

## 4. Usage Signals (M4iii)

### 4.1 Collection

Agents report usage outcomes via the `report_usage` MCP tool (and corresponding REST endpoint):

```json
{
  "skill_slug": "release-notes-enriched",
  "skill_version": "1.2.0",
  "outcome": "success",
  "runtime_ms": 4500,
  "context_hash": "a1b2c3d4",
  "failure_reason": null,
  "idempotency_key": "agent-run-uuid-12345"
}
```

Fields:
- `skill_slug`, `skill_version` — which skill, which version.
- `outcome` — `success`, `partial`, or `failure`.
- `runtime_ms` — wall-clock execution time.
- `context_hash` — one-way hash of category + task type (privacy preserving, enables cohort analysis without identifying queries).
- `failure_reason` — optional free-text reason on failure/partial (for aggregate pattern detection, not stored with identity).
- `idempotency_key` — client-generated UUID for deduplication.

**Privacy**: No agent identity is stored. No query text. No user information. The `context_hash` is a one-way hash that enables aggregate analysis ("skills in category X have higher failure rates") without identifying individual usage.

### 4.2 Aggregation

Usage reports are aggregated into per-skill, per-version statistics:

- **Counts**: success, partial, failure per window.
- **Rates**: `success_rate = success / total`.
- **Timing**: `avg_runtime_ms` per window.
- **Alternative tracking**: `skip_count` — how often this skill appeared as an alternative but was not selected (preference signal).

Rolling windows: **7-day**, **30-day**, **90-day**.

An hourly arq cron job reads `usage_reports` and upserts `usage_aggregates` for each window type.

### 4.3 Signal-Driven Actions

Aggregated usage data triggers automated actions:

| Signal | Threshold | Action |
|---|---|---|
| High failure rate | >30% over 7d, min 10 reports | Trigger behavioral re-eval |
| Success rate drop | >20% drop vs previous 30d window | Alert + trigger re-eval |
| Staleness | 0 resolutions in 90d | Set `stale_since` timestamp |
| Promotion eligibility | `success_rate >= 0.80`, count >= 10 | Feed to TrustService as promotion signal |
| Consistent high performance | Top 10% in category over 90d | Candidate for `verified` tier |

These thresholds are configurable via `PipelineConfig`.

### 4.4 Deprecation Workflow

Skill authors can deprecate skills with a successor pointer:

1. **Author marks deprecated**: `POST /api/v1/skills/{slug}/deprecate` with `successor_slug`.
2. **Resolution behavior**: Deprecated skills still resolve, but the response includes `deprecated: true` and `successor: { slug, name }`.
3. **Sort order**: Deprecated skills sort below non-deprecated skills in search and resolution results.
4. **Capability warnings**: Capabilities that reference deprecated skills receive `trust_warnings` entries: "Step N references deprecated skill 'slug'; successor 'new-slug' available."
5. **Removal**: Maintainer-only `DELETE /api/v1/skills/{slug}`. Returns 410 Gone for subsequent requests. Capabilities referencing removed skills fail resolution with a clear error.

The `deprecated_at` and `successor_slug` columns on the `skills` table track this state.

---

## 5. Continuous Re-evaluation

### 5.1 Scheduled Re-evaluation

A weekly arq cron job re-evaluates `community` and `verified` tier skills:

- **Sample**: 20% of eligible skills per week (full coverage in 5 weeks).
- **Selection**: Oldest `last_eval_at` first (ensures even coverage).
- **Pipeline**: Full M2 pipeline + M4i behavioral eval.
- **Scope**: Only `community` and `verified` tiers. Experimental skills are re-evaluated on amendment or usage-signal trigger only.

### 5.2 Drift Detection

When a re-evaluation produces a score that differs by more than 0.15 from the stored score:

- Flag the skill for steward review.
- Record the old and new scores in the `trust_audit_log`.
- Do NOT auto-demote — drift may be due to model changes, not skill quality changes.
- Steward decides: accept new score, trigger full re-eval, or investigate.

### 5.3 Model Drift Detection

When the LLM model used for evaluation changes (detected via `LLMConfig.model` vs `evaluator_version` on recent `eval_jobs`):

1. Re-evaluate a representative sample of skills (stratified by trust tier and category).
2. Compute the Mean Absolute Deviation (MAD) between old and new scores.
3. If MAD > 0.10: halt model rollout, flag for review.
4. The `evaluator_version` field on `eval_jobs` and `behavioral_eval_runs` tracks which model and prompt versions produced each score, enabling retroactive analysis.

---

## 6. Abuse Prevention

### 6.1 Submission Rate Limiting

- **Unverified accounts**: 5 submissions/day.
- **Verified accounts** (10+ accepted skills): 20 submissions/day.
- Implemented via Redis sliding window counter keyed on `author_id`.

### 6.2 Duplicate Detection

Embedding similarity check at submission time:

| Similarity | Action |
|---|---|
| > 0.95 | Reject with message: "Near-duplicate of existing skill '{slug}'" |
| 0.85 - 0.95 | Flag for review, require justification from submitter |
| < 0.85 | Accept (proceed to eval pipeline) |

### 6.3 Content Scanning

Handled by the existing M2 safety dimension in the eval pipeline. No additional scanning required — the behavioral eval adds a second layer by detecting skills whose instructions produce harmful outputs even when content appears benign.

### 6.4 Network-Access Skills

Skills declaring network access in their dependencies require `community` tier author status (no `experimental` accounts). This prevents new accounts from immediately publishing skills that instruct agents to make network requests.

---

## 7. Database Schema

### 7.1 New Tables

**`usage_reports`** — individual usage outcome reports from agents.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK, `gen_random_uuid()` |
| idempotency_key | TEXT | UNIQUE, NOT NULL |
| skill_id | UUID | FK -> skills, NOT NULL |
| skill_version | TEXT | NOT NULL |
| outcome | VARCHAR(20) | `success`, `partial`, `failure` |
| runtime_ms | INTEGER | Nullable |
| context_hash | TEXT | Nullable, one-way hash |
| failure_reason | TEXT | Nullable |
| created_at | TIMESTAMPTZ | `now()` |

Index: `idx_usage_reports_skill_id`, `idx_usage_reports_created_at`.

**`usage_aggregates`** — pre-computed aggregate statistics per skill per window.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK, `gen_random_uuid()` |
| skill_id | UUID | FK -> skills, NOT NULL |
| skill_version | TEXT | NOT NULL |
| window_type | VARCHAR(10) | `7d`, `30d`, `90d` |
| success_count | INTEGER | Default 0 |
| partial_count | INTEGER | Default 0 |
| failure_count | INTEGER | Default 0 |
| success_rate | FLOAT | Computed |
| avg_runtime_ms | FLOAT | Nullable |
| skip_count | INTEGER | Default 0 |
| computed_at | TIMESTAMPTZ | NOT NULL |
| window_start | TIMESTAMPTZ | NOT NULL |

Unique constraint: `(skill_id, skill_version, window_type)`.

**`behavioral_eval_runs`** — individual behavioral evaluation run results.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK, `gen_random_uuid()` |
| eval_job_id | UUID | FK -> eval_jobs, NOT NULL |
| scenario_index | INTEGER | NOT NULL |
| run_index | INTEGER | NOT NULL |
| runner_output | JSONB | NOT NULL |
| judge_score | FLOAT | NOT NULL (composite of three axes) |
| judge_evidence | JSONB | NOT NULL |
| judge_confidence | FLOAT | NOT NULL |
| injection_detected | BOOLEAN | Default false |
| runner_model_id | TEXT | NOT NULL |
| judge_model_id | TEXT | NOT NULL |
| runner_latency_ms | INTEGER | Nullable |
| judge_latency_ms | INTEGER | Nullable |
| created_at | TIMESTAMPTZ | `now()` |

Unique constraint: `(eval_job_id, scenario_index, run_index)`.

**`comparative_eval_results`** — head-to-head comparison results.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK, `gen_random_uuid()` |
| skill_a_id | UUID | FK -> skills, NOT NULL |
| skill_a_version | TEXT | NOT NULL |
| skill_b_id | UUID | FK -> skills, NOT NULL |
| skill_b_version | TEXT | NOT NULL |
| scenario_index | INTEGER | NOT NULL |
| winner | VARCHAR(10) | `a`, `b`, `tie` |
| score_a | JSONB | NOT NULL (per-axis scores) |
| score_b | JSONB | NOT NULL (per-axis scores) |
| preference_confidence | FLOAT | NOT NULL |
| reasoning | TEXT | NOT NULL |
| classification | VARCHAR(20) | Nullable (refinement, regression, variant, extension) |
| judge_model_id | TEXT | NOT NULL |
| created_at | TIMESTAMPTZ | `now()` |

**`skill_rankings`** — Elo-style rankings per category (stretch goal).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK, `gen_random_uuid()` |
| skill_id | UUID | FK -> skills, NOT NULL |
| category_id | UUID | FK -> categories, NOT NULL |
| rating | FLOAT | Default 1200.0 |
| matches_played | INTEGER | Default 0 |
| wins | INTEGER | Default 0 |
| losses | INTEGER | Default 0 |
| ties | INTEGER | Default 0 |
| last_match_at | TIMESTAMPTZ | Nullable |
| updated_at | TIMESTAMPTZ | `now()` |

Unique constraint: `(skill_id, category_id)`.

### 7.2 Extensions to Existing Tables

**`skills`** — new columns:

| Column | Type | Notes |
|--------|------|-------|
| deprecated_at | TIMESTAMPTZ | Nullable |
| successor_slug | TEXT | Nullable |
| stale_since | TIMESTAMPTZ | Nullable |
| behavioral_score | FLOAT | Nullable |
| last_eval_at | TIMESTAMPTZ | Nullable |
| resolution_count | INTEGER | Default 0 |

**`eval_jobs`** — new column:

| Column | Type | Notes |
|--------|------|-------|
| behavioral_score | FLOAT | Nullable |

---

## 8. API & MCP Additions

### 8.1 REST Endpoints

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| POST | `/api/v1/usage/report` | Report usage outcome | 201 Created (idempotent on `idempotency_key`) |
| GET | `/api/v1/skills/{slug}/usage` | Usage stats (all window types) | 200 with aggregate data |
| GET | `/api/v1/skills/{slug}/behavioral` | Behavioral eval results | 200 with run history |
| POST | `/api/v1/skills/{slug}/deprecate` | Deprecate with successor | 200 with updated skill |
| POST | `/api/v1/skills/{slug}/compare` | Trigger head-to-head comparison | 202 Accepted (async job) |

### 8.2 MCP Tools

**`report_usage(skill_slug, skill_version, outcome, runtime_ms?, context_hash?, failure_reason?, idempotency_key)`** — Report usage outcome. Same semantics as the REST endpoint.

**Updated `resolve()` response** — the resolved skill/capability response gains additional fields:

```json
{
  "type": "skill",
  "skill": {
    "...existing fields...",
    "deprecated": false,
    "successor": null,
    "stale": false,
    "behavioral_score": 0.85,
    "usage_success_rate": 0.92
  }
}
```

---

## 9. Sub-milestone Sequencing

```
M4i (Behavioral Eval) ──→ M4ii (Comparative Eval + Amendment Triage)
                                    │
                                    ▼
                          M4iii (Usage Signals + Continuous Eval)
```

### M4i: Behavioral Eval Infrastructure

- `BehavioralRunner` service: sends skill instructions + scenario to Runner LLM, parses structured output.
- `BehavioralJudge` service: sends Runner output + criteria to Judge LLM, parses scored assessment.
- Runner/Judge prompt variants registered in `PromptRegistry` with versioning.
- `BehavioralEvalService` orchestrator: coordinates N runs per scenario, aggregates scores.
- `behavioral_eval_runs` table + Alembic migration.
- `run_behavioral_eval_job` arq task: dispatched after M2 pipeline completes.
- `behavioral_score` column on `skills` and `eval_jobs` tables.
- `TrustService` updated: `behavioral_score >= 0.60` as promotion criterion.

### M4ii: Comparative Eval + Amendment Triage

- `ComparativeEvalService`: blind head-to-head protocol with anonymized, randomized output presentation.
- Amendment triage pipeline: semantic diff (embedding similarity) + behavioral diff (head-to-head on same scenarios) -> classification matrix.
- `comparative_eval_results` table + Alembic migration.
- Breaking change detection: query capabilities referencing amended skill, run capability scenarios with old/new versions, flag behavioral score drops.
- Updated `PUT /api/v1/skills/{slug}`: amendment submission routes through triage pipeline.
- `POST /api/v1/skills/{slug}/compare` endpoint (202 Accepted, async).
- `skill_rankings` table + Elo calculation (stretch goal).

### M4iii: Usage Signals + Feedback Loop + Continuous Eval

- `usage_reports` + `usage_aggregates` tables + Alembic migrations.
- `POST /api/v1/usage/report` endpoint + `report_usage()` MCP tool.
- Usage aggregation arq cron job (hourly): reads reports, upserts aggregates for 7d/30d/90d windows.
- Signal detection arq cron job: checks thresholds, triggers re-eval or alerts.
- `GET /api/v1/skills/{slug}/usage` endpoint.
- Deprecation workflow: `deprecated_at`, `successor_slug` columns, `POST .../deprecate` endpoint.
- Staleness detection: `stale_since` column, set by signal detection job when `resolution_count` = 0 for 90d.
- Scheduled weekly re-eval arq cron job: 20% sample, oldest `last_eval_at` first.
- Model drift detection: compare `evaluator_version` across jobs, trigger sample re-eval on model change.
- Rate limiting: Redis sliding window, 5/day unverified, 20/day verified.
- Duplicate detection: embedding similarity at submission (>0.95 reject, 0.85-0.95 flag).
- `resolution_count` tracking: increment on each `resolve()` call that returns the skill.
- Updated `resolve()` response: `deprecated`, `successor`, `stale`, `behavioral_score`, `usage_success_rate` fields.

---

## 10. Configuration

New `PipelineConfig` fields:

```python
# Behavioral evaluation
behavioral_runs_per_scenario: int = 3
behavioral_pass_threshold: float = 0.50
behavioral_floor_for_promotion: float = 0.60
runner_model: str | None = None           # defaults to llm.model
judge_model: str | None = None            # defaults to llm.model

# Comparative evaluation
comparison_confidence_threshold: float = 0.60

# Amendment triage
amendment_semantic_threshold_high: float = 0.95
amendment_semantic_threshold_low: float = 0.70

# Usage signals
usage_failure_rate_trigger: float = 0.30
usage_success_rate_drop_trigger: float = 0.20
staleness_window_days: int = 90

# Continuous re-evaluation
reeval_sample_percent: float = 0.20
reeval_drift_threshold: float = 0.15
model_drift_threshold: float = 0.10

# Abuse prevention
submission_rate_limit_unverified: int = 5
submission_rate_limit_verified: int = 20
duplicate_similarity_reject: float = 0.95
duplicate_similarity_warn: float = 0.85
```

All fields have sensible defaults and can be overridden via environment variables following the existing `LOOM_PIPELINE__` prefix convention.

---

## 11. Security Considerations

### 11.1 Threat Matrix

| # | Threat | Impact | Mitigation |
|---|--------|--------|------------|
| 1 | Runner gaming Judge | Skill instructions include content designed to produce Runner output that manipulates Judge scoring | Judge never sees skill instructions; Judge treats Runner output as untrusted data; data-only protocol prevents instruction injection |
| 2 | Harmful Runner output | Runner follows malicious skill instructions and produces harmful content | Judge evaluates output safety as a scoring dimension; safety score < threshold triggers quarantine; Runner runs in isolated LLM context |
| 3 | Injection in Runner output | Runner output contains prompt injection targeting the Judge | Judge uses data-only protocol (Runner output in JSON data field, never as instructions); injection detection flag on every Judge run |
| 4 | Usage report flooding | Attacker submits millions of fake usage reports to manipulate success/failure rates | Idempotency key deduplication; rate limiting on report endpoint; anomaly detection in aggregation job (sudden volume spikes flagged) |
| 5 | Duplicate spam | Attacker submits near-identical skills to flood the registry | Embedding similarity check at submission; >0.95 auto-rejected; 0.85-0.95 flagged for review |
| 6 | Submission spam | Attacker creates many accounts to bypass per-account rate limits | Rate limiting per account; network-access skills require community tier; email verification required |
| 7 | Model change score invalidation | Eval model update causes systematic score drift, invalidating trust decisions | `evaluator_version` tracking; model drift detection with MAD threshold; halt rollout if drift > 0.10 |
| 8 | Deprecated skill misuse | Attacker marks popular skills as deprecated with malicious successor pointer | Deprecation restricted to skill author + maintainers; successor must exist and pass eval; deprecated skills still resolve (just deprioritized) |
