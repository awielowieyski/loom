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
  const qualityDimensions = skill.eval_spec?.quality_dimensions ?? []

  return (
    <div className={cn('space-y-4', className)}>
      <div className="space-y-1">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-muted-foreground">
            Latest Revision Score
          </span>
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
        <p className="text-sm text-muted-foreground">
          Score from the most recent evaluation run for this published revision. This is not a
          usage metric or a count of evaluations.
        </p>
      </div>

      {compositeScore != null && (
        <div className="space-y-2">
          <ScoreBar label="Latest evaluation score" score={compositeScore} />
        </div>
      )}

      <div className="rounded-lg border bg-muted/20 p-3 text-sm text-muted-foreground">
        {qualityDimensions.length > 0 ? (
          <>
            <p className="font-medium text-foreground">Tracked dimensions</p>
            <p className="mt-1">
              This revision defines {qualityDimensions.length} evaluation dimensions, but the
              detailed per-dimension scores from the latest run are not exposed on the public
              detail endpoint yet.
            </p>
            <ul className="mt-2 flex flex-wrap gap-2">
              {qualityDimensions.map((dimension) => (
                <li
                  key={dimension.name}
                  className="rounded-full border px-2 py-1 text-xs text-foreground"
                >
                  {dimension.name}
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p>
            Only the latest overall evaluation score is available for this revision right now.
            Per-dimension scoring details have not been published yet.
          </p>
        )}
      </div>
    </div>
  )
}
