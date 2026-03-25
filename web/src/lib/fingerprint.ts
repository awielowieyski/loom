/**
 * Fingerprint SVG path generation utilities.
 *
 * Five axes: Clarity (top), Completeness (top-right), Correctness (bottom-right),
 * Safety (bottom-left), Behavioral (top-left).
 * Angles: evenly spaced at 72-degree intervals starting from top (270 degrees).
 */

export const AXES = ['clarity', 'completeness', 'correctness', 'safety', 'behavioral'] as const
export type AxisName = (typeof AXES)[number]

const AXIS_ANGLES_DEG = [270, 342, 54, 126, 198] // starting top, clockwise at 72-degree intervals

function degToRad(deg: number): number {
  return (deg * Math.PI) / 180
}

export function polarToCartesian(
  cx: number,
  cy: number,
  radius: number,
  angleDeg: number,
): { x: number; y: number } {
  const rad = degToRad(angleDeg)
  return {
    x: cx + radius * Math.cos(rad),
    y: cy + radius * Math.sin(rad),
  }
}

/**
 * Catmull-Rom spline interpolation through a set of points.
 * Produces a smooth closed SVG path.
 */
export function catmullRomSpline(
  points: { x: number; y: number }[],
  tension: number = 0.5,
): string {
  const n = points.length
  if (n < 3) {
    return points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ') + ' Z'
  }

  const alpha = 1 - tension
  const segments: string[] = []

  for (let i = 0; i < n; i++) {
    const p0 = points[(i - 1 + n) % n]
    const p1 = points[i]
    const p2 = points[(i + 1) % n]
    const p3 = points[(i + 2) % n]

    const cp1x = p1.x + ((p2.x - p0.x) * alpha) / 6
    const cp1y = p1.y + ((p2.y - p0.y) * alpha) / 6
    const cp2x = p2.x - ((p3.x - p1.x) * alpha) / 6
    const cp2y = p2.y - ((p3.y - p1.y) * alpha) / 6

    if (i === 0) {
      segments.push(`M${p1.x},${p1.y}`)
    }
    segments.push(`C${cp1x},${cp1y} ${cp2x},${cp2y} ${p2.x},${p2.y}`)
  }

  segments.push('Z')
  return segments.join(' ')
}

export type FingerprintScores = Record<AxisName, number>

/**
 * Build an SVG path `d` attribute from 5 dimension scores.
 * Each score is 0-1 and maps to distance from center.
 */
export function buildFingerprintPath(scores: FingerprintScores, size: number): string {
  const cx = size / 2
  const cy = size / 2
  const maxRadius = size * 0.42 // leave margin for labels

  const points = AXES.map((axis, i) => {
    const score = Math.max(0, Math.min(1, scores[axis]))
    const radius = score * maxRadius
    return polarToCartesian(cx, cy, radius, AXIS_ANGLES_DEG[i])
  })

  return catmullRomSpline(points, 0.5)
}

/**
 * Build grid ring paths for the background.
 */
export function buildGridRings(size: number, rings: number = 4): string[] {
  const cx = size / 2
  const cy = size / 2
  const maxRadius = size * 0.42

  return Array.from({ length: rings }, (_, i) => {
    const r = ((i + 1) / rings) * maxRadius
    const pts = AXIS_ANGLES_DEG.map((angle) => polarToCartesian(cx, cy, r, angle))
    return pts.map((p, j) => `${j === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ') + ' Z'
  })
}

/**
 * Build axis line paths from center to edge.
 */
export function buildAxisLines(size: number): { x1: number; y1: number; x2: number; y2: number }[] {
  const cx = size / 2
  const cy = size / 2
  const maxRadius = size * 0.42

  return AXIS_ANGLES_DEG.map((angle) => {
    const end = polarToCartesian(cx, cy, maxRadius, angle)
    return { x1: cx, y1: cy, x2: end.x, y2: end.y }
  })
}

/**
 * Get label positions for hero-size fingerprint.
 */
export function getAxisLabelPositions(
  size: number,
): { axis: AxisName; x: number; y: number; anchor: 'start' | 'middle' | 'end' }[] {
  const cx = size / 2
  const cy = size / 2
  const labelRadius = size * 0.48

  return AXES.map((axis, i) => {
    const pos = polarToCartesian(cx, cy, labelRadius, AXIS_ANGLES_DEG[i])
    const angle = AXIS_ANGLES_DEG[i]
    let anchor: 'start' | 'middle' | 'end' = 'middle'
    if (angle > 180 && angle < 360 && angle !== 270) anchor = 'end'
    if (angle > 0 && angle < 180) anchor = 'start'
    return { axis, x: pos.x, y: pos.y, anchor }
  })
}
