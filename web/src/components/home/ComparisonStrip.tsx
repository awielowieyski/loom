import { Layers } from 'lucide-react'
import { cn } from '@/lib/utils'

const layers = [
  {
    name: 'Tool catalogues',
    description: 'Tell the agent what tools exist',
    highlighted: false,
  },
  {
    name: 'Skill directories',
    description: 'Store reusable task knowledge',
    highlighted: false,
  },
  {
    name: 'Agent runtimes',
    description: 'Execute work with tools and memory',
    highlighted: false,
  },
  {
    name: 'Loom',
    description: 'Chooses which path should run here',
    highlighted: true,
  },
] as const

export function ComparisonStrip() {
  return (
    <section className="border-t py-18 md:py-22">
      <div className="max-w-3xl mx-auto space-y-12 md:space-y-14">
        {/* Stack comparison */}
        <div className="space-y-9">
          <div className="text-center space-y-3">
            <h2 className="text-xl md:text-2xl font-semibold tracking-tight">
              Where Loom fits
            </h2>
            <p className="text-sm text-muted-foreground">
              It sits between discovery and execution.
            </p>
          </div>

          <div className="space-y-2">
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
            Loom is not a prompt library or a workflow engine.
            <br className="hidden sm:block" />
            {' '}It is the decision layer that helps an agent choose the right skill or workflow under real constraints.
          </p>
        </div>

        {/* Extends mechanism */}
        <div className="space-y-7">
          <div className="text-center space-y-3">
            <h2 className="text-xl md:text-2xl font-semibold tracking-tight">
              Company context without forking
            </h2>
            <p className="text-sm text-muted-foreground max-w-xl mx-auto">
              Shared workflows improve over time. Loom&apos;s extends mechanism lets
              teams add governance and local preferences without forking the base capability.
            </p>
          </div>

          <div className="space-y-3">
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
