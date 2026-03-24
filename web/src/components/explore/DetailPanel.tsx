import { useEffect, useRef } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { useSkill } from '@/hooks/useSkill'
import { useCapability } from '@/hooks/useCapability'
import { TrustBadge } from '@/components/shared/TrustBadge'
import { formatScore } from '@/lib/format'
import type { MapNode } from './SkillNode'

interface DetailPanelProps {
  node: MapNode | null
  onClose: () => void
}

export function DetailPanel({ node, onClose }: DetailPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null)

  // Always call hooks — use empty slug to disable
  const slug = node?.slug ?? ''
  const isSkill = node?.type === 'skill'

  const { data: skill, isLoading: skillLoading } = useSkill(isSkill ? slug : '')
  const { data: capability, isLoading: capLoading } = useCapability(!isSkill ? slug : '')

  // Click outside to dismiss
  useEffect(() => {
    if (!node) return

    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose()
      }
    }

    // Delay to avoid immediate close from the click that opened the panel
    const timer = setTimeout(() => {
      document.addEventListener('mousedown', handleClick)
    }, 100)

    return () => {
      clearTimeout(timer)
      document.removeEventListener('mousedown', handleClick)
    }
  }, [node, onClose])

  const isLoading = isSkill ? skillLoading : capLoading
  const detail = isSkill ? skill : capability

  return (
    <AnimatePresence>
      {node && (
        <motion.div
          ref={panelRef}
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className="fixed right-0 top-0 h-full w-96 bg-background border-l shadow-xl z-40 overflow-y-auto"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b">
            <h2 className="text-lg font-semibold truncate">{node.name || node.slug}</h2>
            <button
              onClick={onClose}
              className="p-1 hover:bg-muted rounded transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Content */}
          <div className="p-4 space-y-4">
            {/* Type + Trust */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                {node.type}
              </span>
              <TrustBadge tier={node.trust_tier} size="sm" />
            </div>

            {/* Scores */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-muted/50 rounded-lg p-3">
                <p className="text-xs text-muted-foreground">Composite Score</p>
                <p className="text-lg font-semibold">{formatScore(node.composite_score)}</p>
              </div>
              {node.type === 'skill' && (
                <div className="bg-muted/50 rounded-lg p-3">
                  <p className="text-xs text-muted-foreground">Behavioral Score</p>
                  <p className="text-lg font-semibold">
                    {formatScore((detail && 'behavioral_score' in detail) ? (detail as { behavioral_score: number | null }).behavioral_score : null)}
                  </p>
                </div>
              )}
            </div>

            {/* Description */}
            {isLoading ? (
              <div className="space-y-2 animate-pulse">
                <div className="h-4 bg-muted rounded w-full" />
                <div className="h-4 bg-muted rounded w-3/4" />
                <div className="h-4 bg-muted rounded w-1/2" />
              </div>
            ) : detail ? (
              <div className="space-y-3">
                <div>
                  <h3 className="text-sm font-medium mb-1">Description</h3>
                  <p className="text-sm text-muted-foreground">{detail.description}</p>
                </div>

                {/* Tags */}
                {detail.tags && detail.tags.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium mb-1">Tags</h3>
                    <div className="flex flex-wrap gap-1">
                      {detail.tags.map((tag) => (
                        <span
                          key={tag}
                          className="inline-block text-xs bg-muted px-2 py-0.5 rounded"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Version + Cost */}
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-muted-foreground">Version: </span>
                    <span className="font-medium">{detail.version}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Cost: </span>
                    <span className="font-medium">{detail.cost_profile}</span>
                  </div>
                </div>

                {/* Capability steps */}
                {!isSkill && 'steps' in detail && (
                  <div>
                    <h3 className="text-sm font-medium mb-1">
                      Steps ({(detail as { steps: unknown[] }).steps.length})
                    </h3>
                    <ul className="space-y-1">
                      {(detail as { steps: { skill_ref: string; role: string }[] }).steps.map(
                        (step, i) => (
                          <li
                            key={i}
                            className="text-xs text-muted-foreground flex items-center gap-2"
                          >
                            <span className="w-5 h-5 bg-muted rounded-full flex items-center justify-center text-[10px] font-medium shrink-0">
                              {i + 1}
                            </span>
                            <span className="font-mono">{step.skill_ref}</span>
                            <span className="text-muted-foreground/60">{step.role}</span>
                          </li>
                        ),
                      )}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Could not load details.</p>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
