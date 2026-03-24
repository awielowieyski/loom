import { createFileRoute } from '@tanstack/react-router'
import { Fingerprint } from '@/components/shared/Fingerprint'
import { TrustBadge } from '@/components/shared/TrustBadge'
import type { FingerprintScores } from '@/lib/fingerprint'
import type { TrustTier } from '@/types/api'

export const Route = createFileRoute('/dev')({
  component: DevPage,
})

const sampleScores: Record<string, FingerprintScores> = {
  high: { clarity: 0.92, completeness: 0.88, correctness: 0.95, safety: 0.9, behavioral: 0.85 },
  low: { clarity: 0.3, completeness: 0.25, correctness: 0.4, safety: 0.35, behavioral: 0.2 },
  mixed: { clarity: 0.9, completeness: 0.4, correctness: 0.85, safety: 0.3, behavioral: 0.6 },
  zeroBehavioral: {
    clarity: 0.8,
    completeness: 0.75,
    correctness: 0.82,
    safety: 0.78,
    behavioral: 0,
  },
}

const tiers: TrustTier[] = ['experimental', 'community', 'verified']
const badgeSizes = ['sm', 'md', 'lg'] as const

function DevPage() {
  return (
    <div className="space-y-12 max-w-3xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dev Playground</h1>
        <p className="text-muted-foreground mt-1">Component test page for development.</p>
      </div>

      {/* Fingerprint: all sizes */}
      <section className="space-y-6">
        <h2 className="text-xl font-semibold">Fingerprint - Sizes</h2>
        <div className="flex items-end gap-8">
          <div className="space-y-1 text-center">
            <Fingerprint scores={sampleScores.high} size="thumbnail" />
            <span className="text-xs text-muted-foreground">thumbnail</span>
          </div>
          <div className="space-y-1 text-center">
            <Fingerprint scores={sampleScores.high} size="card" />
            <span className="text-xs text-muted-foreground">card</span>
          </div>
          <div className="space-y-1 text-center">
            <Fingerprint scores={sampleScores.high} size="hero" confidence={0.9} />
            <span className="text-xs text-muted-foreground">hero (hover for labels)</span>
          </div>
        </div>
      </section>

      {/* Fingerprint: score variations */}
      <section className="space-y-6">
        <h2 className="text-xl font-semibold">Fingerprint - Variations</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {Object.entries(sampleScores).map(([label, scores]) => (
            <div key={label} className="flex flex-col items-center gap-2">
              <Fingerprint scores={scores} size="card" confidence={0.8} />
              <span className="text-xs text-muted-foreground capitalize">{label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* TrustBadge */}
      <section className="space-y-6">
        <h2 className="text-xl font-semibold">TrustBadge</h2>
        <div className="space-y-4">
          {badgeSizes.map((size) => (
            <div key={size} className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground w-8">{size}</span>
              {tiers.map((tier) => (
                <TrustBadge key={tier} tier={tier} size={size} />
              ))}
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
