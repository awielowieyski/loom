import { useState } from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { formatScore, capitalize } from '@/lib/format'
import {
  buildFingerprintPath,
  buildGridRings,
  buildAxisLines,
  getAxisLabelPositions,
  type FingerprintScores,
  type AxisName,
} from '@/lib/fingerprint'

const SIZE_MAP = {
  thumbnail: 32,
  card: 64,
  hero: 200,
} as const

type FingerprintSize = keyof typeof SIZE_MAP

interface FingerprintProps {
  scores: FingerprintScores
  size?: FingerprintSize
  confidence?: number
  className?: string
}

export function Fingerprint({
  scores,
  size = 'card',
  confidence = 1,
  className,
}: FingerprintProps) {
  const [hoveredAxis, setHoveredAxis] = useState<AxisName | null>(null)
  const px = SIZE_MAP[size]
  const isHero = size === 'hero'

  const path = buildFingerprintPath(scores, px)
  const gridRings = buildGridRings(px)
  const axisLines = buildAxisLines(px)
  const labelPositions = isHero ? getAxisLabelPositions(px) : []

  const fillOpacity = 0.15 + confidence * 0.35
  const behavioralGlow = scores.behavioral * 8

  const ariaLabel = `Skill fingerprint: ${Object.entries(scores)
    .map(([k, v]) => `${capitalize(k)} ${formatScore(v)}`)
    .join(', ')}`

  return (
    <svg
      width={px}
      height={px}
      viewBox={`0 0 ${px} ${px}`}
      role="img"
      aria-label={ariaLabel}
      className={cn('shrink-0', className)}
    >
      <defs>
        <filter id={`glow-${size}`}>
          <feGaussianBlur stdDeviation={behavioralGlow} result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Grid rings */}
      {gridRings.map((ring, i) => (
        <path
          key={i}
          d={ring}
          fill="none"
          stroke="currentColor"
          strokeOpacity={0.08}
          strokeWidth={size === 'thumbnail' ? 0.5 : 1}
        />
      ))}

      {/* Axis lines */}
      {axisLines.map((line, i) => (
        <line
          key={i}
          x1={line.x1}
          y1={line.y1}
          x2={line.x2}
          y2={line.y2}
          stroke="currentColor"
          strokeOpacity={0.1}
          strokeWidth={size === 'thumbnail' ? 0.5 : 1}
        />
      ))}

      {/* Filled polygon with smooth transitions */}
      <motion.path
        d={path}
        fill="oklch(0.546 0.245 262.881)"
        fillOpacity={fillOpacity}
        stroke="oklch(0.546 0.245 262.881)"
        strokeWidth={size === 'thumbnail' ? 0.5 : 1.5}
        strokeOpacity={0.8}
        filter={behavioralGlow > 0 ? `url(#glow-${size})` : undefined}
        initial={false}
        animate={{ d: path }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
      />

      {/* Hero: interactive hover labels */}
      {isHero &&
        labelPositions.map(({ axis, x, y, anchor }) => (
          <g
            key={axis}
            onMouseEnter={() => setHoveredAxis(axis)}
            onMouseLeave={() => setHoveredAxis(null)}
            className="cursor-default"
          >
            <text
              x={x}
              y={y}
              textAnchor={anchor}
              dominantBaseline="central"
              className="fill-foreground text-[10px] font-medium select-none"
              opacity={hoveredAxis === axis ? 1 : 0.6}
            >
              {capitalize(axis)}
            </text>
            {hoveredAxis === axis && (
              <text
                x={x}
                y={y + 14}
                textAnchor={anchor}
                dominantBaseline="central"
                className="fill-muted-foreground text-[9px] select-none"
              >
                {formatScore(scores[axis])}
              </text>
            )}
          </g>
        ))}
    </svg>
  )
}
