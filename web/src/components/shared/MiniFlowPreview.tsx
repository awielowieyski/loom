import { ArrowRight } from 'lucide-react'
import { cn } from '@/lib/utils'

interface MiniFlowPreviewProps {
  steps: { skill_ref: string; role: string }[]
  className?: string
}

export function MiniFlowPreview({ steps, className }: MiniFlowPreviewProps) {
  if (steps.length === 0) return null

  return (
    <div
      className={cn(
        'flex items-center gap-1 overflow-x-auto scrollbar-none py-1',
        className,
      )}
    >
      {steps.map((step, i) => (
        <div key={i} className="flex items-center gap-1 shrink-0">
          <span className="inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
            {step.skill_ref}
          </span>
          {i < steps.length - 1 && (
            <ArrowRight className="h-3 w-3 text-muted-foreground/60 shrink-0" />
          )}
        </div>
      ))}
    </div>
  )
}
