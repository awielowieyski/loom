import { useRef, useEffect, useState, useCallback, useMemo } from 'react'
import * as d3 from 'd3'
import { useEmbeddingMap } from '@/hooks/useEmbeddingMap'
import {
  createScaleX,
  createScaleY,
  computeClusterCentroids,
} from '@/lib/embedding-map'
import { ClusterLabel } from './ClusterLabel'
import { SkillNode, type MapNode } from './SkillNode'
import type { EmbeddingMapSkill, EmbeddingMapCapability } from '@/types/api'

interface SemanticMapProps {
  searchFilter: string
  onHoverNode: (node: MapNode | null, event: React.MouseEvent) => void
  onClickNode: (node: MapNode) => void
}

const MAP_WIDTH = 2000
const MAP_HEIGHT = 2000

export function SemanticMap({ searchFilter, onHoverNode, onClickNode }: SemanticMapProps) {
  const { data, isLoading } = useEmbeddingMap()
  const svgRef = useRef<SVGSVGElement>(null)
  const gRef = useRef<SVGGElement>(null)
  const [zoom, setZoom] = useState(1)

  const scaleX = useMemo(() => createScaleX(MAP_WIDTH), [])
  const scaleY = useMemo(() => createScaleY(MAP_HEIGHT), [])

  // Build unified node list for rendering
  const { skillNodes, capabilityNodes, allNodes } = useMemo(() => {
    if (!data) return { skillNodes: [], capabilityNodes: [], allNodes: [] }

    const skills: MapNode[] = data.skills.map((s: EmbeddingMapSkill) => ({
      slug: s.slug,
      name: s.name,
      x: scaleX(s.x),
      y: scaleY(s.y),
      trust_tier: s.trust_tier,
      composite_score: s.composite_score,
      type: 'skill' as const,
    }))

    const caps: MapNode[] = data.capabilities.map((c: EmbeddingMapCapability) => ({
      slug: c.slug,
      name: c.name,
      x: scaleX(c.x),
      y: scaleY(c.y),
      trust_tier: c.trust_tier,
      composite_score: c.composite_score,
      type: 'capability' as const,
    }))

    return { skillNodes: skills, capabilityNodes: caps, allNodes: [...skills, ...caps] }
  }, [data, scaleX, scaleY])

  // Cluster centroids for labels
  const centroids = useMemo(() => {
    if (!data) return []
    const allItems = [
      ...data.skills.map((s) => ({ ...s, type: 'skill' as const })),
      ...data.capabilities.map((c) => ({ ...c, type: 'capability' as const })),
    ].map((item) => ({
      x: scaleX(item.x),
      y: scaleY(item.y),
      category: item.category,
    }))
    return computeClusterCentroids(allItems, 'category')
  }, [data, scaleX, scaleY])

  // Capability edges: connect capability to its step skills
  const edges = useMemo(() => {
    if (!data) return []
    const skillMap = new Map(skillNodes.map((s) => [s.slug, s]))
    const result: { from: MapNode; to: MapNode }[] = []

    for (let i = 0; i < data.capabilities.length; i++) {
      const cap = data.capabilities[i]
      const capNode = capabilityNodes[i]
      if (!capNode) continue
      for (const stepSlug of cap.step_slugs) {
        const skillNode = skillMap.get(stepSlug)
        if (skillNode) {
          result.push({ from: capNode, to: skillNode })
        }
      }
    }
    return result
  }, [data, skillNodes, capabilityNodes])

  // Search filter: which slugs match
  const matchingSlugs = useMemo(() => {
    if (!searchFilter) return null
    const lower = searchFilter.toLowerCase()
    return new Set(
      allNodes
        .filter((n) => n.slug.toLowerCase().includes(lower) || n.name.toLowerCase().includes(lower))
        .map((n) => n.slug),
    )
  }, [searchFilter, allNodes])

  // Set up D3 zoom
  useEffect(() => {
    const svg = svgRef.current
    const g = gRef.current
    if (!svg || !g) return

    const zoomBehavior = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 5])
      .on('zoom', (event: d3.D3ZoomEvent<SVGSVGElement, unknown>) => {
        d3.select(g).attr('transform', event.transform.toString())
        setZoom(event.transform.k)
      })

    d3.select(svg).call(zoomBehavior)

    // Initial fit: center the map
    const initialTransform = d3.zoomIdentity.translate(-MAP_WIDTH / 4, -MAP_HEIGHT / 4).scale(0.5)
    d3.select(svg).call(zoomBehavior.transform, initialTransform)

    return () => {
      d3.select(svg).on('.zoom', null)
    }
  }, [])

  const isDimmed = useCallback(
    (slug: string) => {
      if (!matchingSlugs) return false
      return !matchingSlugs.has(slug)
    },
    [matchingSlugs],
  )

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full w-full">
        <div className="animate-pulse space-y-2 text-center">
          <div className="h-8 w-48 bg-muted rounded mx-auto" />
          <p className="text-muted-foreground text-sm">Loading semantic map...</p>
        </div>
      </div>
    )
  }

  if (!data || (data.skills.length === 0 && data.capabilities.length === 0)) {
    return (
      <div className="flex items-center justify-center h-full w-full">
        <div className="text-center space-y-2">
          <p className="text-lg font-medium text-muted-foreground">No skills or capabilities</p>
          <p className="text-sm text-muted-foreground">
            Register some skills to see the semantic landscape.
          </p>
        </div>
      </div>
    )
  }

  return (
    <svg
      ref={svgRef}
      className="w-full h-full bg-background"
      style={{ cursor: 'grab' }}
    >
      <g ref={gRef}>
        {/* Layer 1: Edges */}
        <g className="edges">
          {edges.map((edge, i) => (
            <line
              key={`edge-${i}`}
              x1={edge.from.x}
              y1={edge.from.y}
              x2={edge.to.x}
              y2={edge.to.y}
              stroke="currentColor"
              strokeOpacity={0.1}
              strokeWidth={1}
            />
          ))}
        </g>

        {/* Layer 2: Cluster labels (visible at far zoom) */}
        <g className="cluster-labels">
          {centroids.map((c) => (
            <ClusterLabel
              key={c.category}
              category={c.category}
              x={c.x}
              y={c.y}
              count={c.count}
              zoom={zoom}
            />
          ))}
        </g>

        {/* Layer 3: Nodes */}
        <g className="nodes">
          {allNodes.map((node) => (
            <SkillNode
              key={`${node.type}-${node.slug}`}
              node={node}
              onHover={onHoverNode}
              onClick={onClickNode}
              dimmed={isDimmed(node.slug)}
            />
          ))}
        </g>
      </g>
    </svg>
  )
}
