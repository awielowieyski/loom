# External Services & Pricing Evidence Spec

**Date**: 2026-03-28
**Status**: Draft
**Companion to**: [Canonicalization, Provenance & Publication Pipeline Spec](2026-03-28-canonicalization-provenance-pipeline-spec.md) · [ADR 0001: Loom Publishes Normalized Loom Releases](../adr/0001-normalized-package-manager.md) · [M4 Living Registry Spec](2026-03-24-m4-living-registry-spec.md)

---

## 1. Overview

### 1.1 Thesis

Many public skills are not self-contained capabilities. They are instructions for using an external hosted API, SaaS product, MCP server, or third-party dataset.

For those skills, the external dependency surface is part of the truth of the skill:

- whether an account is required
- whether an API key is required
- which environment variables must be set
- whether the service is usage-priced, subscription-priced, or credit-based
- what a representative operation costs

Loom should extract and publish that information as first-class, evidence-backed metadata rather than collapsing it into a coarse `cost_profile` or a free-text description.

### 1.2 Problem Statement

The current model has:

- `cost_profile` and `cost_drivers`
- `dependencies.apis[]`
- `source_uri`

Those fields are useful summaries, but they are too weak to answer product-critical questions like:

- "Does this skill require a paid external service?"
- "What service is it actually wrapping?"
- "Which secret or environment variable do I need?"
- "What does a typical call cost?"
- "Is this price a source claim or Loom-verified evidence?"

### 1.3 Example

A skill like `aisa-youtube-skill` should not just canonicalize to "low cost" and "uses an API."

It should canonicalize to something closer to:

- external service: `aisa.one`
- service type: hosted API
- required auth: API key
- required environment variable: `AISA_API_KEY`
- setup steps: create account, add credits, configure key
- priced operation: YouTube search
- indicative price: approximately `$0.002` per request
- evidence source: pricing section in upstream docs
- confidence/freshness: extracted from source on a specific date

---

## 2. Design Principles

1. **External service facts are canonical metadata.**
   They are not optional annotations for "advanced" skills; they are part of what the skill is.

2. **Pricing is evidence, not just a normalized enum.**
   Loom should preserve the raw pricing text and the evidence source alongside any normalized cost fields.

3. **Skill-level summaries should be derived from structured service facts.**
   `cost_profile`, `cost_drivers`, and dependency declarations remain useful, but they should be projections of richer truth.

4. **Source-derived and Loom-observed facts must be distinguishable.**
   A price extracted from a README is not the same as a price verified from a live pricing page.

5. **Absence of evidence is not free.**
   If the skill references sign-up, credits, billing, or API keys but Loom cannot extract a reliable price, the skill should still be marked as externally dependent and potentially paid.

---

## 3. Product Goals

This subsystem should enable Loom to:

1. explain clearly when a skill requires a third-party product or account
2. show the operational requirements to run the skill
3. differentiate low-friction and high-friction variants in search and comparison
4. rank and filter skills by credible cost evidence rather than vague self-description
5. preserve pricing/service provenance over time as those services change

---

## 4. Proposed Data Model

### 4.1 New Concepts

Separate four concerns:

| Concern | Meaning |
|--------|---------|
| `external_service` | A third-party system the skill depends on |
| `service_dependency` | How a specific skill revision depends on that service |
| `pricing_fact` | A normalized price or billing fact with evidence |
| `setup_requirement` | Concrete auth/account/env setup needed to use the skill |

### 4.2 New Tables

#### `external_services`

Canonical registry of third-party services.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `service_key` | text | Stable normalized identity, e.g. `aisa.one` |
| `display_name` | text | Human label |
| `vendor_name` | text | Organization/provider |
| `service_type` | text | `api`, `saas`, `mcp`, `oauth_app`, `dataset`, `sdk`, `other` |
| `homepage_url` | text | Canonical homepage/docs root |
| `docs_url` | text | Primary documentation URL |
| `pricing_url` | text | Primary pricing page if known |
| `default_auth_methods` | JSONB | e.g. `["api_key"]` |
| `default_env_vars` | JSONB | e.g. `["AISA_API_KEY"]` |
| `metadata` | JSONB | Rate-limit notes, branding aliases, other service-level facts |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

Unique key: `service_key`

#### `skill_service_dependencies`

Revision-scoped dependency from a published or canonical skill revision to a service.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `skill_version_id` | UUID | FK -> `skill_versions.id` |
| `service_id` | UUID | FK -> `external_services.id` |
| `required` | bool | Whether the skill is meaningfully unusable without it |
| `dependency_role` | text | `primary_runtime`, `optional_enrichment`, `authoring`, `distribution`, `observability` |
| `operations` | JSONB | Normalized operations, e.g. `["youtube_search"]` |
| `setup_requirements` | JSONB | Account, credits, API key, env vars, OAuth, etc. |
| `pricing_summary` | JSONB | Current best-known compact summary for UI/read performance |
| `evidence_summary` | JSONB | Why Loom believes this dependency exists |
| `created_at` | timestamptz | |

Unique key: `(skill_version_id, service_id, dependency_role)`

#### `pricing_facts`

Immutable evidence-backed pricing observations.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `subject_kind` | text | `service` or `skill_version` |
| `subject_id` | UUID | FK-ish; points to service or skill version |
| `fact_type` | text | `unit_cost`, `credit_pack`, `subscription`, `free_tier`, `rate_limit`, `billing_model` |
| `pricing_model` | text | `free`, `usage_based`, `subscription`, `credits`, `hybrid`, `unknown` |
| `operation_name` | text | e.g. `youtube_search` |
| `unit_name` | text | `request`, `search`, `credit`, `month`, etc. |
| `unit_cost_usd` | numeric | Nullable if not directly normalizable |
| `currency` | text | Source currency if known |
| `price_text_raw` | text | Raw source wording |
| `price_structured` | JSONB | Structured non-scalar details |
| `source_kind` | text | `artifact`, `loom_observed`, `manual_override`, `crawl` |
| `source_artifact_id` | UUID | Nullable FK -> `source_artifacts.id` |
| `source_uri` | text | URL or page where fact came from |
| `evidence_snippet` | text | Short supporting excerpt or selector metadata |
| `confidence` | numeric | 0..1 |
| `observed_at` | timestamptz | When Loom observed/extracted it |
| `superseded_by` | UUID | Self-reference for stale prices |
| `created_at` | timestamptz | |

Index: `(subject_kind, subject_id, observed_at desc)`

#### `service_setup_requirements`

Normalized setup requirements that may also be reused by the UI.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `skill_version_id` | UUID | FK -> `skill_versions.id` |
| `service_id` | UUID | FK -> `external_services.id` |
| `requirement_type` | text | `account`, `billing`, `api_key`, `oauth`, `env_var`, `region`, `network_access` |
| `key` | text | e.g. `AISA_API_KEY` |
| `value_hint` | text | e.g. `api_key` |
| `required` | bool | |
| `instructions` | text | Human-readable summary |
| `evidence_summary` | JSONB | Parsed evidence and provenance |
| `created_at` | timestamptz | |

### 4.3 Projection Back to Existing Fields

The existing fields stay, but become derived:

| Existing field | Derived from |
|---------------|--------------|
| `cost_profile` | best-known pricing facts + service dependency friction |
| `cost_drivers` | service dependency roles + pricing model + setup requirements |
| `dependencies.apis` | normalized service dependency projections |
| `estimated_duration` | may factor in setup friction, not just execution runtime |

Examples:

- a skill with required API key + usage-based billing should not be `free`
- a skill with unknown price but required credits should likely become `moderate` or `unknown`-leaning rather than `free`

---

## 5. Canonicalization Pipeline Changes

### 5.1 Stage Placement

This belongs in the **canonicalize** stage, not the eval stage.

Pipeline:

1. ingest raw artifact
2. derive source claims
3. extract external-service and setup signals
4. extract pricing evidence
5. generate canonical metadata
6. derive coarse projections (`cost_profile`, `cost_drivers`, `dependencies`)
7. pass canonical revision into dedup and evaluation

### 5.2 Extraction Passes

#### Pass A: Service Signal Detection

Inputs:

- markdown content
- attached code/manifests
- URLs
- environment variable names
- shell commands

Signals:

- `API_KEY`, `TOKEN`, `SECRET`, `CLIENT_ID`
- `sign up`, `create account`, `add credits`, `billing`, `pricing`
- domain mentions and docs links
- SDK/import/package names

Output:

- candidate external services
- candidate auth methods
- candidate setup requirements
- candidate pricing sections

#### Pass B: Service Canonicalization

Normalize candidate services into stable records:

- `aisa.one`, `docs.aisa.one`, and "AISA" should resolve to one service identity
- preserve aliases in metadata
- identify likely primary docs/pricing URLs

#### Pass C: Pricing Extraction

Look for:

- pricing tables
- phrases like `$0.002`, `per request`, `credits`, `pay-as-you-go`
- "every response includes usage.cost"
- free tier or subscription notes

Output:

- one or more `pricing_facts`
- compact `pricing_summary`
- confidence score
- raw evidence retention

#### Pass D: Runtime Friction Derivation

Derive operational metadata:

- account needed?
- billing needed?
- secret/env var needed?
- internet access needed?
- third-party data processing implied?

This should feed:

- dependency declarations
- trust/safety review inputs
- UI warnings

### 5.3 Canonicalization Heuristics

Heuristic rules for V1:

1. if the artifact references a third-party domain and an API key env var, classify as external service dependency
2. if setup instructions mention credits, billing, or pay-as-you-go, mark pricing model as non-free even if exact price is missing
3. if explicit price text is found, preserve it verbatim in `pricing_facts.price_text_raw`
4. if the price appears approximate, preserve the approximation rather than pretending it is exact
5. if multiple price facts disagree, keep both and route to `review` when confidence is low

---

## 6. Evaluation Implications

External service metadata is not only a discovery concern; it affects trust and evaluation.

### 6.1 Correctness

If a skill claims to solve a task but depends on an external paid API, the canonical record should say so. Hidden dependence is a metadata truthfulness problem.

### 6.2 Safety

External services can imply:

- outbound network access
- data transfer to third parties
- credentials handling
- paid side effects

Those should feed adversarial and safety review.

### 6.3 Usability

The setup burden and pricing burden should inform ranking and comparative selection.

For example, a free local skill and a paid external API wrapper should not be treated as identical alternatives.

---

## 7. Discovery, Resolver, and UI Changes

### 7.1 Discovery / Resolver

Expose structured filters and ranking inputs:

- requires external service: yes/no
- requires paid account: yes/no/unknown
- pricing model
- auth method
- required env vars
- estimated unit cost

Ranking can then distinguish:

- self-contained skills
- external but free skills
- external usage-priced skills
- high-friction enterprise-only skills

### 7.2 Skill Detail Page

Add explicit sections:

#### External Services

- service name
- service type
- dependency role
- homepage/docs link
- required auth
- required environment variables

#### Pricing

- pricing model
- indicative unit cost
- raw source text
- freshness date
- evidence source label: `source-derived`, `Loom-observed`, or `manual`

#### Setup Requirements

- sign-up required
- billing/credits required
- API key/OAuth required
- network access required

### 7.3 Governance Dashboard

Canonicalization review should show:

- detected external services
- unresolved service aliases
- extracted pricing facts
- conflicting price evidence
- reviewer controls to confirm, reject, or override extracted facts

---

## 8. API Changes

### 8.1 Skill Detail Response

Augment skill detail with:

- `external_services`
- `pricing`
- `setup_requirements`
- `requires_paid_service`
- `requires_network`

### 8.2 New Endpoints

Potential endpoints:

- `GET /api/v1/services`
- `GET /api/v1/services/{service_key}`
- `GET /api/v1/skills/{slug}/pricing`
- `POST /api/v1/governance/service-overrides`

V1 can begin by embedding the data on skill detail and governance payloads without exposing all of these separately.

---

## 9. Implementation Plan

### Phase 1: Minimal Schema and Read Model

Goal: represent the truth even before full automation.

1. add `external_services`
2. add `skill_service_dependencies`
3. add `pricing_facts`
4. extend skill detail API response models
5. render external services + pricing cards in the web skill page

Keep extraction manual or script-assisted at first if needed.

### Phase 2: Canonicalization Extraction

Goal: populate this metadata during ingest/vet.

1. add a service/pricing extraction module under canonicalization
2. detect env vars, domains, auth patterns, pricing phrases
3. store extracted dependencies and pricing facts on the candidate revision
4. derive `cost_profile`, `cost_drivers`, and dependency projections from extracted facts

### Phase 3: Governance Workflow

Goal: let stewards review ambiguous or conflicting service/pricing evidence.

1. add governance queue annotations for extracted service/pricing facts
2. support confirm/reject/override actions
3. preserve override provenance distinctly from source-derived facts

### Phase 4: Search / Ranking / Comparison

Goal: make the metadata useful to end users.

1. add search filters for external dependency and pricing model
2. incorporate setup friction and price evidence into ranking
3. show service/pricing differences in comparative cluster review

### Phase 5: Freshness and Revalidation

Goal: detect stale service/pricing data.

1. add scheduled service metadata refresh jobs
2. mark stale pricing facts when source pages change materially
3. route significant pricing drift to review

---

## 10. Open Questions

1. Should service identity be global across skills, or can there be per-scope aliases?
2. Do we want a first-class `unknown` cost profile rather than forcing everything into `free/low/moderate/high`?
3. How aggressively should Loom browse/crawl external pricing pages versus relying on imported source artifacts?
4. Should paid external wrappers be represented separately in dedup/comparison against self-contained skills?
5. How should capability-level pricing aggregate when a workflow combines multiple priced services?

---

## 11. Recommended V1 Decisions

To keep this tractable, I recommend:

1. treat external service extraction as canonicalization work
2. add first-class evidence tables rather than extending `cost_profile` further
3. keep `cost_profile` as a projection for ranking compatibility
4. start with source-artifact extraction before adding live crawling
5. surface "requires paid external service" prominently in UI and resolver ranking

This keeps the first implementation honest, provenance-safe, and incremental.
