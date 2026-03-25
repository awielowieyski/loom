import { cn } from '@/lib/utils'

interface ScoreBarProps {
  score: number
  label: string
  color?: string
  className?: string
}

function getScoreColor(score: number): string {
  if (score < 0.4) return 'bg-red-500'
  if (score <= 0.7) return 'bg-amber-500'
  return 'bg-green-500'
}

export function ScoreBar({ score, label, color, className }: ScoreBarProps) {
  const pct = Math.round(score * 100)
  const barColor = color ?? getScoreColor(score)

  return (
    <div className={cn('flex flex-col gap-1', className)}>
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium tabular-nums">{pct}%</span>
      </div>
      <div className="h-2 w-full rounded-full bg-muted">
        <div
          className={cn('h-full rounded-full transition-all', barColor)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
