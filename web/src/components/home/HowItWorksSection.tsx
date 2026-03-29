import { ArrowRight, Files, ShieldCheck, Route, Play } from 'lucide-react'

const steps = [
  {
    icon: Files,
    label: 'Describe the task',
    description: 'The runtime sends task intent plus context like tools, policy, trust floor, and budget.',
  },
  {
    icon: ShieldCheck,
    label: 'Evaluate constraints',
    description: 'Loom checks candidate skills and capabilities against quality, dependency, trust, and cost signals.',
  },
  {
    icon: Route,
    label: 'Resolve',
    description: 'It returns the best viable path, ranked alternatives, rejection reasons, and the rationale for the choice.',
  },
  {
    icon: Play,
    label: 'Execute',
    description: 'The agent runtime carries out the resolved plan using its own tools, workflows, and observability stack.',
  },
] as const

const differentiators = [
  {
    title: 'Better than search',
    description: 'Loom is not just matching words. It is choosing a path that can actually work in the current runtime.',
  },
  {
    title: 'Safer by default',
    description: 'Dependency gaps, trust warnings, and policy conflicts are surfaced before the agent starts executing.',
  },
  {
    title: 'Clearer tradeoffs',
    description: 'The runtime can see why one option won and what it gives up by choosing a cheaper or lighter fallback.',
  },
  {
    title: 'Portable knowledge',
    description: 'Shared capabilities stay reusable while enterprises and individuals layer on local governance and preferences.',
  },
] as const

export function HowItWorksSection() {
  return (
    <section className="border-t py-18 md:py-22">
      <div className="max-w-3xl mx-auto space-y-12 md:space-y-14">
        <div className="text-center space-y-3">
          <h2 className="text-xl md:text-2xl font-semibold tracking-tight">
            What Loom actually does
          </h2>
          <p className="text-sm text-muted-foreground">
            It turns externalised task knowledge into constrained runtime choice.
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
                <li>Ranks viable capabilities</li>
                <li>Rejects paths that do not fit the runtime</li>
              </ul>
            </div>

            <ArrowRight className="hidden md:block h-4 w-4 text-muted-foreground/40" />

            <div className="rounded-2xl border border-chart-2/20 bg-background/95 p-4">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground/70">
                Output
              </p>
              <ul className="mt-2 space-y-2 text-sm text-foreground/80">
                <li>Selected capability and rationale</li>
                <li>Alternatives and fallbacks</li>
                <li>Resolved plan the agent can execute</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          {steps.map((step, i) => (
            <div key={step.label} className="relative flex flex-col items-center text-center">
              <div className="flex items-center gap-2 md:flex-col md:gap-3 w-full md:w-auto">
                <div className="shrink-0 h-10 w-10 rounded-xl bg-primary/5 border border-border/50 flex items-center justify-center">
                  <step.icon className="h-4.5 w-4.5 text-foreground/70" />
                </div>
                <div className="flex-1 md:flex-none text-left md:text-center">
                  <p className="text-sm font-medium text-foreground">{step.label}</p>
                  <p className="text-xs text-muted-foreground leading-relaxed mt-0.5 md:mt-1">
                    {step.description}
                  </p>
                </div>
              </div>
              {i < steps.length - 1 && (
                <ArrowRight className="hidden md:block absolute -right-3 top-5 h-3.5 w-3.5 text-muted-foreground/40" />
              )}
            </div>
          ))}
        </div>

        {/* Differentiators */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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
