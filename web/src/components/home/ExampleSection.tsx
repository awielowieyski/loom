import { CheckCircle2, AlertTriangle, Layers, Plus } from 'lucide-react'

export function ExampleSection() {
  return (
    <section className="border-t py-18 md:py-22">
      <div className="max-w-2xl mx-auto space-y-8 md:space-y-10">
        <h2 className="text-xl md:text-2xl font-semibold tracking-tight">
          Example: account brief
        </h2>

        <div className="space-y-4 text-sm md:text-base text-muted-foreground leading-relaxed">
          <p>
            An agent is asked to prepare an account brief before a customer call. It has
            CRM access through an MCP server, internal docs, support history, web search,
            and Slack. The company wants the brief grounded in internal context, but does
            not want CRM notes sent to external services.
          </p>
          <p>
            Without Loom, a strong model might improvise something plausible. With Loom, the
            runtime gets a workflow that matches the task shape, fits the environment,
            and degrades gracefully when a dependency is missing.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-border/70 bg-card p-4">
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground/70">
              Runtime context
            </p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
              <span className="rounded-full border border-border/70 bg-accent/60 px-2 py-1">CRM MCP</span>
              <span className="rounded-full border border-border/70 bg-accent/60 px-2 py-1">Support history</span>
              <span className="rounded-full border border-border/70 bg-accent/60 px-2 py-1">Internal docs</span>
              <span className="rounded-full border border-border/70 bg-accent/60 px-2 py-1">Web search</span>
              <span className="rounded-full border border-border/70 bg-accent/60 px-2 py-1">Slack</span>
              <span className="rounded-full border border-border/70 bg-accent/60 px-2 py-1">Internal-only CRM notes</span>
            </div>
          </div>

          <div className="rounded-2xl border border-primary/15 bg-primary/5 p-4">
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-primary/70">
              Resolution outcome
            </p>
            <div className="mt-3 space-y-2 text-sm text-foreground/80">
              <p>Choose the `account-brief-prep` workflow</p>
              <p>Use CRM, support, docs, and public web context together</p>
              <p>Keep internal notes out of the external research step</p>
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
                <p className="text-sm font-medium text-foreground">account-brief-prep</p>
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-accent border border-border/50 text-muted-foreground">
                  community
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Resolved — gather public company context, recent news, and the standard
                customer-facing brief structure from a vetted community workflow.
              </p>
            </div>
          </div>

          {/* Corporate extends */}
          <div className="flex items-start gap-3 px-4 py-3 rounded-lg bg-primary/5 border border-primary/15">
            <Plus className="h-4 w-4 text-primary/70 shrink-0 mt-0.5" />
            <div>
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium text-foreground">acme-account-context</p>
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-primary/10 border border-primary/15 text-primary">
                  corporate
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Extends the community workflow with CRM access, support history,
                approved brief structure, and a guardrail that keeps internal notes
                out of external enrichment.
              </p>
            </div>
          </div>

          {/* Personal extends */}
          <div className="flex items-start gap-3 px-4 py-3 rounded-lg bg-chart-2/5 border border-chart-2/15">
            <Plus className="h-4 w-4 text-chart-2/70 shrink-0 mt-0.5" />
            <div>
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium text-foreground">my-sales-handoff</p>
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-chart-2/10 border border-chart-2/15 text-chart-2">
                  personal
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Extends the company workflow with personal preferences — post the
                brief to the deal room in Slack and create a follow-up note for the AE.
              </p>
            </div>
          </div>
        </div>

        {/* Trust warning */}
        <div className="flex items-start gap-2 px-4 py-2.5 rounded-lg bg-warning/5 border border-warning/20">
          <AlertTriangle className="h-3.5 w-3.5 text-warning shrink-0 mt-0.5" />
          <p className="text-xs text-muted-foreground">
            Guardrail surfaced: CRM notes stay internal. Only the company name,
            public facts, and approved fields flow into the external research step.
          </p>
        </div>

        <div className="text-sm md:text-base text-muted-foreground leading-relaxed">
          <p>
            The result is not just a match. It is a concrete workflow plan, plus the
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
              'The merged workflow layers: community base + corporate governance + personal preferences',
              'A reusable workflow made from vetted community logic plus company-specific MCP context',
              'Dependency status for every step, including CRM and support-system inputs',
              'Data-flow guardrails that keep internal notes out of external steps',
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
            When the community workflow improves — better brief structure, stronger
            research steps, clearer output guidance — the company and personal layers
            inherit the improvement automatically. No fork divergence. No manual merge treadmill.
          </p>
        </div>
      </div>
    </section>
  )
}
