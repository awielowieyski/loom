import { memo } from 'react'
import { BaseEdge, EdgeLabelRenderer, getBezierPath } from '@xyflow/react'
import type { EdgeProps } from '@xyflow/react'
import { cn } from '@/lib/utils'

const CLASSIFICATION_STYLES: Record<string, { stroke: string; label: string }> = {
  internal: { stroke: '#9ca3af', label: 'text-muted-foreground bg-muted' },
  sensitive: { stroke: '#ef4444', label: 'text-red-700 bg-red-100 dark:text-red-300 dark:bg-red-900/30' },
  confidential: { stroke: '#ef4444', label: 'text-red-700 bg-red-100 dark:text-red-300 dark:bg-red-900/30' },
  public: { stroke: '#22c55e', label: 'text-green-700 bg-green-100 dark:text-green-300 dark:bg-green-900/30' },
  none: { stroke: '#9ca3af', label: 'text-muted-foreground bg-muted' },
}

function DataFlowEdgeComponent({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps) {
  const classification = (data?.classification as string) ?? 'internal'
  const styles = CLASSIFICATION_STYLES[classification] ?? CLASSIFICATION_STYLES.internal

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  })

  return (
    <>
      <BaseEdge id={id} path={edgePath} style={{ stroke: styles.stroke, strokeWidth: 1.5 }} />
      <EdgeLabelRenderer>
        <div
          className={cn(
            'absolute rounded px-1.5 py-0.5 text-[10px] font-medium pointer-events-none',
            styles.label,
          )}
          style={{
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
          }}
        >
          {classification}
        </div>
      </EdgeLabelRenderer>
    </>
  )
}

export const DataFlowEdge = memo(DataFlowEdgeComponent)
