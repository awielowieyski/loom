import { motion } from 'framer-motion'
import { Card, CardContent } from '@/components/ui/card'
import { TrustBadge } from '@/components/shared/TrustBadge'
import { Fingerprint } from '@/components/shared/Fingerprint'
import type { FingerprintScores } from '@/lib/fingerprint'
import type { Alternative } from '@/types/api'

interface AlternativeListProps {
  alternatives: Alternative[]
  onSelect: (alt: Alternative) => void
}

function summaryToFingerprint(score: number): FingerprintScores {
  return {
    clarity: score,
    completeness: score,
    correctness: score,
    safety: score,
    behavioral: 0,
  }
}

const staggerContainer = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.08 },
  },
}

const staggerItem = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.2 } },
}

export function AlternativeList({ alternatives, onSelect }: AlternativeListProps) {
  const visible = alternatives.slice(0, 3)

  if (visible.length === 0) return null

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-muted-foreground">Alternatives</h3>
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="show"
        className="space-y-2"
      >
        {visible.map((alt) => (
          <motion.div key={alt.skill.slug} variants={staggerItem}>
            <Card
              size="sm"
              className="cursor-pointer transition-colors hover:bg-muted/50"
              onClick={() => onSelect(alt)}
            >
              <CardContent className="flex items-center gap-3">
                <Fingerprint
                  scores={summaryToFingerprint(alt.match_score)}
                  size="thumbnail"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium truncate">{alt.skill.name}</span>
                    <TrustBadge tier={alt.skill.trust_tier} size="sm" />
                  </div>
                  <p className="text-xs text-muted-foreground line-clamp-1">{alt.tradeoff}</p>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </motion.div>
    </div>
  )
}
