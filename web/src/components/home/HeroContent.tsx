import type { ReactNode } from 'react'
import { CheckCircle2, ShieldCheck, GitCompareArrows, Zap } from 'lucide-react'

interface HeroContentProps {
  children: ReactNode
}

const outcomes = [
  {
    icon: CheckCircle2,
    label: 'Picks executable paths',
  },
  {
    icon: ShieldCheck,
    label: 'Applies trust and policy',
  },
  {
    icon: GitCompareArrows,
    label: 'Ranks fallbacks and tradeoffs',
  },
  {
    icon: Zap,
    label: 'Returns a plan, not just a match',
  },
] as const

export function HeroContent({ children }: HeroContentProps) {
  return (
    <div className="space-y-10 pt-12 pb-6 md:space-y-12 md:pt-16 md:pb-8">
      <div className="text-center space-y-5">
        <p className="text-xs font-medium uppercase tracking-[0.22em] text-muted-foreground/70">
          From tool access to capability choice
        </p>
        <h1 className="text-4xl md:text-5xl font-semibold tracking-tight text-foreground leading-tight">
          Help agents choose
          <br />
          the right path.
        </h1>
        <p className="text-base md:text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
          Loom helps agents choose the right skill or multi-step capability for a task,
          in the environment they are actually running in, with the tools, policies,
          trust boundaries, and budget they have right now.
        </p>
      </div>

      <div className="max-w-2xl mx-auto w-full space-y-5 md:space-y-6">
        {children}

        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {outcomes.map((outcome) => (
            <div
              key={outcome.label}
              className="rounded-2xl border border-border/70 bg-card/70 px-3 py-3 text-left shadow-sm"
            >
              <outcome.icon className="h-4 w-4 text-foreground/75" />
              <p className="mt-2 text-sm font-medium text-foreground">{outcome.label}</p>
            </div>
          ))}
        </div>

        <div className="rounded-3xl border border-border/70 bg-gradient-to-br from-accent/60 via-background to-primary/5 p-5 md:p-6 shadow-sm">
          <div className="grid gap-4 md:grid-cols-[1fr_auto_1fr] md:items-stretch">
            <div className="rounded-2xl border border-border/60 bg-background/90 p-4 text-left">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground/70">
                Without Loom
              </p>
              <p className="mt-2 text-sm font-medium text-foreground">
                The agent sees tools and has to improvise.
              </p>
              <ul className="mt-3 space-y-2 text-xs text-muted-foreground">
                <li>Wrong provider for the budget</li>
                <li>Missing dependency discovered too late</li>
                <li>Policy-unsafe data flow hidden in the workflow</li>
              </ul>
            </div>

            <div className="hidden md:flex items-center justify-center text-muted-foreground/45">
              <div className="rounded-full border border-border/70 bg-background/80 px-3 py-2 text-xs font-medium">
                Resolve
              </div>
            </div>

            <div className="rounded-2xl border border-primary/15 bg-primary/5 p-4 text-left">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-primary/70">
                With Loom
              </p>
              <p className="mt-2 text-sm font-medium text-foreground">
                The agent gets the best viable path for this runtime.
              </p>
              <ul className="mt-3 space-y-2 text-xs text-muted-foreground">
                <li>Preferred option plus ranked alternatives</li>
                <li>Dependency status, trust warnings, and fallbacks</li>
                <li>A resolved execution plan the runtime can actually use</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <p className="pt-1 text-center text-xs text-muted-foreground/60">
        Open registry. Search and resolve freely.{' '}
        <a href="/login" className="underline underline-offset-2 hover:text-muted-foreground transition-colors">
          Sign in
        </a>
        {' '}to contribute, set persistent filters, or opt out of logging.
      </p>
    </div>
  )
}
