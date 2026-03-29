import { useState } from 'react'
import {
  AlertTriangle,
  FileEdit,
  Layers3,
  PackageSearch,
  Rocket,
  ShieldAlert,
  Sparkles,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useGovernanceQueue } from '@/hooks/useStats'
import { cn } from '@/lib/utils'
import type { GovernanceQueueItem, GovernanceReason, GovernanceStage } from '@/types/api'

interface ReviewQueueProps {
  onSelect: (item: GovernanceQueueItem) => void
  stage?: GovernanceStage
  selectedId?: string
  className?: string
}

const REASON_CONFIG: Record<
  GovernanceReason,
  { label: string; icon: typeof ShieldAlert; className: string }
> = {
  injection_flag: {
    label: 'Injection Flag',
    icon: ShieldAlert,
    className: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  },
  low_confidence: {
    label: 'Low Confidence',
    icon: AlertTriangle,
    className: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  },
  recent_amendment: {
    label: 'Workflow',
    icon: FileEdit,
    className: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  },
}

const STAGE_CONFIG: Record<
  GovernanceStage,
  { label: string; icon: typeof PackageSearch; className: string }
> = {
  quarantine: {
    label: 'Quarantine',
    icon: PackageSearch,
    className: 'bg-slate-100 text-slate-800 dark:bg-slate-900/30 dark:text-slate-300',
  },
  canonicalization: {
    label: 'Canonicalize',
    icon: Sparkles,
    className: 'bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-300',
  },
  dedup: {
    label: 'Dedup',
    icon: Layers3,
    className: 'bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-300',
  },
  evaluation: {
    label: 'Evaluate',
    icon: ShieldAlert,
    className: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  },
  publication: {
    label: 'Publish',
    icon: Rocket,
    className: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300',
  },
}

export function ReviewQueue({ onSelect, stage, selectedId, className }: ReviewQueueProps) {
  const [reasonFilter, setReasonFilter] = useState<string | undefined>(undefined)
  const { data, isLoading, error } = useGovernanceQueue(
    reasonFilter || stage ? { reason: reasonFilter, stage } : undefined,
  )

  const stageLabel = stage ? STAGE_CONFIG[stage].label : 'Review'

  return (
    <Card className={cn('flex flex-col', className)}>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>{stageLabel} Queue</CardTitle>
          <select
            value={reasonFilter ?? ''}
            onChange={(e) => setReasonFilter(e.target.value || undefined)}
            className="rounded-md border bg-background px-2 py-1 text-sm"
          >
            <option value="">All reasons</option>
            <option value="injection_flag">Injection flags</option>
            <option value="low_confidence">Low confidence</option>
            <option value="recent_amendment">Workflow/default</option>
          </select>
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto">
        {isLoading && (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-16 animate-pulse rounded-lg bg-muted" />
            ))}
          </div>
        )}
        {error && <p className="text-sm text-muted-foreground">Failed to load queue.</p>}
        {!isLoading && !error && (!data || data.length === 0) && (
          <div className="flex h-32 items-center justify-center">
            <p className="text-sm text-muted-foreground">No items in this stage.</p>
          </div>
        )}
        {!isLoading && !error && data && data.length > 0 && (
          <ul className="space-y-2">
            {data.map((item) => {
              const reasonConfig = REASON_CONFIG[item.reason]
              const stageConfig = STAGE_CONFIG[item.stage]
              const ReasonIcon = reasonConfig.icon
              const StageIcon = stageConfig.icon
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(item)}
                    className={cn(
                      'w-full rounded-lg border p-3 text-left transition-colors hover:bg-accent',
                      selectedId === item.id && 'border-primary bg-accent',
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium truncate">{item.name}</span>
                      <div className="flex items-center gap-1">
                        <Badge
                          variant="secondary"
                          className={cn('shrink-0 text-[10px] border-0', stageConfig.className)}
                        >
                          <StageIcon className="mr-1 h-3 w-3" />
                          {stageConfig.label}
                        </Badge>
                        <Badge
                          variant="secondary"
                          className={cn('shrink-0 text-[10px] border-0', reasonConfig.className)}
                        >
                          <ReasonIcon className="mr-1 h-3 w-3" />
                          {reasonConfig.label}
                        </Badge>
                      </div>
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <span>{item.slug}</span>
                      <span>-</span>
                      <span>{item.lifecycle_state}</span>
                      {item.authorship_status && (
                        <>
                          <span>-</span>
                          <span>{item.authorship_status}</span>
                        </>
                      )}
                      {item.submitted_at && (
                        <>
                          <span>-</span>
                          <span>{new Date(item.submitted_at).toLocaleDateString()}</span>
                        </>
                      )}
                    </div>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
