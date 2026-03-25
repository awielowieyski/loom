import { useMemo, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useUsageHeatmap } from '@/hooks/useStats'
import { cn } from '@/lib/utils'

interface UsageHeatmapProps {
  className?: string
}

function getCellColor(value: number, maxValue: number): string {
  if (maxValue === 0) return 'bg-muted'
  const intensity = value / maxValue
  if (intensity === 0) return 'bg-muted'
  if (intensity < 0.25) return 'bg-green-200 dark:bg-green-900/30'
  if (intensity < 0.5) return 'bg-green-400 dark:bg-green-700/50'
  if (intensity < 0.75) return 'bg-green-600 dark:bg-green-600/60'
  return 'bg-green-800 dark:bg-green-500/80'
}

export function UsageHeatmap({ className }: UsageHeatmapProps) {
  const { data, isLoading, error } = useUsageHeatmap({ period_type: 'week', periods: 12 })
  const [tooltip, setTooltip] = useState<{
    category: string
    period: string
    count: number
    x: number
    y: number
  } | null>(null)

  const maxValue = useMemo(() => {
    if (!data?.data) return 0
    return Math.max(0, ...data.data.flat())
  }, [data])

  const periodLabels = useMemo(() => {
    if (!data?.periods) return []
    return data.periods.map((p) => {
      const d = new Date(p)
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    })
  }, [data])

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Usage Heatmap</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div className="flex h-48 items-center justify-center">
            <p className="text-sm text-muted-foreground">Loading heatmap...</p>
          </div>
        )}
        {error && (
          <p className="text-sm text-muted-foreground">Failed to load usage data.</p>
        )}
        {!isLoading && !error && (!data || data.categories.length === 0) && (
          <div className="flex h-48 items-center justify-center">
            <p className="text-sm text-muted-foreground">No usage data available yet.</p>
          </div>
        )}
        {!isLoading && !error && data && data.categories.length > 0 && (
          <div className="relative overflow-x-auto">
            <div className="inline-grid gap-1" style={{
              gridTemplateColumns: `8rem repeat(${data.periods.length}, 2rem)`,
            }}>
              {/* Header row */}
              <div />
              {periodLabels.map((label, i) => (
                <div
                  key={i}
                  className="text-[9px] text-muted-foreground text-center -rotate-45 origin-bottom-left h-8 flex items-end"
                >
                  {label}
                </div>
              ))}

              {/* Data rows */}
              {data.categories.map((cat, rowIdx) => (
                <>
                  <div
                    key={`label-${cat}`}
                    className="truncate text-xs text-muted-foreground pr-2 flex items-center"
                  >
                    {cat}
                  </div>
                  {data.data[rowIdx].map((count, colIdx) => (
                    <div
                      key={`${cat}-${colIdx}`}
                      className={cn(
                        'h-6 w-6 rounded-sm cursor-pointer transition-colors',
                        getCellColor(count, maxValue),
                      )}
                      onMouseEnter={(e) =>
                        setTooltip({
                          category: cat,
                          period: periodLabels[colIdx],
                          count,
                          x: e.clientX,
                          y: e.clientY,
                        })
                      }
                      onMouseLeave={() => setTooltip(null)}
                    />
                  ))}
                </>
              ))}
            </div>

            {/* Tooltip */}
            {tooltip && (
              <div
                className="fixed z-50 rounded-md border bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-md"
                style={{ left: tooltip.x + 12, top: tooltip.y - 10 }}
              >
                <p className="font-medium">{tooltip.category}</p>
                <p>{tooltip.period}: {tooltip.count} resolutions</p>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
