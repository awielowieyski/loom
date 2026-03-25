import { cn } from '@/lib/utils'

interface ProgressRingProps {
  value: number // 0–1
  label: string
  size?: number
  className?: string
}

function getColor(value: number): string {
  if (value > 0.7) return 'text-green-500'
  if (value >= 0.4) return 'text-amber-500'
  return 'text-red-500'
}

function getStrokeColor(value: number): string {
  if (value > 0.7) return 'stroke-green-500'
  if (value >= 0.4) return 'stroke-amber-500'
  return 'stroke-red-500'
}

export function ProgressRing({ value, label, size = 120, className }: ProgressRingProps) {
  const clampedValue = Math.max(0, Math.min(1, value))
  const percentage = Math.round(clampedValue * 100)
  const strokeWidth = 8
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - clampedValue * circumference

  return (
    <div className={cn('flex flex-col items-center gap-2', className)}>
      <svg width={size} height={size} className="-rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          className="stroke-muted"
          strokeWidth={strokeWidth}
        />
        {/* Progress arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          className={cn('transition-all duration-500', getStrokeColor(clampedValue))}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      {/* Percentage in center */}
      <div
        className="absolute flex items-center justify-center"
        style={{ width: size, height: size }}
      >
        <span className={cn('text-xl font-bold', getColor(clampedValue))}>
          {percentage}%
        </span>
      </div>
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  )
}
