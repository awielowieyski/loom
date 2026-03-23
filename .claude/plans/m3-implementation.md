# M3 Implementation Plan

## Overview
Build composition & capabilities — multi-step execution plans resolved as first-class objects alongside skills. Key innovation: composition security model that prevents trust laundering, injection via extends chains, and step substitution.

## Security Model (6 threats addressed)
1. **Injection via extends** → minimum trust across all layers in chain
2. **Dependency confusion** → mandatory URI prefixes (loom://, corp://), strict source resolution
3. **Data flow injection** → classification per flow edge, safety warnings for external data
4. **Privilege escalation** → minimum trust across ALL steps, experimental warnings
5. **Step substitution** → append-only extends (can add steps, cannot replace)
6. **Circular extends** → visited-set cycle detection + depth limit (10)

## Sub-milestones
- **M3i**: Capability model, DB tables, CRUD, validation (Chunks 1-2)
- **M3ii**: Resolution, semantic integration, MCP tools (Chunk 3)
- **M3iii**: Extends + composition security + adversarial tests (Chunk 4)
- **M3iv**: API routes, seed capabilities, integration tests (Chunks 5-6)

## Implementation Chunks (21 tasks)

### Chunk 1: Infrastructure
- [ ] Task 1: DB tables + Alembic migration (capabilities, capability_versions)
- [ ] Task 2: Domain models (Capability, CapabilityStep, ResolvedCapability, etc.)
- [ ] Task 3: CapabilityRepo (CRUD, versioning)

### Chunk 2: Registry
- [ ] Task 4: CapabilityRegistryService (lifecycle management)
- [ ] Task 5: Step reference validation (skills exist + trust floor)
- [ ] Task 6: Dependency aggregation (union of steps' deps)
- [ ] Task 7: Data flow validation (outputs → inputs)

### Chunk 3: Resolution
- [ ] Task 8: CapabilityDiscoveryService (vector search alongside skills)
- [ ] Task 9: Full plan resolution (embed skill content per step)
- [ ] Task 10: Unified resolve() — returns skill OR capability with type indicator

### Chunk 4: Extends & Security
- [ ] Task 11: Capability extends in ExtendsResolver
- [ ] Task 12: Minimum-trust-across-chain rule
- [ ] Task 13: Cycle detection (visited set + depth limit)
- [ ] Task 14: Append-only merge enforcement
- [ ] Task 15: Cross-source URI validation

### Chunk 5: API & MCP
- [ ] Task 16: API routes (capability CRUD + resolution)
- [ ] Task 17: MCP tools (resolve_capability, get_capability)
- [ ] Task 18: Update resolve() to return capabilities

### Chunk 6: Seeds + Tests
- [ ] Task 19: 3 seed capabilities from existing skills
- [ ] Task 20: Adversarial test suite for composition attacks
- [ ] Task 21: Integration tests + E2E demo

## Spec References
- [M3 Composition Spec](../../docs/specs/2026-03-23-m3-composition-spec.md)
- [Implementation Plan](../../docs/superpowers/plans/2026-03-23-m3-implementation.md)
- [Milestones](../../docs/specs/implementation-milestones.md)
