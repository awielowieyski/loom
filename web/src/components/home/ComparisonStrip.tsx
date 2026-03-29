import { Layers } from 'lucide-react'
import { cn } from '@/lib/utils'

const layers = [
  {
    name: 'Tool catalogues',
    description: 'Expose available tools',
    highlighted: false,
  },
  {
    name: 'Skill directories',
    description: 'Store reusable task knowledge',
    highlighted: false,
  },
  {
    name: 'Workflow engines',
    description: 'Execute defined processes',
    highlighted: false,
  },
  {
    name: 'Agent frameworks',
    description: 'Provide runtime structure',
    highlighted: false,
  },
  {
    name: 'Loom',
    description: 'Resolves the right path for the current environment',
    highlighted: true,
  },
] as const

export function ComparisonStrip() {
  return (
    <section className="py-16 border-t">
      <div className="max-w-3xl mx-auto space-y-12">
        {/* Stack comparison */}
        <div className="space-y-8">
          <div className="text-center space-y-2">
            <h2 className="text-xl md:text-2xl font-semibold tracking-tight">
              A distinct layer in the stack
            </h2>
          </div>

          <div className="space-y-1.5">
            {layers.map((layer) => (
              <div
                key={layer.name}
                className={cn(
                  'flex items-baseline gap-4 px-4 py-3 rounded-lg text-sm transition-colors',
                  layer.highlighted
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-accent/50 text-foreground/80',
                )}
              >
                <span className={cn(
                  'font-medium shrink-0 w-36 md:w-44',
                  layer.highlighted && 'font-semibold',
                )}>
                  {layer.name}
                </span>
                <span className={cn(
                  layer.highlighted ? 'text-primary-foreground/80' : 'text-muted-foreground',
                )}>
                  {layer.description}
                </span>
              </div>
            ))}
          </div>

          <p className="text-xs text-center text-muted-foreground/70">
            Loom is not a prompt library, skill marketplace, workflow engine, or agent framework.
            <br className="hidden sm:block" />
            {' '}It is a policy-aware capability router for agent systems.
          </p>
        </div>

        {/* Extends mechanism */}
        <div className="space-y-6">
          <div className="text-center space-y-2">
            <h2 className="text-xl md:text-2xl font-semibold tracking-tight">
              Layered knowledge, not endless forks
            </h2>
            <p className="text-sm text-muted-foreground max-w-xl mx-auto">
              The same task needs different things at different scales.
              Loom&apos;s extends mechanism lets each layer add what it knows
              without copying or overriding what came before.
            </p>
          </div>

          <div className="space-y-2">
            <div className="flex items-start gap-3 px-4 py-3 rounded-lg bg-accent/50 border border-border/50">
              <Layers className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-foreground">Community</p>
                <p className="text-xs text-muted-foreground">
                  The general approach. Task structure, typical steps, common tool compositions,
                  best-practice instructions. Available to everyone.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 px-4 py-3 rounded-lg bg-primary/5 border border-primary/15">
              <Layers className="h-4 w-4 text-primary/70 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-foreground">Corporate</p>
                <p className="text-xs text-muted-foreground">
                  Extends the community layer with organisational policy: approved providers,
                  internal tool integrations, compliance requirements, risk thresholds.
                  Private to the organisation.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 px-4 py-3 rounded-lg bg-chart-2/5 border border-chart-2/15">
              <Layers className="h-4 w-4 text-chart-2/70 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-foreground">Personal</p>
                <p className="text-xs text-muted-foreground">
                  Extends the corporate layer with individual preferences: notification
                  channels, output formats, team-specific routing. Lives on disk or
                  in personal config.
                </p>
              </div>
            </div>
          </div>

          <p className="text-xs text-center text-muted-foreground/70">
            When the community skill improves, the corporate and personal layers inherit the improvement automatically.
            <br className="hidden sm:block" />
            {' '}No manual merging. No fork divergence.
          </p>
        </div>
      </div>
    </section>
  )
}
