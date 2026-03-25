/* eslint-disable react-refresh/only-export-components */
import { useState, useCallback } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { SemanticMap } from '@/components/explore/SemanticMap'
import { MapSearch } from '@/components/explore/MapSearch'
import { NodeTooltip } from '@/components/explore/NodeTooltip'
import { DetailPanel } from '@/components/explore/DetailPanel'
import type { MapNode } from '@/components/explore/SkillNode'

export const Route = createFileRoute('/explore')({
  component: ExploreView,
})

function ExploreView() {
  const [searchFilter, setSearchFilter] = useState('')
  const [hoveredNode, setHoveredNode] = useState<MapNode | null>(null)
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 })
  const [selectedNode, setSelectedNode] = useState<MapNode | null>(null)

  const handleHoverNode = useCallback((node: MapNode | null, event: React.MouseEvent) => {
    setHoveredNode(node)
    if (node && event.clientX !== undefined) {
      setTooltipPos({ x: event.clientX, y: event.clientY })
    }
  }, [])

  const handleClickNode = useCallback((node: MapNode) => {
    setSelectedNode(node)
  }, [])

  const handleCloseDetail = useCallback(() => {
    setSelectedNode(null)
  }, [])

  return (
    <div className="relative h-[calc(100vh-4rem)] w-full overflow-hidden">
      {/* Search overlay */}
      <MapSearch value={searchFilter} onChange={setSearchFilter} />

      {/* Full-viewport semantic map */}
      <SemanticMap
        searchFilter={searchFilter}
        onHoverNode={handleHoverNode}
        onClickNode={handleClickNode}
      />

      {/* Tooltip on hover */}
      {hoveredNode && (
        <NodeTooltip node={hoveredNode} x={tooltipPos.x} y={tooltipPos.y} />
      )}

      {/* Detail panel on click */}
      <DetailPanel node={selectedNode} onClose={handleCloseDetail} />
    </div>
  )
}
