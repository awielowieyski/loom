import { useState } from 'react'
import { CheckCircle2, XCircle, MessageSquare, ShieldAlert } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useSubmitReview } from '@/hooks/useStats'
import { cn } from '@/lib/utils'
import type { GovernanceQueueItem } from '@/types/api'

interface ReviewInterfaceProps {
  item: GovernanceQueueItem
  onComplete: () => void
  className?: string
}

function ScoreBar({ label, score }: { label: string; score: number }) {
  const percentage = Math.round(score * 100)
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">{percentage}%</span>
      </div>
      <div className="h-2 w-full rounded-full bg-muted">
        <div
          className={cn(
            'h-full rounded-full transition-all',
            score >= 0.7 ? 'bg-green-500' : score >= 0.4 ? 'bg-amber-500' : 'bg-red-500',
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}

export function ReviewInterface({ item, onComplete, className }: ReviewInterfaceProps) {
  const [note, setNote] = useState('')
  const { mutate: submitReview, isPending } = useSubmitReview()

  const handleSubmit = (decision: 'approve' | 'reject' | 'request_changes') => {
    if (!note.trim()) return
    submitReview(
      { queue_item_id: item.id, decision, note },
      {
        onSuccess: () => {
          setNote('')
          onComplete()
        },
      },
    )
  }

  const dimensionScores = item.eval_summary?.dimension_scores ?? {}

  return (
    <Card className={cn('flex flex-col', className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="truncate">{item.name}</CardTitle>
          {item.eval_summary?.injection_flagged && (
            <Badge variant="secondary" className="bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300 border-0">
              <ShieldAlert className="mr-1 h-3 w-3" />
              Injection Detected
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex-1 space-y-4 overflow-y-auto">
        {/* Eval summary */}
        <div className="space-y-3">
          <h4 className="text-sm font-medium">Eval Scores</h4>
          {item.eval_summary?.composite_score != null && (
            <ScoreBar label="Composite" score={item.eval_summary.composite_score} />
          )}
          {Object.entries(dimensionScores).map(([dim, score]) => (
            <ScoreBar key={dim} label={dim} score={score} />
          ))}
          {Object.keys(dimensionScores).length === 0 &&
            item.eval_summary?.composite_score == null && (
              <p className="text-xs text-muted-foreground">No eval scores available.</p>
            )}
        </div>

        {/* Changelog if amendment */}
        {item.eval_summary?.changelog && (
          <div className="space-y-1">
            <h4 className="text-sm font-medium">Amendment Changelog</h4>
            <p className="rounded-md bg-muted p-2 text-xs whitespace-pre-wrap">
              {item.eval_summary.changelog}
            </p>
          </div>
        )}

        {/* Note textarea */}
        <div className="space-y-2">
          <label htmlFor="review-note" className="text-sm font-medium">
            Review Note <span className="text-red-500">*</span>
          </label>
          <textarea
            id="review-note"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Provide reasoning for your decision..."
            className="w-full rounded-md border bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            rows={3}
          />
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            onClick={() => handleSubmit('approve')}
            disabled={isPending || !note.trim()}
            className="bg-green-600 hover:bg-green-700 text-white"
          >
            <CheckCircle2 className="mr-1 h-4 w-4" />
            Approve
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleSubmit('request_changes')}
            disabled={isPending || !note.trim()}
            className="border-amber-500 text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-950/20"
          >
            <MessageSquare className="mr-1 h-4 w-4" />
            Request Changes
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleSubmit('reject')}
            disabled={isPending || !note.trim()}
            className="border-red-500 text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20"
          >
            <XCircle className="mr-1 h-4 w-4" />
            Reject
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
