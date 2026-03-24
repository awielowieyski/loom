# M5: Web UI — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a resolution-first web UI for the Loom registry: a Vite + React 19 SPA with four views (Resolve, Explore, Inspect, Govern), skill fingerprint visualizations, a semantic landscape map, and a governance dashboard. Auth is deferred to M6 — all views are public and accessible without authentication.

**Architecture:** Standalone Vite SPA in `/web` directory, talking to the existing FastAPI backend via proxy. TanStack Router for type-safe routing, TanStack Query for data fetching, Tailwind CSS + shadcn/ui for styling, D3/visx for data visualization, React Flow for capability pipeline diagrams, Framer Motion for animations. Four new backend endpoints provide data not available in M1-M4: embedding map, stats overview, eval trends, usage heatmap, governance queue, governance review, and skill timeline.

**Tech Stack:**
- React 19 + TypeScript + Vite
- Tailwind CSS + shadcn/ui
- TanStack Router v1 + TanStack Query v5
- D3.js / visx (semantic map, fingerprint)
- React Flow (capability flow diagrams)
- Framer Motion (animations)
- Recharts (charts in Govern view)
- Vitest + Playwright (testing)

**Spec references:**
- [M5 Web UI Spec](../../specs/2026-03-24-m5-web-ui-spec.md)
- [Loom Design Spec](../../specs/2026-03-21-loom-design.md)
- [Implementation Milestones](../../specs/implementation-milestones.md)

**Auth note:** Auth is deferred to M6. The Govern view is accessible to anyone. Governance actions (approve/reject) are unprotected — this is acceptable for development and will be gated in M6.

---

## Chunk 1: Project Scaffold (M5i Foundation)

---

### Task 1: Vite + React 19 + TypeScript Project

**Files:**
- Create: `web/` directory (via `npm create vite@latest`)
- Create: `web/postcss.config.js`
- Create: `web/tailwind.config.ts`
- Modify: `web/vite.config.ts` (add API proxy)
- Create: `.claude/launch.json` (dev server config)
- Modify: `web/package.json` (add dependencies)

- [ ] **Step 1: Scaffold Vite project**

```bash
cd /Users/adam/Projects/loom
npm create vite@latest web -- --template react-ts
cd web && npm install
```

- [ ] **Step 2: Install core dependencies**

```bash
cd /Users/adam/Projects/loom/web
npm install @tanstack/react-router @tanstack/react-query tailwindcss @tailwindcss/vite
npm install framer-motion recharts reactflow @xyflow/react
npm install react-markdown remark-gfm
npm install clsx tailwind-merge class-variance-authority lucide-react
npm install -D @types/d3 d3 visx prettier eslint @eslint/js typescript-eslint
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

- [ ] **Step 3: Configure Tailwind CSS**

Set up `tailwind.config.ts` with:
- Dark mode support (`class` strategy)
- Custom color palette (blue family for skills, amber for capabilities)
- Custom font configuration

Add Tailwind directives to `web/src/index.css`.

- [ ] **Step 4: Configure Vite proxy**

Update `web/vite.config.ts`:

```typescript
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

- [ ] **Step 5: Configure `.claude/launch.json`**

Create `.claude/launch.json`:

```json
{
  "version": "0.0.1",
  "configurations": [
    {
      "name": "web-dev",
      "runtimeExecutable": "npm",
      "runtimeArgs": ["run", "dev"],
      "port": 5173,
      "cwd": "web"
    }
  ]
}
```

- [ ] **Step 6: Configure ESLint + Prettier**

Create `web/.prettierrc` and `web/eslint.config.js` with TypeScript strict rules.

- [ ] **Step 7: Verify**

Run: `cd /Users/adam/Projects/loom/web && npm run dev`
Expected: Dev server starts on port 5173, serves default Vite page.

Run: `cd /Users/adam/Projects/loom/web && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 8: Commit**

```bash
git add web/ .claude/launch.json
git commit -m "feat(m5): scaffold Vite + React 19 + TypeScript project with Tailwind, TanStack, and dev tooling"
```

---

### Task 2: Base Layout + Routing

**Depends on:** Task 1

**Files:**
- Create: `web/src/routes/__root.tsx`
- Create: `web/src/routes/index.tsx` (Resolve View — `/`)
- Create: `web/src/routes/explore.tsx` (`/explore`)
- Create: `web/src/routes/skills.$slug.tsx` (`/skills/$slug`)
- Create: `web/src/routes/capabilities.$slug.tsx` (`/capabilities/$slug`)
- Create: `web/src/routes/govern.tsx` (`/govern`)
- Create: `web/src/components/layout/AppShell.tsx`
- Create: `web/src/components/layout/Header.tsx`
- Create: `web/src/components/layout/Sidebar.tsx`
- Modify: `web/src/main.tsx`

- [ ] **Step 1: Set up TanStack Router**

Create route tree with file-based routing convention:
- `__root.tsx` — AppShell layout (Header + main + sidebar slot)
- `index.tsx` — Resolve View (homepage, `/`)
- `explore.tsx` — Explore View (`/explore`)
- `skills.$slug.tsx` — Skill Inspect (`/skills/:slug`)
- `capabilities.$slug.tsx` — Capability Inspect (`/capabilities/:slug`)
- `govern.tsx` — Govern View (`/govern`)

- [ ] **Step 2: Create AppShell component**

Layout structure:
- Header: logo/title, nav links (Resolve, Explore, Govern), active state indicator
- Main content area: `<Outlet />` from router
- Right sidebar slot: for Living Feed (implemented in Task 10)
- Responsive: sidebar collapses on tablet/mobile

- [ ] **Step 3: Create Header component**

- Navigation links: Resolve (`/`), Explore (`/explore`), Govern (`/govern`)
- Active link highlighting via TanStack Router's `useMatchRoute`
- Dark mode toggle button (Tailwind `dark` class on `<html>`)
- Responsive hamburger menu for mobile

- [ ] **Step 4: Create placeholder pages**

Each route file renders a placeholder with the view name. These will be replaced in subsequent tasks.

- [ ] **Step 5: Verify**

Run: `cd /Users/adam/Projects/loom/web && npm run dev`
Expected: Navigation between all routes works, active states update, URL changes correctly.

Run: `cd /Users/adam/Projects/loom/web && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 6: Commit**

```bash
git add web/src/
git commit -m "feat(m5): app shell layout with TanStack Router and responsive navigation"
```

---

### Task 3: API Client Layer + TypeScript Types

**Depends on:** Task 1

**Files:**
- Create: `web/src/api/client.ts`
- Create: `web/src/api/skills.ts`
- Create: `web/src/api/capabilities.ts`
- Create: `web/src/api/resolve.ts`
- Create: `web/src/api/stats.ts`
- Create: `web/src/types/api.ts`
- Create: `web/src/hooks/useResolve.ts`
- Create: `web/src/hooks/useSkill.ts`
- Create: `web/src/hooks/useCapability.ts`
- Create: `web/src/hooks/useSearch.ts`
- Create: `web/src/hooks/useStats.ts`
- Modify: `web/src/main.tsx` (add QueryClientProvider)

- [ ] **Step 1: Create TypeScript types mirroring API models**

Create `web/src/types/api.ts` with types for all backend models:
- `TrustTier`, `CostProfile`, `EstimatedDuration`, `Scope` (enums)
- `Skill`, `SkillSummary`, `SkillCreate`, `SkillUpdate`
- `Capability`, `CapabilitySummary`, `CapabilityStep`, `DataFlowEdge`
- `ResolvedSkill`, `ResolvedCapability`, `ResolvedResult`, `Alternative`, `RejectedCandidate`
- `EvalJob`, `EvalResult`, `DimensionResult`, `TrustAuditEntry`
- `UsageStats`, `UsageReport`
- `BehavioralRunResult`, `BehavioralEvalResult`
- `ResolutionContext` (available_tools, trust_floor, cost_budget)
- `Category`

Reference models from: `src/loom/models/skill.py`, `resolution.py`, `capability.py`, `eval.py`, `usage.py`, `behavioral.py`, `common.py`, `category.py`.

- [ ] **Step 2: Create base fetch wrapper**

Create `web/src/api/client.ts`:
- `apiGet<T>(path, params?)` — GET with query params, JSON response
- `apiPost<T>(path, body?)` — POST with JSON body
- `apiPut<T>(path, body)` — PUT with JSON body
- Error handling: parse error response, throw typed `ApiError`
- Base URL: relative `/api/v1/` (proxied by Vite in dev)

- [ ] **Step 3: Create endpoint functions**

`web/src/api/skills.ts`:
- `listSkills(params?)` → `SkillSummary[]`
- `getSkill(slug)` → `Skill`
- `searchSkills(query, filters?)` → `SkillSummary[]`
- `getSkillUsage(slug)` → `UsageStats`
- `getSkillBehavioral(slug)` → `BehavioralRunResult[]`
- `getSkillTimeline(slug)` → `TimelineEvent[]`

`web/src/api/capabilities.ts`:
- `listCapabilities(params?)` → `CapabilitySummary[]`
- `getCapability(slug)` → `Capability`
- `searchCapabilities(query, filters?)` → `CapabilitySummary[]`

`web/src/api/resolve.ts`:
- `resolveSkill(body)` → `ResolvedSkill`
- `resolveCapability(body)` → `ResolvedCapability`
- `resolveAny(body)` → `ResolvedResult` (calls skill resolve with `type=any`)

`web/src/api/stats.ts`:
- `getStatsOverview()` → `StatsOverview`
- `getEvalTrends(params?)` → `EvalTrendsData`
- `getUsageHeatmap(params?)` → `UsageHeatmapData`
- `getGovernanceQueue(params?)` → `GovernanceQueueData`
- `submitReview(body)` → `ReviewResult`
- `getEmbeddingMap()` → `EmbeddingMapData`

- [ ] **Step 4: Create TanStack Query hooks**

`web/src/hooks/useResolve.ts`:
- `useResolve(query, context)` — mutation-style hook for resolution
- Debounced query key, enabled when query is non-empty

`web/src/hooks/useSkill.ts`:
- `useSkill(slug)` — fetch skill by slug
- `useSkillUsage(slug)` — fetch usage stats
- `useSkillBehavioral(slug)` — fetch behavioral results
- `useSkillTimeline(slug)` — fetch timeline events

`web/src/hooks/useCapability.ts`:
- `useCapability(slug)` — fetch capability by slug

`web/src/hooks/useSearch.ts`:
- `useSearch(query, type)` — debounced search across skills/capabilities

`web/src/hooks/useStats.ts`:
- `useStatsOverview()`, `useEvalTrends()`, `useUsageHeatmap()`
- `useGovernanceQueue()`, `useSubmitReview()`

- [ ] **Step 5: Add QueryClientProvider to App**

Wrap the app with `QueryClientProvider` in `main.tsx`. Configure default stale times (30s for listings, 5min for individual items).

- [ ] **Step 6: Verify**

Run: `cd /Users/adam/Projects/loom/web && npx tsc --noEmit`
Expected: All types compile, no errors.

- [ ] **Step 7: Commit**

```bash
git add web/src/api/ web/src/types/ web/src/hooks/ web/src/main.tsx
git commit -m "feat(m5): API client layer with TypeScript types, fetch wrapper, and TanStack Query hooks"
```

---

### Task 4: Skill Fingerprint Component

**Depends on:** Task 1

**Files:**
- Create: `web/src/components/shared/Fingerprint.tsx`
- Create: `web/src/lib/fingerprint.ts`
- Create: `web/src/components/shared/TrustBadge.tsx`
- Create: `web/src/routes/dev.tsx` (dev-only test page)

- [ ] **Step 1: Implement cardinal spline math**

Create `web/src/lib/fingerprint.ts`:
- `catmullRomSpline(points, tension)` — Catmull-Rom interpolation for smooth curves
- `polarToCartesian(cx, cy, radius, angle)` — axis point calculation
- `buildFingerprintPath(scores, size)` — converts 5 dimension scores to SVG path `d` attribute
- Five axes: Clarity (top), Completeness (top-right), Correctness (bottom-right), Safety (bottom-left), Behavioral (top-left)
- Angles: evenly spaced at 72-degree intervals starting from top (270 degrees)

- [ ] **Step 2: Implement Fingerprint component**

Create `web/src/components/shared/Fingerprint.tsx`:
- Props: `scores: { clarity, completeness, safety, correctness, behavioral }`, `size: 'thumbnail' | 'card' | 'hero'`, `confidence?: number`, `className?: string`
- SVG rendering with:
  - Background grid (faint axis lines from center to edge)
  - Filled polygon with cardinal spline interpolation
  - Semi-transparent fill with color intensity mapped to `confidence` (high = saturated, low = desaturated)
  - Glow filter (SVG `<feGaussianBlur>`) intensity from `behavioral` score
  - Thin stroke border
- Size mapping: thumbnail = 32px, card = 64px, hero = 200px
- Hero size: interactive hover labels showing axis name + score on each axis point
- Accessible: `role="img"`, `aria-label` describing scores

- [ ] **Step 3: Implement TrustBadge component**

Create `web/src/components/shared/TrustBadge.tsx`:
- Props: `tier: TrustTier`, `size?: 'sm' | 'md' | 'lg'`
- Visual: colored badge (experimental = amber, community = blue, verified = green)
- Icon + text label

- [ ] **Step 4: Create dev test page**

Create `web/src/routes/dev.tsx`:
- Renders Fingerprint at all three sizes with sample data
- Shows variations: high scores, low scores, mixed, zero behavioral
- Shows TrustBadge at all tiers
- Only accessible at `/dev` in development

- [ ] **Step 5: Verify**

Run: `cd /Users/adam/Projects/loom/web && npm run dev`
Navigate to `http://localhost:5173/dev`
Expected: Fingerprints render at all sizes, smooth shapes, glow on high behavioral score, no glow on zero behavioral, hover labels on hero size.

Run: `cd /Users/adam/Projects/loom/web && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 6: Commit**

```bash
git add web/src/components/shared/ web/src/lib/fingerprint.ts web/src/routes/dev.tsx
git commit -m "feat(m5): skill fingerprint SVG component with cardinal spline interpolation and trust badge"
```

---

## Chunk 2: Resolve View (M5i Core)

---

### Task 5: HeroSearchBar Component

**Depends on:** Task 2, Task 3

**Files:**
- Create: `web/src/components/resolve/HeroSearchBar.tsx`

- [ ] **Step 1: Implement HeroSearchBar**

Create `web/src/components/resolve/HeroSearchBar.tsx`:
- Full-width search input: placeholder "What do you need to do?"
- Debounced input (300ms) — uses `useState` + `useEffect` with timer
- On debounced value change: calls `useResolve` hook
- Loading spinner during resolution (inline, right side of input)
- Keyboard support: Enter to resolve immediately (bypass debounce), Escape to clear
- Visual: large text, prominent border, subtle shadow, focus ring
- Passes resolved query up via `onResolve(result)` callback

- [ ] **Step 2: Verify**

Run: `cd /Users/adam/Projects/loom/web && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/resolve/
git commit -m "feat(m5): hero search bar with debounced resolution"
```

---

### Task 6: PrimaryResult Component

**Depends on:** Task 4, Task 5

**Files:**
- Create: `web/src/components/resolve/PrimaryResult.tsx`
- Create: `web/src/components/shared/SkillCard.tsx`
- Create: `web/src/components/shared/MiniFlowPreview.tsx`

- [ ] **Step 1: Implement PrimaryResult**

Create `web/src/components/resolve/PrimaryResult.tsx`:
- Props: `result: ResolvedSkill | ResolvedCapability`, `type: 'skill' | 'capability'`
- Displays: name, description, trust badge (TrustBadge component), fingerprint (card size)
- Type indicator: "Skill" or "Capability" label with icon
- If capability: inline MiniFlowPreview showing step names connected by arrows
- Click navigates to Inspect view (`/skills/:slug` or `/capabilities/:slug`)
- Usage stats: success rate, resolution count (compact inline display)
- Enter/exit animation via Framer Motion (`AnimatePresence`)

- [ ] **Step 2: Implement MiniFlowPreview**

Create `web/src/components/shared/MiniFlowPreview.tsx`:
- Props: `steps: CapabilityStep[]`
- Horizontal sequence of step name pills connected by arrow lines
- Compact: fits in a single row, scrollable if many steps
- Each pill shows: step role, skill ref (truncated)

- [ ] **Step 3: Verify**

Run: `cd /Users/adam/Projects/loom/web && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/resolve/ web/src/components/shared/
git commit -m "feat(m5): primary result card with fingerprint, trust badge, and mini flow preview"
```

---

### Task 7: AlternativeList Component

**Depends on:** Task 4, Task 6

**Files:**
- Create: `web/src/components/resolve/AlternativeList.tsx`

- [ ] **Step 1: Implement AlternativeList**

Create `web/src/components/resolve/AlternativeList.tsx`:
- Props: `alternatives: Alternative[]`, `onSelect: (alt: Alternative) => void`
- Shows up to 3 alternatives
- Each alternative: fingerprint thumbnail, trust badge, name, dismissal reason
- Dismissal reason: human-readable text from `rejection_rationale`
- Click calls `onSelect` to promote alternative to primary position
- Subtle card styling, less prominent than PrimaryResult
- Framer Motion list animations (stagger enter)

- [ ] **Step 2: Verify**

Run: `cd /Users/adam/Projects/loom/web && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/resolve/AlternativeList.tsx
git commit -m "feat(m5): alternatives list with rejection rationale and promotion"
```

---

### Task 8: ContextToggles Component

**Depends on:** Task 5

**Files:**
- Create: `web/src/components/resolve/ContextToggles.tsx`

- [ ] **Step 1: Implement ContextToggles**

Create `web/src/components/resolve/ContextToggles.tsx`:
- Collapsible panel (chevron toggle) below search bar
- `available_tools`: multi-select checkboxes for common tool sets (git, filesystem, network, browser)
- `trust_floor`: dropdown select (experimental, community, verified)
- `cost_budget`: range slider (free, low, medium, high) with label
- State persisted in URL search params via TanStack Router's `useSearch`
- Changes re-trigger resolution immediately via callback
- Compact layout: single row on desktop, stacked on mobile

- [ ] **Step 2: Verify**

Run: `cd /Users/adam/Projects/loom/web && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/resolve/ContextToggles.tsx
git commit -m "feat(m5): context toggles with URL-persisted state"
```

---

### Task 9: ResolutionHistory Component

**Depends on:** Task 5

**Files:**
- Create: `web/src/components/resolve/ResolutionHistory.tsx`
- Create: `web/src/lib/storage.ts`

- [ ] **Step 1: Implement localStorage helper**

Create `web/src/lib/storage.ts`:
- `getHistory(): string[]` — read recent queries from localStorage
- `addToHistory(query: string)` — prepend, deduplicate, cap at 20 items
- `clearHistory()` — remove all

- [ ] **Step 2: Implement ResolutionHistory**

Create `web/src/components/resolve/ResolutionHistory.tsx`:
- Collapsible panel showing recent queries
- Click to re-run a previous resolution (calls `onSelect(query)`)
- Clear all button with confirmation
- Timestamps stored alongside queries
- Empty state: "No recent queries"

- [ ] **Step 3: Verify**

Run: `cd /Users/adam/Projects/loom/web && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/resolve/ web/src/lib/storage.ts
git commit -m "feat(m5): resolution history with localStorage persistence"
```

---

### Task 10: Living Feed Sidebar + Resolve View Assembly

**Depends on:** Tasks 5-9

**Files:**
- Create: `web/src/components/shared/LivingFeed.tsx`
- Modify: `web/src/routes/index.tsx` (assemble Resolve View)
- Modify: `web/src/components/layout/AppShell.tsx` (add sidebar)

- [ ] **Step 1: Implement LivingFeed**

Create `web/src/components/shared/LivingFeed.tsx`:
- Polls `GET /api/v1/skills?sort=created_at&limit=20` every 30s via TanStack Query `refetchInterval`
- Shows recent activity items:
  - New skills: "[name] submitted" with timestamp
  - Trust changes: "[name] promoted to [tier]" (detect from trust_tier field)
  - Deprecations: "[name] deprecated"
- Each item: icon (based on event type), name (link to inspect), timestamp (relative: "2m ago")
- Collapsible via toggle button
- Scrollable container with max height

- [ ] **Step 2: Assemble Resolve View**

Update `web/src/routes/index.tsx` (the `/` route):
- HeroSearchBar at top
- ContextToggles below search bar
- PrimaryResult when result available
- AlternativeList below primary result
- ResolutionHistory at bottom
- Loading skeleton while resolving
- Empty state: descriptive text about Loom when no query entered

- [ ] **Step 3: Wire sidebar into AppShell**

Update `web/src/components/layout/AppShell.tsx`:
- Add LivingFeed in right sidebar
- Sidebar hidden on mobile, toggle on tablet, visible on desktop
- Sidebar width: 280px fixed

- [ ] **Step 4: Verify**

Run: `cd /Users/adam/Projects/loom/web && npm run dev`
With backend running (`uv run python -m loom.api`):
- Navigate to `http://localhost:5173`
- Type a query in the search bar
- Expected: resolution result appears with fingerprint, trust badge, alternatives
- Expected: living feed shows recent skills (or empty state if no skills)
- Expected: context toggles collapse/expand, URL params update

Run: `cd /Users/adam/Projects/loom/web && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 5: Commit**

```bash
git add web/src/
git commit -m "feat(m5): resolve view assembly with living feed sidebar"
```

---

## Chunk 3: Explore View (M5ii)

---

### Task 11: Backend — Embedding Map Endpoint

**Depends on:** None (backend only)

**Files:**
- Modify: `pyproject.toml` (add `umap-learn`, `numpy`)
- Create: `src/loom/services/embedding_map.py`
- Create: `src/loom/api/routes/embeddings.py`
- Modify: `src/loom/api/app.py` (register route)
- Create: `tests/unit/test_embedding_map.py`

- [ ] **Step 1: Add dependencies**

Add to `pyproject.toml`:
```toml
    "umap-learn>=0.5",
    "numpy>=1.26",
```

Run: `uv sync`

- [ ] **Step 2: Implement EmbeddingMapService**

Create `src/loom/services/embedding_map.py`:
- `compute_map(skills, capabilities)` → `EmbeddingMapData`
- Collects embeddings from all skills and capabilities
- Runs UMAP (2D, `n_neighbors=15`, `min_dist=0.1`) on concatenated embeddings
- Returns projected coordinates with metadata (slug, trust_tier, category, composite_score, behavioral_score)
- Caches result in memory with TTL (1 hour)
- Handles edge case: fewer than 5 items → skip UMAP, use random 2D layout
- Thread-safe: UMAP runs in executor to avoid blocking event loop

- [ ] **Step 3: Create API route**

Create `src/loom/api/routes/embeddings.py`:
- `GET /api/v1/embeddings/map` → `EmbeddingMapData`
- Fetches all skills and capabilities from repos
- Calls `EmbeddingMapService.compute_map()`
- Response shape matches spec §6.2

- [ ] **Step 4: Write tests**

Create `tests/unit/test_embedding_map.py`:
- Test with mock embeddings (random 384-dim vectors)
- Test cache hit (second call returns same result)
- Test edge case: empty registry returns empty lists
- Test edge case: single skill returns valid coordinates

- [ ] **Step 5: Verify**

Run: `uv run pytest tests/unit/test_embedding_map.py -v`
Expected: PASS.

Run: `uv run python -m loom.api` (start server)
Run: `curl -s http://localhost:8000/api/v1/embeddings/map | python3 -m json.tool | head -20`
Expected: JSON with `skills` and `capabilities` arrays.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock src/loom/services/embedding_map.py src/loom/api/routes/embeddings.py src/loom/api/app.py tests/unit/test_embedding_map.py
git commit -m "feat(m5): embedding map endpoint with UMAP projection"
```

---

### Task 12: SemanticMap Component

**Depends on:** Task 2, Task 3, Task 11

**Files:**
- Create: `web/src/components/explore/SemanticMap.tsx`
- Create: `web/src/components/explore/SkillNode.tsx`
- Create: `web/src/components/explore/ClusterLabel.tsx`
- Create: `web/src/hooks/useEmbeddingMap.ts`
- Create: `web/src/lib/embedding-map.ts`

- [ ] **Step 1: Implement embedding map hook**

Create `web/src/hooks/useEmbeddingMap.ts`:
- `useEmbeddingMap()` — fetches `GET /api/v1/embeddings/map`
- Long stale time (5 minutes — data changes infrequently)
- Returns typed `EmbeddingMapData`

- [ ] **Step 2: Implement map utilities**

Create `web/src/lib/embedding-map.ts`:
- `computeClusterCentroids(nodes, categoryField)` — group by category, compute centroid x/y
- `nodeSize(trustTier)` — verified=large, community=medium, experimental=small
- `nodeOpacity(compositeScore)` — high score = solid (1.0), low = translucent (0.3)
- Scale functions for mapping UMAP coordinates to canvas pixel space

- [ ] **Step 3: Implement SemanticMap**

Create `web/src/components/explore/SemanticMap.tsx`:
- SVG canvas with D3 zoom behavior (`d3-zoom`)
- Pan and zoom via mouse/trackpad
- Renders skill nodes as circles, capability nodes as hexagons
- Visual encoding: size=trust tier, color=type (blue/amber), opacity=quality
- Capability edges: thin lines connecting capability node to constituent skill nodes (via `step_slugs`)
- Zoom levels:
  - Far (< 0.5x): density clouds + category labels only
  - Near (> 1.5x): individual nodes + fingerprint thumbnails
  - Default: individual nodes without fingerprints
- Performance: use `<g>` groups with `will-change: transform`

- [ ] **Step 4: Implement ClusterLabel**

Create `web/src/components/explore/ClusterLabel.tsx`:
- Positioned at cluster centroid
- Category name text
- Font size scales with cluster population (min 12px, max 24px)
- Fade in/out based on zoom level

- [ ] **Step 5: Verify**

Run: `cd /Users/adam/Projects/loom/web && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 6: Commit**

```bash
git add web/src/components/explore/ web/src/hooks/useEmbeddingMap.ts web/src/lib/embedding-map.ts
git commit -m "feat(m5): semantic map with D3 zoom, visual encoding, and cluster labels"
```

---

### Task 13: Map Interactions + Explore View Assembly

**Depends on:** Task 12

**Files:**
- Create: `web/src/components/explore/MapSearch.tsx`
- Create: `web/src/components/explore/NodeTooltip.tsx`
- Create: `web/src/components/explore/DetailPanel.tsx`
- Modify: `web/src/routes/explore.tsx`

- [ ] **Step 1: Implement MapSearch**

Create `web/src/components/explore/MapSearch.tsx`:
- Text filter input overlaid on map (top-left)
- Filters nodes by slug, name, or description (client-side)
- Matching nodes: full opacity, non-matching: fade to 0.1 opacity
- Clear button to reset filter

- [ ] **Step 2: Implement NodeTooltip**

Create `web/src/components/explore/NodeTooltip.tsx`:
- Appears on hover over a node
- Shows: name, trust tier, composite score
- Positioned near cursor, avoids viewport edges
- Dismiss on mouse leave

- [ ] **Step 3: Implement DetailPanel**

Create `web/src/components/explore/DetailPanel.tsx`:
- Slide-out panel from right side on node click
- Shows skill/capability detail (reuses content from Inspect view components)
- Close button, click outside to dismiss
- Framer Motion slide animation

- [ ] **Step 4: Assemble Explore View**

Update `web/src/routes/explore.tsx`:
- Full-viewport SemanticMap
- MapSearch overlay
- NodeTooltip on hover
- DetailPanel on click
- Loading skeleton while embedding data loads
- Empty state if no skills/capabilities in registry

- [ ] **Step 5: Verify**

Run: `cd /Users/adam/Projects/loom/web && npm run dev`
With backend running:
- Navigate to `http://localhost:5173/explore`
- Expected: map renders with nodes positioned by embedding similarity
- Expected: hover shows tooltip, click opens detail panel
- Expected: search filters nodes with opacity

Run: `cd /Users/adam/Projects/loom/web && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 6: Commit**

```bash
git add web/src/components/explore/ web/src/routes/explore.tsx
git commit -m "feat(m5): explore view with map interactions, search, and detail panel"
```

---

## Chunk 4: Inspect View (M5ii)

---

### Task 14: SkillDetail Component

**Depends on:** Task 3, Task 4

**Files:**
- Create: `web/src/components/inspect/SkillDetail.tsx`
- Create: `web/src/components/inspect/EvalHistory.tsx`
- Create: `web/src/components/inspect/UsageStatsDisplay.tsx`
- Create: `web/src/components/shared/ScoreBar.tsx`

- [ ] **Step 1: Implement ScoreBar**

Create `web/src/components/shared/ScoreBar.tsx`:
- Props: `score: number` (0-1), `label: string`, `color?: string`
- Horizontal bar showing score fill, label on left, value on right
- Color gradient: red (< 0.4), amber (0.4-0.7), green (> 0.7)

- [ ] **Step 2: Implement EvalHistory**

Create `web/src/components/inspect/EvalHistory.tsx`:
- Props: `skillId: string`
- Fetches eval history (scores by dimension across eval jobs)
- Renders: dimension scores as ScoreBar components
- Composite score prominently displayed
- Confidence indicator

- [ ] **Step 3: Implement UsageStatsDisplay**

Create `web/src/components/inspect/UsageStatsDisplay.tsx`:
- Props: `slug: string`
- Uses `useSkillUsage` hook
- Shows: success rate (percentage with color), total resolutions, avg runtime
- Compact card layout

- [ ] **Step 4: Implement SkillDetail**

Create `web/src/components/inspect/SkillDetail.tsx`:
- Props: `slug: string`
- Uses `useSkill` hook
- Header: name, slug, version, trust badge, created/updated dates
- Description: full text
- Content preview: collapsible, rendered as styled markdown (react-markdown with remark-gfm, HTML stripped via `allowedElements`)
- Large interactive Fingerprint (hero size)
- EvalHistory section
- UsageStatsDisplay section
- Dependencies list with satisfaction indicators

- [ ] **Step 5: Verify**

Run: `cd /Users/adam/Projects/loom/web && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 6: Commit**

```bash
git add web/src/components/inspect/ web/src/components/shared/ScoreBar.tsx
git commit -m "feat(m5): skill detail view with eval history, usage stats, and content preview"
```

---

### Task 15: Backend — Skill Timeline Endpoint

**Depends on:** None (backend only)

**Files:**
- Create: `src/loom/api/routes/timeline.py` (or add to existing eval routes)
- Modify: `src/loom/api/app.py` (register route if new file)
- Create: `tests/unit/test_timeline.py`

- [ ] **Step 1: Implement timeline endpoint**

Add `GET /api/v1/skills/{slug}/timeline` to backend:
- Fetches skill by slug
- Aggregates events from:
  - `skills` table: created_at → "submitted" event
  - `eval_jobs` table: completed jobs → "eval_completed" events with composite score
  - `trust_audit_log` table: tier changes → "promoted"/"demoted" events with from/to tiers
  - `skill_versions` table: version changes → "version_updated" events
- Returns unified, chronologically sorted event list
- Response shape matches spec §6.2 (`GET /api/v1/skills/{slug}/timeline`)

- [ ] **Step 2: Write tests**

Create `tests/unit/test_timeline.py`:
- Test: empty timeline for new skill
- Test: events sorted chronologically
- Test: event types correctly identified
- Test: 404 for non-existent slug

- [ ] **Step 3: Verify**

Run: `uv run pytest tests/unit/test_timeline.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/loom/api/routes/ src/loom/api/app.py tests/unit/test_timeline.py
git commit -m "feat(m5): skill timeline endpoint aggregating trust, eval, and version events"
```

---

### Task 16: TrustJourney + VersionTimeline Components

**Depends on:** Task 14, Task 15

**Files:**
- Create: `web/src/components/inspect/TrustJourney.tsx`
- Create: `web/src/components/inspect/VersionTimeline.tsx`

- [ ] **Step 1: Implement TrustJourney**

Create `web/src/components/inspect/TrustJourney.tsx`:
- Props: `slug: string`
- Uses `useSkillTimeline` hook
- Visual timeline: vertical line with event nodes
- Event types color-coded: submitted=gray, eval=blue, promoted=green, demoted=red
- Each event: icon, timestamp (relative), description
- Trust tier changes shown prominently with badge transition animation

- [ ] **Step 2: Implement VersionTimeline**

Create `web/src/components/inspect/VersionTimeline.tsx`:
- Props: `slug: string`
- Shows version history entries from timeline
- Each version: version string, changelog, date
- Links to version comparison (future: inline diff)

- [ ] **Step 3: Verify**

Run: `cd /Users/adam/Projects/loom/web && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/inspect/
git commit -m "feat(m5): trust journey and version timeline components"
```

---

### Task 17: CapabilityDetail + FlowDiagram

**Depends on:** Task 3, Task 4

**Files:**
- Create: `web/src/components/inspect/CapabilityDetail.tsx`
- Create: `web/src/components/inspect/FlowDiagram.tsx`
- Create: `web/src/components/inspect/StepNode.tsx`
- Create: `web/src/components/inspect/DataFlowEdge.tsx`

- [ ] **Step 1: Implement StepNode**

Create `web/src/components/inspect/StepNode.tsx`:
- Custom React Flow node component
- Shows: skill name (from skill_ref), role, trust badge, required indicator
- Required steps: solid border; optional: dashed border
- Expandable on click: shows embedded skill content preview + fingerprint thumbnail
- Width: fixed (200px), height: auto based on content

- [ ] **Step 2: Implement DataFlowEdge**

Create `web/src/components/inspect/DataFlowEdge.tsx`:
- Custom React Flow edge component
- Label showing data classification (internal, sensitive, public)
- Color-coded: internal=gray, sensitive=red, public=green
- Animated path for visual flow direction

- [ ] **Step 3: Implement FlowDiagram**

Create `web/src/components/inspect/FlowDiagram.tsx`:
- Props: `capability: Capability`
- Uses React Flow (`@xyflow/react`)
- Converts capability steps to React Flow nodes
- Converts data_flow edges to React Flow edges
- Dagre layout for automatic positioning (`dagre` npm package — add to deps)
- Pan/zoom enabled
- Background grid
- Minimap for large diagrams

- [ ] **Step 4: Implement CapabilityDetail**

Create `web/src/components/inspect/CapabilityDetail.tsx`:
- Props: `slug: string`
- Uses `useCapability` hook
- Header: name, slug, version, trust badge, dates
- Description text
- FlowDiagram: interactive pipeline visualization
- Aggregate trust tier: effective tier (minimum across steps) with per-step breakdown
- Dependencies: aggregated across all steps
- Preconditions and expected outcome text

- [ ] **Step 5: Install dagre**

```bash
cd /Users/adam/Projects/loom/web && npm install dagre @types/dagre
```

- [ ] **Step 6: Verify**

Run: `cd /Users/adam/Projects/loom/web && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 7: Commit**

```bash
git add web/src/components/inspect/ web/package.json web/package-lock.json
git commit -m "feat(m5): capability detail with React Flow diagram, step nodes, and data flow edges"
```

---

### Task 18: Inspect View Assembly + Cross-View Components

**Depends on:** Tasks 14-17

**Files:**
- Create: `web/src/components/inspect/WhyThisWorks.tsx`
- Create: `web/src/components/inspect/AlternativesComparison.tsx`
- Create: `web/src/components/shared/DiffView.tsx`
- Modify: `web/src/routes/skills.$slug.tsx`
- Modify: `web/src/routes/capabilities.$slug.tsx`

- [ ] **Step 1: Implement WhyThisWorks**

Create `web/src/components/inspect/WhyThisWorks.tsx`:
- Props: `evalResult: EvalResult`
- Shows eval evidence per dimension (clarity, completeness, safety, correctness)
- Each dimension: ScoreBar + evidence text (truncated, expandable)
- Behavioral judge reasoning if available
- Injection flag warning if flagged

- [ ] **Step 2: Implement AlternativesComparison**

Create `web/src/components/inspect/AlternativesComparison.tsx`:
- Props: `primary: Skill`, `alternative: Skill`
- Two-column layout comparing skills
- Per-dimension score comparison with side-by-side ScoreBars
- Fingerprint comparison (card size, side by side)
- Usage stats comparison
- Behavioral score comparison

- [ ] **Step 3: Implement DiffView**

Create `web/src/components/shared/DiffView.tsx`:
- Props: `oldText: string`, `newText: string`, `title?: string`
- Simple side-by-side diff display
- Highlighted additions (green) and deletions (red)
- Line-by-line comparison

- [ ] **Step 4: Assemble Inspect routes**

Update `web/src/routes/skills.$slug.tsx`:
- Extract `slug` from route params
- Render SkillDetail with all sub-components
- TrustJourney + VersionTimeline in sidebar or below main content
- WhyThisWorks section
- Loading skeleton while data loads
- 404 handling for unknown slugs

Update `web/src/routes/capabilities.$slug.tsx`:
- Extract `slug` from route params
- Render CapabilityDetail with FlowDiagram
- Loading skeleton
- 404 handling

- [ ] **Step 5: Verify**

Run: `cd /Users/adam/Projects/loom/web && npm run dev`
With backend running:
- Navigate to `http://localhost:5173/skills/some-skill`
- Expected: skill detail renders with fingerprint, eval history, timeline
- Navigate to `http://localhost:5173/capabilities/some-capability`
- Expected: capability detail renders with flow diagram

Run: `cd /Users/adam/Projects/loom/web && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 6: Commit**

```bash
git add web/src/
git commit -m "feat(m5): inspect view assembly with skill detail, capability flow, and cross-view components"
```

---

## Chunk 5: Govern View (M5iii, No Auth)

---

### Task 19: Backend — Stats + Governance Endpoints

**Depends on:** None (backend only)

**Files:**
- Create: `src/loom/api/routes/stats.py`
- Create: `src/loom/api/routes/governance.py`
- Create: `src/loom/services/stats_service.py`
- Create: `src/loom/services/governance_service.py`
- Create: `src/loom/db/repositories/governance_repo.py`
- Modify: `src/loom/api/app.py` (register routes)
- Modify: `src/loom/services/container.py` (wire services)
- Create: `tests/unit/test_stats_service.py`
- Create: `tests/unit/test_governance_service.py`

- [ ] **Step 1: Implement StatsService**

Create `src/loom/services/stats_service.py`:
- `get_overview()` → `StatsOverview`
  - Counts skills by trust tier (SQL GROUP BY)
  - Counts capabilities
  - Computes behavioral eval coverage (skills with behavioral score / total)
  - Counts stale skills (no eval in 30 days)
  - Counts deprecated skills
  - Sums resolutions in last 7d and 30d from usage aggregates
- `get_eval_trends(category?, weeks?)` → `EvalTrendsData`
  - Groups eval jobs by week
  - Computes p25/p50/p75 of composite scores per week
  - Includes behavioral score median
- `get_usage_heatmap(period_type?, periods?)` → `UsageHeatmapData`
  - Groups usage aggregates by category and time period
  - Returns matrix of resolution counts

- [ ] **Step 2: Create stats routes**

Create `src/loom/api/routes/stats.py`:
- `GET /api/v1/stats/overview` → `StatsOverview`
- `GET /api/v1/stats/eval-trends?category=&weeks=` → `EvalTrendsData`
- `GET /api/v1/stats/usage-heatmap?period_type=week&periods=12` → `UsageHeatmapData`

- [ ] **Step 3: Implement GovernanceService**

Create `src/loom/services/governance_service.py`:
- `get_queue(reason?, limit?, offset?)` → `GovernanceQueueData`
  - Finds skills with: injection flags, low confidence evals, mixed amendments
  - Returns queue items with eval summaries
- `submit_review(queue_item_id, decision, note)` → `ReviewResult`
  - Records review decision
  - If approved: update skill status
  - If rejected: mark skill appropriately
  - Creates trust audit log entry

Create `src/loom/db/repositories/governance_repo.py`:
- `get_queue_items(reason?, limit?, offset?)` — query skills needing review
- `create_review(item_id, decision, note)` — persist review decision

- [ ] **Step 4: Create governance routes**

Create `src/loom/api/routes/governance.py`:
- `GET /api/v1/governance/queue?reason=&limit=&offset=` → `GovernanceQueueData`
- `POST /api/v1/governance/review` → `ReviewResult`

Note: No auth gating — deferred to M6.

- [ ] **Step 5: Write tests**

Create `tests/unit/test_stats_service.py`:
- Test overview with mock data
- Test eval trends computation
- Test usage heatmap matrix shape

Create `tests/unit/test_governance_service.py`:
- Test queue filtering by reason
- Test review submission creates audit entry

- [ ] **Step 6: Verify**

Run: `uv run pytest tests/unit/test_stats_service.py tests/unit/test_governance_service.py -v`
Expected: PASS.

Run: `uv run python -m loom.api` and test endpoints with curl:
```bash
curl -s http://localhost:8000/api/v1/stats/overview | python3 -m json.tool
curl -s http://localhost:8000/api/v1/stats/eval-trends | python3 -m json.tool
curl -s http://localhost:8000/api/v1/governance/queue | python3 -m json.tool
```
Expected: Valid JSON responses (may be empty if no data).

- [ ] **Step 7: Commit**

```bash
git add src/loom/services/stats_service.py src/loom/services/governance_service.py src/loom/db/repositories/governance_repo.py src/loom/api/routes/stats.py src/loom/api/routes/governance.py src/loom/api/app.py src/loom/services/container.py tests/unit/test_stats_service.py tests/unit/test_governance_service.py
git commit -m "feat(m5): stats and governance backend endpoints"
```

---

### Task 20: HealthDashboard Component

**Depends on:** Task 3, Task 19

**Files:**
- Create: `web/src/components/govern/HealthDashboard.tsx`
- Create: `web/src/components/govern/StatCard.tsx`
- Create: `web/src/components/govern/ProgressRing.tsx`

- [ ] **Step 1: Implement StatCard**

Create `web/src/components/govern/StatCard.tsx`:
- Props: `title: string`, `value: number | string`, `trend?: 'up' | 'down' | 'flat'`, `icon?: ReactNode`
- Card with large value, title below, optional trend arrow
- Color-coded trend: up=green, down=red, flat=gray

- [ ] **Step 2: Implement ProgressRing**

Create `web/src/components/govern/ProgressRing.tsx`:
- Props: `value: number` (0-1), `label: string`, `size?: number`
- SVG circular progress indicator
- Percentage label in center
- Color: green (> 0.7), amber (0.4-0.7), red (< 0.4)

- [ ] **Step 3: Implement HealthDashboard**

Create `web/src/components/govern/HealthDashboard.tsx`:
- Uses `useStatsOverview` hook
- Skill counts by trust tier: three StatCards (experimental, community, verified)
- Behavioral eval coverage: ProgressRing
- Stale/deprecated: StatCards with trend arrows
- Total resolutions: StatCard with sparkline (7d values)
- Grid layout: 2-3 columns on desktop, 1 column mobile

- [ ] **Step 4: Verify**

Run: `cd /Users/adam/Projects/loom/web && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/govern/
git commit -m "feat(m5): health dashboard with stat cards, progress ring, and overview metrics"
```

---

### Task 21: EvalTrends + UsageHeatmap Components

**Depends on:** Task 3, Task 19

**Files:**
- Create: `web/src/components/govern/EvalTrends.tsx`
- Create: `web/src/components/govern/UsageHeatmap.tsx`

- [ ] **Step 1: Implement EvalTrends**

Create `web/src/components/govern/EvalTrends.tsx`:
- Uses `useEvalTrends` hook
- Recharts `AreaChart` showing score distribution over time
- Three area bands: p25 (light), p50 (medium), p75 (dark)
- X-axis: week labels
- Y-axis: score (0-1)
- Tooltip showing exact values on hover
- Optional category filter dropdown

- [ ] **Step 2: Implement UsageHeatmap**

Create `web/src/components/govern/UsageHeatmap.tsx`:
- Uses `useUsageHeatmap` hook
- Grid of colored cells: rows = categories, columns = time periods
- Color intensity = resolution count (linear scale, light to dark)
- Row labels (category names) on left
- Column labels (period names) on top
- Tooltip on hover showing exact count
- SVG-based for precise control

- [ ] **Step 3: Verify**

Run: `cd /Users/adam/Projects/loom/web && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/govern/
git commit -m "feat(m5): eval trends area chart and usage heatmap"
```

---

### Task 22: ReviewQueue + ReviewInterface + Govern View Assembly

**Depends on:** Tasks 19-21

**Files:**
- Create: `web/src/components/govern/ReviewQueue.tsx`
- Create: `web/src/components/govern/ReviewInterface.tsx`
- Create: `web/src/hooks/useGovernanceQueue.ts`
- Modify: `web/src/routes/govern.tsx`

- [ ] **Step 1: Implement useGovernanceQueue hook**

Create `web/src/hooks/useGovernanceQueue.ts`:
- `useGovernanceQueue(reason?, limit?)` — fetches queue items
- `useSubmitReview()` — mutation for submitting review decisions
- Refetches queue after successful review submission

- [ ] **Step 2: Implement ReviewQueue**

Create `web/src/components/govern/ReviewQueue.tsx`:
- Props: `onSelectItem: (item: QueueItem) => void`
- Fetches queue via `useGovernanceQueue`
- List of queue items: skill name, reason badge, submitted date, eval summary
- Reason badges: injection_flag (red), low_confidence (amber), mixed_amendment (blue)
- Click to select item for review
- Filter dropdown by reason type
- Empty state: "No items in review queue"

- [ ] **Step 3: Implement ReviewInterface**

Create `web/src/components/govern/ReviewInterface.tsx`:
- Props: `item: QueueItem`, `onComplete: () => void`
- Full eval context display:
  - Per-dimension scores as ScoreBars
  - Injection indicators highlighted in red
  - Behavioral eval results if available
  - Skill content preview (markdown, sanitized)
- Action buttons: Approve (green), Reject (red), Request Changes (amber)
- Required note textarea (must be non-empty to submit)
- Submit calls `useSubmitReview` mutation
- Loading state on submit, success/error feedback

- [ ] **Step 4: Assemble Govern View**

Update `web/src/routes/govern.tsx`:
- Tab layout or scrollable sections:
  1. Health Dashboard (always visible at top)
  2. Eval Trends chart
  3. Usage Heatmap
  4. Review Queue + Review Interface (split view)
- Responsive: stacked on mobile, side-by-side on desktop

- [ ] **Step 5: Verify**

Run: `cd /Users/adam/Projects/loom/web && npm run dev`
With backend running:
- Navigate to `http://localhost:5173/govern`
- Expected: dashboard renders with stats (or zeros for empty registry)
- Expected: review queue shows items (or empty state)
- Expected: charts render (or empty state)

Run: `cd /Users/adam/Projects/loom/web && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 6: Commit**

```bash
git add web/src/
git commit -m "feat(m5): govern view with review queue, review interface, and assembled dashboard"
```

---

## Chunk 6: Polish + Integration Tests (M5iv, Partial)

---

### Task 23: Framer Motion Animations

**Depends on:** Tasks 10, 13, 18, 22 (all views assembled)

**Files:**
- Modify: `web/src/routes/__root.tsx` (page transitions)
- Modify: `web/src/components/resolve/PrimaryResult.tsx` (result animations)
- Modify: `web/src/components/shared/Fingerprint.tsx` (morph animation)
- Create: `web/src/components/shared/Skeleton.tsx`

- [ ] **Step 1: Page transitions**

Update `web/src/routes/__root.tsx`:
- Wrap `<Outlet />` with `AnimatePresence`
- Each page: `motion.div` with fade + slide animation
- `initial={{ opacity: 0, y: 10 }}`, `animate={{ opacity: 1, y: 0 }}`, `exit={{ opacity: 0, y: -10 }}`
- Transition: 200ms ease-out

- [ ] **Step 2: Result card animations**

Update PrimaryResult and AlternativeList:
- Enter: fade in + slide up with stagger
- Exit: fade out
- Layout animation on position change (when alternative promoted)

- [ ] **Step 3: Fingerprint morph**

Update Fingerprint component:
- Use `motion.path` for the fingerprint shape
- Animate `d` attribute transition when scores change
- Spring physics for organic feel

- [ ] **Step 4: Skeleton loading states**

Create `web/src/components/shared/Skeleton.tsx`:
- Reusable skeleton component with shimmer animation
- Variants: text line, card, fingerprint, chart
- Used across all views during data loading

- [ ] **Step 5: Verify**

Run: `cd /Users/adam/Projects/loom/web && npm run dev`
Expected: Smooth page transitions, result card animations, fingerprint morphing.

- [ ] **Step 6: Commit**

```bash
git add web/src/
git commit -m "feat(m5): Framer Motion animations — page transitions, result cards, fingerprint morph, skeleton loading"
```

---

### Task 24: Responsive Design

**Depends on:** Tasks 10, 13, 18, 22 (all views assembled)

**Files:**
- Modify: various component files (Tailwind responsive classes)
- Modify: `web/src/components/layout/AppShell.tsx`
- Modify: `web/src/components/explore/SemanticMap.tsx`

- [ ] **Step 1: Desktop layout**

- Full sidebar (280px), multi-column layouts
- Govern view: side-by-side dashboard + queue
- Inspect view: main content + sidebar timeline

- [ ] **Step 2: Tablet layout (< 1024px)**

- Collapsible sidebar (toggle button)
- Single column content layouts
- Govern view: stacked sections
- Inspect view: stacked content

- [ ] **Step 3: Mobile layout (< 640px)**

- Hidden sidebar (sheet/drawer pattern)
- Full-width components
- Hamburger menu in header
- Touch-friendly: larger tap targets (min 44px)

- [ ] **Step 4: Touch-friendly map**

Update SemanticMap:
- Touch events for pan/zoom (pinch to zoom)
- Larger hit areas for nodes on touch devices
- Disable hover tooltip on touch (use tap instead)

- [ ] **Step 5: Verify**

Run: `cd /Users/adam/Projects/loom/web && npm run dev`
Test at viewport widths: 375px, 768px, 1280px.
Expected: Layout adapts correctly at each breakpoint.

- [ ] **Step 6: Commit**

```bash
git add web/src/
git commit -m "feat(m5): responsive design for desktop, tablet, and mobile viewports"
```

---

### Task 25: Integration Test

**Depends on:** All previous tasks

**Files:**
- Create: `web/e2e/resolve.spec.ts`
- Create: `web/e2e/explore.spec.ts`
- Create: `web/e2e/inspect.spec.ts`
- Create: `web/playwright.config.ts`
- Modify: `web/package.json` (add playwright dev dep + script)

- [ ] **Step 1: Install Playwright**

```bash
cd /Users/adam/Projects/loom/web
npm install -D @playwright/test
npx playwright install chromium
```

- [ ] **Step 2: Configure Playwright**

Create `web/playwright.config.ts`:
- Base URL: `http://localhost:5173`
- Web server command: `npm run dev` (auto-start)
- Single browser: Chromium
- Screenshots on failure

- [ ] **Step 3: Write Resolve view test**

Create `web/e2e/resolve.spec.ts`:
- Navigate to `/`
- Type query in search bar
- Wait for result to appear
- Verify: result card visible with skill name
- Verify: fingerprint SVG rendered
- Verify: alternatives section present

- [ ] **Step 4: Write Explore view test**

Create `web/e2e/explore.spec.ts`:
- Navigate to `/explore`
- Wait for map to load
- Verify: SVG canvas present
- Verify: at least one node rendered (or empty state)

- [ ] **Step 5: Write Inspect view test**

Create `web/e2e/inspect.spec.ts`:
- Navigate to `/skills/some-test-skill` (requires seeded data or mock)
- Verify: skill detail header visible
- Verify: fingerprint rendered
- Verify: 404 page for non-existent skill

- [ ] **Step 6: Verify**

Run: `cd /Users/adam/Projects/loom/web && npx playwright test`
Expected: All tests pass (may need backend running with seeded data).

- [ ] **Step 7: Commit**

```bash
git add web/e2e/ web/playwright.config.ts web/package.json web/package-lock.json
git commit -m "test(m5): Playwright integration tests for resolve, explore, and inspect views"
```

---

### Task 26: CI Setup

**Depends on:** Tasks 1-25

**Files:**
- Create or modify: `.github/workflows/ci.yml` (add frontend jobs)
- Modify: `web/package.json` (ensure scripts exist)

- [ ] **Step 1: Add frontend CI scripts to package.json**

Ensure these scripts exist in `web/package.json`:
```json
{
  "scripts": {
    "typecheck": "tsc --noEmit",
    "lint": "eslint src/",
    "test": "vitest run",
    "build": "vite build"
  }
}
```

- [ ] **Step 2: Add frontend job to GitHub Actions**

Add a `frontend` job to `.github/workflows/ci.yml`:
```yaml
  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: web
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'npm'
          cache-dependency-path: web/package-lock.json
      - run: npm ci
      - run: npm run typecheck
      - run: npm run lint
      - run: npm run test
      - run: npm run build
```

- [ ] **Step 3: Verify**

Run locally:
```bash
cd /Users/adam/Projects/loom/web
npm run typecheck && npm run lint && npm run test && npm run build
```
Expected: All pass, `web/dist/` directory created with production build.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml web/package.json
git commit -m "ci(m5): add frontend type check, lint, test, and build to GitHub Actions"
```

---

## New Files Summary

### Frontend (`web/`)

| File | Purpose |
|------|---------|
| `web/src/api/client.ts` | Base fetch wrapper with error handling |
| `web/src/api/skills.ts` | Skill endpoint functions |
| `web/src/api/capabilities.ts` | Capability endpoint functions |
| `web/src/api/resolve.ts` | Resolution endpoint functions |
| `web/src/api/stats.ts` | Stats + governance endpoint functions |
| `web/src/types/api.ts` | TypeScript types mirroring all API models |
| `web/src/hooks/useResolve.ts` | Resolution query hook |
| `web/src/hooks/useSkill.ts` | Skill data hooks |
| `web/src/hooks/useCapability.ts` | Capability data hook |
| `web/src/hooks/useSearch.ts` | Debounced search hook |
| `web/src/hooks/useStats.ts` | Governance stats hooks |
| `web/src/hooks/useEmbeddingMap.ts` | Embedding map data hook |
| `web/src/hooks/useGovernanceQueue.ts` | Review queue + mutation hooks |
| `web/src/lib/fingerprint.ts` | Cardinal spline math for fingerprint SVG |
| `web/src/lib/embedding-map.ts` | D3 scale/zoom utilities |
| `web/src/lib/storage.ts` | localStorage helpers |
| `web/src/routes/__root.tsx` | Root layout with app shell |
| `web/src/routes/index.tsx` | Resolve View (homepage) |
| `web/src/routes/explore.tsx` | Explore View |
| `web/src/routes/skills.$slug.tsx` | Skill Inspect View |
| `web/src/routes/capabilities.$slug.tsx` | Capability Inspect View |
| `web/src/routes/govern.tsx` | Govern View |
| `web/src/routes/dev.tsx` | Dev-only component test page |
| `web/src/components/layout/AppShell.tsx` | App layout shell |
| `web/src/components/layout/Header.tsx` | Navigation header |
| `web/src/components/layout/Sidebar.tsx` | Sidebar container |
| `web/src/components/shared/Fingerprint.tsx` | SVG 5-axis radar fingerprint |
| `web/src/components/shared/TrustBadge.tsx` | Trust tier badge |
| `web/src/components/shared/LivingFeed.tsx` | Activity feed sidebar |
| `web/src/components/shared/SkillCard.tsx` | Compact skill summary card |
| `web/src/components/shared/MiniFlowPreview.tsx` | Inline capability step preview |
| `web/src/components/shared/ScoreBar.tsx` | Horizontal score bar |
| `web/src/components/shared/DiffView.tsx` | Side-by-side text diff |
| `web/src/components/shared/Skeleton.tsx` | Loading skeleton animations |
| `web/src/components/resolve/HeroSearchBar.tsx` | Search input with debounced resolution |
| `web/src/components/resolve/PrimaryResult.tsx` | Top match detail card |
| `web/src/components/resolve/AlternativeList.tsx` | Rejected alternatives |
| `web/src/components/resolve/ContextToggles.tsx` | Resolution context controls |
| `web/src/components/resolve/ResolutionHistory.tsx` | Recent queries |
| `web/src/components/explore/SemanticMap.tsx` | D3/visx canvas with pan/zoom |
| `web/src/components/explore/SkillNode.tsx` | Map node renderer |
| `web/src/components/explore/ClusterLabel.tsx` | Category cluster label |
| `web/src/components/explore/MapSearch.tsx` | Map search overlay |
| `web/src/components/explore/NodeTooltip.tsx` | Hover tooltip |
| `web/src/components/explore/DetailPanel.tsx` | Click detail slide-out |
| `web/src/components/inspect/SkillDetail.tsx` | Full skill detail layout |
| `web/src/components/inspect/EvalHistory.tsx` | Eval scores display |
| `web/src/components/inspect/UsageStatsDisplay.tsx` | Usage statistics |
| `web/src/components/inspect/TrustJourney.tsx` | Trust tier change timeline |
| `web/src/components/inspect/VersionTimeline.tsx` | Version history |
| `web/src/components/inspect/CapabilityDetail.tsx` | Full capability detail |
| `web/src/components/inspect/FlowDiagram.tsx` | React Flow pipeline diagram |
| `web/src/components/inspect/StepNode.tsx` | Custom React Flow node |
| `web/src/components/inspect/DataFlowEdge.tsx` | Custom React Flow edge |
| `web/src/components/inspect/WhyThisWorks.tsx` | Eval evidence section |
| `web/src/components/inspect/AlternativesComparison.tsx` | Side-by-side comparison |
| `web/src/components/govern/HealthDashboard.tsx` | Registry health overview |
| `web/src/components/govern/StatCard.tsx` | Individual stat card |
| `web/src/components/govern/ProgressRing.tsx` | Circular progress indicator |
| `web/src/components/govern/EvalTrends.tsx` | Score distribution chart |
| `web/src/components/govern/UsageHeatmap.tsx` | Resolution frequency heatmap |
| `web/src/components/govern/ReviewQueue.tsx` | Queue item list |
| `web/src/components/govern/ReviewInterface.tsx` | Full review context + actions |
| `web/e2e/resolve.spec.ts` | Playwright test: Resolve view |
| `web/e2e/explore.spec.ts` | Playwright test: Explore view |
| `web/e2e/inspect.spec.ts` | Playwright test: Inspect view |
| `web/playwright.config.ts` | Playwright configuration |

### Backend

| File | Purpose |
|------|---------|
| `src/loom/services/embedding_map.py` | UMAP projection for embedding map |
| `src/loom/services/stats_service.py` | Registry health and trend statistics |
| `src/loom/services/governance_service.py` | Review queue and decision logic |
| `src/loom/db/repositories/governance_repo.py` | Governance persistence |
| `src/loom/api/routes/embeddings.py` | Embedding map endpoint |
| `src/loom/api/routes/stats.py` | Stats endpoints |
| `src/loom/api/routes/governance.py` | Governance queue + review endpoints |
| `src/loom/api/routes/timeline.py` | Skill timeline endpoint |
| `tests/unit/test_embedding_map.py` | Embedding map tests |
| `tests/unit/test_stats_service.py` | Stats service tests |
| `tests/unit/test_governance_service.py` | Governance service tests |
| `tests/unit/test_timeline.py` | Timeline endpoint tests |

### Config

| File | Purpose |
|------|---------|
| `.claude/launch.json` | Dev server configuration |

## Modified Files Summary

| File | Changes |
|------|---------|
| `pyproject.toml` | Add `umap-learn`, `numpy` |
| `src/loom/api/app.py` | Register embeddings, stats, governance, timeline routes |
| `src/loom/services/container.py` | Wire StatsService, GovernanceService, EmbeddingMapService |
| `.github/workflows/ci.yml` | Add frontend CI job |

## Dependency Graph

```
Task 1 (scaffold)
├── Task 2 (layout + routing)
│   ├── Task 5 (search bar) ──→ Task 6 (primary result) ──→ Task 7 (alternatives)
│   ├── Task 8 (context toggles)
│   ├── Task 9 (history)
│   └── Tasks 5-9 ──→ Task 10 (living feed + resolve assembly)
├── Task 3 (API client)
│   ├── Task 12 (semantic map)
│   ├── Task 14 (skill detail)
│   ├── Task 17 (capability detail)
│   ├── Task 20 (health dashboard)
│   └── Task 21 (eval trends + heatmap)
└── Task 4 (fingerprint)
    ├── Task 6 (primary result)
    ├── Task 7 (alternatives)
    ├── Task 14 (skill detail)
    └── Task 17 (capability detail)

Task 11 (embedding endpoint) ──→ Task 12 (semantic map) ──→ Task 13 (map interactions + explore assembly)

Task 14 + Task 15 (timeline endpoint) ──→ Task 16 (trust journey) ──→ Task 18 (inspect assembly)
Task 17 ──→ Task 18

Task 19 (stats + governance endpoints) ──→ Task 20 + Task 21 ──→ Task 22 (govern assembly)

Tasks 10, 13, 18, 22 ──→ Task 23 (animations) + Task 24 (responsive)
All tasks ──→ Task 25 (integration tests) ──→ Task 26 (CI)
```
