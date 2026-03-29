# ADR 0001: Loom Publishes Normalized Loom Releases

**Date**: 2026-03-28
**Status**: Accepted
**Related**: [Canonicalization, Provenance & Publication Pipeline Spec](../specs/2026-03-28-canonicalization-provenance-pipeline-spec.md) · [External Services & Pricing Evidence Spec](../specs/2026-03-28-external-services-pricing-spec.md)

## Decision

Loom will operate as a **hybrid normalized package manager**.

Loom preserves raw source artifacts and source claims as immutable provenance inputs, derives canonical Loom revisions from them, evaluates those canonical revisions, and publishes only those Loom revisions for discovery and execution.

The resolver and search stack must never serve raw drafts, in-flight rewrites, or unpublished source artifacts.

## Why

Public skills are not trustworthy as-authored:

- names and descriptions are often vague or misleading
- metadata coverage is inconsistent
- source-provided eval criteria are often weak or self-serving
- duplicate and near-duplicate skills are common
- attached code and manifests often reveal more truth than the prose does

A package-manager-first model preserves too much noise and weakens discovery quality.

A normalizer-first model improves quality but can obscure provenance and overstate authorship if Loom materially rewrites artifacts without recording that clearly.

The hybrid model keeps both:

- strong provenance and source recoverability
- strong canonicalization, evaluation, and deduplication

## Consequences

- Introduce `lifecycle_state` separate from `trust_tier`
- Treat `source_artifact`, `source_claims`, and `canonical_release` as different truth layers
- Make canonical revisions immutable and hash-bound
- Publish only `published_version_id`
- Represent authorship explicitly with `canonicalization_level` and `authorship_status`
- Use the steward dashboard as the primary operational interface for intake, canonicalization review, deduplication, evaluation, and publication

## Alternatives Considered

### Package-manager-first

Loom would mostly validate and distribute upstream skills with limited normalization.

Rejected because:

- discovery quality would remain poor
- duplicates would remain noisy
- trust in metadata would be too weak
- evaluation would still be anchored to low-quality upstream claims

### Normalizer-first

Loom would treat upstream artifacts mainly as raw material and publish heavily editorialized registry objects.

Rejected because:

- provenance becomes harder to understand
- authorship becomes ambiguous under heavy mutation
- users can no longer easily answer "what was the original source?"

### Hybrid normalized package manager

Chosen because it combines:

- immutable provenance
- canonicalized registry truth
- publishable Loom-managed releases
- honest authorship labeling

## Non-goals

- serving raw drafts in resolver/search
- destructive in-place metadata rewrites with no provenance
- conflating original source authorship with Loom-derived releases
- making the public homepage the primary stewardship surface

## Follow-on Requirements

- lifecycle-aware schema and APIs
- published-only discovery filters
- provenance-aware revision records
- authorship/canonicalization labeling in the UI
- dashboard queues by pipeline stage rather than a single flat review queue
