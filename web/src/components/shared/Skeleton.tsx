import type { CSSProperties } from 'react'
import { cn } from '@/lib/utils'

type SkeletonVariant = 'text' | 'card' | 'fingerprint' | 'chart'

interface SkeletonProps {
  variant?: SkeletonVariant
  className?: string
  /** Number of text lines to render (only for 'text' variant) */
  lines?: number
}

function SkeletonBase({ className, style }: { className?: string; style?: CSSProperties }) {
  return <div className={cn('animate-pulse rounded bg-muted', className)} style={style} />
}

function TextSkeleton({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonBase
          key={i}
          className={cn('h-4', i === lines - 1 ? 'w-2/3' : 'w-full')}
        />
      ))}
    </div>
  )
}

function CardSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('rounded-xl border bg-card p-6 space-y-4', className)}>
      <div className="flex items-start gap-4">
        <SkeletonBase className="h-12 w-12 rounded-full" />
        <div className="flex-1 space-y-2">
          <SkeletonBase className="h-5 w-1/3" />
          <SkeletonBase className="h-4 w-2/3" />
        </div>
      </div>
      <SkeletonBase className="h-3 w-1/4" />
    </div>
  )
}

function FingerprintSkeleton({ className }: { className?: string }) {
  return (
    <SkeletonBase className={cn('h-16 w-16 rounded-full', className)} />
  )
}

const CHART_BAR_HEIGHTS = [65, 40, 85, 55, 75, 45, 90]

function ChartSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('rounded-xl border bg-card p-6', className)}>
      <SkeletonBase className="h-4 w-32 mb-4" />
      <div className="flex items-end gap-2 h-32">
        {CHART_BAR_HEIGHTS.map((h, i) => (
          <SkeletonBase
            key={i}
            className="flex-1"
            style={{ height: `${h}%` }}
          />
        ))}
      </div>
    </div>
  )
}

export function Skeleton({ variant = 'text', className, lines }: SkeletonProps) {
  switch (variant) {
    case 'text':
      return <TextSkeleton lines={lines} className={className} />
    case 'card':
      return <CardSkeleton className={className} />
    case 'fingerprint':
      return <FingerprintSkeleton className={className} />
    case 'chart':
      return <ChartSkeleton className={className} />
  }
}
