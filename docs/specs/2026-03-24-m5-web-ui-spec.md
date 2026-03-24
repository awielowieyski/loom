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
| Data viz | D3.js / visx | Semantic landscape map, skill fingerprint polygons |
| Animation | Framer Motion | Layout animations, page transitions, micro-interactions |
| Data fetching | TanStack Query v5 | Cache management, background refetching, optimistic updates |
| Routing | TanStack Router | Type-safe routing, search param validation, code splitting |
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

The Govern View is restricted to authenticated users with the `steward` role. It provides registry health observability and human review workflows.

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

Data source: polling `GET /api/v1/skills?sort=created_at&limit=20` and related endpoints. Future enhancement: WebSocket for real-time push.

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
| `POST /api/v1/skills/resolve` | Resolve View (live resolution) |
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
| `POST /api/v1/capabilities/resolve` | Resolve View (capability resolution) |
| `GET /api/v1/categories` | Explore View (category labels) |
| `POST /api/v1/usage/report` | Contribution (usage reporting) |

### 6.2 New Endpoints Required

These endpoints provide data that does not exist in M1-M4 and must be implemented as part of M5:

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

Requires `steward` role.

#### `POST /api/v1/governance/review`

Submit a review decision on a queued item.

```json
{
  "queue_item_id": "uuid",
  "decision": "approve|reject|request_changes",
  "note": "Free text explanation for the decision"
}
```

Returns 200 with the updated item. Requires `steward` role.

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
        SemanticMap.tsx            — D3/visx canvas with pan/zoom
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
        GovernView.tsx            — page container (auth-gated)
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
      useAuth.ts                 — authentication state and role checks
    api/
      client.ts                  — base fetch wrapper with auth headers
      skills.ts                  — skill endpoint functions
      capabilities.ts            — capability endpoint functions
      resolve.ts                 — resolution endpoint functions
      stats.ts                   — stats/governance endpoint functions
      auth.ts                    — OAuth flow functions
    routes/
      index.tsx                  — TanStack Router route tree
      resolve.tsx                — / (Resolve View)
      explore.tsx                — /explore (Explore View)
      inspect.skill.tsx          — /skills/$slug (Skill Inspect)
      inspect.capability.tsx     — /capabilities/$slug (Capability Inspect)
      govern.tsx                 — /govern (Govern View, auth-gated)
    lib/
      fingerprint.ts             — cardinal spline math for fingerprint rendering
      embedding-map.ts           — D3 scale/zoom utilities for semantic landscape
      format.ts                  — score formatting, date formatting, etc.
    types/
      api.ts                     — TypeScript types mirroring API response shapes
      auth.ts                    — user, role, session types
```

---

## 8. Authentication

### 8.1 OAuth Providers

- **GitHub**: primary provider for developer contributors
- **Google**: secondary provider for broader access

OAuth flow: standard authorization code flow. The SPA redirects to the provider, receives a code on callback, exchanges it for a JWT via the backend.

### 8.2 Backend Auth Endpoints (New)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/auth/github` | Redirect to GitHub OAuth |
| `GET` | `/api/v1/auth/github/callback` | Exchange code for JWT |
| `GET` | `/api/v1/auth/google` | Redirect to Google OAuth |
| `GET` | `/api/v1/auth/google/callback` | Exchange code for JWT |
| `GET` | `/api/v1/auth/me` | Current user profile + role |
| `POST` | `/api/v1/auth/logout` | Invalidate session |

### 8.3 JWT Tokens

- Short-lived access tokens (15 minutes) stored in memory
- Refresh tokens (7 days) stored in httpOnly cookies
- Token refresh handled transparently by the API client layer

### 8.4 Roles

| Role | Permissions |
|------|------------|
| `viewer` | Browse, resolve, search — all read operations |
| `contributor` | All viewer permissions + submit skills, submit amendments, report usage |
| `steward` | All contributor permissions + governance queue, review actions, promotion overrides |

Anonymous (unauthenticated) users can browse and resolve. Authentication is required only for contribution and governance.

### 8.5 Database

Uses the existing `users` table from M1. New columns:

| Column | Type | Notes |
|--------|------|-------|
| `oauth_provider` | VARCHAR(20) | `github`, `google` |
| `oauth_id` | TEXT | Provider-specific user ID |
| `display_name` | TEXT | From OAuth profile |
| `avatar_url` | TEXT | From OAuth profile |
| `role` | VARCHAR(20) | `viewer`, `contributor`, `steward` |
| `last_login_at` | TIMESTAMPTZ | Updated on each login |

Unique constraint: `(oauth_provider, oauth_id)`.

---

## 9. Sub-milestones

```
M5i (Foundation + Resolve) ──→ M5ii (Explore + Inspect)
                                        │
                                        ▼
                                 M5iii (Govern + Auth)
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

### M5iii: Govern + Auth

**Proves:** Stewards can govern the registry through a web interface. OAuth enables human identity.

#### OAuth Login Flow
- [ ] GitHub OAuth provider integration (backend + frontend)
- [ ] Google OAuth provider integration (backend + frontend)
- [ ] JWT token management (access + refresh)
- [ ] Auth state hook with role checks
- [ ] Login/logout UI in header
- [ ] `users` table migration: `oauth_provider`, `oauth_id`, `display_name`, `avatar_url`, `role`, `last_login_at`
- [ ] Auth middleware for role-gated endpoints

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

### 10.1 Authentication & Authorization

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

- No secrets in client-side code; OAuth client IDs are public, secrets stay on the backend
- Dependency audit in CI (npm audit)
- Subresource integrity (SRI) on CDN-served assets

### 10.5 Threat Matrix

| # | Threat | Impact | Mitigation |
|---|--------|--------|------------|
| 1 | XSS via skill content | Script execution in user's browser | Safe markdown renderer, CSP headers, no raw HTML rendering |
| 2 | CSRF on governance actions | Unauthorized review approvals | Double-submit cookie CSRF protection, sameSite cookies |
| 3 | OAuth token theft | Session hijacking | httpOnly refresh tokens, short-lived access tokens, secure flag |
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
