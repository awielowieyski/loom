import { formatScore, capitalize } from '@/lib/format'
import { TrustBadge } from '@/components/shared/TrustBadge'
import type { MapNode } from './SkillNode'

interface NodeTooltipProps {
  node: MapNode
  x: number
  y: number
}

export function NodeTooltip({ node, x, y }: NodeTooltipProps) {
  // Position near cursor, nudge away from viewport edges
  const tooltipWidth = 220
  const tooltipHeight = 80
  const offsetX = 12
  const offsetY = 12

  // Avoid going off right/bottom edge
  const adjustedX = x + tooltipWidth + offsetX > window.innerWidth ? x - tooltipWidth - offsetX : x + offsetX
  const adjustedY = y + tooltipHeight + offsetY > window.innerHeight ? y - tooltipHeight - offsetY : y + offsetY

  return (
    <div
      className="fixed z-50 bg-popover border rounded-lg shadow-lg p-3 space-y-1.5 pointer-events-none"
      style={{
        left: adjustedX,
        top: adjustedY,
        width: tooltipWidth,
      }}
    >
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium truncate">{node.name || node.slug}</span>
        <span className="text-xs text-muted-foreground">
          {capitalize(node.type)}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <TrustBadge tier={node.trust_tier} size="sm" />
        <span className="text-xs text-muted-foreground">
          Score: {formatScore(node.composite_score)}
        </span>
      </div>
    </div>
  )
}
