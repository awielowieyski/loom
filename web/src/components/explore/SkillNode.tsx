import { nodeSize, nodeOpacity, hexagonPath } from '@/lib/embedding-map'
import type { TrustTier } from '@/types/api'

export interface MapNode {
  slug: string
  name: string
  x: number
  y: number
  trust_tier: TrustTier
  composite_score: number | null
  type: 'skill' | 'capability'
}

interface SkillNodeProps {
  node: MapNode
  onHover: (node: MapNode | null, event: React.MouseEvent) => void
  onClick: (node: MapNode) => void
  dimmed: boolean
}

// Skill nodes = blue circles, capability nodes = amber hexagons
const TYPE_COLORS = {
  skill: 'oklch(0.546 0.245 262.881)',
  capability: 'oklch(0.705 0.213 47.604)',
} as const

export function SkillNode({ node, onHover, onClick, dimmed }: SkillNodeProps) {
  const r = nodeSize(node.trust_tier)
  const baseOpacity = nodeOpacity(node.composite_score)
  const opacity = dimmed ? 0.1 : baseOpacity
  const fill = TYPE_COLORS[node.type]

  return (
    <g
      className="cursor-pointer"
      onMouseEnter={(e) => onHover(node, e)}
      onMouseLeave={() => onHover(null, {} as React.MouseEvent)}
      onClick={() => onClick(node)}
    >
      {node.type === 'skill' ? (
        <circle
          cx={node.x}
          cy={node.y}
          r={r}
          fill={fill}
          fillOpacity={opacity}
          stroke={fill}
          strokeWidth={1.5}
          strokeOpacity={opacity * 0.8}
        />
      ) : (
        <path
          d={hexagonPath(node.x, node.y, r)}
          fill={fill}
          fillOpacity={opacity}
          stroke={fill}
          strokeWidth={1.5}
          strokeOpacity={opacity * 0.8}
        />
      )}
      {/* Label only visible at near zoom — controlled by parent SVG transform */}
      <text
        x={node.x}
        y={node.y + r + 12}
        textAnchor="middle"
        className="fill-foreground text-[10px] select-none pointer-events-none"
        opacity={opacity * 0.8}
      >
        {node.slug}
      </text>
    </g>
  )
}
