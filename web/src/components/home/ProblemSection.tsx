import { ArrowRight, BadgeCheck, CircleAlert } from 'lucide-react'

const constraints = [
  {
    label: 'Executable now',
    detail: 'Choose paths that fit the MCP servers, APIs, scopes, and data sources the agent actually has.',
  },
  {
    label: 'Governed by policy',
    detail: 'Apply trust boundaries, approved providers, and data-classification rules before execution starts.',
  },
  {
    label: 'Cost-aware by default',
    detail: 'Prefer cheaper routes when they are good enough, and justify premium paths when they are not.',
  },
  {
    label: 'Fallback-ready',
    detail: 'Surface viable alternatives and graceful degradation instead of discovering broken workflows midway through.',
  },
] as const

export function ProblemSection() {
  return (
    <section className="border-t py-18 md:py-22">
      <div className="max-w-3xl mx-auto space-y-10 md:space-y-12">
        <h2 className="text-xl md:text-2xl font-semibold tracking-tight text-foreground">
          Tool access is not the same as capability choice.
          <br />
          <span className="text-muted-foreground">That is where Loom comes in.</span>
        </h2>

        <div className="space-y-4 text-sm md:text-base text-muted-foreground leading-relaxed">
          <p>
            Agents often fail after tool discovery, not before it. They can see many possible
            paths, but still need help deciding which one is appropriate, executable, and safe
            for the current environment.
          </p>
          <p>
            A tool catalogue shows what exists. A skill directory stores reusable know-how.
            Loom resolves which skill or workflow should actually be used now.
          </p>
        </div>

        <div className="grid gap-5 md:grid-cols-[1fr_auto_1fr] md:items-stretch">
          <div className="rounded-3xl border border-border/70 bg-card p-5 space-y-4 shadow-sm">
            <div className="flex items-center gap-2">
              <CircleAlert className="h-4 w-4 text-warning" />
              <p className="text-sm font-medium text-foreground">Without Loom</p>
            </div>
            <div className="space-y-2">
              {[
                'Many tools are available',
                'Several skills look plausible',
                'The model improvises the route',
              ].map((item) => (
                <div key={item} className="rounded-xl border border-border/60 bg-background px-3 py-2 text-sm text-muted-foreground">
                  {item}
                </div>
              ))}
            </div>
            <p className="text-xs leading-relaxed text-muted-foreground">
              Result: the agent may pick a path that is unavailable, too expensive, or out of policy.
            </p>
          </div>

          <div className="hidden md:flex items-center justify-center text-muted-foreground/45">
            <ArrowRight className="h-5 w-5" />
          </div>

          <div className="rounded-3xl border border-primary/15 bg-gradient-to-br from-primary/8 via-background to-chart-2/8 p-5 space-y-4 shadow-sm">
            <div className="flex items-center gap-2">
              <BadgeCheck className="h-4 w-4 text-success" />
              <p className="text-sm font-medium text-foreground">With Loom</p>
            </div>
            <div className="space-y-2">
              {[
                'Task intent + runtime context go in',
                'Constraints are applied before selection',
                'The best viable path comes back fully resolved',
              ].map((item) => (
                <div key={item} className="rounded-xl border border-primary/10 bg-background/90 px-3 py-2 text-sm text-foreground/80">
                  {item}
                </div>
              ))}
            </div>
            <p className="text-xs leading-relaxed text-muted-foreground">
              Result: the runtime gets a usable plan, clear tradeoffs, and warnings where they matter.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {constraints.map((c) => (
            <div
              key={c.label}
              className="rounded-2xl border bg-card px-4 py-4 space-y-1.5"
            >
              <p className="text-sm font-medium text-foreground">{c.label}</p>
              <p className="text-xs text-muted-foreground leading-relaxed">{c.detail}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
