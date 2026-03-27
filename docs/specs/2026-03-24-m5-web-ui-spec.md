# M5: Web UI — Resolution-First UX, Semantic Landscape & Governance Dashboard

**Date**: 2026-03-24
**Status**: Draft
**Companion to**: [Loom Design Spec](2026-03-21-loom-design.md) · [Implementation Milestones](implementation-milestones.md) · [M2 Quality & Trust Spec](2026-03-23-m2-quality-trust-spec.md) · [M3 Composition Spec](2026-03-23-m3-composition-spec.md) · [M4 Living Registry Spec](2026-03-24-m4-living-registry-spec.md)

---

## 1. Overview

### 1.1 Thesis

Humans can browse, contribute, and curate the Loom registry through a web interface that makes resolution — not browsing — the primary interaction. The UI proves that Loom's value proposition is legible to humans, not just agents.

### 1.2 Why This Spec Exists

M1-M4 built a powerful backend: constraint-aware resolution, quality evaluation, composition, behavioral testing, and usage feedback. But all interaction flows through MCP tools and REST endpoints designed for agents. M5 makes the registry accessible to human contributors, stewards, and curious developers — and it does so by centering the same operation that agents use: resolution.

### 1.3 Design Principles

1. **Resolution-first** — the homepage IS the resolver. The first thing a visitor sees is a search bar that performs live resolution, not a marketplace grid. The resolution is the product.
2. **Composition as flow, not lists** — capabilities are shown as visual pipelines (React Flow diagrams), not bulleted step lists. Data flow between steps is visible.
3. **Skill fingerprints instead of star ratings** — each skill's eval dimensions are rendered as a smooth organic shape (radar polygon with cardinal spline interpolation). This conveys multidimensional quality at a glance.
4. **Semantic landscape for volume** — as the registry grows, card grids break down. A 2D embedding map (UMAP/t-SNE projection) lets users explore the skill space spatially, discovering clusters and relationships.
5. **Living feed** — the registry's heartbeat is visible. Recent submissions, promotions, deprecations, and amendments stream in a sidebar feed.
6. **"Why not?" as a first-class concept** — alternatives and rejection rationale are always visible. When the resolver picks a skill, it explains why it rejected the others.

---

## 2. Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Framework | React 19 + TypeScript | Industry standard, large ecosystem |
| Build | Vite | Fast HMR, ESM-native, minimal config |
| Styling | Tailwind CSS + shadcn/ui | Utility-first CSS with pre-built accessible components |
| Flow diagrams | React Flow | Purpose-built for node/edge diagrams; capabilities as pipelines |
| Data viz | D3.js (semantic map, fingerprint SVG) + Recharts (Govern charts) | Semantic landscape map, skill fingerprint polygons, governance charts |
| Animation | Framer Motion | Layout animations, page transitions, micro-interactions |
| Data fetching | TanStack Query v5 | Cache management, background refetching, optimistic updates |
| Routing | TanStack Router + @tanstack/router-plugin | Type-safe file-based routing, search param validation, code splitting |
| Deployment | Vite SPA | Static build, served from CDN or same-origin as API |

The frontend is a standalone Vite SPA that talks to the existing FastAPI backend. No server-side rendering — the API already provides all data. The SPA is deployed independently from the backend.

---

## 3. Four Views

### 3.1 Resolve View (Homepage)

The Resolve View is the entry point. It surfaces the same `POST /api/v1/skills/resolve` endpoint that agents use, making Loom's core value proposition interactive.

#### Hero Search Bar

- Full-width search input: "What do you need to do?"
- Live resolution as the user types (debounced 300ms, calls `/api/v1/skills/resolve` with `type=any`)
- Results appear below the search bar with smooth enter/exit animations

#### Primary Result

- Skill or capability name, description, trust tier badge, version
- Eval fingerprint (skill fingerprint component — see Section 5)
- Behavioral score indicator (glow intensity)
- Usage success rate (compact stat)
- If capability: inline flow preview showing steps as a mini pipeline

#### Alternatives Section

- Up to 3 alternatives with rejection rationale
- Each shows: name, trust tier, fingerprint thumbnail, and the specific reason it was not selected
- Rejection reasons are human-readable: "Not selected: narrower scope", "Not selected: missing `git` dependency", "Not selected: cost exceeds budget"
- Click an alternative to promote it to the primary result position (re-renders detail)

#### Context Toggles

- Collapsible panel below the search bar
- `available_tools`: multi-select of common tool sets (git, filesystem, network, browser)
- `trust_floor`: dropdown (experimental, community, verified)
- `cost_budget`: slider (free, low, medium, high)
- Changing any toggle re-runs resolution immediately — the user watches results shift in real time

#### Resolution History

- Collapsible sidebar or bottom panel
- Recent queries stored in `localStorage`
- Click to re-run any previous resolution
- Clear history button

### 3.2 Explore View (Semantic Landscape)

The Explore View provides spatial navigation of the entire registry using pre-computed 2D embeddings.

#### Map Rendering

- Canvas-based 2D scatter plot (D3/visx) of skill and capability embeddings
- Pre-computed UMAP or t-SNE projections served from `GET /api/v1/embeddings/map`
- Smooth pan and zoom with mouse/trackpad

#### Visual Encoding

| Property | Visual Mapping |
|----------|---------------|
| Type | Color palette: skills = blue family, capabilities = amber family |
| Trust tier | Node size: verified = large, community = medium, experimental = small |
| Category | Cluster position (emerges from embedding similarity) |
| Eval quality | Node opacity: high composite score = solid, low = translucent |
| Behavioral score | Glow/vibrancy: tested skills glow, untested are muted |

#### Interaction

- **Zoom out**: category cluster labels appear, individual nodes merge into density clouds
- **Zoom in**: individual skills visible with fingerprint thumbnails on each node
- **Capabilities as edges**: capability nodes shown with thin lines connecting to their constituent skill nodes
- **Search**: typing in the explore search bar highlights matching nodes and fades the rest
- **Click node**: slide-out detail panel (same content as Inspect View, but in a side panel)
- **Hover node**: tooltip with name, trust tier, composite score

#### Cluster Labels

- Auto-generated from category names
- Positioned at cluster centroid
- Font size scales with cluster population

### 3.3 Inspect View (Detail + Flow)

The Inspect View provides deep detail on a single skill or capability. Reached by clicking a result in Resolve View, a node in Explore View, or a direct URL (`/skills/{slug}` or `/capabilities/{slug}`).

#### Skill Detail

- **Header**: name, slug, version, author, trust tier badge, created/updated dates
- **Description**: full description text
- **Content preview**: collapsible skill content (markdown rendered as styled text, NOT as HTML — XSS prevention)
- **Eval fingerprint**: large interactive version (see Section 5), with score labels on each axis
- **Behavioral score**: prominent display with judge evidence summary
- **Usage stats**: success rate, total resolutions, avg runtime — pulled from `GET /api/v1/skills/{slug}/usage`
- **Version history**: timeline of versions with diff links
- **Trust journey timeline**: visual timeline of trust tier changes from `GET /api/v1/skills/{skill_id}/trust`
- **Extends chain**: if the skill extends another, show the chain with links
- **Dependencies**: listed with satisfaction status for common tool sets

#### Capability Detail

- **Header**: same as skill header
- **Flow diagram**: interactive React Flow diagram
  - Each step rendered as a node: skill name, role, trust badge
  - Data flow edges connecting outputs to inputs with classification labels
  - Required vs optional steps visually distinguished (solid vs dashed borders)
  - Click a step node to expand it: shows the embedded skill content and eval fingerprint
- **Aggregate trust**: effective trust tier (minimum across all steps) with per-step breakdown
- **Dependencies**: aggregated across all steps with per-step satisfaction status

#### "Why This Works" Section

- Eval evidence from each dimension (clarity, completeness, safety, correctness)
- Behavioral judge reasoning (from most recent eval)
- If the user arrived from Resolve View: side-by-side comparison with the top rejected alternative

#### Alternatives Comparison

- Two-column layout comparing the inspected skill with a selected alternative
- Per-dimension score comparison with bar charts
- Behavioral score comparison
- Usage stats comparison

#### Version Diff

- When viewing a skill with amendments, side-by-side diff of content
- Triage classification label (refinement, regression, variant, extension)
- Per-dimension score delta indicators

### 3.4 Govern View (Dashboard + Queue)

The Govern View provides registry health observability and human review workflows. In M5, this view is publicly accessible without authentication. Role-based access control (`steward` role gating) is deferred to M6.

#### Registry Health Dashboard

- **Skill counts by trust tier**: stacked bar chart (experimental, community, verified)
- **Behavioral eval coverage**: percentage of skills with behavioral scores, shown as progress ring
- **Stale/deprecated counts**: summary cards with trend arrows
- **Total resolutions**: counter with daily/weekly trend sparkline

#### Eval Trends

- **Composite score distribution over time**: area chart showing score distribution bands by week
- **Dimension breakdown**: toggle between clarity, completeness, safety, correctness, behavioral
- **Category filter**: focus on a specific category's trends
- Data from `GET /api/v1/stats/eval-trends`

#### Usage Heatmap

- **Resolution frequency by category x time**: heatmap grid
- Rows = categories, columns = time periods (days or weeks)
- Color intensity = resolution count
- Data from `GET /api/v1/stats/usage-heatmap`

#### Review Queue

- **Queue items**: skills with low-confidence evals, injection flags, mixed amendments
- Each item shows: skill name, slug, reason for queue entry, submission date, eval summary
- Data from `GET /api/v1/governance/queue`

#### Review Interface

- Full eval context for the queued item:
  - Eval fragments (what the LLM saw during evaluation)
  - Per-dimension scores with evidence
  - Injection indicators (flagged dimensions highlighted)
  - Behavioral eval results if available
  - Amendment diff if applicable
- Action buttons: Approve, Reject, Request Changes
- Action requires a note (free text)
- Submit via `POST /api/v1/governance/review`

#### Promotion Queue

- Skills meeting auto-promotion criteria, with current scores and usage stats
- Steward can: confirm promotion, defer, or block with reason
- Override controls for edge cases

#### Breaking Change Reports

- Capabilities affected by skill amendments (from M4ii breaking change detection)
- Each report shows: capability name, affected step, old vs new behavioral scores
- Link to the capability's Inspect View for full context

---

## 4. Living Feed

A sidebar component visible across all views (collapsible on smaller screens). Shows the registry's recent activity:

- New skill submissions (with eval status)
- Trust tier promotions and demotions
- Amendments merged or rejected
- Skills deprecated (with successor link)
- Capabilities created or updated
- High-impact usage events (e.g., a skill crossing the 80% success threshold)

Data source: `GET /api/v1/activity/feed` — a new endpoint that aggregates registry events (submissions, promotions, deprecations, amendments, capability changes) into a unified chronological feed. Polled every 30 seconds. Future enhancement: WebSocket for real-time push.

---

## 5. Skill Fingerprint Design

Each skill's eval dimensions are rendered as a smooth organic shape — a visual fingerprint that conveys multidimensional quality at a glance.

### 5.1 Axes

Five axes arranged radially:

1. **Clarity** (0-1) — from M2 LLM evaluation
2. **Completeness** (0-1) — from M2 LLM evaluation
3. **Safety** (0-1) — from M2 LLM evaluation
4. **Correctness** (0-1) — from M2 LLM evaluation
5. **Behavioral** (0-1) — from M4 behavioral evaluation

### 5.2 Rendering

- **Shape**: filled polygon with smooth interpolation (cardinal spline / Catmull-Rom) connecting the five axis points
- **Fill**: semi-transparent fill with category-aware color
- **Color intensity**: maps to overall confidence (high confidence = saturated, low = desaturated)
- **Glow/vibrancy**: behavioral score controls a subtle glow effect. Tested skills (behavioral score > 0) have a luminous quality; untested skills are muted and flat
- **Border**: thin stroke following the shape, slightly darker than fill

### 5.3 Sizes

The fingerprint component renders at three sizes:

| Size | Context | Dimensions |
|------|---------|------------|
| Thumbnail | Search results, explore map nodes | 32x32px |
| Card | Result cards, alternative list | 64x64px |
| Hero | Inspect view header | 200x200px, interactive (hover axis for label + score) |

### 5.4 Implementation

SVG-based component using visx or raw D3 path generation. The cardinal spline interpolation produces organic, recognizable shapes — a skill that excels at safety but lacks completeness looks visibly different from one that is complete but unsafe. Over time, users develop intuition for "good shapes."

---

## 6. API Requirements

### 6.1 Existing Endpoints (Sufficient for Core Views)

The existing M1-M4 API surface covers the majority of data needs:

| Endpoint | Used By |
|----------|---------|
| `POST /api/v1/skills/resolve` | Resolve View (skill-only resolution) |
| `GET /api/v1/skills` | Explore View (skill listing) |
| `GET /api/v1/skills/search` | Resolve/Explore (search) |
| `GET /api/v1/skills/{slug}` | Inspect View (skill detail) |
| `PUT /api/v1/skills/{slug}` | Contribution (amendment submission) |
| `POST /api/v1/skills` | Contribution (new skill) |
| `GET /api/v1/skills/{skill_id}/eval` | Inspect View (eval history) |
| `GET /api/v1/skills/{slug}/behavioral` | Inspect View (behavioral results) |
| `GET /api/v1/skills/{slug}/usage` | Inspect View (usage stats) |
| `GET /api/v1/skills/{skill_id}/trust` | Inspect View (trust journey) |
| `POST /api/v1/skills/{slug}/deprecate` | Govern View (deprecation) |
| `POST /api/v1/skills/{slug}/compare` | Govern View (comparison trigger) |
| `GET /api/v1/capabilities` | Explore View (capability listing) |
| `GET /api/v1/capabilities/{slug}` | Inspect View (capability detail) |
| `GET /api/v1/capabilities/search` | Explore/Resolve (capability search) |
| `POST /api/v1/capabilities/resolve` | Resolve View (capability-only resolution) |
| `GET /api/v1/categories` | Explore View (category labels) |
| `POST /api/v1/usage/report` | Contribution (usage reporting) |

### 6.2 New Endpoints Required

These endpoints provide data that does not exist in M1-M4 and must be implemented as part of M5:

#### `POST /api/v1/resolve`

Unified resolution endpoint used by the Resolve View's hero search bar. Wraps the existing `UnifiedResolver` service, which already exists but has no API route.

```json
// Request
{
  "task_description": "review my pull request for security issues",
  "context": {
    "available_tools": ["git", "filesystem"],
    "trust_floor": "community",
    "cost_budget": "low"
  },
  "type": "any"  // "any" | "skill" | "capability"
}

// Response — ResolvedResult (union of ResolvedSkill | ResolvedCapability)
{
  "type": "skill",
  "result": { /* ResolvedSkill */ },
  "alternatives": [
    {
      "skill": { /* SkillSummary */ },
      "match_score": 0.72,
      "rejection_reason": "Not selected: narrower scope — only covers code style, not security"
    }
  ],
  "selection_rationale": ["..."]
}
```

The `type` filter allows the Resolve View's context toggles to constrain resolution to skills only, capabilities only, or either.

#### `GET /api/v1/activity/feed`

Aggregated registry activity feed for the Living Feed sidebar. Returns recent events across all event types in chronological order.

```json
{
  "events": [
    {
      "id": "uuid",
      "event_type": "skill_submitted",
      "timestamp": "2026-03-24T10:00:00Z",
      "skill_slug": "review-security",
      "skill_name": "Security Code Review",
      "detail": "New skill submitted",
      "trust_tier": "experimental"
    },
    {
      "id": "uuid",
      "event_type": "trust_promoted",
      "timestamp": "2026-03-24T09:30:00Z",
      "skill_slug": "commit-ai-message",
      "skill_name": "AI Commit Message",
      "detail": "experimental → community",
      "from_tier": "experimental",
      "to_tier": "community"
    },
    {
      "id": "uuid",
      "event_type": "skill_deprecated",
      "timestamp": "2026-03-24T09:00:00Z",
      "skill_slug": "old-review",
      "skill_name": "Old Review",
      "detail": "Deprecated in favor of review-pull-request",
      "successor_slug": "review-pull-request"
    }
  ]
}
```

Event types: `skill_submitted`, `capability_submitted`, `trust_promoted`, `trust_demoted`, `skill_deprecated`, `amendment_merged`, `amendment_rejected`, `eval_completed`.

Query params: `?limit={n}` (default 20), `?since={iso_timestamp}` (for incremental polling).

Aggregates data from: `skills` (created_at), `capabilities` (created_at), `trust_audit_log`, `eval_jobs`, and skill version history.

### 6.3 Backend Enhancements Required

These changes improve existing M1-M4 functionality to support M5 UX requirements:

#### Alternative Rejection Rationale

The existing `Alternative` model has a `tradeoff` field that is currently populated with a static string (`"Alternative skill"`). The Resolve View requires meaningful per-alternative rejection reasons.

Enhancement: update `DiscoveryService.resolve()` and `CapabilityDiscoveryService.resolve()` to populate `tradeoff` with contextual reasons based on:
- Match score gap vs. winner (e.g., "Lower semantic relevance to task")
- Missing dependencies (e.g., "Missing required dependency: git")
- Cost difference (e.g., "Cost exceeds budget")
- Scope mismatch (e.g., "Narrower scope — covers only X, not Y")
- Trust tier gap (e.g., "Experimental tier — winner is community")

### 6.4 Data Endpoints

#### `GET /api/v1/embeddings/map`

Returns pre-computed 2D projections for all skills and capabilities, for the Explore View semantic landscape.

```json
{
  "skills": [
    {
      "slug": "release-notes-enriched",
      "x": 0.42,
      "y": -0.18,
      "trust_tier": "community",
      "category": "documentation",
      "composite_score": 0.82,
      "behavioral_score": 0.85
    }
  ],
  "capabilities": [
    {
      "slug": "comprehensive-code-review",
      "x": 0.55,
      "y": 0.12,
      "trust_tier": "community",
      "category": "development/review",
      "composite_score": 0.78,
      "step_slugs": ["review-pull-request", "review-security", "review-performance"]
    }
  ]
}
```

Implementation: run UMAP/t-SNE on the existing pgvector embeddings as a scheduled job, cache the 2D projections. Re-compute on embedding changes (new skills, amendments).

#### `GET /api/v1/stats/overview`

Registry health metrics for the Govern View dashboard.

```json
{
  "skill_counts": { "experimental": 42, "community": 18, "verified": 5 },
  "capability_count": 8,
  "behavioral_eval_coverage": 0.72,
  "stale_count": 3,
  "deprecated_count": 2,
  "total_resolutions_7d": 1240,
  "total_resolutions_30d": 4820
}
```

#### `GET /api/v1/stats/eval-trends`

Eval score distribution over time windows for the Govern View eval trends chart.

```json
{
  "windows": [
    {
      "week_start": "2026-03-17T00:00:00Z",
      "composite_score_p25": 0.55,
      "composite_score_p50": 0.72,
      "composite_score_p75": 0.85,
      "behavioral_score_p50": 0.68,
      "eval_count": 34
    }
  ]
}
```

Query params: `?category={slug}&weeks={count}`

#### `GET /api/v1/stats/usage-heatmap`

Resolution frequency by category and time period for the Govern View usage heatmap.

```json
{
  "categories": ["development/git", "documentation", "code-review"],
  "periods": ["2026-W10", "2026-W11", "2026-W12"],
  "data": [
    [120, 95, 140],
    [45, 52, 48],
    [88, 102, 91]
  ]
}
```

Query params: `?period_type=week|day&periods={count}`

#### `GET /api/v1/governance/queue`

Items needing human review for the Govern View review queue.

```json
{
  "items": [
    {
      "id": "uuid",
      "skill_slug": "suspicious-skill",
      "reason": "injection_flag",
      "submitted_at": "2026-03-24T10:00:00Z",
      "eval_summary": {
        "composite_score": 0.45,
        "flagged_dimensions": ["safety"],
        "injection_detected": true
      }
    }
  ]
}
```

Query params: `?reason={injection_flag|low_confidence|mixed_amendment}&limit={n}&offset={n}`

Unprotected in M5. Will require `steward` role in M6.

#### `POST /api/v1/governance/review`

Submit a review decision on a queued item.

```json
{
  "queue_item_id": "uuid",
  "decision": "approve|reject|request_changes",
  "note": "Free text explanation for the decision"
}
```

Returns 200 with the updated item. Unprotected in M5. Will require `steward` role in M6.

#### `GET /api/v1/skills/{slug}/timeline`

Trust journey events for the Inspect View timeline visualization.

```json
{
  "events": [
    {
      "timestamp": "2026-03-20T14:00:00Z",
      "event_type": "submitted",
      "detail": "Initial submission"
    },
    {
      "timestamp": "2026-03-20T14:05:00Z",
      "event_type": "eval_completed",
      "detail": "Composite score: 0.78"
    },
    {
      "timestamp": "2026-03-22T09:00:00Z",
      "event_type": "promoted",
      "detail": "experimental -> community",
      "from_tier": "experimental",
      "to_tier": "community"
    }
  ]
}
```

Aggregates data from `trust_audit_log`, `eval_jobs`, `usage_aggregates`, and `skills` version history into a unified timeline.

---

## 7. Component Architecture

```
web/
  src/
    components/
      resolve/
        ResolveView.tsx           — page container
        HeroSearchBar.tsx         — search input with debounced resolution
        PrimaryResult.tsx         — full detail for top match
        AlternativeList.tsx       — rejected alternatives with rationale
        ContextToggles.tsx        — available_tools, trust_floor, cost_budget
        ResolutionHistory.tsx     — localStorage-backed recent queries
      explore/
        ExploreView.tsx           — page container
        SemanticMap.tsx            — D3 canvas with pan/zoom
        ClusterLabel.tsx          — auto-positioned category labels
        SkillNode.tsx             — individual node renderer with fingerprint
        CapabilityEdge.tsx        — lines connecting capability to constituent skills
        MapSearch.tsx             — search overlay that highlights/fades nodes
      inspect/
        InspectView.tsx           — page container (routes to skill or capability)
        skill/
          SkillDetail.tsx         — full skill detail layout
          EvalHistory.tsx         — eval dimension scores over versions
          VersionTimeline.tsx     — version history with diff links
          TrustJourney.tsx        — trust tier change timeline
          ExtendsChain.tsx        — extends relationship visualization
        capability/
          CapabilityDetail.tsx    — full capability detail layout
          FlowDiagram.tsx         — React Flow pipeline visualization
          StepNode.tsx            — individual step node (expandable)
          DataFlowEdge.tsx        — data flow edge with classification label
      govern/
        GovernView.tsx            — page container (public in M5, auth-gated in M6)
        HealthDashboard.tsx       — skill counts, coverage, staleness
        EvalTrends.tsx            — composite score distribution over time
        UsageHeatmap.tsx          — resolution frequency by category x time
        ReviewQueue.tsx           — list of items needing review
        ReviewInterface.tsx       — full review context + action buttons
        PromotionQueue.tsx        — skills meeting promotion criteria
        BreakingChanges.tsx       — capabilities affected by amendments
      shared/
        Fingerprint.tsx           — eval dimension SVG visualization (3 sizes)
        TrustBadge.tsx            — trust tier indicator (experimental/community/verified)
        LivingFeed.tsx            — activity feed sidebar
        SearchBar.tsx             — shared search input component
        SkillCard.tsx             — compact skill summary card
        CapabilityCard.tsx        — compact capability summary card
        ScoreBar.tsx              — horizontal score bar (0-1)
        DiffView.tsx              — side-by-side content diff
    hooks/
      useResolve.ts              — TanStack Query wrapper for resolution
      useSkill.ts                — fetch skill by slug
      useCapability.ts           — fetch capability by slug
      useSearch.ts               — debounced search with filters
      useEmbeddingMap.ts         — fetch and cache 2D projections
      useStats.ts                — governance dashboard stats
      useGovernanceQueue.ts      — review queue with pagination
      useActivityFeed.ts         — activity feed polling
    api/
      client.ts                  — base fetch wrapper
      skills.ts                  — skill endpoint functions
      capabilities.ts            — capability endpoint functions
      resolve.ts                 — unified resolution endpoint functions
      stats.ts                   — stats/governance endpoint functions
      activity.ts                — activity feed endpoint functions
    routes/
      index.tsx                  — TanStack Router route tree
      resolve.tsx                — / (Resolve View)
      explore.tsx                — /explore (Explore View)
      inspect.skill.tsx          — /skills/$slug (Skill Inspect)
      inspect.capability.tsx     — /capabilities/$slug (Capability Inspect)
      govern.tsx                 — /govern (Govern View)
    lib/
      fingerprint.ts             — cardinal spline math for fingerprint rendering
      embedding-map.ts           — D3 scale/zoom utilities for semantic landscape
      format.ts                  — score formatting, date formatting, etc.
    types/
      api.ts                     — TypeScript types mirroring API response shapes
```

---

## 8. Authentication (M6 Preview)

> **Out of scope for M5.** Authentication, authorization, and role-based access control are deferred to M6. All M5 views and endpoints are publicly accessible without authentication. This section is retained as a preview of M6 requirements to inform design decisions.
>
> See [Implementation Milestones](implementation-milestones.md) for the full M6 scope: OAuth login, JWT sessions, role-based access, API key management, and the foundation for M8 federation credential delegation.

### 8.1 M6 Auth Summary

- **OAuth providers**: GitHub (primary), Google (secondary)
- **Session management**: JWT access tokens (short-lived) + httpOnly refresh tokens
- **Roles**: `viewer` → `contributor` → `steward` → `admin` (hierarchy)
- **Gating**: Governance actions (review, promotion) require `steward` role; contribution requires `contributor` role; browse/resolve remain public
- **Database**: extends existing `users` table with `oauth_provider`, `oauth_id`, `display_name`, `avatar_url`, `last_login_at`

---

## 9. Sub-milestones

```
M5i (Foundation + Resolve) ──→ M5ii (Explore + Inspect)
                                        │
                                        ▼
                                 M5iii (Govern)
                                        │
                                        ▼
                                 M5iv (Polish + Contribution)
```

### M5i: Foundation + Resolve View

**Proves:** The resolution-first UX concept works. Users can resolve skills through a browser.

#### Project Setup
- [ ] Vite project scaffold with React 19 + TypeScript
- [ ] Tailwind CSS + shadcn/ui integration
- [ ] TanStack Router setup with route structure
- [ ] TanStack Query setup with API client layer
- [ ] Base layout: header navigation, responsive shell
- [ ] Type definitions mirroring existing API response shapes

#### Resolve View
- [ ] Hero search bar with debounced resolution (300ms)
- [ ] Primary result card with full detail
- [ ] Alternatives list with rejection rationale
- [ ] Context toggles: available_tools, trust_floor, cost_budget
- [ ] Resolution history (localStorage-backed)
- [ ] Loading states, empty states, error handling

#### Skill Fingerprint Component
- [ ] SVG-based 5-axis radar with cardinal spline interpolation
- [ ] Three sizes: thumbnail (32px), card (64px), hero (200px)
- [ ] Color intensity mapping to confidence
- [ ] Glow effect for behavioral score
- [ ] Interactive hover labels on hero size

#### Living Feed Sidebar
- [ ] Recent activity feed component
- [ ] Polling-based updates from skill/capability listing endpoints
- [ ] Collapsible on smaller viewports

### M5ii: Explore + Inspect

**Proves:** The registry is navigable as a spatial landscape and individual skills are deeply inspectable.

#### Semantic Landscape
- [ ] `GET /api/v1/embeddings/map` backend endpoint (UMAP/t-SNE projection job)
- [ ] D3/visx canvas with pan/zoom interaction
- [ ] Skill nodes with fingerprint thumbnails
- [ ] Capability nodes with edges to constituent skills
- [ ] Cluster labels from category names
- [ ] Visual encoding: trust tier → size, type → color, quality → opacity
- [ ] Search overlay: highlight matching nodes, fade others
- [ ] Click node → slide-out detail panel

#### Skill Inspect View
- [ ] Full skill detail layout: header, description, content preview
- [ ] Large interactive fingerprint with axis labels
- [ ] Eval history (scores over versions)
- [ ] Usage stats display (success rate, resolution count, avg runtime)
- [ ] Trust journey timeline
- [ ] Extends chain visualization
- [ ] `GET /api/v1/skills/{slug}/timeline` backend endpoint

#### Capability Inspect View
- [ ] React Flow diagram: steps as nodes, data flow as edges
- [ ] Step nodes expandable to show embedded skill content
- [ ] Required vs optional step visual distinction
- [ ] Aggregate trust tier display with per-step breakdown

#### Cross-View Navigation
- [ ] "Why This Works" section with eval evidence
- [ ] Alternatives comparison (two-column layout)
- [ ] Version diff view with triage classification

### M5iii: Govern

**Proves:** The registry's governance workflow is operational through a web interface. Auth is deferred to M6 — all governance views and actions are publicly accessible.

#### Govern Dashboard
- [ ] `GET /api/v1/stats/overview` backend endpoint
- [ ] `GET /api/v1/stats/eval-trends` backend endpoint
- [ ] `GET /api/v1/stats/usage-heatmap` backend endpoint
- [ ] Registry health cards: skill counts by tier, behavioral coverage, stale/deprecated
- [ ] Eval trends chart: composite score distribution over time
- [ ] Usage heatmap: resolution frequency by category x time

#### Review Queue + Interface
- [ ] `GET /api/v1/governance/queue` backend endpoint
- [ ] `POST /api/v1/governance/review` backend endpoint
- [ ] Queue list with filtering by reason
- [ ] Review interface: eval fragments, scores, injection indicators
- [ ] Action buttons: approve, reject, request changes (with required note)

#### Promotion + Breaking Changes
- [ ] Promotion queue with override controls
- [ ] Breaking change reports with capability impact details

### M5iv: Polish + Contribution

**Proves:** The full community contribution workflow is operational. The UI is production-quality.

#### Skill Submission
- [ ] New skill form: name, slug, description, content, dependencies, eval_spec
- [ ] Live validation: slug uniqueness, required fields, dependency format
- [ ] Content editor with markdown preview
- [ ] Eval spec builder: add/remove scenarios with input_context, success_criteria
- [ ] Submission status tracking: eval pipeline progress indicator

#### Amendment Submission
- [ ] Amendment form with current version displayed
- [ ] Side-by-side diff preview (current vs proposed)
- [ ] Amendment status tracking with triage classification result

#### Animations + Polish
- [ ] Framer Motion page transitions
- [ ] Layout animations on result changes
- [ ] Micro-interactions: fingerprint hover, trust badge transitions
- [ ] Skeleton loading states throughout

#### Responsive Design
- [ ] Desktop layout: full sidebar, multi-column
- [ ] Tablet layout: collapsible sidebar, single column
- [ ] Touch-friendly map interactions on tablet

#### Performance
- [ ] Route-based code splitting (TanStack Router lazy routes)
- [ ] Image and SVG optimization
- [ ] TanStack Query cache tuning (stale times, prefetching on hover)
- [ ] Embedding map data chunking for large registries

---

## 10. Security Considerations

### 10.1 Authentication & Authorization (M6)

> Auth is deferred to M6. In M5, all endpoints are publicly accessible. The following requirements apply once M6 is implemented:

- All API calls require authentication except browse and resolve operations (public read)
- Governance actions (review, promotion override) require `steward` role
- JWT tokens are validated on every request; refresh tokens use httpOnly, secure, sameSite cookies
- OAuth state parameter validated to prevent CSRF on auth flow

### 10.2 Content Security

- Skill content is NEVER rendered as raw HTML. All markdown is displayed as styled text using a safe renderer that strips HTML tags
- Content Security Policy (CSP) headers enforced: no inline scripts, no eval, restricted connect-src to API origin
- All user-provided content (skill names, descriptions, notes) is escaped before rendering

### 10.3 API Security

- CSRF protection on all state-changing operations (double-submit cookie pattern)
- Rate limiting on resolve endpoint (existing M4 rate limiter applies)
- Rate limiting on governance actions (prevent bulk approve/reject)
- API responses never include internal IDs or stack traces in production

### 10.4 Frontend Security

- No secrets in client-side code (M6: OAuth client IDs are public, secrets stay on the backend)
- Dependency audit in CI (npm audit)
- Subresource integrity (SRI) on CDN-served assets

### 10.5 Threat Matrix

| # | Threat | Impact | Mitigation |
|---|--------|--------|------------|
| 1 | XSS via skill content | Script execution in user's browser | Safe markdown renderer, CSP headers, no raw HTML rendering |
| 2 | CSRF on governance actions | Unauthorized review approvals | M5: unprotected (acceptable for dev). M6: double-submit cookie CSRF protection, sameSite cookies |
| 3 | OAuth token theft (M6) | Session hijacking | M6: httpOnly refresh tokens, short-lived access tokens, secure flag |
| 4 | Clickjacking | Governance actions triggered by invisible overlay | X-Frame-Options: DENY, CSP frame-ancestors: none |
| 5 | Embedding map data poisoning | Misleading spatial relationships | Map projections computed server-side from verified embeddings; no client-side embedding input |
| 6 | Review queue manipulation | Steward tricked into approving malicious skill | Full eval context shown in review interface; injection flags prominently displayed |

---

## 11. Deployment

### 11.1 Build

- Vite production build produces static assets (HTML, JS, CSS)
- Output directory served by CDN or static file server
- Environment variables for API base URL injected at build time

### 11.2 Development

- `npm run dev` starts Vite dev server with HMR
- API proxy configured in Vite to forward `/api/` requests to the FastAPI backend
- Mock data layer for offline development (optional)

### 11.3 CI

- Type checking: `tsc --noEmit`
- Linting: ESLint with strict TypeScript rules
- Unit tests: Vitest
- Component tests: Vitest + Testing Library
- Build verification: `vite build` succeeds with zero warnings

---

## 12. Future Vision: Federation & Execution Authority

> This section captures architectural direction beyond M5. It is not in scope for this milestone but informs design decisions — particularly around auth, which deserves its own milestone.

### 12.1 The Trajectory

**Today (M1-M5)**: Loom is a **resolution layer** — agents describe a task, Loom returns instructions (markdown), the agent executes locally.

**Future**: Loom becomes an **execution authority** — agents describe a task, Loom routes the request to the right downstream agent or MCP service, orchestrates execution, and returns results. Loom evolves from DNS-for-capabilities to a capability broker.

### 12.2 What Federation Requires

When Loom brokers execution rather than just returning instructions:

- **Credential delegation** — Loom passes auth tokens to downstream MCP services on behalf of the requesting agent. The requesting agent never directly authenticates with the downstream service.
- **Scope boundaries** — a request for "review my PR" must not grant access to "deploy to production" even if the same MCP service handles both. Scopes are per-resolution, not per-service.
- **Trust chain** — the requesting agent trusts Loom, Loom trusts the downstream service, the service trusts the delegated credentials. Each link in the chain is independently verifiable.
- **Audit trail** — who requested what, which service executed it, what credentials were used, what the outcome was. Full provenance for every federated execution.
- **Billing/metering** — if Loom routes to a paid service, the cost must be attributed to the requesting org/user. This connects to the economic metadata already in the skill model (cost_profile, cost_drivers).

### 12.3 Auth as Its Own Milestone (M6)

Auth is not a feature bolted onto the UI — it's a cross-cutting concern that affects every layer:

| Layer | Auth Impact |
|-------|-------------|
| **Web UI** | OAuth login, role-based view access, steward tools |
| **API** | JWT tokens, API key management, per-org rate limits |
| **MCP** | Agent identity, credential delegation to downstream services |
| **Resolution** | Org-scoped `corp://` URIs, private skill visibility |
| **Evaluation** | Author reputation, contribution history, account standing |
| **Federation** | Trust chains, scope delegation, credential brokering |

M6 should design auth with federation in mind from the start, even if federation itself is a later milestone. The auth model must support:
- Individual identity (GitHub/Google OAuth)
- Org membership and isolation
- API key management for agent access
- Role hierarchy (viewer → contributor → steward → admin)
- Scope-based permissions (per-skill, per-category, per-org)
- Credential delegation primitives (for future federation)

---

## 13. Known Issues & Backlog

### 13.1 Dependency Schema: Prerequisites vs MCP Servers

**Problem**: The `dependencies.mcp_servers` field is currently overloaded. Seed data declares items like `filesystem` and `git` as MCP servers, but these are really **environment prerequisites** — the skill needs file system access or a git repo, not an actual MCP server endpoint.

**Impact**: The UI displays "MCP Servers: filesystem, git" which is misleading. The schema conflates three distinct concepts:
1. **MCP Servers** — actual MCP server endpoints the skill calls (e.g. `github-mcp`, `slack-mcp`)
2. **Environment prerequisites** — capabilities of the host environment (file system access, git, network)
3. **CLI tools** — specific executables the skill invokes (e.g. `ruff`, `pytest`, `docker`)

**Proposed fix (schema)**:
- Rename/restructure `DependencyDeclaration` to separate these:
  - `mcp_servers`: actual MCP server URIs
  - `prerequisites`: environment requirements (`filesystem`, `git`, `network`, `docker`, etc.)
  - `tools`: specific CLI tools with optional version constraints
- Requires: model change, migration, seed data update, API response update, frontend update

**Proposed fix (eval pipeline)**:
- During static analysis, **scan skill content** for actual tool usage (shell commands, file operations, API calls, MCP tool invocations)
- **Verify** declared dependencies match what the skill actually uses
- **Discover** undeclared dependencies and flag them (e.g. skill runs `git log` but didn't declare `git`)
- **Reject or warn** on skills with undeclared dependencies that could affect trust scoring

**Priority**: Medium — affects correctness of dependency display and trust assessment. Should be addressed before M6 (auth) since dependency declarations feed into trust decisions.

### 13.2 Seed Data Quality

The current seed skills/capabilities are minimal bootstrap data. Before wider release:
- Review all dependency declarations for accuracy
- Ensure skill content follows consistent markdown structure
- Add more diverse examples across categories
- Eventually: automated ingestion from the wider internet with quality gates

### 13.3 Semantic Map: Pre-compute & Cache UMAP Coordinates

**Problem**: The embedding map currently recomputes UMAP on every page load via `GET /api/v1/embeddings/map`. This is O(n²) and will not scale beyond a few hundred skills.

**Proposed fix**:
1. **Pre-compute**: Run UMAP when skills are submitted/updated and store `(x, y)` coordinates in the DB (new columns on skills/capabilities tables, or a dedicated `embedding_coordinates` table)
2. **Serve cached**: The map endpoint returns pre-computed coordinates — no UMAP at request time
3. **Recompute triggers**: New skill submitted, skill embedding updated, periodic batch job (e.g. nightly), or manual admin trigger
4. **Incremental updates**: For small additions, consider approximate projection of new points into existing UMAP space rather than full recomputation

**Priority**: Medium — works fine for current scale (~20 items) but will break at ~500+.

---

## 14. Versioning & Provenance — Assessment and Roadmap

### 14.1 Current State

The versioning system follows an **immutable-append model** (like Git):
- `skills` table: always reflects the latest version (denormalized for fast reads)
- `skill_versions` table: immutable historical record of every version, with full content snapshots
- Unique constraint on `(skill_id, version)` prevents duplicate versions
- Same pattern for capabilities via `capability_versions`

**What's wired up today:**
| Aspect | Status | Notes |
|--------|--------|-------|
| Version history | ✅ | `skill_versions` table with full content snapshots |
| Eval per version | ✅ | `eval_jobs.skill_version` ties eval to specific version |
| Usage per version | ✅ | `usage_reports.skill_version` tracks per-version usage |
| Version pinning in API | ✅ | `GET /skills/{slug}?version=X` returns specific version |
| Version pinning in extends | ✅ | `loom://slug@version` syntax in extends URIs |
| Cryptographic signing | ✅ | ed25519 signing of `(content, version, deps, eval_spec)` canonical hash |
| Author tracking | ✅ | `author_id` FK on both skills and skill_versions |
| Comparative eval | ✅ | Stores `skill_a_version` + `skill_b_version` for head-to-head |

### 14.2 Gaps — Versioning

**Gap V1: No version format validation**
Versions are plain strings with no validation. Clients can submit "1", "banana", "v1.0-rc". We should enforce semantic versioning (major.minor.patch) to enable version comparison and compatibility reasoning.

**Gap V2: Embeddings are per-skill, not per-version**
The `skills.embedding` column stores a single vector overwritten on each update. If a skill's content changes significantly between v1 and v2, vector search can't distinguish them. For version-aware resolution, we need per-version embeddings — either a new `skill_version_embeddings` table or adding an embedding column to `skill_versions`.

**Gap V3: No "active version" concept**
The `skills` table always reflects the latest version. If v3 introduces a regression, there's no way to "roll back" — you'd have to publish v4 with the v2 content. We should add an `active_version` field to the `skills` table, distinct from `latest_version`, allowing a maintainer to pin the recommended version.

**Gap V4: Deprecation is skill-level, not version-level**
`deprecated_at` and `successor_slug` live on the `skills` table. Can't express "v1 is deprecated, use v2" — only "entire skill is deprecated, use this other skill". Should add version-level deprecation (on `skill_versions` table or a new `version_deprecations` table).

**Gap V5: No version constraints in extends/capabilities**
If a capability step references `loom://foo` (no version pin), it silently gets whatever version is current. If `loom://foo@1.0.0` is pinned but v2.0.0 exists, no warning is raised. We need:
- Default pinning: when a capability is created, resolve unpinned refs to the current version and record them
- Staleness detection: warn when pinned versions are outdated
- Compatibility markers: `breaking_change: true` on version records that aren't backward-compatible

**Gap V6: No version ordering or comparison**
Without semver parsing, the system can't determine if v2.0.0 > v1.5.3, whether an update is a major/minor/patch bump, or whether two versions are compatible. This matters for:
- Auto-updating capability step references on minor/patch bumps
- Blocking auto-updates on major bumps (breaking changes)
- Sorting version history chronologically (currently relies on `created_at`, not version number)

### 14.3 Gaps — Provenance

**What exists:**
- `author_id` on skills and versions (tracks who authored each version)
- `signature` + `signature_key_fingerprint` for cryptographic provenance (ed25519)
- `content_hash` on eval jobs (snapshot of what was evaluated)
- `changelog` on version records

**Gap P1: No source tracking for external skills**
There's no `source_uri` field to record where a skill came from (GitHub repo, ClawHub, manual authoring). Critical for:
- Re-fetching/syncing from upstream sources
- Deduplication across ingestion runs
- Trust assessment (a skill from a reputable GitHub repo vs an anonymous submission)
- Audit trail for the living feed

**Proposed schema addition** (`ingestion_sources` table):

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `source_type` | text | `github`, `manual`, `clawhub`, `skillsmp` |
| `source_uri` | text | e.g. `github:owner/repo/path@commitsha` |
| `content_hash` | text | SHA-256 of raw source content |
| `skill_id` | UUID | FK → skills |
| `skill_version` | text | Version created from this source |
| `ingested_at` | timestamptz | When we fetched it |
| `raw_metadata` | JSONB | Source-specific metadata (repo stars, last commit date, license, etc.) |

Plus a `source_uri` column on the `skills` table (nullable — null for manually authored skills).

**Gap P2: No content integrity chain**
The signing service exists but isn't wired into the submission flow — skills can be submitted without signatures. For a trust-based system, we should:
- Make signing optional but tracked (signed vs unsigned is a trust signal)
- Verify signatures on read if present
- Include signature status in the eval pipeline's trust assessment

**Gap P3: No license/attribution tracking**
When ingesting from GitHub, we need to respect and record the source license. Should add `license` field to skills and ingestion sources.

### 14.4 Recommended Priority

**Before ingestion pipeline (Chunk 3 of current plan):**
1. P1: Add `source_uri` to skills + `ingestion_sources` table (migration)
2. V1: Add semver validation on skill creation/update

**Before wider release:**
3. V3: Add `active_version` concept (decouple from `latest_version`)
4. V4: Version-level deprecation
5. V2: Per-version embeddings
6. P3: License tracking

**Future (M6+ timeframe):**
7. V5: Version constraints in extends/capabilities
8. V6: Semver comparison and compatibility logic
9. P2: Signature enforcement and verification in eval pipeline

---

## 15. Skill Disambiguation & Resolution Quality

### 15.1 Problem

When hundreds of skills share a domain (e.g., "supabase"), they cluster tightly in embedding space. A query like "implement supabase auth" matches dozens of skills at similar scores, making resolution unreliable.

Root causes:
1. **Embedding full content** dilutes the discriminative signal — two skills that differ in purpose but share 80% boilerplate text embed nearly identically
2. **Flat retrieval** — vector search returns a ranked list with no structural pre-filtering
3. **No ingestion-time dedup** — near-duplicates slip through (thresholds exist but aren't wired in)
4. **Resolver doesn't surface ambiguity** — silently picks one when top candidates are indistinguishable

### 15.2 Discriminative Embedding (Phase A — implement now)

**Change what we embed.** Instead of embedding the full markdown content, embed:

```
{name} — {description}
```

This pushes similar-domain-but-different-purpose skills apart in embedding space. "Set up Supabase Row-Level Security policies for multi-tenant apps" embeds very differently from "Configure Supabase Edge Functions with Deno runtime".

**Implementation:**
- Change `get_embedding()` in seed/ingestion to embed `f"{name} — {description}"` instead of `content`
- Store the embedding input text on the record for debuggability

### 15.3 Eval-Time Rewrite — `indexability` dimension (Phase B)

Author-provided names/descriptions are often vague, duplicative, or marketing-speak. During evaluation, an LLM agent should rewrite the embedding text for optimal retrieval:

**Input to the rewrite agent:**
1. Full skill content
2. Author-provided name + description
3. Nearest 5 existing skills' descriptions (distinctiveness requires context)

**Output:**
- `display_name`: human-friendly (what the UI shows)
- `embedding_text`: optimized for vector search, includes negative framing ("does NOT cover X") to push similar skills apart
- `disambiguation_note`: "Unlike skill X, this one specifically handles Y"

**Example:**
```
Author says: "Supabase Auth"
Eval rewrites: "Implement Supabase email/password authentication with
signup confirmation flow, password reset, and session management.
Does NOT cover OAuth, magic links, or SSO."
```

This becomes a new eval dimension (`indexability`) alongside clarity/completeness/safety/correctness. The output is both a 0-1 score and the rewritten embedding text itself.

**Schema changes needed:**
- Add `embedding_text` column to `skills` (what was actually embedded)
- Add `display_name` column or just overwrite `name` with eval-approved version
- Store `disambiguation_note` in eval results

### 15.4 Semantic Dedup at Ingestion (Phase A — implement now)

Wire the existing thresholds into the ingestion pipeline:

| Similarity to existing skill | Action |
|---|---|
| ≥ 0.95 | Auto-reject as duplicate |
| 0.85 – 0.95 | Flag for review — require distinctiveness justification |
| 0.70 – 0.85 | Accept, link as `related_skills` |
| < 0.70 | Accept freely |

At ingestion time:
1. Compute embedding of the new skill's `name + description`
2. Find k-nearest existing skills by embedding similarity
3. If above warn threshold, generate comparative analysis
4. Use analysis to reject, merge, or accept with distinctiveness metadata

### 15.5 Layered Resolution (Phase B)

Replace flat vector search with layered retrieval:

```
Query → Category narrowing (keyword + tag match)
      → Vector search within category (discriminative embedding)
      → LLM re-rank (sees descriptions + tags + categories)
      → Single best match OR alternatives if ambiguous
```

When the resolver's top candidates are within a tight similarity band (top-3 within 0.05 of each other), return alternatives with a disambiguation prompt rather than silently picking one.

### 15.6 Feedback Loop (Phase C — ongoing)

- Track resolution → usage conversion (resolved but never used = bad match)
- Surface "frequently confused" skill pairs for manual review/merge
- Use rejection data from the living feed to tune thresholds
- Periodically re-run indexability eval when new similar skills are added

### 15.7 Package Evaluation (Phase B/C)

Many openclaw skills include scripts, references, and test data alongside SKILL.md. Current eval treats skills as prose. Planned additions:

1. Clone skill directory from `source_uri` into temp sandbox
2. Parse manifest files (requirements.txt, package.json) if present
3. Install deps + run included tests
4. Validate referenced scripts/files exist
5. New eval dimension: `executability` (0-1 score)

### 15.8 Priority

**Phase A (now, during M5 ingestion):**
1. Embed `name — description` instead of full content
2. Wire semantic dedup into ingestion pipeline

**Phase B (M6):**
3. Indexability eval dimension with LLM rewrite
4. Layered resolution with category pre-filtering
5. Alternatives response when ambiguous
6. Package validation in sandbox

**Phase C (M7+):**
7. Feedback loop: resolution → usage tracking
8. Automated skill pair merging/splitting
9. Periodic re-indexing as catalog grows

---

## 16. Audit & Provenance for Mutations

### 16.1 Problem

As the platform matures, skill text will be modified by multiple agents:
- **Eval pipeline**: rewrites name/description for indexability
- **Admin**: manual corrections, merges, content edits
- **Auto-merge**: combining near-duplicate skills
- **Ingestion re-sync**: upstream source changed

Every mutation must be auditable. The original author's text must always be recoverable. Without this, we lose trust — a skill author can't verify what happened to their submission, and the governance dashboard can't show a meaningful change history.

### 16.2 Design Principle: Immutable Version Chain

The existing `skill_versions` table stores full content snapshots per version. We extend this with **mutation metadata** so each version record answers five questions:

1. **What** changed? (diff summary)
2. **Who** changed it? (agent identity)
3. **When**? (timestamp — already have `created_at`)
4. **Why**? (rationale)
5. **How**? (change type — manual, automated, pipeline)

### 16.3 Schema Addition: Version Provenance

Add columns to `skill_versions`:

| Column | Type | Notes |
|--------|------|-------|
| `change_type` | text | `author_submission`, `eval_rewrite`, `admin_edit`, `auto_merge`, `ingestion_sync`, `deprecation` |
| `change_agent` | text | Identifier: user UUID, `eval-pipeline/indexability`, `ingestion-bot`, `admin/{user_id}` |
| `change_rationale` | text | Human-readable reason: "Rewritten for disambiguation — 3 similar skills detected" |
| `diff_summary` | JSONB | `{"fields_changed": ["description", "name"], "old_values": {"description": "..."}}` |
| `parent_version` | text | The version string this was derived from (null for initial submission) |

### 16.4 Change Types

| Type | Trigger | Agent | Example |
|------|---------|-------|---------|
| `author_submission` | Skill created or updated by author | User UUID | Initial publish or version bump |
| `eval_rewrite` | Eval pipeline modifies name/description/embedding_text | `eval-pipeline/{dimension}` | Indexability rewrite for disambiguation |
| `admin_edit` | Manual edit via governance UI | `admin/{user_id}` | Fix typo, add missing tag |
| `auto_merge` | Two skills merged by dedup pipeline | `dedup-pipeline` | Near-duplicate merged, content combined |
| `ingestion_sync` | Re-ingestion detects upstream changes | `ingestion-bot` | Source repo updated |
| `deprecation` | Skill deprecated in favour of another | User or pipeline | Superseded by better version |

### 16.5 Logging & Storage Strategy

**What to log (structured, queryable):**
- Version provenance (above) — stored in DB, powers governance UI timeline
- Eval results per version — already stored in `eval_jobs`
- Resolution events — already stored in `resolution_logs`

**What to log (operational, ephemeral):**
- API request traces — structured logging (JSON) to stdout, shipped to log aggregator
- Embedding generation calls — duration, model, input length
- Scraper activity — repos scanned, files fetched, rate limits hit

**What NOT to store in the DB:**
- Full API request/response bodies (too large, use log aggregator)
- Intermediate eval pipeline state (only final results matter)
- Raw scraped content before transformation (reconstruct from `source_uri`)

### 16.6 Governance UI Integration

The living feed and skill detail pages should surface mutation history:

```
v1.0.0  [author_submission]  alice@example.com  "Initial publish"
v1.0.1  [eval_rewrite]       eval-pipeline      "Description rewritten for disambiguation"
v1.1.0  [admin_edit]         admin/bob           "Added missing safety warning for API key handling"
```

Each entry links to the full diff and the eval results for that version.

### 16.7 Priority

**Must have before any text mutation feature ships (M6):**
1. Add `change_type`, `change_agent`, `change_rationale`, `diff_summary`, `parent_version` to `skill_versions`
2. Populate `change_type=author_submission` for all existing creation flows
3. Governance UI shows version timeline with change metadata

**Before M7:**
4. Eval pipeline writes `eval_rewrite` versions with full provenance
5. Ingestion re-sync creates `ingestion_sync` versions
6. Admin edit UI creates `admin_edit` versions

---

## 17. Two-Pass Ingestion Pipeline

### 17.1 Overview

Ingestion is split into two distinct passes to separate cheap bulk import from expensive LLM-powered vetting:

```
                    PASS 1: Ingest + Gate                    PASS 2: Vet + Enrich
                    (bulk, no LLM, fast)                     (batch, LLM-powered)

Scrape → Transform → Cheap Gates → Persist as 'unvetted'    Pick unvetted → LLM Meta Rewrite
                      ├── Content hash dedup                                 ├── Name / description
                      ├── Slug collision                                     ├── Embedding text
                      ├── Min content length                                 ├── Eval scenarios
                      ├── Injection pattern scan                             ├── Category / tags
                      └── Basic structure check                              └── Disambiguation note
                                                             → Full Eval Pipeline
                                                               ├── Clarity
                                                               ├── Completeness
                                                               ├── Safety
                                                               ├── Correctness
                                                             → Semantic Dedup (embedding similarity)
                                                             → Pass? → Promote to 'candidate'
                                                             → Fail? → Mark as 'rejected'
```

### 17.2 Trust Tier Progression

Add `unvetted` as the new entry point before the existing tiers:

```
unvetted → submitted → candidate → promoted
                ↘          ↘          ↘
              rejected   rejected   deprecated
```

| Tier | Meaning | Visible in search/resolve? | How you get here |
|------|---------|---------------------------|------------------|
| `unvetted` | Ingested, passed cheap gates only | No | Pass 1 bulk import |
| `submitted` | Passed LLM meta rewrite, has real eval scenarios | No | Pass 2 meta rewrite complete |
| `candidate` | Passed full eval pipeline | Yes | Pass 2 eval pass |
| `promoted` | High usage + consistently good eval scores | Yes (prioritised) | Automated promotion |
| `rejected` | Failed gates or eval | No (visible in governance) | Any stage failure |
| `deprecated` | Superseded by another skill | Yes (with warning) | Manual or auto |

Key rule: **the resolver and search endpoints only return `candidate` or `promoted` skills.** Unvetted and submitted skills exist in the DB for governance/admin but are invisible to consumers.

### 17.3 Pass 1: Cheap Gates (no LLM)

These run during `ingest.py --approve` and filter out obvious junk:

| Gate | Check | Reject threshold |
|------|-------|-----------------|
| **Content hash dedup** | SHA-256 of normalized content | Exact match → skip |
| **Slug collision** | Existing skill with same slug | Same source → skip, different source → suffix |
| **Min content length** | `len(content.strip())` | < 100 chars → reject |
| **Max content length** | `len(content)` | > 50,000 chars → reject |
| **Injection patterns** | 11 regex patterns from static_analyser | Any match → reject |
| **Structure check** | Has at least one heading or paragraph | No structure → reject |

Skills that pass all gates are persisted with `trust_tier = 'unvetted'`, no embedding, no eval.

### 17.4 Pass 2: LLM Meta Rewrite + Eval

Runs as a batch job (`scripts/vet.py` or worker task), processing unvetted skills:

**Step 1: Meta Rewrite (new)**
- Input: full skill content + nearest 5 existing vetted skills' descriptions
- LLM generates:
  - `display_name`: clean, descriptive name
  - `description`: what the skill does, when to use it, what it does NOT do
  - `embedding_text`: optimized for discriminative vector search
  - `eval_scenarios`: 3-5 meaningful test scenarios derived from content
  - `category_slug`: proper categorization
  - `tags`: relevant tags
  - `disambiguation_note`: how this differs from similar existing skills
- Output stored as a new version with `change_type = 'eval_rewrite'`

**Step 2: Semantic Dedup**
- Generate embedding from the rewritten `embedding_text`
- Compare against all existing vetted skills
- \> 0.95 similarity → reject as duplicate, link to existing
- 0.85 – 0.95 → flag for human review in governance dashboard
- < 0.85 → proceed

**Step 3: Full Eval Pipeline (existing)**
- Run the existing 5-phase eval using the generated eval scenarios
- Score clarity, completeness, safety, correctness
- Apply pass/fail thresholds

**Step 4: Promotion**
- Pass → update `trust_tier` to `candidate`, persist embedding, now searchable
- Fail → update `trust_tier` to `rejected`, store reason

### 17.5 Batch Processing Strategy

- Process unvetted skills oldest-first (FIFO)
- Configurable batch size (default: 50 per run)
- Rate limit LLM calls (respect provider limits)
- Resumable: tracks progress via `trust_tier` state
- Can run as: manual CLI (`scripts/vet.py --batch 50`), arq worker job, or cron

### 17.6 Implementation Priority

**Now (M5):**
1. Remove auto-generated eval_spec from transformer (revert placeholder)
2. Skip eval validation for ingestion (allow empty eval_spec for `unvetted` tier)
3. Persist ingested skills as `unvetted` — no embedding, no eval
4. Update resolver/search to filter out `unvetted` and `submitted`

**Next (M6):**
5. Build `scripts/vet.py` with LLM meta rewrite
6. Implement semantic dedup in vetting pass
7. Wire into eval pipeline for full scoring
8. Governance dashboard shows vetting queue + rejection reasons
