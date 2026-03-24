import { useSkill } from '@/hooks/useSkill'
import { ScoreBar } from '@/components/shared/ScoreBar'
import { formatScore } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { EvalDimension } from '@/types/api'

const EVAL_DIMENSIONS: EvalDimension[] = ['clarity', 'completeness', 'safety', 'correctness']

interface EvalHistoryProps {
  slug: string
  className?: string
}

export function EvalHistory({ slug, className }: EvalHistoryProps) {
  const { data: skill, isLoading } = useSkill(slug)

  if (isLoading) {
    return (
      <div className={cn('space-y-3', className)}>
        {EVAL_DIMENSIONS.map((d) => (
          <div key={d} className="h-8 animate-pulse rounded bg-muted" />
        ))}
      </div>
    )
  }

  if (!skill) return null

  const compositeScore = skill.composite_score

  // Build dimension scores from eval_spec quality dimensions and composite
  // The skill model stores per-dimension scores indirectly; use composite as fallback
  const dimensionScores: Record<string, number> = {}
  for (const dim of EVAL_DIMENSIONS) {
    // If the skill has eval data, we approximate from composite
    // In a full implementation, this would come from the latest eval result
    dimensionScores[dim] = compositeScore ?? 0
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Composite score prominently */}
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-muted-foreground">Composite Score</span>
        <span
          className={cn(
            'text-2xl font-bold tabular-nums',
            compositeScore == null
              ? 'text-muted-foreground'
              : compositeScore >= 0.7
                ? 'text-green-600 dark:text-green-400'
                : compositeScore >= 0.4
                  ? 'text-amber-600 dark:text-amber-400'
                  : 'text-red-600 dark:text-red-400',
          )}
        >
          {formatScore(compositeScore)}
        </span>
      </div>

      {/* Per-dimension bars */}
      <div className="space-y-3">
        {EVAL_DIMENSIONS.map((dim) => (
          <ScoreBar
            key={dim}
            label={dim.charAt(0).toUpperCase() + dim.slice(1)}
            score={dimensionScores[dim]}
          />
        ))}
      </div>
    </div>
  )
}
