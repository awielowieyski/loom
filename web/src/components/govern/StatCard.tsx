import type { ReactNode } from 'react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface StatCardProps {
  title: string
  value: number | string
  trend?: 'up' | 'down' | 'flat'
  icon?: ReactNode
  className?: string
}

const TREND_CONFIG = {
  up: { Icon: TrendingUp, className: 'text-green-500' },
  down: { Icon: TrendingDown, className: 'text-red-500' },
  flat: { Icon: Minus, className: 'text-muted-foreground' },
} as const

export function StatCard({ title, value, trend, icon, className }: StatCardProps) {
  const trendConfig = trend ? TREND_CONFIG[trend] : null

  return (
    <Card className={cn('relative', className)}>
      <CardContent className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-2xl font-bold tracking-tight">{value}</p>
          <p className="text-sm text-muted-foreground">{title}</p>
        </div>
        <div className="flex items-center gap-2">
          {trendConfig && (
            <trendConfig.Icon className={cn('h-4 w-4', trendConfig.className)} />
          )}
          {icon && (
            <div className="text-muted-foreground">{icon}</div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
