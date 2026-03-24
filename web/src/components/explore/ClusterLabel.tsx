interface ClusterLabelProps {
  category: string
  x: number
  y: number
  count: number
  zoom: number
}

export function ClusterLabel({ category, x, y, count, zoom }: ClusterLabelProps) {
  // Font size scales with count (min 12px, max 24px), adjusted for zoom
  const baseFontSize = Math.min(24, Math.max(12, 10 + count * 1.5))
  const fontSize = baseFontSize / zoom

  // Fade in at far zoom (< 0.5x), fade out at near zoom (> 1.5x)
  const opacity = zoom < 0.5 ? 0.8 : zoom > 1.5 ? 0 : 0.8 * (1.5 - zoom)

  if (opacity <= 0) return null

  return (
    <text
      x={x}
      y={y}
      textAnchor="middle"
      dominantBaseline="central"
      className="fill-muted-foreground font-semibold select-none pointer-events-none"
      style={{ fontSize: `${fontSize}px`, opacity }}
    >
      {category}
    </text>
  )
}
