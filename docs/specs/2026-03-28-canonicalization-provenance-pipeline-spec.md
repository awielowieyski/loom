# Canonicalization, Provenance & Publication Pipeline Spec

**Date**: 2026-03-28
**Status**: Draft
**Companion to**: [Loom Design Spec](2026-03-21-loom-design.md) · [Implementation Milestones](implementation-milestones.md) · [M2 Quality & Trust Spec](2026-03-23-m2-quality-trust-spec.md) · [M3 Composition Spec](2026-03-23-m3-composition-spec.md) · [M4 Living Registry Spec](2026-03-24-m4-living-registry-spec.md) · [M5 Web UI Spec](2026-03-24-m5-web-ui-spec.md) · [External Services & Pricing Evidence Spec](2026-03-28-external-services-pricing-spec.md)

---

## 1. Overview

### 1.1 Thesis

Public skills and capabilities are not trustworthy as-authored. Their names, descriptions, tags, evaluation criteria, and even claimed scope should be treated as untrusted evidence, not as canonical truth.

Loom's job is to ingest those artifacts, preserve them immutably, derive a canonical registry record from them, evaluate that derived record against both usefulness and safety criteria, deduplicate overlapping submissions, and only then publish a frozen, versioned artifact for discovery and execution.

### 1.2 Four Product Responsibilities

This spec turns the product goals into concrete system responsibilities:

1. **Canonical metadata coverage** — Loom derives complete, consistent metadata for skill prose, attached code, manifests, tests, and dependency surface.
2. **Normalization and deduplication** — Loom clusters overlapping artifacts, rejects exact duplicates, merges or supersedes equivalent variants, and promotes true multi-step workflows into capabilities.
3. **Truth-bound evaluation** — Loom evaluates whether the artifact actually does what the canonical record says it does, including adversarial and execution safety checks.
4. **Fast discovery over frozen releases** — the resolver/search stack only sees published, versioned Loom releases, never raw submissions or transient rewrite states.

### 1.3 Why This Spec Exists

The current codebase has the right ingredients but not yet the right boundaries:

- ingestion stores raw skills
- metadata can be rewritten
- eval exists
- behavioral eval exists
- comparative eval exists

What is missing is a first-class model for:

- immutable source provenance
- non-destructive adaptation by Loom
- content-addressed versioning
- separating workflow state from trust tier
- defining exactly when canonicalization, deduplication, evaluation, and publication should run

### 1.4 Design Principles

1. **Source is evidence, not truth** — author metadata, source eval criteria, and upstream packaging are inputs to Loom, not fields Loom blindly serves.
2. **Immutable provenance** — the original source artifact must always be recoverable, including attached files and code inventory.
3. **Frozen evaluation subject** — evaluation always runs against a frozen canonical revision hash, never a mutable row that may change under it.
4. **Workflow state is not trust tier** — "still being processed" and "trusted enough to serve" are different axes.
5. **Safety overrides utility** — adversarial and harmfulness findings are hard gates, not soft score penalties.
6. **Publication is explicit** — the resolver/search index is built from published releases only.
7. **Capabilities are content-addressed graphs** — capability identity should be bound to the exact step graph and constituent revision hashes, not just a human version string.

---

## 2. Core Model

### 2.1 Three Layers of Truth

Every registry item has three conceptual layers:

| Layer | Meaning | Trust Level |
|-------|---------|-------------|
| **Source artifact** | Raw imported skill/capability files, attached code, manifests, upstream metadata | Untrusted |
| **Source claims** | Name, description, tags, eval criteria, "what this does" as stated by the author | Untrusted |
| **Loom canonical record** | Loom-derived metadata, code inventory, eval criteria, safety notices, dedup links, search text | Registry truth |

Loom never discards the first two layers. It simply does not publish them as authoritative.

### 2.2 Stable Identity vs Immutable Revision

The system distinguishes:

- **Registry identity**: stable logical object, such as a `skill` or `capability`
- **Revision**: immutable canonical release of that object
- **Source artifact**: immutable ingested upstream material that may contribute to one or more canonical revisions

This is analogous to:

- `skills` / `capabilities`: stable ids and lifecycle state
- `skill_versions` / `capability_versions`: immutable canonical revisions
- new `source_artifacts` / `artifact_files`: immutable source-side provenance

### 2.3 Lifecycle State vs Trust Tier

Trust tier is not a workflow state. Replace the current overloading with two separate fields:

#### `lifecycle_state`

| Value | Meaning | Visible in discovery? |
|-------|---------|-----------------------|
| `quarantined` | Raw artifact stored, only cheap gates run | No |
| `canonicalizing` | Loom is deriving metadata / code inventory / eval candidates | No |
| `deduplicating` | Artifact under similarity / merge / split analysis | No |
| `evaluating` | Canonical revision is frozen and under evaluation | No |
| `review` | Awaiting human review after low-confidence or conflict | No |
| `published` | Canonical revision approved for search/resolve | Yes |
| `rejected` | Artifact or candidate rejected | No |
| `deprecated` | Published but superseded | Yes, with warning |

#### `trust_tier`

| Value | Meaning |
|-------|---------|
| `experimental` | Published but lightly proven |
| `community` | Published with stronger evidence and/or comparative wins |
| `verified` | Published with strongest evidence and/or human stewardship |

`trust_tier` is only meaningful when `lifecycle_state = 'published'` or `deprecated`.

### 2.4 Content Addressing

Every important object gets a stable hash:

| Hash | Bound To | Purpose |
|------|----------|---------|
| `artifact_hash` | Full raw source artifact bundle | Provenance and exact-source recovery |
| `source_claims_hash` | Extracted upstream metadata claims | Auditing author assertions |
| `canonical_hash` | Canonical prose + metadata + code inventory + eval spec + dependency declarations | Evaluation binding and publication |
| `execution_bundle_hash` | Attached code/manifests/tests selected for sandbox evaluation | Executability binding |
| `capability_root_hash` | Merkle root over capability step graph | Versioning of composed capabilities |

The resolver and all eval records should bind to `canonical_hash` or `capability_root_hash`, not only to a mutable `(skill_id, version)` pair.

---

## 3. Proposed Data Model

### 3.0 Authorship & Provenance Policy

Authorship is not binary. Loom should preserve source authorship when possible, but it must not imply that an upstream author stands behind a heavily rewritten canonical release they did not actually write.

The system therefore distinguishes:

| Concept | Meaning |
|--------|---------|
| `submitted_by` | The user or ingestion agent that introduced the artifact into Loom |
| `source_authors` | Authors attributable from the upstream source |
| `canonical_authors` | Authors of the published canonical release |
| `change_agent` | The actor that made the current revision-level mutation |

The key policy rule is:

- the more Loom materially changes an artifact, the weaker the claim that the original author is the author of the published release

#### Canonicalization Levels

Every published revision should carry a `canonicalization_level`:

| Value | Meaning | Authorship Implication |
|-------|---------|------------------------|
| `none` | Published essentially as submitted, with no meaningful Loom rewrite | Original author retains strong authorship |
| `minor` | Loom corrected or filled in small metadata gaps without changing scope | Original author remains primary; Loom is an editor/reviewer |
| `substantive` | Loom materially changed description, eval criteria, safety notices, dependency declarations, or package understanding | Original author remains source author; canonical release is "normalized by Loom" |
| `derived` | Loom split, merged, extracted, or fully rewrote the artifact into a different publishable object | Published release is Loom-derived from source artifacts |

#### Authorship Status

Every published revision should also carry an `authorship_status`:

| Value | Meaning |
|-------|---------|
| `author_owned` | The published release substantially reflects the submitter/source author's own work |
| `loom_amended` | The release is still primarily the author's work, but Loom materially amended it |
| `loom_derived` | The release is a Loom-derived artifact based on one or more sources |

#### Display Rules

The UI and API should present authorship honestly:

- `author_owned`: "Authored by Alice"
- `loom_amended`: "Authored by Alice, normalized by Loom"
- `loom_derived`: "Derived by Loom from sources by Alice and Bob"

The system should never flatten these into a single ambiguous `author` label once substantive mutation has occurred.

#### Submission Incentives

This policy intentionally rewards native Loom publication:

- authors who submit directly in Loom format with complete metadata keep stronger authorship attribution
- native submissions should go through review and evaluation before publication
- authors should be able to amend metadata or eval criteria in response to review feedback
- the less Loom needs to adapt, the faster and more directly a submission can move toward publication

Imported public artifacts remain important inputs, but they should default toward weaker authorship claims once heavy canonicalization is required.

### 3.1 New Tables

#### `source_artifacts`

Immutable record of every acquired upstream submission.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `entity_kind` | text | `skill` or `capability_candidate` |
| `source_type` | text | github, local, manual, import |
| `source_uri` | text | Canonical source locator |
| `source_ref` | text | commit SHA, tag, branch, release id |
| `artifact_hash` | text | SHA-256 of normalized bundle |
| `raw_metadata` | JSONB | Upstream metadata blob |
| `ingest_notes` | JSONB | Cheap gate findings |
| `created_at` | timestamptz | |

Unique key: `(source_uri, source_ref, artifact_hash)`.

#### `artifact_files`

Immutable file inventory for each source artifact.

| Column | Type | Notes |
|--------|------|-------|
| `artifact_id` | UUID | FK -> source_artifacts |
| `path` | text | Relative path in bundle |
| `kind` | text | `skill_markdown`, `manifest`, `script`, `test`, `data`, `asset`, `other` |
| `sha256` | text | File hash |
| `size_bytes` | bigint | |
| `language` | text | Optional |
| `is_entrypoint` | bool | Heuristic |
| `content_ref` | text | Blob reference if file bodies are externalized |

#### `canonicalization_jobs`

Tracks Loom adaptation work, including metadata derivation and feedback loops.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `artifact_id` | UUID | FK -> source_artifacts |
| `status` | text | pending, running, completed, failed |
| `trigger_type` | text | ingest, source_change, manual, neighborhood_change |
| `output_kind` | text | `new_skill`, `revision`, `alias`, `capability_candidate`, `split_candidate`, `rejected` |
| `canonical_hash` | text | Nullable until produced |
| `feedback` | JSONB | Structured canonicalization feedback |
| `created_at` | timestamptz | |
| `completed_at` | timestamptz | |

#### `dedup_clusters`

Represents "same capability neighborhood" rather than just exact duplicates.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `cluster_key` | text | Stable cluster identifier |
| `entity_kind` | text | skill or capability |
| `canonical_member_id` | UUID | Current winner / representative |
| `cluster_summary` | JSONB | What the cluster does, common confusions |
| `created_at` | timestamptz | |

#### `artifact_adaptations`

Provenance link between source artifacts and canonical revisions.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `artifact_id` | UUID | FK -> source_artifacts |
| `target_kind` | text | `skill_version` or `capability_version` |
| `target_id` | UUID | FK target |
| `adaptation_type` | text | `source_import`, `canonicalize`, `merge`, `split`, `supersede`, `capability_extract` |
| `rationale` | text | Human-readable |
| `diff_summary` | JSONB | Structured field-level diff |
| `created_at` | timestamptz | |

### 3.2 Changes to Existing Version Tables

Add the following to `skill_versions` and `capability_versions`:

| Column | Type | Notes |
|--------|------|-------|
| `canonical_hash` | text | Immutable evaluated release hash |
| `execution_bundle_hash` | text | Bound code/package/test bundle hash |
| `change_type` | text | `author_submission`, `loom_canonicalize`, `eval_amendment`, `auto_merge`, `split_extract`, `deprecation` |
| `change_agent` | text | `loom/canonicalizer`, `loom/dedup`, `admin/{id}`, `author/{id}` |
| `change_rationale` | text | Human-readable reason |
| `diff_summary` | JSONB | Structured changes |
| `parent_version_id` | UUID | Previous canonical revision |
| `derived_from_artifact_ids` | UUID[] or JSONB | Source lineage |
| `display_name` | text | Published user-facing name |
| `embedding_text` | text | Exact embedded string |
| `safety_notices` | JSONB | Warnings required at publish time |
| `canonicalization_level` | text | `none`, `minor`, `substantive`, `derived` |
| `authorship_status` | text | `author_owned`, `loom_amended`, `loom_derived` |

### 3.3 Changes to `skills` / `capabilities`

Add:

| Column | Type | Notes |
|--------|------|-------|
| `lifecycle_state` | text | See §2.3 |
| `current_version_id` | UUID | Latest canonical revision |
| `published_version_id` | UUID | Resolver-visible revision |
| `dedup_cluster_id` | UUID | FK -> dedup_clusters |
| `superseded_by_id` | UUID | Optional |
| `provenance_summary` | JSONB | Compact "sourced from / adapted from" data |

### 3.4 Evaluation Binding

`eval_jobs`, `behavioral_eval_runs`, and comparative eval results should include:

| Column | Type | Notes |
|--------|------|-------|
| `subject_kind` | text | skill_version or capability_version |
| `subject_id` | UUID | FK target |
| `canonical_hash` | text | Evaluated canonical subject |
| `execution_bundle_hash` | text | Evaluated code bundle |
| `meta_feedback` | JSONB | Structured feedback that may trigger re-canonicalization |

This allows future audits to answer: "What exact canonical revision and attached code were these scores produced against?"

---

## 4. Pipeline A: Source Ingest & Quarantine

### 4.1 Purpose

Persist upstream material cheaply, safely, and immutably before any normalization or trust decision.

### 4.2 Steps

1. Acquire source bundle from GitHub, local upload, or API submission.
2. Normalize bundle layout and compute `artifact_hash`.
3. Store `source_artifacts` and `artifact_files`.
4. Run cheap gates:
   - content length bounds
   - file count / size bounds
   - obvious injection signatures
   - manifest parseability
   - prohibited file types if needed
5. Extract raw source claims:
   - upstream name / description / tags
   - upstream eval criteria
   - dependency declarations
   - package manifests, scripts, tests
6. Set `lifecycle_state = 'quarantined'`.
7. Enqueue canonicalization.

### 4.3 Output

- immutable source artifact
- file/code inventory
- raw source claims
- cheap-gate findings

### 4.4 Important Rule

Nothing from this stage is discoverable or executable by the resolver.

---

## 5. Pipeline B: Canonicalization

### 5.1 Purpose

Derive Loom's best current understanding of what the artifact is, what it depends on, how it should be found, and how it should be evaluated.

### 5.2 Inputs

- source artifact bundle
- source claims
- parsed code/manifests/tests
- nearby published cluster members
- existing capability graph if relevant

### 5.3 Outputs

Canonicalization produces a draft canonical record with:

- `display_name`
- canonical description
- canonical tags and category
- `embedding_text`
- safety notices
- dependency declarations inferred from both prose and code
- code inventory
- capability claims
- candidate eval scenarios
- candidate behavioral scenarios
- dedup hints
- provenance summary:
  - sourced from `{source_uri}@{source_ref}`
  - adapted by Loom on `{date}`
  - adapted fields: name, description, tags, eval_spec, dependency surface, safety notices

### 5.4 Rules

1. Canonical metadata may use source claims as evidence, but never as sole truth.
2. Attached code and manifests can override vague prose.
3. Canonical descriptions should state both positive scope and explicit non-goals.
4. Canonical eval criteria must test the canonical goal, not the author's self-serving framing.
5. Canonicalization is non-destructive: source claims remain queryable.
6. Canonicalization must classify how much Loom changed the artifact so authorship can be represented honestly.

### 5.5 Code-Aware Canonicalization

If code is attached, canonicalization must also derive:

- executable entrypoints
- required runtime(s)
- package manager / manifest type
- declared and implied dependencies
- likely side effects:
  - shell execution
  - filesystem writes
  - network access
  - external APIs
  - secret handling
- test presence and likely test command

### 5.6 Canonicalization Feedback Loop

Canonicalization may run in at most one feedback loop before review:

```
source artifact
  -> canonical draft
  -> eval + safety feedback
  -> canonical amendment (optional, single loop)
  -> frozen candidate revision
```

The loop is allowed to refine:

- scope wording
- tags/category
- safety notices
- eval scenario coverage

The loop is not allowed to silently broaden the claimed capability.

---

## 6. Pipeline C: Deduplication, Merge, Split & Capability Extraction

### 6.1 Purpose

The goal is not just duplicate detection. The goal is normalization of the capability surface.

### 6.2 Comparison Outcomes

Every canonical draft is compared against nearby published and draft neighbors. The system may conclude:

| Outcome | Meaning | Action |
|---------|---------|--------|
| `exact_duplicate` | Same artifact or same canonical capability | Attach source to existing revision, reject new publishable object |
| `equivalent_variant` | Same capability, different implementation | Comparative eval decides winner; loser becomes alternative or superseded source |
| `narrower_specialization` | Same family, tighter scope | Publish as separate skill linked in same cluster |
| `broader_blob` | Contains multiple distinct tasks | Generate split candidates |
| `multi_step_workflow` | Better represented as composition | Generate capability candidate |
| `truly_new` | Distinct capability | Create new cluster member |

### 6.3 Dedup Signals

Use multiple signals together:

- canonical embedding similarity
- code inventory similarity
- manifest overlap
- declared dependency overlap
- eval scenario overlap
- comparative behavioral evaluation
- metadata truthfulness mismatch

Similarity alone should not auto-merge near neighbors.

### 6.4 Merge Rules

Auto-merge is only safe for:

- exact content duplicates
- identical canonical hash
- extremely high similarity plus comparative tie plus matching code inventory

Everything else either stays separate or routes to `review`.

### 6.5 Split Rules

A skill becomes a split candidate when:

- canonical description requires multiple unrelated verbs or subdomains
- inferred eval scenarios decompose cleanly into distinct goals
- attached code exposes multiple largely independent entrypoints
- comparative analysis shows users would likely search for parts independently

Split outputs are new draft canonical candidates with shared source provenance.

### 6.6 Capability Extraction

When a broad artifact is best understood as "sequence of smaller tasks," Loom should:

1. derive smaller skill candidates
2. derive the composed capability graph
3. evaluate both the parts and the full capability
4. publish the capability only if the graph adds value beyond a flat blob

---

## 7. Pipeline D: Evaluation

### 7.1 Purpose

Evaluate whether the frozen canonical revision is:

- truthful about its goal
- useful for that goal
- safe in content
- safe in execution
- robust under adversarial conditions

### 7.2 Evaluation Subject

Evaluation always runs against a frozen revision:

- `skill_version.canonical_hash`
- `skill_version.execution_bundle_hash`
- or `capability_version.capability_root_hash`

If any of those change, the system is evaluating a different subject and must create a new revision or new eval job bound to the new hash.

### 7.3 Evaluation Axes

#### Utility / Correctness

- clarity
- completeness
- correctness
- behavioral success
- executability of attached code

#### Safety / Adversarial

- prompt injection / instruction override attempts
- harmful or unsafe execution behavior
- privilege escalation or exfiltration risk
- scope overreach beyond canonical goal
- deceptive metadata or understated side effects

Safety findings are hard gates.

### 7.4 Metadata Truthfulness Check

Evaluation should explicitly score whether the canonical metadata is honest:

- does the description match the actual behavior?
- do stated non-goals match observed non-capabilities?
- are safety notices adequate?
- are dependency claims complete?

This output feeds `meta_feedback` and may trigger one controlled canonicalization amendment.

### 7.5 Attached Code Evaluation

If code/manifests/tests are present, evaluation should include:

1. file existence validation
2. manifest parsing
3. dependency installability where feasible
4. sandboxed tests, lint, or smoke execution
5. side-effect analysis
6. evidence capture bound to `execution_bundle_hash`

### 7.6 Comparative Evaluation in Clusters

For `equivalent_variant` candidates, publication should usually require head-to-head comparison against the cluster representative:

- same canonical scenarios
- same safety tests
- same execution checks when possible

The system can then decide:

- new revision wins and supersedes
- existing representative remains canonical
- both remain as differentiated variants

---

## 8. Pipeline E: Publication

### 8.1 Purpose

Freeze and publish only evaluated canonical releases.

### 8.2 Publish Preconditions

A revision may become `published_version_id` only if:

1. canonicalization completed
2. dedup disposition resolved
3. required eval and adversarial eval completed
4. no hard safety gate failed
5. no unresolved low-confidence conflict remains

### 8.3 Publish Actions

1. Create immutable `skill_version` or `capability_version`.
2. Store `canonical_hash` and `execution_bundle_hash`.
3. Set `published_version_id`.
4. Set `lifecycle_state = 'published'`.
5. Assign or update `trust_tier`.
6. Persist `canonicalization_level` and `authorship_status`.
7. Index `embedding_text` for discovery.
8. Persist provenance summary:
   - sourced from
   - adapted by Loom
   - derived from artifact ids
   - superseded/merged/split relationships if any

### 8.4 Resolver Rule

The resolver and search API must query only:

- `lifecycle_state = 'published'`
- `published_version_id IS NOT NULL`

They must not index:

- quarantined artifacts
- canonical drafts
- in-flight dedup candidates
- evaluation-in-progress rows

---

## 9. Triggering Rules

### 9.1 Canonicalization

Trigger canonicalization on:

- new source artifact
- source bundle hash change
- manual "recanonicalize" request
- high-confidence metadata truthfulness drift from eval

Do not trigger it on ordinary scheduled re-evals by default.

### 9.2 Dedup / Cluster Review

Trigger dedup analysis on:

- new canonical draft
- new published neighbor entering the same cluster
- cluster representative change
- explicit steward action

### 9.3 Full Evaluation

Trigger full evaluation on:

- new canonical revision
- new execution bundle hash
- new capability root hash
- source-backed revision change
- usage-signal regression
- scheduled sample re-evaluation
- evaluator model / prompt version drift

### 9.4 Reindex-Only

Trigger reindex only on:

- `embedding_text` change
- category/tag change that affects retrieval
- cluster-neighborhood changes affecting disambiguation

Reindex-only must not mutate the canonical record.

### 9.5 Capability Rebuild

Trigger capability rebuild when:

- any referenced published skill revision changes
- step topology changes
- bindings / data flow annotations change
- step-level safety notices change

---

## 10. Capability Merkle Versioning

### 10.1 Goal

Capabilities are graphs, not files. Their identity should be bound to the exact graph and its constituents.

### 10.2 Merkle Leaves

Each capability step leaf hash should include:

- referenced `skill_version.canonical_hash`
- step role / purpose
- required vs optional status
- input/output bindings
- step-local constraints

Example leaf input:

```json
{
  "skill_hash": "sha256:...",
  "role": "collect-release-inputs",
  "required": true,
  "bindings": {"repo": "ctx.repo", "since": "ctx.last_tag"},
  "constraints": {"trust_floor": "community"}
}
```

### 10.3 Edge Hashes

Each data-flow edge hash should include:

- source step id
- target step id
- payload label
- classification / privacy label
- transform hint if present

### 10.4 Root Hash

`capability_root_hash = MerkleRoot(sorted(step_hashes + edge_hashes + capability_metadata_hash))`

This gives Loom:

- exact rebuild detection
- stable provenance over composed workflows
- ability to answer "what exact composed graph was evaluated?"

### 10.5 Publish Rule

Any change to step order, step revision, bindings, or data flow yields a new `capability_root_hash` and therefore a new capability revision.

---

## 11. Governance & Audit Requirements

The system must answer these questions for every published item:

1. What exact upstream artifact(s) did this come from?
2. What did the upstream author claim?
3. What did Loom change, add, or remove?
4. What exact revision did evaluation run against?
5. What exact code bundle was executed in sandbox?
6. Why was this merged, split, superseded, or published?
7. What cluster or capability neighborhood does it belong to?

The governance UI should therefore surface:

- source provenance chain
- canonical revision history
- adaptation diffs
- eval evidence by revision hash
- dedup/merge/split decisions
- capability graph root hash

---

## 12. Migration From the Current System

### 12.1 Immediate Corrections

1. Stop using `trust_tier` as an in-flight processing state.
2. Ensure search/resolve uses only explicitly published rows.
3. Make metadata rewrite non-destructive by writing a new canonical revision/provenance record.
4. Bind eval jobs to revision hashes.

### 12.2 Transitional Mapping

Until `lifecycle_state` exists:

- current `unvetted` maps to `quarantined`
- current `experimental` should be treated as "published experimental", not "mid-pipeline"

No mid-pipeline artifact should ever be promoted into resolver visibility simply to get past a validation constraint.

### 12.3 Schema Rollout Order

1. Add provenance tables and `lifecycle_state`
2. Add version provenance fields and hashes
3. Route ingestion to `source_artifacts`
4. Route rewrite output to new immutable revisions
5. Bind eval records to revision hashes
6. Add capability Merkle hashing
7. Tighten resolver/search to published revisions only

---

## 13. Implementation Phasing

### Phase 1: Safety Boundaries

- add `lifecycle_state`
- resolver/search only serve published revisions
- non-destructive metadata rewrite with provenance
- eval bound to immutable revision hash

### Phase 2: Canonicalization as Product

- source artifact + file inventory
- canonical metadata model
- code-aware canonicalization
- metadata truthfulness feedback

### Phase 3: Normalization

- dedup clusters
- merge/split workflows
- capability extraction pipeline
- comparative canonical representative selection

### Phase 4: Content-Addressed Registry

- canonical hashes everywhere
- capability Merkle root hashing
- version-aware provenance UI
- signed published releases if desired

---

## 14. Summary

Loom should not behave like a searchable folder of user-authored files. It should behave like a normalization and evidence system:

- ingest raw artifacts immutably
- derive canonical records non-destructively
- deduplicate and reshape the capability surface
- evaluate frozen revisions against usefulness and safety
- publish only content-addressed Loom releases

That is the architectural basis for trustworthy discovery, governance, and later execution.
