import { CheckCircle2, AlertTriangle, Layers, Plus } from 'lucide-react'

export function ExampleSection() {
  return (
    <section className="border-t py-18 md:py-22">
      <div className="max-w-2xl mx-auto space-y-8 md:space-y-10">
        <h2 className="text-xl md:text-2xl font-semibold tracking-tight">
          Example: vendor risk
        </h2>

        <div className="space-y-4 text-sm md:text-base text-muted-foreground leading-relaxed">
          <p>
            An agent is asked to produce a vendor-risk briefing. It has internal ticketing,
            a document repository, web search, and Slack, but no premium financial-data API.
            The enterprise has a trust floor and a moderate cost budget.
          </p>
          <p>
            Without Loom, a strong model might improvise something plausible. With Loom, the
            runtime gets a capability that matches the task shape, fits the environment,
            and degrades gracefully when a dependency is missing.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-border/70 bg-card p-4">
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground/70">
              Runtime context
            </p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
              <span className="rounded-full border border-border/70 bg-accent/60 px-2 py-1">Internal ticketing</span>
              <span className="rounded-full border border-border/70 bg-accent/60 px-2 py-1">Document repository</span>
              <span className="rounded-full border border-border/70 bg-accent/60 px-2 py-1">Web search</span>
              <span className="rounded-full border border-border/70 bg-accent/60 px-2 py-1">Slack</span>
              <span className="rounded-full border border-border/70 bg-accent/60 px-2 py-1">Moderate budget</span>
            </div>
          </div>

          <div className="rounded-2xl border border-primary/15 bg-primary/5 p-4">
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-primary/70">
              Resolution outcome
            </p>
            <div className="mt-3 space-y-2 text-sm text-foreground/80">
              <p>Choose `vendor-risk-briefing`</p>
              <p>Skip optional financial-data step</p>
              <p>Surface trust warning for external claims</p>
            </div>
          </div>
        </div>

        {/* Resolution trace — extends in action */}
        <div className="space-y-3">
          {/* Community base */}
          <div className="flex items-start gap-3 px-4 py-3 rounded-lg bg-accent/50 border border-border/50">
            <CheckCircle2 className="h-4 w-4 text-success shrink-0 mt-0.5" />
            <div>
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium text-foreground">vendor-risk-briefing</p>
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-accent border border-border/50 text-muted-foreground">
                  community
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Resolved — web search, data retrieval, risk synthesis.
                Financial data step skipped (API unavailable, marked optional).
              </p>
            </div>
          </div>

          {/* Corporate extends */}
          <div className="flex items-start gap-3 px-4 py-3 rounded-lg bg-primary/5 border border-primary/15">
            <Plus className="h-4 w-4 text-primary/70 shrink-0 mt-0.5" />
            <div>
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium text-foreground">acme-vendor-assessment</p>
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-primary/10 border border-primary/15 text-primary">
                  corporate
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Extends community skill — cross-references approved vendor list,
                applies GDPR compliance section, queries internal incident database,
                enforces risk-score threshold.
              </p>
            </div>
          </div>

          {/* Personal extends */}
          <div className="flex items-start gap-3 px-4 py-3 rounded-lg bg-chart-2/5 border border-chart-2/15">
            <Plus className="h-4 w-4 text-chart-2/70 shrink-0 mt-0.5" />
            <div>
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium text-foreground">my-vendor-workflow</p>
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-chart-2/10 border border-chart-2/15 text-chart-2">
                  personal
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Extends corporate skill — posts briefing to #procurement-review on Slack,
                creates a Jira ticket in the VENDOR project.
              </p>
            </div>
          </div>
        </div>

        {/* Trust warning */}
        <div className="flex items-start gap-2 px-4 py-2.5 rounded-lg bg-warning/5 border border-warning/20">
          <AlertTriangle className="h-3.5 w-3.5 text-warning shrink-0 mt-0.5" />
          <p className="text-xs text-muted-foreground">
            Trust warning surfaced: data flows from web search (external)
            into risk synthesis. Output may contain unverified external claims.
          </p>
        </div>

        <div className="text-sm md:text-base text-muted-foreground leading-relaxed">
          <p>
            The result is not just a match. It is a concrete execution plan, plus the
            governance and preferences layered on top of it.
          </p>
        </div>

        {/* What the agent receives */}
        <div className="rounded-xl border bg-card p-4 space-y-3">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            The agent receives
          </p>
          <ul className="space-y-1.5">
            {[
              'The merged capability: community base + corporate governance + personal preferences',
              'Dependency status for every step, including skipped optional steps',
              'Trust warnings where external data enters the flow',
              'Alternatives and tradeoffs if the preferred route is unavailable',
              'A fully resolved execution plan — no further calls to Loom required',
            ].map((item) => (
              <li key={item} className="flex items-start gap-2 text-sm text-foreground/80">
                <span className="text-muted-foreground/40 select-none mt-px">–</span>
                {item}
              </li>
            ))}
          </ul>
        </div>

        {/* Layering summary */}
        <div className="flex items-start gap-3 px-4 py-3 rounded-lg bg-accent/30">
          <Layers className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
          <p className="text-xs text-muted-foreground leading-relaxed">
            When the community skill improves — better search strategy, updated synthesis
            instructions — the corporate and personal layers inherit the improvement
            automatically. No fork divergence. No manual merge treadmill.
          </p>
        </div>
      </div>
    </section>
  )
}
