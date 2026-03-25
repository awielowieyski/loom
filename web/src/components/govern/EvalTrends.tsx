import { useState } from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useEvalTrends } from '@/hooks/useStats'

interface EvalTrendsProps {
  className?: string
}

export function EvalTrends({ className }: EvalTrendsProps) {
  const [category, setCategory] = useState<string | undefined>(undefined)
  const { data, isLoading, error } = useEvalTrends({ category, weeks: 12 })

  const chartData = (data?.windows ?? []).map((w) => ({
    week: w.week ? new Date(w.week).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '',
    p25: w.p25,
    p50: w.p50,
    p75: w.p75,
    behavioral_p50: w.behavioral_p50,
  }))

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Eval Score Trends</CardTitle>
          <select
            value={category ?? ''}
            onChange={(e) => setCategory(e.target.value || undefined)}
            className="rounded-md border bg-background px-2 py-1 text-sm"
          >
            <option value="">All categories</option>
          </select>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div className="flex h-64 items-center justify-center">
            <p className="text-sm text-muted-foreground">Loading trends...</p>
          </div>
        )}
        {error && (
          <p className="text-sm text-muted-foreground">Failed to load eval trends.</p>
        )}
        {!isLoading && !error && chartData.length === 0 && (
          <div className="flex h-64 items-center justify-center">
            <p className="text-sm text-muted-foreground">No eval data available yet.</p>
          </div>
        )}
        {!isLoading && !error && chartData.length > 0 && (
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="gradP75" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--chart-1))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--chart-1))" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradP50" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--chart-2))" stopOpacity={0.5} />
                  <stop offset="95%" stopColor="hsl(var(--chart-2))" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradP25" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--chart-3))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--chart-3))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="week"
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                domain={[0, 1]}
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => v.toFixed(1)}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: '8px',
                  border: '1px solid hsl(var(--border))',
                  backgroundColor: 'hsl(var(--popover))',
                  color: 'hsl(var(--popover-foreground))',
                }}
                formatter={(value) => typeof value === 'number' ? value.toFixed(3) : String(value ?? '')}
              />
              <Area
                type="monotone"
                dataKey="p75"
                stroke="hsl(var(--chart-1))"
                fill="url(#gradP75)"
                name="p75"
              />
              <Area
                type="monotone"
                dataKey="p50"
                stroke="hsl(var(--chart-2))"
                fill="url(#gradP50)"
                strokeWidth={2}
                name="p50 (median)"
              />
              <Area
                type="monotone"
                dataKey="p25"
                stroke="hsl(var(--chart-3))"
                fill="url(#gradP25)"
                name="p25"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
