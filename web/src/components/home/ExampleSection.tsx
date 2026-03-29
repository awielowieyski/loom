import { CheckCircle2, AlertTriangle, Layers, Plus } from 'lucide-react'

export function ExampleSection() {
  return (
    <section className="py-16 border-t">
      <div className="max-w-2xl mx-auto space-y-6">
        <h2 className="text-xl md:text-2xl font-semibold tracking-tight">
          Example: vendor risk
        </h2>

        <div className="space-y-4 text-sm md:text-base text-muted-foreground leading-relaxed">
          <p>
            An agent is asked to produce a vendor-risk briefing.
            It has access to internal ticketing, a document repository, web search, and Slack.
            It does not have access to a premium financial-data API.
            The enterprise has set a trust floor and a moderate cost budget.
          </p>
          <p>
            Loom resolves a community capability for vendor-risk briefings.
            Then extends it.
          </p>
        </div>

        {/* Resolution trace — extends in action */}
        <div className="space-y-2">
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
            The result is not just a match. It is three layers merged into
            a single, inspectable execution plan.
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
              'The full extends chain, so the decision is auditable',
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
            automatically. No fork. No manual merge.
          </p>
        </div>
      </div>
    </section>
  )
}
