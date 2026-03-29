import * as d3 from 'd3'
import type { TrustTier } from '@/types/api'

// ---- Node sizing by trust tier ----

const NODE_SIZE: Record<TrustTier, number> = {
  unvetted: 4,
  verified: 16,
  community: 10,
  experimental: 6,
}

export function nodeSize(trustTier: TrustTier): number {
  return NODE_SIZE[trustTier] ?? 10
}

// ---- Node opacity by composite score ----

export function nodeOpacity(compositeScore: number | null): number {
  if (compositeScore == null) return 0.5
  // Map score (0-1) to opacity (0.3-1.0)
  return 0.3 + compositeScore * 0.7
}

// ---- Scale functions for mapping UMAP coords to pixel space ----

export function createScaleX(width: number, padding = 60) {
  return d3.scaleLinear().domain([-1, 1]).range([padding, width - padding])
}

export function createScaleY(height: number, padding = 60) {
  return d3.scaleLinear().domain([-1, 1]).range([padding, height - padding])
}

// ---- Cluster centroid computation ----

interface NodeWithCategory {
  x: number
  y: number
  [key: string]: unknown
}

export interface ClusterCentroid {
  category: string
  x: number
  y: number
  count: number
}

export function computeClusterCentroids<T extends NodeWithCategory>(
  nodes: T[],
  categoryField: keyof T & string,
): ClusterCentroid[] {
  const groups = new Map<string, { sumX: number; sumY: number; count: number }>()

  for (const node of nodes) {
    const category = String(node[categoryField] ?? 'uncategorized')
    const group = groups.get(category) ?? { sumX: 0, sumY: 0, count: 0 }
    group.sumX += node.x
    group.sumY += node.y
    group.count += 1
    groups.set(category, group)
  }

  const centroids: ClusterCentroid[] = []
  for (const [category, group] of groups) {
    centroids.push({
      category,
      x: group.sumX / group.count,
      y: group.sumY / group.count,
      count: group.count,
    })
  }

  return centroids
}

// ---- Hexagon path for capability nodes ----

export function hexagonPath(cx: number, cy: number, r: number): string {
  const points: string[] = []
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i - Math.PI / 6
    points.push(`${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`)
  }
  return `M${points.join('L')}Z`
}
