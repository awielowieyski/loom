# Loom: Product Brief

**Date**: 2026-03-21
**Status**: Draft
**Purpose**: Internal messaging brief for future website, deck, and product copy

---

## 1. Working Description

Loom is a capability resolution service for agents.

It helps an agent choose the right skill or multi-step capability for a task, given the tools, policies, trust requirements, and budget constraints of the environment it is operating in.

This is not primarily a marketplace for markdown files. It is a runtime decision layer for agent systems.

## 2. The Problem

MCP and adjacent tooling are making it easier to expose tools to models and agents. That solves tool access. It does not solve capability choice.

In practice, agents still need help answering questions like:

- What can I actually accomplish with the tools available here?
- Which option is approved and trustworthy?
- Which option is executable with the tools, scopes, and policies I have right now?
- Which route is worth using at this budget and latency target?
- How do I combine multiple steps without hardcoding a brittle workflow?

Today, that logic is usually spread across local prompts, hand-installed skills, product-specific glue code, and human judgment.

## 3. Why Now

Today’s strongest models can often brute-force around this gap. With enough context and tool access, they can infer plausible workflows even when those workflows have not been explicitly described.

That is useful in the short term, but it is not a complete long-term architecture.

The pressure in production systems points the other way:

- Agents will often run on smaller or more cost-sensitive model stacks.
- Enterprise environments prefer constraint, auditability, and approved paths over open-ended improvisation.
- Tool ecosystems are getting larger and more dynamic, which makes implicit model knowledge less reliable.
- Multi-step, multi-provider workflows create real trade-offs around trust, policy, and economics.

As those pressures increase, capability discovery and constrained runtime choice matter more, not less.

## 4. Who Loom Is For

Primary audiences:

- Agent platform builders who need capability discovery and selection above the tool layer
- Enterprises with internal workflows, compliance constraints, and approved providers
- Teams building multi-agent or multi-tool systems where routing and composition matter
- Developers who want shared capabilities to stay current without manual reinstall/update cycles

Loom is most valuable in environments with:

- Many tools or providers
- Changing workflows
- Org-specific policy or process
- Meaningful trust and approval requirements
- Cost or latency constraints

Loom is less compelling for:

- Solo users with a frontier model and a small, stable local setup
- One-off tasks where best-effort tool use is acceptable
- Simple workflows already covered by a handful of local skills

## 5. What Makes Loom Different

### Better discovery

Loom resolves from task intent to the best matching skill or capability. The point is not just search. The point is choosing a usable path for the task at hand.

### Better trust and provenance

Skills and capabilities are signed, evaluated, tiered, and continuously re-checked. The agent can distinguish between "available" and "appropriate to trust."

### Better dependency awareness

Loom understands what a capability needs to run. It can prefer options that fit the current tool availability, scopes, network constraints, and data handling requirements.

### Better composition

Loom models higher-order outcomes as first-class capabilities, not just flat lists of instructions. A runtime can resolve a task into a structured plan with steps, data flow, and fallbacks.

### Better org-specific adaptation

Community capabilities can be layered with corporate policy and personal preference using `extends`. Shared task shapes stay portable while execution remains locally governed.

### Better economics

Capabilities carry cost and duration metadata so runtimes can route based on budget, latency, and quality trade-offs instead of treating all viable paths as equivalent.

## 6. The Core Product Claim

Loom does not make agents intelligent by itself.

It makes them better at constrained choice:

- choosing the right capability
- in the right environment
- under the right trust and policy constraints
- at the right cost

That is the product.

## 7. Example Story

An agent is asked to produce a vendor-risk briefing.

Without Loom, a strong model may improvise a workflow from whatever tools it sees. That can work, but it may use the wrong providers, miss an internal check, exceed cost expectations, or route sensitive data through an external step that policy would reject.

With Loom, the runtime can resolve a capability that:

- matches the task shape
- uses approved internal and external sources
- respects trust and data-flow constraints
- exposes step-by-step execution guidance
- surfaces alternatives when the preferred route is unavailable or too expensive

The improvement is not just a nicer prompt. It is a better runtime decision.

## 8. Messaging Guardrails

When describing Loom, we should emphasize:

- capability resolution, not file hosting
- runtime choice under constraints, not generic orchestration
- portable task contracts plus local policy binding
- agents and runtimes as primary consumers

We should avoid leading with:

- "marketplace"
- "download registry"
- "workflow engine"
- "agent operating system"

Those frames either undersell the product or imply a much broader system than we are building.

## 9. Claims We Should Be Able to Prove

The product and messaging should eventually be able to support claims like:

- Loom returns better task matches than keyword search or static local skill lookup.
- Loom can explain why one viable capability was chosen over another.
- Loom can reject or downrank capabilities that do not fit the current runtime constraints.
- Loom can resolve layered capabilities that combine community knowledge with local policy.
- Loom can route between viable paths using trust, dependency, and economic metadata.

If we cannot demonstrate these clearly, the messaging is ahead of the product.

## 10. Near-Term Messaging Angle

For early messaging, the most credible frame is:

"Loom helps agents choose the right capability for a task, in the environment they are actually running in."

That is narrower than a grand platform claim, but it is concrete, legible, and defensible.
