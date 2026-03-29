import { ArrowRight, PackagePlus, ShieldCheck, Route, Play } from 'lucide-react'

const steps = [
  {
    icon: PackagePlus,
    label: 'Register',
    description: 'Skills and capabilities are added from community, enterprise, or local sources.',
  },
  {
    icon: ShieldCheck,
    label: 'Evaluate',
    description: 'Loom assesses quality, trust, dependencies, and cost signals, and keeps them current over time.',
  },
  {
    icon: Route,
    label: 'Resolve',
    description: 'Given a task and runtime context, Loom selects the right skill or composed capability, ranks alternatives, and explains the choice.',
  },
  {
    icon: Play,
    label: 'Execute',
    description: 'The agent runtime carries out the resolved plan using its own tools, workflows, and observability stack.',
  },
] as const

const differentiators = [
  {
    title: 'Evaluated',
    description: 'Loom does not just index skills. It evaluates them and keeps reassessing as evidence changes.',
  },
  {
    title: 'Controlled',
    description: 'Policy, trust, dependency, and budget constraints are applied at resolution time.',
  },
  {
    title: 'Updated',
    description: 'A living registry, not a static folder. Better paths rise, stale ones fall, and resolution reflects the current best-known option.',
  },
  {
    title: 'Extended',
    description: 'Shared task knowledge can be layered without forks. Community skills define the base, enterprises add governance, individuals add preferences.',
  },
] as const

export function HowItWorksSection() {
  return (
    <section className="py-16 border-t">
      <div className="max-w-3xl mx-auto space-y-12">
        <div className="text-center space-y-2">
          <h2 className="text-xl md:text-2xl font-semibold tracking-tight">
            How Loom works
          </h2>
          <p className="text-sm text-muted-foreground">
            Externalised task knowledge, turned into governed runtime choice.
          </p>
        </div>

        {/* Pipeline */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
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
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
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
