import { useState, memo } from 'react'
import { Handle, Position } from '@xyflow/react'
import type { NodeProps } from '@xyflow/react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { useNavigate } from '@tanstack/react-router'
import { cn } from '@/lib/utils'
import { TrustBadge } from '@/components/shared/TrustBadge'
import type { TrustTier } from '@/types/api'

export interface StepNodeData {
  skillRef: string
  role: string
  required: boolean
  trustTier?: TrustTier
  contentPreview?: string
  [key: string]: unknown
}

function StepNodeComponent({ data }: NodeProps) {
  const [expanded, setExpanded] = useState(false)
  const nodeData = data as StepNodeData
  const navigate = useNavigate()
  const slug = nodeData.skillRef.replace(/^loom:\/\//, '')

  return (
    <div
      className={cn(
        'rounded-lg bg-card px-3 py-2 text-sm ring-1 min-w-[200px] max-w-[260px] cursor-pointer hover:ring-foreground/40 transition-all',
        nodeData.required
          ? 'ring-foreground/20'
          : 'ring-foreground/10 ring-dashed',
      )}
      onClick={() => navigate({ to: '/skills/$slug', params: { slug } })}
    >
      <Handle type="target" position={Position.Top} className="!bg-foreground/30 !w-2 !h-2" />

      <div className="space-y-1">
        <div className="flex items-center gap-1.5">
          <span className="font-medium truncate">{nodeData.skillRef}</span>
          {!nodeData.required && (
            <span className="text-[10px] text-muted-foreground">(optional)</span>
          )}
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-xs text-muted-foreground">{nodeData.role}</span>
          {nodeData.trustTier && <TrustBadge tier={nodeData.trustTier} size="sm" />}
        </div>

        {nodeData.contentPreview && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            {expanded ? (
              <ChevronDown className="h-3 w-3" />
            ) : (
              <ChevronRight className="h-3 w-3" />
            )}
            Preview
          </button>
        )}

        {expanded && nodeData.contentPreview && (
          <p className="text-xs text-muted-foreground mt-1 line-clamp-3">
            {nodeData.contentPreview}
          </p>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-foreground/30 !w-2 !h-2" />
    </div>
  )
}

export const StepNode = memo(StepNodeComponent)
