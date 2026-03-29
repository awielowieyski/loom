# Loom: Capability Resolution for the Cognitive Core

A whitepaper on the architectural need for capability resolution in agent systems, and a concrete system that addresses it.

**Date**: 2026-03-25
**Status**: Draft
**Author**: Adam

---

## Abstract

Agent systems are converging on a pattern that might be called the cognitive core: a lean reasoning engine that delegates functional work to external tools, services, and other agents rather than carrying the full solution internally. This pattern is already visible in production systems and is likely to accelerate as deployment economics, enterprise constraints, and tool ecosystem growth create pressure against monolithic, improvisation-heavy architectures.

The Model Context Protocol has established a credible standard for how agents access tools. What it does not yet provide is a shared way for agents to understand what those tools can accomplish together, under what constraints, with what trust assumptions, and at what cost. That gap, between tool access and capability choice, is where agent systems most frequently fail in practice: not because they cannot call a tool, but because they do not know which tool, or which combination of tools, is the right one for the task at hand.

This paper describes that gap, argues that it will widen rather than narrow as the ecosystem matures, and presents Loom: a capability resolution service designed to help agents make better decisions about what to do, given what they have, under the constraints they face.

---

## 1. The cognitive core convergence

There is a useful idea, articulated most clearly by Andrej Karpathy, that the long-term shape of an agent system is something like a cognitive core: a reasoning engine that is good at understanding tasks, evaluating options, and orchestrating work, but that does not attempt to carry the full solution inside itself. Instead, it delegates. It calls tools. It follows recipes. It routes to specialised services. It composes capabilities from external parts.

This is not a speculative prediction. It is a description of what is already happening.

Contemporary agent frameworks are structured around exactly this pattern. The model reasons about the task. It consults available tools. It follows structured instructions (skills, prompts, workflows) that encode known ways of accomplishing specific outcomes. The quality of the agent's work depends not only on the model's reasoning ability but on the quality, relevance, and trustworthiness of the external capabilities it can reach.

Whether this pattern becomes the dominant architecture for all agent systems is genuinely uncertain. Frontier models are becoming more capable, not less, and it is possible that very large, very powerful models will continue to carry more of the solution internally than the cognitive core thesis suggests. That said, several independent pressures push toward delegation rather than internalisation, and they are worth taking seriously even if the full cognitive core thesis proves too strong.

**Economics.** Frontier models are powerful but expensive. Many useful agentic deployments will be built around smaller, cheaper models that are strong at reasoning and routing but cannot carry an entire complex workflow inside a single context window. These systems need external capability descriptions more, not less. The interesting empirical question is not whether frontier models can improvise around the gap, but what happens when you pair a fast, cheap model (a Haiku-class or Qwen-class system) with structured capability resolution versus without it. Early indications suggest the delta is significant.

**Enterprise constraint.** This is perhaps the most durable pressure, and the one least dependent on the cognitive core thesis being fully correct. Even if models improve dramatically, enterprises still need explicit capability resolution because auditability, policy enforcement, and cost governance are organisational requirements, not compensations for model weakness. A model that can infer the right workflow is not the same as a model that can prove it chose an approved workflow, within budget, using authorised providers, with an auditable trace. These are governance properties, and they require explicit metadata regardless of how capable the underlying model becomes.

**Ecosystem scale.** Tool ecosystems are growing rapidly. MCP alone has reported more than 10,000 public servers. As the number of available tools increases, the combinatorial space of possible compositions grows faster. Implicit knowledge of what is available and how it should be combined becomes progressively less reliable.

**Specialisation.** As the ecosystem matures, specialised providers emerge for specific tasks: financial data retrieval, compliance checking, document generation, code analysis. An agent that can discover and evaluate these specialised capabilities at runtime is more capable than one that relies on a static, hand-curated list.

The full cognitive core convergence may or may not arrive in the form Karpathy describes. But even under more conservative assumptions about model architecture, the pressures above create real demand for some form of capability resolution. The question is less whether that demand exists and more what shape the solution should take.

---

## 2. The gap between tools and capabilities

The easiest way to describe the missing layer is this: protocols like MCP expose tools, but agents need capabilities.

A tool is a relatively local abstraction. It has a name, a schema, some invocation semantics, and an output. "Search the web" is a tool. "Read a file" is a tool. "Query a database" is a tool.

A capability is a broader, outcome-oriented abstraction. "Produce a competitive landscape briefing" is not a tool. It is a composed capability that might involve search, retrieval of financial filings, ranking, filtering, synthesis, citation handling, and document generation. Each of those steps might use a different tool or service. The composition has preconditions, trust requirements, data flow constraints, and cost implications that no individual tool description captures.

Humans bridge this gap constantly. A developer looks at a set of available MCP servers and understands, from experience and context, how they might be combined into something useful. But that understanding lives outside the protocol. It sits in documentation, in product configuration, in the developer's head, or increasingly in ad hoc prompting that the model interprets at runtime.

This works tolerably well under two conditions: the set of tools is small and stable, and a capable human is available to supervise. It works less well as either condition weakens.

Consider a concrete scenario. An agent is asked to produce a vendor-risk briefing. It can see several relevant tools: an internal ticketing server, a financial data provider, a document repository, and an external search service. The problem is not tool access. The agent can call any of them. The problem is deciding what to do with them.

Can internal operational data be passed into an external search step? Which credentials should be delegated downstream, and with what scope? Is a premium financial data provider justified for this task, or should the system use a cheaper route? If the financial data service is unavailable, is there a fallback that produces an acceptable result? What does a good vendor-risk briefing actually look like, and what steps reliably produce one?

None of these questions are answered by tool schemas. They are answered by capability descriptions: structured knowledge about what can be accomplished, how, under what constraints, and at what quality level.

The gap, then, is not invocation. It is governed composition. And it has three interdependent dimensions.

**Semantic.** What outcomes are achievable with the available tools and services? What compositions of tools produce meaningful results? What does good output look like for a given task class?

**Trust and provenance.** Which capabilities are trustworthy? Who authored them? Have they been evaluated? What data flows do they create, and are those flows permissible under the current policy? Can a downstream service be trusted with the credentials and data it would need?

**Economic.** What does it cost to execute a given capability? Are there cheaper alternatives with acceptable quality? Is the premium route justified for this particular task? Can budget and latency constraints be factored into the routing decision?

These dimensions are not independent. A cheaper capability that requires lower trust may be acceptable for a draft summary but not for regulatory analysis. A highly trusted capability that costs ten times as much may be worth it for a compliance-critical workflow but wasteful for an internal sketch. The routing decision is a joint optimisation across all three.

My working view is that this three-dimensional gap represents a genuine architectural layer: not merely a product opportunity, but a structural requirement that the ecosystem will need to address as agent systems mature.

---

## 3. Why the gap widens

There is a reasonable objection to the above: that increasingly capable models may reduce the need for explicit capability resolution by learning to infer composition directly from tool descriptions and examples. Today's frontier models can often brute-force around the gap with enough context, strong enough reasoning, and access to web search and retrieval.

This objection has real force in the short term. But I think it underestimates several pressures, and it also misidentifies what capability resolution is for.

**Recipes are independently valuable.** The strongest counter to "models will figure it out" is not about model limitations. It is about the independent value of known-good recipes. Even a highly capable model benefits from a pre-approved, evaluated, version-controlled description of how to accomplish a task well. The rapid growth of SKILLS.md distribution across agent frameworks is evidence of this: developers are voluntarily creating and sharing structured capability descriptions not because their models cannot improvise, but because recipes produce more consistent, higher-quality results than improvisation. A model following a well-tested recipe for writing release notes will, on average, produce better release notes than a model improvising the process from scratch each time. This is true regardless of the model's raw capability.

**Smaller models benefit disproportionately.** The economics of deployment are pushing toward smaller, cheaper model stacks for many agentic workloads. A Haiku-class or Gemini Flash-class model paired with structured capability resolution can plausibly match or exceed a frontier model improvising without it, at a fraction of the cost. This is an empirical claim that should be tested directly, and it would be interesting to run systematic comparisons across model sizes (including models as small as Qwen 1.6B) with and without capability resolution. But the directional expectation is clear: the smaller the model, the more it gains from external structure. Capability resolution is not a crutch for weak models; it is a multiplier that makes any model more effective, with the largest gains at the lower end of the capability spectrum.

**More tools means harder choice, not easier.** As tool ecosystems grow, the number of possible compositions grows combinatorially. A model with access to five tools can plausibly evaluate all reasonable compositions in context. A model with access to fifty tools, each with multiple scopes and configuration options, faces a much harder selection problem, particularly when the wrong composition is not merely suboptimal but policy-violating.

**Enterprise constraints are not model weaknesses.** In production enterprise deployments, the question is not "can the model figure out a plausible workflow?" but "can it figure out a workflow that complies with data residency rules, uses only approved providers, respects role-based access controls, stays within budget, and produces an auditable trace?" These are not shortcomings that better models will outgrow. They are governance requirements that exist independently of model capability and that require explicit metadata to satisfy.

**Reproducibility matters.** When an agent improvises a workflow, it may produce a good result once. But producing the same quality consistently, across different model versions, different tool configurations, and different invocation contexts, is much harder without a stable capability description that encodes what good execution looks like.

**Composition creates non-obvious risks.** Individual tools may be safe and well-behaved in isolation. Composed into a workflow, they can create data flows, trust relationships, and cost exposures that are difficult to reason about from tool descriptions alone. A capability description that makes these composition effects explicit is a safety mechanism, not just a convenience.

For these reasons, I think the demand for capability resolution will grow as the ecosystem matures, regardless of how capable individual models become. The question is not whether models can improvise workflows. Many already can. The question is whether improvisation is the right default when you need consistency, auditability, cost control, and policy compliance. For a growing class of use cases, it is not.

---

## 4. What capability resolution requires

If the gap is real and growing, the next question is what a system designed to address it would need to provide. My current view is that useful capability resolution requires at least six properties, and that most existing approaches in the ecosystem satisfy at most two or three.

### 4.1 Semantic resolution from task intent

The most basic requirement is that an agent should be able to describe what it needs to accomplish, in natural language or structured form, and receive back a capability that matches that intent. This is more than keyword search. It requires understanding task semantics well enough to match "produce a competitive landscape briefing" to a capability that involves search, financial data retrieval, synthesis, and document generation, even if the capability was not described using those exact words.

This is not a solved problem, but it is an approachable one. Embedding-based semantic search, combined with structured metadata about what a capability does and when it applies, can produce surprisingly good matches. The harder challenge is ranking: when multiple capabilities match the intent, choosing the one that best fits the current context.

### 4.2 Constraint-aware ranking

Discovery alone is not sufficient. The agent needs to choose among viable options based on the constraints of its current environment.

A capability that requires a financial data API is not useful if that API is not available. A capability with a "high" cost profile is not appropriate if the budget is "low." A capability at "experimental" trust tier may be acceptable for a draft but not for a compliance-critical output. A capability that requires network access may be unsuitable if the agent is operating in an air-gapped environment.

Constraint-aware ranking means that the resolution system understands the agent's runtime context (what tools are available, what trust floor applies, what budget exists, what data classification constraints are in force) and factors those constraints into the ranking decision. This is not just filtering. It includes soft penalties, alternative suggestions, and explicit explanations of why a particular option was chosen or rejected.

### 4.3 Composition as a first-class concept

Many meaningful outcomes require multiple steps. A capability resolution system that can only return atomic, single-step instructions is fundamentally limited. It needs to model composition: multi-step capabilities with declared inputs, outputs, data flow between steps, fallback handling for unavailable dependencies, and trust propagation across the composition chain.

This is where the gap with existing approaches is widest. Most skill directories and prompt libraries treat capabilities as flat, independent units. But the most valuable capabilities in practice are composed ones, and composition introduces its own challenges around trust, data flow, and failure handling that atomic descriptions cannot address.

### 4.4 Trust and provenance

In any system where agents consume external capability descriptions, trust is a critical concern. An agent following instructions from an untrusted source is a security vulnerability. An agent following instructions that were once trustworthy but have since been modified without detection is a subtler one.

Useful capability resolution requires at minimum: cryptographic provenance (who authored this, and can the content be verified as unmodified), earned trust tiers (not self-declared but computed from evaluation scores and usage outcomes), and compositional trust propagation (a composed capability is only as trustworthy as its least trustworthy component).

These are not theoretical concerns. Surveys of existing open skill registries have found meaningful rates of quality issues and even malicious content. A resolution system that surfaces capabilities to agents without trust mechanisms is a liability, not an asset.

### 4.5 Economic metadata

Agents cannot make sensible routing decisions without visibility into cost. Many of the tools and services accessible through MCP have their own pricing models, rate limits, and quality tiers. If there are three viable ways to fulfil a capability and they differ in cost, latency, and quality, the choice among them is not just a technical decision. It is an economic one.

A resolution system that treats cost as an afterthought will produce technically correct but economically wasteful routing decisions. Cost and duration metadata should be first-class properties of capability descriptions, available to the resolution logic at decision time.

### 4.6 Adaptation across organisational boundaries

Perhaps the most practically important requirement is the ability to layer capability descriptions across organisational boundaries. A community may define a general-purpose approach to producing release notes. An enterprise may need to layer corporate-specific compliance requirements on top of that general approach. An individual developer may want to add personal workflow preferences on top of the corporate layer.

This layering must be additive, predictable, and independently maintainable. The community layer should not need to know about the corporate layer. The corporate layer should not need to fork the community layer to add its constraints. The personal layer should not need to re-specify what the community and corporate layers already handle.

This is a specific architectural requirement, not a general wish. Without it, enterprises face an unpleasant choice: fork every community capability they use (creating maintenance burden and losing upstream improvements) or accept community capabilities without modification (sacrificing org-specific governance). Neither is acceptable at scale.

---

## 5. Loom

Loom is a capability resolution service designed around the six requirements above. It helps agents choose the right skill or multi-step capability for a task, given the tools, policies, trust requirements, and budget constraints of the environment they are operating in.

It is useful to be precise about what Loom is and is not.

Loom is not a marketplace for prompt files. It is not a workflow execution engine. It is not an agent framework or an agent operating system. It does not run capabilities. It resolves them.

The distinction matters because it defines the architectural boundary. Loom's job is to take a task description and a set of runtime constraints, and return the best matching capability, fully resolved, with all dependencies evaluated, alternatives surfaced, and a clear explanation of why this particular option was chosen. The agent runtime then executes the capability using its own tools and infrastructure. Loom is the intelligence layer for capability choice. Execution remains the responsibility of the agent.

### 5.1 Skills

The atomic unit in Loom is a skill: a structured description of how to accomplish a specific class of task. A skill is not code. It is not a raw prompt. It is a semantic contract that describes what the task is, when the skill applies, what tools and services it requires, how to perform it well, and what good output looks like.

A skill carries structured metadata alongside its instructional content: a category within a hierarchical taxonomy, a version following semantic versioning, declared dependencies on specific MCP servers or APIs, trust requirements around data classification and network access, cost and duration profiles, and evaluation scenarios that define what success looks like.

This metadata is not decorative. It is what makes resolution possible. Without declared dependencies, the resolution system cannot determine whether a skill is executable in the agent's current environment. Without cost profiles, it cannot factor economics into the routing decision. Without evaluation scenarios, it cannot assess or maintain the skill's quality over time.

### 5.2 Capabilities

A capability is a composed recipe that chains multiple skills into a higher-order outcome. Where a skill describes how to accomplish a single task, a capability describes how to accomplish a multi-step workflow: which skills to invoke in what order, how data flows between steps, what happens when an optional step's dependencies are not met, and what the expected outcome of the full composition looks like.

Capabilities are first-class objects in Loom, not ad hoc compositions assembled at query time. Each capability declares its steps, with explicit input and output bindings between them. Each step references a skill by URI, declares its role in the workflow, specifies what data it needs and what data it produces, and indicates whether it is required or optional.

Data flow between steps carries classification metadata (internal, external, or confidential) so that trust evaluation can reason about what data crosses what boundaries. A step that receives confidential internal data and passes it to an external service creates a specific trust concern that the resolution system can surface.

The vendor-risk briefing example illustrates this concretely. A capability for that task might compose three skills: one for gathering public information about the vendor, one for retrieving financial filings and credit data, and one for synthesising findings into a structured risk assessment. The financial data step might be marked as optional, with graceful degradation if the required API is unavailable. The data flow from the public search step to the synthesis step is classified as external. The data flow from the financial step to synthesis is also external. These classifications allow the resolution system to generate trust warnings when the composition involves data flows that might concern the consuming enterprise.

### 5.3 Resolution

Resolution is the core operation. An agent describes what it needs to accomplish. Optionally, it provides context: what trust floor applies, what cost budget exists, what tools are currently available, what data classification constraints are in force. Loom returns the best matching skill or capability, fully resolved.

The resolution process works in several stages. First, the task description is embedded and compared against the registry using semantic similarity. This produces a set of candidate matches. Then, constraint-aware ranking evaluates each candidate against the provided context: does it satisfy the trust floor? Are its dependencies met? Does it fit the cost budget? Is it flagged as deprecated or stale?

The result is not just the winning match. It includes dependency status (which dependencies are satisfied and which are missing), ranked alternatives with explicit tradeoff descriptions, rejected candidates with explanations of why they were rejected, and a selection rationale that traces the reasoning behind the choice.

This transparency is a deliberate design choice. An agent, or a human supervising an agent, should be able to understand not just what was chosen but why. "Preferred over higher-cost alternatives because cost budget is low" is a different kind of answer than "best match." The former is auditable. The latter is opaque.

### 5.4 Resolution, not execution

It is worth emphasising that Loom resolves capabilities but does not execute them. When a capability is resolved, every skill referenced in every step is fully expanded and embedded in the response. The agent receives a self-contained execution plan: step-by-step instructions, fully resolved, with all metadata and dependency information included. The agent does not need to make additional calls to Loom during execution.

This separation has several virtues. It keeps Loom architecturally simple: a resolution service, not a workflow engine. It avoids Loom becoming a bottleneck in the execution path. It allows the agent runtime to adapt execution to its own capabilities, parallelising independent steps, handling retries with its own logic, integrating with its own observability and logging infrastructure.

And it means that the agent, having received a resolved plan, can operate without further network access to Loom. This matters in air-gapped or latency-sensitive environments, and it matters for resilience.

### 5.5 Resolution in practice

The abstractions above are clearer when traced through a concrete example. This walkthrough follows a single resolution from task to plan, and the rest of the paper will refer back to it.

An agent operating inside a mid-size European company receives a request: "Produce a vendor-risk briefing for Nexora Systems." The agent has access to several MCP servers: internal ticketing, a document repository, web search, and a Slack integration. It does not have access to a premium financial data API. The enterprise has configured a trust floor of "community" and a cost budget of "moderate."

The agent calls Loom's resolve endpoint with the task description and this context.

Loom embeds the task description and runs semantic search against the registry. Several candidates match. The highest-ranked is a capability called `vendor-risk-briefing`, a three-step composition at community trust tier. An alternative, `quick-company-summary`, is a single-step skill that produces a lighter-weight overview. A third candidate, `deep-vendor-diligence`, is a five-step capability requiring a premium financial API and rated at high cost.

Constraint-aware ranking proceeds. `deep-vendor-diligence` is rejected: its cost profile exceeds the moderate budget, and it requires a financial data API the agent does not have. The rejection rationale is recorded: "Cost profile 'high' exceeds budget 'moderate'; required dependency 'financial-data-api' not available." `quick-company-summary` is viable but ranks lower on semantic match because it does not cover risk assessment. `vendor-risk-briefing` ranks highest.

Loom resolves the capability's three steps. Step 1 references `web-search-structured`: the agent has a web search MCP server, so this dependency is satisfied. Step 2 references `financial-data-retrieval`: the agent does not have the required API. But this step is marked `required: false`, meaning the capability degrades gracefully without it. The resolution notes the missing dependency and flags it: "Step 2 skipped; financial-data-api not available. Briefing will proceed without financial filings." Step 3, `risk-synthesis`, requires only the outputs of earlier steps and is satisfied.

The data flow classification surfaces a trust warning. The flow from Step 1 (web search, classified as external data) into Step 3 (synthesis) means the briefing will incorporate external data. The resolution response includes: "Data flow from web-search-structured to risk-synthesis classified as external. Output may contain unverified external claims."

Now, the extends mechanism activates. The company has a corporate Loom instance with a skill called `acme-vendor-assessment` that extends `loom://vendor-risk-briefing@community`. The corporate extension adds: cross-reference against the company's approved vendor list via an internal MCP server; apply a risk threshold below which vendors are automatically flagged; include a GDPR compliance section because the company is EU-based; query the internal incident database for prior issues with this vendor.

The agent also has a personal skill on disk, `my-vendor-workflow`, that extends the corporate skill. It adds: post the completed briefing to #procurement-review on Slack; create a Jira ticket in the VENDOR project.

Loom walks the extends chain, resolves all three layers, and merges them with section delimiters. The agent receives a single response: a fully resolved execution plan with the community capability's three steps (one skipped), the corporate layer's additional constraints and checks, the personal layer's notification preferences, dependency status for every step, the trust warning about external data, the rejected alternative with its rejection rationale, and the viable alternative (`quick-company-summary`) with a note that it provides less coverage.

The agent now has everything it needs to execute. It proceeds step by step, using its available MCP servers, following the merged instructions, skipping the financial data step, applying the corporate risk threshold, and posting the result to Slack when finished.

No further calls to Loom are required. The resolution took one request. Execution is entirely the agent's responsibility.

This is what capability resolution looks like in practice: not a single moment of intelligence, but a structured decision that factors in task semantics, dependency reality, trust policy, cost constraints, organisational governance, and personal preferences, and produces an executable plan that the agent can follow with confidence.

---

## 6. The extends mechanism

The walkthrough above illustrates one of Loom's most architecturally significant features: the extends mechanism. It addresses the layering requirement described in Section 4.6, and it does so with a simplicity that belies the difficulty of the underlying problem.

### 6.1 The problem extends solves

Consider a common situation. A community of practitioners develops a well-tested approach to a specific task: writing release notes, conducting a security review, onboarding a new vendor. This knowledge is encoded as a skill and made available publicly. It represents genuine collective expertise.

An enterprise wants to use this skill but needs to add constraints specific to its own environment: use only approved data providers, comply with specific regulatory requirements, route outputs through internal review workflows, apply org-specific quality standards. The enterprise has three bad options:

**Fork.** Copy the community skill and modify it. This works initially but creates a maintenance burden. When the community skill improves (new best practices, updated tool integrations, refined instructions), the fork diverges. The enterprise must manually merge upstream changes or accept growing staleness.

**Accept without modification.** Use the community skill as-is and handle org-specific requirements through separate mechanisms: policy layers, wrapper prompts, post-processing. This avoids forking but scatters the capability logic across multiple systems, making it harder to reason about and audit.

**Rebuild from scratch.** Ignore the community skill entirely and build an internal version. This maximises control but sacrifices the community's accumulated expertise and creates redundant effort.

None of these options scale well across the dozens or hundreds of capabilities an enterprise might use.

### 6.2 How extends works

The extends mechanism provides a fourth option: layered refinement. A skill at any layer can declare that it extends a skill at a lower-priority layer, using a URI reference that specifies the source and version.

Resolution priority follows a clear hierarchy: personal overrides corporate, corporate overrides community. When an agent resolves a skill that uses extends, Loom walks the chain, resolving each referenced skill in turn, and produces a merged result with clear section boundaries.

The merge semantics are intentionally simple. The base skill's content appears first. Corporate extensions appear under a corporate context header. Personal extensions appear under a local overrides header. The agent (which is an LLM) reads the merged content as layered instructions where later sections refine or override earlier ones.

This simplicity is deliberate. More sophisticated merge strategies (structural diffing, field-level overrides, conflict resolution algorithms) would be more powerful in theory but much harder to make predictable in practice, particularly when the consumer is a language model interpreting natural-language instructions. Simple concatenation with clear section headers produces results that are predictable, inspectable, and easy for both humans and models to understand.

### 6.3 What this enables

The extends mechanism transforms the relationship between community knowledge and enterprise governance from a tension into a layered architecture.

The community layer defines the task shape: what the task is, what steps are typically involved, what good output looks like, what tools are commonly used. This layer benefits from broad contribution and continuous improvement.

The corporate layer binds that task shape to organisational reality: approved providers, compliance requirements, internal data sources, risk thresholds, output standards. This layer is maintained by the enterprise and never leaves its control boundary.

The personal layer adds individual preferences: specific notification channels, preferred formatting, personal workflow integrations. This layer lives on the individual's machine and is never transmitted to any Loom instance.

Each layer is independently versioned, independently maintained, and independently evaluable. The community skill can improve without affecting the corporate extension. The corporate extension can change policy without touching the community skill. The personal layer can be modified freely without affecting either.

Perhaps most importantly, the boundary between layers corresponds to a trust boundary. Community skills are resolved from the public Loom registry. Corporate skills are resolved from a private corporate Loom instance. Personal skills live locally. Data and instructions flow downward in the resolution chain, from personal to corporate to community, but never upward. A corporate skill cannot reach into a user's personal configuration. A community skill cannot access corporate-internal knowledge.

This architecture makes it possible for enterprises to participate in a shared capability ecosystem without sacrificing governance. The portable part (the task shape) travels through the public layer. The governed part (policy, constraints, approved paths) stays private. The same capability contract can be bound to different policies by different enterprises, producing different execution paths from the same task description.

---

## 7. Trust, quality, and the living registry

A capability resolution service is only as valuable as the capabilities it contains. If the registry fills with low-quality, stale, or malicious content, resolution becomes a liability rather than an asset.

This is not a hypothetical concern. Analysis of existing open skill registries has found that a significant fraction of published skills have quality issues, and a smaller but non-trivial fraction contain content that is actively harmful: prompt injections, instructions that exfiltrate data, or capabilities that produce subtly incorrect results. The problem is structural; registries that accept contributions without meaningful quality gates and maintain content without continuous evaluation inevitably accumulate debt.

Loom's approach to this problem is what might be called a living registry: a system that does not merely store capabilities but actively evaluates, monitors, and maintains them over time.

### 7.1 Evaluation at submission

When a skill is submitted to Loom, it passes through a multi-phase evaluation pipeline before it becomes available for resolution.

The first phase is entirely deterministic: structural validation, complexity bounds, and pattern-based scanning for known injection techniques. This phase has no LLM in the loop and therefore no injection surface. It catches malformed submissions, unreasonably large content, and known attack patterns quickly and cheaply.

The second phase decomposes the skill into evaluation-safe fragments: separating metadata from content, encoding content as structured data rather than raw text, normalising unicode to remove zero-width characters and directional overrides. This preparation step is critical for the phases that follow, because it ensures that skill content is never presented to an evaluation model as instructions to follow, only as data to assess.

The third phase uses LLM-based evaluation, but with careful isolation. Each quality dimension (clarity, completeness, safety, correctness) is evaluated in a separate LLM call. The skill content appears in a structured data field within the prompt, never as part of the system message or as instructions. The evaluation model is asked to assess the content, not to follow it. Multiple independent runs produce scores that are aggregated by median, with outlier detection to identify attempts at score manipulation.

The fourth phase, for skills that include executable evaluation scenarios, runs those scenarios in a sandboxed environment: a minimal container with no network access, limited memory, read-only filesystem, and strict timeouts.

The fifth phase aggregates scores across dimensions, computes confidence intervals from the spread of independent runs, and applies injection response logic: skills that trigger injection detection in two or more evaluation dimensions are quarantined for human review rather than published.

This pipeline is deliberately conservative. The goal is not to be the fastest path to publication but to ensure that every skill available for resolution has passed a meaningful quality bar. Speed of publication is much less important than trust in what gets published.

### 7.2 Earned trust

Trust in Loom is computed, not declared. A newly submitted skill that passes evaluation enters the registry at the "experimental" tier. It is available for resolution but ranked below higher-trust alternatives.

Promotion to the "community" tier requires meeting quantitative thresholds: a composite evaluation score above a defined floor, a minimum number of usage reports from agents in production with a high success rate, no active security flags, and a valid cryptographic signature from the author.

Promotion to the "verified" tier requires all of the above plus review by a human steward: a category expert who evaluates the skill against domain-specific quality standards. This is a deliberately manual gate. Verified status is the highest trust signal in the system, and it should not be achievable through gaming automated metrics alone.

Trust never flows upward through composition. A capability that includes an experimental-tier skill in any of its steps has an effective trust tier of experimental, regardless of the trust tiers of its other steps. This is a hard constraint, not a soft signal, and it gives consumers a clear, worst-case trust bound for any composed workflow.

### 7.3 Continuous maintenance

The evaluation pipeline runs not only at submission but continuously throughout a skill's lifecycle. Several mechanisms drive this.

**Usage signals.** Agents report the outcome of skill execution (success, partial success, or failure) back to Loom through a lightweight, privacy-preserving reporting mechanism. No agent identity, query text, or user information is collected. A one-way hash of the task category enables cohort analysis without identifying individual queries. These usage signals are aggregated over rolling windows and feed back into the trust system.

**Signal-driven re-evaluation.** When usage signals indicate a problem (a high failure rate over a recent window, or a significant drop in success rate compared to the previous period), the skill is automatically re-evaluated through the full pipeline. This catches skills that have become stale due to changes in the tool ecosystem, model behaviour, or external APIs they depend on.

**Scheduled re-evaluation.** Even in the absence of negative usage signals, skills at the community and verified tiers are periodically re-evaluated. A rotating sample ensures full coverage over a defined cycle. This catches gradual drift that usage signals alone might miss.

**Drift detection.** When re-evaluation produces a score that differs significantly from the stored score, the skill is flagged for steward review. Importantly, it is not automatically demoted. Score drift may reflect changes in the evaluation model rather than changes in the skill's quality. The steward makes the determination.

**Deprecation.** Authors can mark skills as deprecated with a pointer to a successor. Deprecated skills remain resolvable but are ranked below non-deprecated alternatives, and the response includes the deprecation status and successor information. This provides a graceful migration path rather than a hard cutoff.

The cumulative effect of these mechanisms is a registry that improves over time. Good skills accumulate positive usage signals and rise in ranking. Poor skills accumulate negative signals and are re-evaluated or deprecated. Stale skills that no one uses are surfaced for review. The registry's quality is not a point-in-time property set at curation. It is a continuously maintained property that reflects actual usage and ongoing assessment.

### 7.4 Behavioural evaluation

Quality evaluation has a subtle vulnerability: a skill might produce content that looks good to an evaluator examining it statically but performs poorly when an agent actually tries to follow it. The instructions might be ambiguous, incomplete, or subtly misleading in ways that only become apparent during execution.

Loom addresses this with behavioural evaluation: a runner-judge architecture where one model attempts to follow the skill's instructions for a given scenario, and a separate model evaluates the quality of the output.

The critical design constraint is that the judge never sees the original skill instructions. It receives only the runner's output and the scenario's success criteria. This prevents a specific class of gaming where a skill is optimised to produce output that looks good relative to its own instructions rather than output that is genuinely useful.

Behavioural evaluation scores feed into trust tier promotion alongside static evaluation scores and usage signals. A skill that scores well on static evaluation but poorly on behavioural evaluation, indicating that its instructions are superficially clear but practically misleading, will not be promoted to community tier.

---

## 8. Corporate Loom: enterprise deployment

The architecture described above operates at two scales: a public registry serving the community, and private instances serving individual enterprises.

A corporate Loom instance is a private deployment of the same service, scoped to an organisation. It runs the same resolution logic, the same evaluation pipeline, the same trust system. The difference is scope: corporate skills are visible only to agents authenticated with the organisation's credentials. They encode org-specific knowledge (internal tool integrations, proprietary workflows, compliance procedures, approved providers) that should not be public.

Corporate instances can resolve references to the public registry. When a corporate skill uses extends to reference a community skill, the corporate instance resolves the community skill from the public registry (or from a cached mirror in air-gapped deployments), merges it with the corporate layer, and returns the combined result. The agent receives a single, coherent capability description that blends community knowledge with corporate governance.

This architecture has a specific commercial shape. The public registry is free. It creates ecosystem value by accumulating community knowledge and making it available to any agent. Corporate instances are the paid product. They capture the value of org-specific knowledge management, governed resolution, and private capability curation.

This alignment is deliberate. It means that the incentive to grow the public registry and the incentive to serve enterprise customers reinforce rather than conflict with each other. A richer public registry makes corporate extends more valuable. More corporate deployments create demand for higher-quality community skills.

### 8.1 The bootstrapping problem

The commercial model is sound in theory, but it faces a practical challenge that should be stated directly: a capability resolution service with sparse coverage is much less valuable than one with deep coverage, and coverage takes time to build. An enterprise evaluating Loom will not be persuaded by architectural elegance alone. It will ask: does the public registry already contain high-quality capabilities for the tasks my agents actually perform? If the answer is "not yet, but we are building toward broad coverage," most enterprises will solve the problem in-house or through adjacent platforms rather than wait.

This is the density problem, and it is the most important near-term commercial risk. The correct response is not to pursue breadth first but to pursue depth in a specific wedge where capability resolution is most obviously valuable.

The strongest initial wedge is likely compliance-heavy enterprise workflows: vendor risk assessment, regulatory reporting, internal audit preparation, data-handling compliance checks. These tasks share several properties that make them particularly good fits for Loom. They involve multi-step compositions across internal and external data sources. They have hard trust and data-flow constraints that improvisation handles poorly. They benefit enormously from the extends mechanism, because the general task shape is similar across enterprises but the specific regulatory requirements, approved providers, and risk thresholds differ. And they are tasks where the cost of getting it wrong (a compliance failure, a missed risk flag) is high enough to justify investment in structured resolution.

A secondary wedge is multi-tool research and reporting workflows: competitive landscape briefings, market analysis, technical due diligence. These are less compliance-critical but involve complex tool compositions (search, data retrieval, synthesis, document generation) where the difference between a good recipe and ad hoc improvisation is immediately visible in output quality.

The strategy, then, is not to build a general-purpose registry and hope it reaches critical mass. It is to build deep, high-quality coverage in one or two job-to-be-done clusters where capability resolution delivers clear, demonstrable value; prove the model there; and expand from that foundation. The vendor-risk briefing traced through Section 5.5 is not an arbitrary illustration. It is an example of the kind of task where Loom should be meaningfully better than the alternatives from day one.

---

## 9. Toward federation

The architecture described so far is centripetal: agents resolve capabilities from a central public registry or a private corporate instance. This is the right starting point for practical reasons; it is simpler to build, simpler to operate, and simpler to reason about trust. But it is likely not the endpoint.

The cognitive core thesis, taken to its logical conclusion, suggests that agents will increasingly delegate not just to tools but to other agents and specialised services. An agent that is good at reasoning about vendor risk but bad at financial analysis might delegate the financial analysis step to a specialised service that is better at it. That delegation requires everything that capability resolution provides (semantic matching, trust evaluation, cost awareness, provenance) but applied to a network of providers rather than a single registry.

Loom's architecture contains several design decisions that anticipate this evolution without attempting to build it prematurely.

**URI-based resolution.** Skills and capabilities are referenced by URIs with scheme prefixes: `loom://` for community, `corp://` for corporate. This namespace is extensible. A `partner://` scheme could resolve against a partner organisation's instance. A `federation://` scheme could resolve against a federated discovery network. The resolution logic already knows how to walk URI chains; extending it to walk across organisational boundaries is an architectural evolution, not a redesign.

**Trust propagation with minimum semantics.** The rule that a composed capability's trust tier equals the minimum across its steps is a federation-safe primitive. When a capability includes a step resolved from a different trust domain, the minimum-trust rule ensures that the overall trust assessment is conservative. No trust domain can inflate the trust of the composition by self-declaring high trust for its own steps.

**Scoped delegation.** The capability data model already supports scope narrowing: a step can declare that it needs only specific, limited access to the output of a previous step, not the full context. This is a delegation primitive. In a federated architecture, it would mean that a delegated service receives only the data it needs, with the scope constraint enforced by the delegating agent's runtime.

**Economic metadata.** Cost profiles and duration estimates, already present on every skill and capability, become routing inputs in a federated architecture. When an agent can delegate a task to multiple specialised providers, cost and latency metadata enable informed routing decisions without requiring the agent to query each provider for pricing.

These primitives are designed in but not built out. Federation introduces hard problems (distributed trust establishment, cross-organisational policy negotiation, payment settlement, dispute resolution) that are premature to solve today. But the architectural foundations are in place to evolve toward federation without discarding the resolution model that works today.

The analogy is not exact, but it is suggestive: DNS began as a simple, centralised name resolution system and evolved into a federated hierarchy that resolves names across organisational boundaries with delegated authority. Loom begins as a centralised capability resolution system. The path to federated resolution is visible in the architecture, even if the timeline is uncertain.

---

## 10. Relationship to adjacent systems

Loom occupies a specific position in the emerging agent infrastructure stack. Clarifying its boundaries helps avoid both overstatement and confusion.

**MCP and tool protocols.** MCP standardises how agents access tools: discovery, invocation, transport, authentication. Loom operates above this layer. It consumes tool availability information as input to resolution (an agent's available MCP servers are part of its resolution context) and produces capability descriptions that reference tools the agent can invoke through MCP. The relationship is complementary. MCP provides the wiring. Loom provides the routing intelligence.

**Skill and prompt directories.** Platforms that host skill files, prompt libraries, or agent instruction sets serve a discovery function, but typically without constraint-aware resolution, quality evaluation, trust mechanisms, composition support, or organisational layering. Loom is not a better file host. It is a different kind of system: a resolution service rather than a repository.

**Workflow engines.** Systems like Temporal and AWS Step Functions solve the mechanical problems of workflow execution: state management, retry logic, fan-out, observability. Loom does not compete with these systems. It addresses a prior question: given the current constraints, what workflow should be executed? The resolution layer decides what to do. The execution layer decides how to do it reliably.

**Gateway and marketplace platforms.** Some approaches centralise tool discovery, trust, pricing, and routing behind a gateway or marketplace. This is a viable architecture but optimises for different properties than Loom. Gateways tend toward centralisation and platform lock-in. Loom is designed for federation and enterprise self-hosting. The extends mechanism specifically enables portable capability contracts that work across providers without requiring a single intermediary.

**In-model reasoning.** Frontier models can often infer plausible workflows from tool descriptions alone. This is genuinely useful and will remain important. Loom does not replace model reasoning. It augments it with structured information that the model would otherwise need to infer or improvise: known-good composition patterns, explicit trust and cost metadata, evaluated quality signals, and organisational policy. The model still reasons about how to use the resolved capability. It just starts from a better-informed position.

---

## 11. Why this shape

If the problem described in this paper is real, there are at least three credible approaches to solving it beyond Loom's. Each has genuine strengths. The argument for Loom is not that these alternatives are wrong, but that Loom is better positioned on the specific properties that matter most: adoption speed, governance flexibility, and evolutionary capacity.

### 11.1 Protocol-level capability description

The most natural response to "the layer above MCP is missing" is to extend MCP itself. Initiatives like Server Cards already move toward richer machine-readable descriptions of individual servers. One could imagine a more ambitious extension: a standardised capability description schema built into the protocol, with composition semantics, trust metadata, and cost signals as first-class protocol features.

This approach has the advantage of universality. If capability description were part of the protocol, every MCP-compatible agent would speak it natively. The disadvantage is that protocol standardisation requires the ecosystem to agree on abstractions before those abstractions have been validated in practice. The history of standards efforts suggests that premature formalisation tends to freeze early, imperfect design choices. JSON-RPC succeeded where SOAP failed partly because it standardised less and left more to the application layer.

Loom takes the opposite approach: build a working system, learn which abstractions earn their keep through actual resolution and usage, and allow successful patterns to inform future protocol work if warranted. This is a deliberate sequencing choice, not an argument against eventual standardisation. But it means that Loom can iterate on its capability model (what metadata matters, how composition works, what trust signals are useful) at product speed rather than standards-committee speed.

There is a more specific limitation of protocol-level approaches: a protocol can describe capabilities, but it cannot evaluate or maintain them. Trust tiers, behavioural evaluation, continuous re-evaluation, drift detection, and usage-driven quality signals are runtime services, not schema features. A protocol can carry trust metadata; it cannot compute it. Loom's living registry is a service-layer concern that protocol extensions cannot replicate.

### 11.2 Gateway and marketplace centralisation

A second approach is to centralise capability discovery, trust, routing, and pricing behind a gateway or marketplace. This is the model familiar from app stores: a single intermediary controls what is available, evaluates quality, handles payment, and mediates trust. Several early agent infrastructure companies are pursuing variations of this pattern.

Gateways have real strengths. They can enforce quality standards, simplify billing, and provide a single integration point. For some use cases, particularly consumer-facing agent applications, a curated marketplace may be the right model.

The limitations become apparent in enterprise settings. Gateways centralise control, and enterprises are typically reluctant to route sensitive capability resolution through a third-party intermediary they do not control. Corporate knowledge, internal workflows, and proprietary process descriptions cannot live in someone else's marketplace. And gateways tend toward lock-in: once an organisation's capability descriptions live inside a specific gateway's schema and trust model, migration is expensive.

Loom's architecture specifically avoids this centralisation. Corporate Loom instances are self-hostable, running the same resolution logic on the organisation's own infrastructure. The extends mechanism allows enterprises to layer private governance onto public community knowledge without either layer depending on a single intermediary. The URI-based resolution model is designed for federation across organisational boundaries, not concentration behind a single gateway.

The deeper architectural difference is about where intelligence lives. In a gateway model, the intermediary makes routing decisions on behalf of the agent. In Loom's model, the agent makes its own routing decisions, informed by metadata and resolution logic that it can inspect, audit, and override. This keeps the agent as the decision-maker, which aligns better with enterprise governance expectations and with the cognitive core pattern itself.

### 11.3 Framework-embedded capability routing

A third approach is to build capability resolution into specific agent frameworks. LangChain, CrewAI, AutoGen, and similar frameworks could each develop their own capability registries, routing logic, and composition models as built-in features.

This has the advantage of tight integration. Framework-specific resolution can be deeply aware of the framework's runtime model, tool abstractions, and execution patterns. For teams already committed to a specific framework, the switching cost is minimal.

The disadvantage is fragmentation. If every framework builds its own capability resolution, the ecosystem ends up with multiple incompatible registries, each with its own trust model, its own quality standards, and its own skill format. Capabilities written for one framework do not work in another. Community knowledge is siloed rather than shared.

Loom is framework-agnostic by design. It operates through MCP, which is itself framework-agnostic. A skill resolved from Loom can be consumed by any agent runtime that can follow structured instructions, regardless of what framework it uses. This means that community knowledge accumulates in a single, shared registry rather than being fragmented across framework-specific silos.

There is also a governance argument. Framework-embedded resolution tends to be opaque: the framework's routing logic decides what capability to use, and the agent (or the human supervising it) may not have clear visibility into why. Loom's explicit selection rationale and rejection explanations make the routing decision auditable in a way that framework-internal routing typically is not.

### 11.4 The case for Loom's shape

None of the alternatives above are unreasonable. Protocol extensions may eventually emerge and Loom could inform them. Gateways will serve some market segments well. Framework-specific solutions will satisfy teams that have already standardised on a particular stack.

Loom's advantage is that it occupies a specific point in the design space that none of these alternatives cover: an independent resolution service that is framework-agnostic (via MCP), self-hostable (for enterprise governance), composable across organisational boundaries (via extends), and continuously self-improving (via the living registry). It standardises enough to enable shared capability knowledge without standardising so much that it becomes rigid or requires ecosystem-wide consensus to evolve.

The bet is that this particular combination of properties, rather than any single feature, is what the ecosystem needs now. Protocol extensions are too slow to iterate. Gateways centralise too much. Framework-specific solutions fragment too much. Loom aims for the middle ground: shared enough to build a community, flexible enough to serve enterprises, and evolvable enough to track a rapidly changing landscape.

---

## 12. Objections and honest uncertainties

Several objections to this line of argument deserve direct engagement.

**"Models will get good enough to make this unnecessary."** This deserves a more nuanced answer than "no." Models will absolutely get better at inferring compositions from tool descriptions. The question is whether that makes capability resolution unnecessary or merely changes what it is for. My view is the latter. Even a model that can perfectly infer the right workflow still benefits from a pre-approved, evaluated recipe that has been tested against real scenarios, version-controlled, and layered with organisational policy. The value of capability resolution is not primarily about compensating for model weakness; it is about providing consistency, auditability, and governance. A surgeon who can improvise does not therefore discard established surgical protocols. The protocol provides reliability that improvisation, however skilled, does not. That said, if models become so capable that the governance argument also weakens (because models can reliably self-audit and self-constrain), then the case for Loom does diminish. I hold that as a genuine uncertainty.

**"This should be a protocol extension, not a product."** There is a reasonable argument that capability description should be standardised at the protocol level rather than implemented as a separate service. My view is that the problem space is not yet well enough understood for formal standardisation. A working system that demonstrates which abstractions earn their keep is more valuable at this stage than a specification designed in the abstract. If Loom's abstractions prove durable, they could inform future protocol work. That seems like the right sequence.

**"Enterprises will build this internally."** Many will, and some already are. The question is whether building bespoke capability resolution for each enterprise is a good use of resources, or whether a shared layer with enterprise-specific configuration (via extends and corporate instances) is more efficient. The same question has been answered in favour of shared infrastructure in analogous domains: source control, CI/CD, observability, authentication. My expectation is that capability resolution will follow a similar trajectory, though the timeline is uncertain.

**"The registry will fill with junk."** This is the most operationally serious objection. Any open registry faces quality pressure. Loom's answer (multi-phase evaluation, behavioural testing, continuous re-evaluation, earned trust tiers, steward review for the highest tier) is designed to be conservative rather than permissive. Whether it is conservative enough in practice remains to be proven. The living registry architecture means that quality maintenance is ongoing rather than point-in-time, which helps, but does not eliminate the challenge.

**"Federation is speculative."** It is. The federation vision described in Section 9 is architecturally grounded but not yet implemented. The honest framing is: Loom's architecture is designed to support federation, but federation introduces hard problems that are not yet solved. The current system is centralised with self-hosting options. The path to federation is visible but unproven. I prefer to state this directly rather than present federation as an accomplished fact.

---

## 13. Conclusion

The cognitive core pattern — lean reasoning engines that delegate to external capabilities — creates a specific, growing demand for capability resolution. Agents need structured help answering the question: what can I accomplish, with what I have, under what constraints, at what cost?

This question is not answered by tool protocols, which solve the narrower problem of tool access. It is not answered by skill file directories, which solve the narrower problem of content hosting. It is not answered by workflow engines, which solve the narrower problem of execution mechanics. And it is not reliably answered by model improvisation alone, particularly in environments with many tools, complex policies, meaningful trust requirements, and real cost constraints.

Loom is an attempt to address this gap directly. It provides semantic resolution from task intent to executable capability. It evaluates and maintains capabilities through a living registry that improves over time. It supports constrained choice across trust, cost, dependency, and policy dimensions. It enables enterprises to layer organisational governance onto community knowledge through the extends mechanism, without forking or losing upstream improvements.

The system is at an early stage. The public registry is operational. Corporate instances are in development. Federation is an architectural direction, not an implemented feature. The evaluation pipeline and trust mechanisms are designed to be conservative, but their effectiveness at scale remains to be demonstrated.

What I am most confident about is the structural argument: the gap between tool access and capability resolution is real, it is growing, and it will need to be addressed by the ecosystem. Whether Loom is the right answer in every detail is less certain. But the question it is trying to answer — how agents make good capability choices under real-world constraints — is one the ecosystem cannot avoid for much longer.
