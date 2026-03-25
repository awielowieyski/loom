import { CheckCircle, Clock, BarChart3 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useSkillUsage } from '@/hooks/useSkill'
import { cn } from '@/lib/utils'

interface UsageStatsDisplayProps {
  slug: string
  className?: string
}

export function UsageStatsDisplay({ slug, className }: UsageStatsDisplayProps) {
  const { data: usage, isLoading } = useSkillUsage(slug)

  if (isLoading) {
    return (
      <div className={cn('grid grid-cols-3 gap-3', className)}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-24 animate-pulse rounded-xl bg-muted" />
        ))}
      </div>
    )
  }

  if (!usage) return null

  // Aggregate from the latest window (prefer 30d)
  const agg =
    usage.aggregates.find((a) => a.window_type === '30d') ??
    usage.aggregates.find((a) => a.window_type === '7d') ??
    usage.aggregates[0]

  if (!agg) {
    return (
      <p className={cn('text-sm text-muted-foreground', className)}>No usage data available.</p>
    )
  }

  const totalResolutions = agg.success_count + agg.partial_count + agg.failure_count
  const successRate = agg.success_rate ?? 0
  const avgRuntime = agg.avg_runtime_ms

  return (
    <div className={cn('grid grid-cols-1 gap-3 sm:grid-cols-3', className)}>
      <Card size="sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
            Success Rate
          </CardTitle>
        </CardHeader>
        <CardContent>
          <span
            className={cn(
              'text-2xl font-bold tabular-nums',
              successRate >= 0.8
                ? 'text-green-600 dark:text-green-400'
                : successRate >= 0.5
                  ? 'text-amber-600 dark:text-amber-400'
                  : 'text-red-600 dark:text-red-400',
            )}
          >
            {Math.round(successRate * 100)}%
          </span>
        </CardContent>
      </Card>

      <Card size="sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
            Resolutions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <span className="text-2xl font-bold tabular-nums">{totalResolutions}</span>
        </CardContent>
      </Card>

      <Card size="sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Clock className="h-4 w-4 text-muted-foreground" />
            Avg Runtime
          </CardTitle>
        </CardHeader>
        <CardContent>
          <span className="text-2xl font-bold tabular-nums">
            {avgRuntime != null ? `${Math.round(avgRuntime)}ms` : '--'}
          </span>
        </CardContent>
      </Card>
    </div>
  )
}
