import { ArrowRight } from 'lucide-react'

const differentiators = [
  {
    title: 'Chooses a viable workflow',
    description: 'Loom does not just return similar matches. It selects a skill or multi-step workflow that fits the current runtime.',
  },
  {
    title: 'Explains the tradeoff',
    description: 'The runtime can see why a path won, what was rejected, and when a fallback is good enough.',
  },
  {
    title: 'Leaves execution to your runtime',
    description: 'Loom resolves the plan, but your agent still executes it with its own tools, logging, and control flow.',
  },
] as const

export function HowItWorksSection() {
  return (
    <section className="border-t py-18 md:py-22">
      <div className="max-w-3xl mx-auto space-y-12 md:space-y-14">
        <div className="text-center space-y-3">
          <h2 className="text-xl md:text-2xl font-semibold tracking-tight">
            Governed resolution in practice
          </h2>
          <p className="text-sm text-muted-foreground">
            It turns trusted skills and workflows into a concrete choice for this runtime.
          </p>
        </div>

        <div className="rounded-3xl border border-border/70 bg-gradient-to-br from-accent/50 via-background to-chart-2/8 p-5 md:p-6">
          <div className="grid gap-4 md:grid-cols-[1.1fr_auto_1.2fr_auto_1.2fr] md:items-center">
            <div className="rounded-2xl border border-border/60 bg-background/90 p-4">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground/70">
                Input
              </p>
              <p className="mt-2 text-sm font-medium text-foreground">
                “Produce a vendor-risk briefing”
              </p>
              <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                <span className="rounded-full border border-border/70 bg-accent/60 px-2 py-1">Web search</span>
                <span className="rounded-full border border-border/70 bg-accent/60 px-2 py-1">Internal docs</span>
                <span className="rounded-full border border-border/70 bg-accent/60 px-2 py-1">Moderate budget</span>
                <span className="rounded-full border border-border/70 bg-accent/60 px-2 py-1">Community trust floor</span>
              </div>
            </div>

            <ArrowRight className="hidden md:block h-4 w-4 text-muted-foreground/40" />

            <div className="rounded-2xl border border-primary/15 bg-primary/5 p-4">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-primary/70">
                Resolution
              </p>
              <ul className="mt-2 space-y-2 text-sm text-foreground/80">
                <li>Checks dependencies and trust boundaries</li>
                <li>Ranks viable skills and workflows</li>
                <li>Rejects paths that do not fit the runtime</li>
              </ul>
            </div>

            <ArrowRight className="hidden md:block h-4 w-4 text-muted-foreground/40" />

            <div className="rounded-2xl border border-chart-2/20 bg-background/95 p-4">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground/70">
                Output
              </p>
              <ul className="mt-2 space-y-2 text-sm text-foreground/80">
                <li>Selected skill or workflow and rationale</li>
                <li>Alternatives and fallbacks</li>
                <li>Resolved plan the agent can execute</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {differentiators.map((d) => (
            <div
              key={d.title}
              className="rounded-xl border bg-card p-4 space-y-1.5"
            >
              <p className="text-sm font-medium text-foreground">{d.title}</p>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {d.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
