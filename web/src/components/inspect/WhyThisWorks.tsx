import { AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ScoreBar } from '@/components/shared/ScoreBar'
import type { DimensionResult, EvalResult } from '@/types/api'

interface WhyThisWorksProps {
  evalResult?: EvalResult | null
  dimensionResults?: DimensionResult[]
  className?: string
}

export function WhyThisWorks({ evalResult, dimensionResults, className }: WhyThisWorksProps) {
  if (!evalResult) {
    return (
      <p className={cn('text-sm text-muted-foreground', className)}>
        No evaluation data available.
      </p>
    )
  }

  const dimensions = Object.entries(evalResult.dimension_scores)

  return (
    <div className={cn('space-y-4', className)}>
      {/* Injection warning */}
      {evalResult.injection_flagged && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>Injection attempt detected during evaluation</span>
        </div>
      )}

      {/* Per-dimension scores */}
      <div className="space-y-3">
        {dimensions.map(([dim, score]) => (
          <div key={dim} className="space-y-1">
            <ScoreBar label={dim.charAt(0).toUpperCase() + dim.slice(1)} score={score} />
            {/* Show evidence from dimension results if available */}
            {dimensionResults && (
              <DimensionEvidence dimension={dim} results={dimensionResults} />
            )}
          </div>
        ))}
      </div>

      {/* Behavioral judge reasoning */}
      {dimensionResults && dimensionResults.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium">Evidence</h3>
          {dimensionResults.map((dr, i) => (
            <div key={i} className="rounded-lg bg-muted/50 px-3 py-2 text-xs">
              <span className="font-medium capitalize">{dr.dimension}</span>
              <span className="mx-1 text-muted-foreground">
                (confidence: {Math.round(dr.confidence * 100)}%)
              </span>
              {dr.evidence.length > 0 && (
                <ul className="mt-1 space-y-0.5 text-muted-foreground">
                  {dr.evidence.slice(0, 3).map((e, j) => (
                    <li key={j}>{e}</li>
                  ))}
                </ul>
              )}
              {dr.injection_detected && (
                <p className="mt-1 text-red-600 dark:text-red-400">
                  Injection detected: {dr.injection_detail}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function DimensionEvidence({
  dimension,
  results,
}: {
  dimension: string
  results: DimensionResult[]
}) {
  const match = results.find((r) => r.dimension === dimension)
  if (!match || match.evidence.length === 0) return null

  return (
    <ul className="ml-1 space-y-0.5 text-xs text-muted-foreground">
      {match.evidence.slice(0, 2).map((e, i) => (
        <li key={i} className="truncate">
          {e}
        </li>
      ))}
    </ul>
  )
}
