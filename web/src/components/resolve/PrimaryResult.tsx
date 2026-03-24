import { Link } from '@tanstack/react-router'
import { AnimatePresence, motion } from 'framer-motion'
import { Blocks, Puzzle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { TrustBadge } from '@/components/shared/TrustBadge'
import { Fingerprint } from '@/components/shared/Fingerprint'
import { MiniFlowPreview } from '@/components/shared/MiniFlowPreview'
import { formatScore } from '@/lib/format'
import type { FingerprintScores } from '@/lib/fingerprint'
import type { ResolvedResult } from '@/types/api'

interface PrimaryResultProps {
  result: ResolvedResult
}

function skillToFingerprint(composite: number | null, behavioral: number | null): FingerprintScores {
  const base = composite ?? 0.5
  return {
    clarity: base,
    completeness: base,
    correctness: base,
    safety: base,
    behavioral: behavioral ?? 0,
  }
}

export function PrimaryResult({ result }: PrimaryResultProps) {
  const isSkill = result.type === 'skill' && result.skill
  const isCapability = result.type === 'capability' && result.capability

  if (!isSkill && !isCapability) return null

  const name = isSkill ? result.skill!.skill.name : result.capability!.capability.name
  const slug = isSkill ? result.skill!.skill.slug : result.capability!.capability.slug
  const description = isSkill
    ? result.skill!.skill.description
    : result.capability!.capability.description
  const trustTier = isSkill
    ? result.skill!.skill.trust_tier
    : result.capability!.effective_trust_tier
  const compositeScore = isSkill
    ? result.skill!.skill.composite_score
    : result.capability!.capability.eval_spec ? null : null
  const behavioralScore = isSkill ? result.skill!.skill.behavioral_score : null
  const resolutionCount = isSkill ? result.skill!.skill.resolution_count : 0
  const rationale = isSkill
    ? result.skill!.selection_rationale
    : result.capability!.selection_rationale

  const linkTo = isSkill ? `/skills/${slug}` : `/capabilities/${slug}`
  const fingerprint = skillToFingerprint(compositeScore, behavioralScore)

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={slug}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.25, ease: 'easeOut' }}
      >
        <Link to={linkTo}>
          <Card className="cursor-pointer transition-shadow hover:shadow-md">
            <CardHeader>
              <div className="flex items-start gap-4">
                <Fingerprint scores={fingerprint} size="card" />
                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <CardTitle className="truncate">{name}</CardTitle>
                    <Badge variant="outline" className="gap-1 text-xs shrink-0">
                      {isSkill ? (
                        <Puzzle className="h-3 w-3" />
                      ) : (
                        <Blocks className="h-3 w-3" />
                      )}
                      {isSkill ? 'Skill' : 'Capability'}
                    </Badge>
                    <TrustBadge tier={trustTier} size="sm" />
                  </div>
                  <CardDescription className="line-clamp-2">{description}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Capability step preview */}
              {isCapability && result.capability!.capability.steps.length > 0 && (
                <MiniFlowPreview steps={result.capability!.capability.steps} />
              )}

              {/* Stats row */}
              <div className="flex items-center gap-4 text-xs text-muted-foreground">
                {compositeScore != null && (
                  <span>Score: {formatScore(compositeScore)}</span>
                )}
                {resolutionCount > 0 && (
                  <span>Resolved {resolutionCount} {resolutionCount === 1 ? 'time' : 'times'}</span>
                )}
                {rationale.length > 0 && (
                  <span className="truncate">{rationale[0]}</span>
                )}
              </div>
            </CardContent>
          </Card>
        </Link>
      </motion.div>
    </AnimatePresence>
  )
}
