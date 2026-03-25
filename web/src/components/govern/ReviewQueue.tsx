import { useState } from 'react'
import { ShieldAlert, AlertTriangle, FileEdit } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useGovernanceQueue } from '@/hooks/useStats'
import { cn } from '@/lib/utils'
import type { GovernanceQueueItem, GovernanceReason } from '@/types/api'

interface ReviewQueueProps {
  onSelect: (item: GovernanceQueueItem) => void
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
    label: 'Amendment',
    icon: FileEdit,
    className: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  },
}

export function ReviewQueue({ onSelect, selectedId, className }: ReviewQueueProps) {
  const [reasonFilter, setReasonFilter] = useState<string | undefined>(undefined)
  const { data, isLoading, error } = useGovernanceQueue(
    reasonFilter ? { reason: reasonFilter } : undefined,
  )

  return (
    <Card className={cn('flex flex-col', className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Review Queue</CardTitle>
          <select
            value={reasonFilter ?? ''}
            onChange={(e) => setReasonFilter(e.target.value || undefined)}
            className="rounded-md border bg-background px-2 py-1 text-sm"
          >
            <option value="">All reasons</option>
            <option value="injection_flag">Injection flags</option>
            <option value="low_confidence">Low confidence</option>
            <option value="recent_amendment">Recent amendments</option>
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
        {error && (
          <p className="text-sm text-muted-foreground">Failed to load queue.</p>
        )}
        {!isLoading && !error && (!data || data.length === 0) && (
          <div className="flex h-32 items-center justify-center">
            <p className="text-sm text-muted-foreground">
              No items in the review queue. The registry is healthy.
            </p>
          </div>
        )}
        {!isLoading && !error && data && data.length > 0 && (
          <ul className="space-y-2">
            {data.map((item) => {
              const config = REASON_CONFIG[item.reason]
              const Icon = config.icon
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
                      <Badge
                        variant="secondary"
                        className={cn('shrink-0 text-[10px] border-0', config.className)}
                      >
                        <Icon className="mr-1 h-3 w-3" />
                        {config.label}
                      </Badge>
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                      <span>{item.slug}</span>
                      {item.submitted_at && (
                        <>
                          <span>-</span>
                          <span>
                            {new Date(item.submitted_at).toLocaleDateString()}
                          </span>
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
