import {
  Upload,
  CheckCircle2,
  ArrowUpCircle,
  ArrowDownCircle,
  GitBranch,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useSkillTimeline } from '@/hooks/useSkill'
import { TrustBadge } from '@/components/shared/TrustBadge'
import { formatRelativeTime } from '@/lib/format'
import type { SkillTimelineEvent, TrustTier } from '@/types/api'

const EVENT_CONFIG: Record<
  string,
  { icon: typeof Upload; color: string; dotColor: string }
> = {
  submitted: {
    icon: Upload,
    color: 'text-muted-foreground',
    dotColor: 'bg-muted-foreground',
  },
  eval_completed: {
    icon: CheckCircle2,
    color: 'text-blue-600 dark:text-blue-400',
    dotColor: 'bg-blue-500',
  },
  promoted: {
    icon: ArrowUpCircle,
    color: 'text-green-600 dark:text-green-400',
    dotColor: 'bg-green-500',
  },
  demoted: {
    icon: ArrowDownCircle,
    color: 'text-red-600 dark:text-red-400',
    dotColor: 'bg-red-500',
  },
  version: {
    icon: GitBranch,
    color: 'text-muted-foreground',
    dotColor: 'bg-muted-foreground',
  },
}

function extractTierFromDetail(detail: string): TrustTier | null {
  const match = detail.match(/-> (\w+)/)
  if (match) {
    const tier = match[1]
    if (tier === 'experimental' || tier === 'community' || tier === 'verified') {
      return tier
    }
  }
  return null
}

interface TrustJourneyProps {
  slug: string
  className?: string
}

export function TrustJourney({ slug, className }: TrustJourneyProps) {
  const { data: timeline, isLoading } = useSkillTimeline(slug)

  if (isLoading) {
    return (
      <div className={cn('space-y-4', className)}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex gap-3">
            <div className="h-6 w-6 animate-pulse rounded-full bg-muted" />
            <div className="h-4 w-48 animate-pulse rounded bg-muted" />
          </div>
        ))}
      </div>
    )
  }

  const events = timeline?.events ?? []

  if (events.length === 0) {
    return (
      <p className={cn('text-sm text-muted-foreground', className)}>
        No timeline events available.
      </p>
    )
  }

  return (
    <div className={cn('relative', className)}>
      {/* Vertical timeline line */}
      <div className="absolute left-3 top-0 bottom-0 w-px bg-border" />

      <div className="space-y-4">
        {events.map((event, i) => (
          <TimelineNode key={`${event.event_type}-${event.timestamp}-${i}`} event={event} />
        ))}
      </div>
    </div>
  )
}

function TimelineNode({ event }: { event: SkillTimelineEvent }) {
  const config = EVENT_CONFIG[event.event_type] ?? EVENT_CONFIG.submitted
  const Icon = config.icon
  const newTier = extractTierFromDetail(event.detail)

  return (
    <div className="relative flex items-start gap-3 pl-0">
      {/* Dot on the timeline */}
      <div
        className={cn(
          'relative z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-background ring-2 ring-background',
        )}
      >
        <Icon className={cn('h-4 w-4', config.color)} />
      </div>

      <div className="flex-1 pt-0.5">
        <p className="text-sm">{event.detail}</p>
        <div className="mt-0.5 flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {formatRelativeTime(event.timestamp)}
          </span>
          {newTier && <TrustBadge tier={newTier} size="sm" />}
        </div>
      </div>
    </div>
  )
}
