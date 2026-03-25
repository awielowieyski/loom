import { Calendar, Tag, Package } from 'lucide-react'
import { Link } from '@tanstack/react-router'
import { cn } from '@/lib/utils'
import { useCapability } from '@/hooks/useCapability'
import { formatRelativeTime } from '@/lib/format'
import { TrustBadge } from '@/components/shared/TrustBadge'
import { FlowDiagram } from '@/components/inspect/FlowDiagram'
import { Badge } from '@/components/ui/badge'
import type { TrustTier } from '@/types/api'

const TRUST_RANK: Record<TrustTier, number> = {
  experimental: 0,
  community: 1,
  verified: 2,
}

const RANK_TO_TIER: TrustTier[] = ['experimental', 'community', 'verified']

interface CapabilityDetailProps {
  slug: string
  className?: string
}

export function CapabilityDetail({ slug, className }: CapabilityDetailProps) {
  const { data: capability, isLoading, error } = useCapability(slug)

  if (isLoading) {
    return (
      <div className={cn('space-y-6', className)}>
        <div className="h-8 w-64 animate-pulse rounded bg-muted" />
        <div className="h-4 w-96 animate-pulse rounded bg-muted" />
        <div className="h-[400px] animate-pulse rounded bg-muted" />
      </div>
    )
  }

  if (error || !capability) {
    return (
      <div className={cn('py-12 text-center', className)}>
        <p className="text-lg font-medium text-muted-foreground">
          {error ? 'Failed to load capability' : 'Capability not found'}
        </p>
      </div>
    )
  }

  // Aggregate trust tier: minimum across steps
  const stepTiers = capability.steps.map(() => capability.trust_tier)
  const minRank = Math.min(...stepTiers.map((t) => TRUST_RANK[t]))
  const aggregateTier = RANK_TO_TIER[minRank] ?? 'experimental'

  const deps = capability.dependencies
  const hasDeps =
    deps &&
    (deps.mcp_servers.length > 0 || deps.apis.length > 0 || deps.trust_requirements.network_access)

  return (
    <div className={cn('space-y-8', className)}>
      {/* Header */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold tracking-tight">{capability.name}</h1>
          <TrustBadge tier={aggregateTier} size="lg" />
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          <span className="font-mono">{capability.slug}</span>
          <span>v{capability.version}</span>
          {capability.created_at && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              Created {formatRelativeTime(capability.created_at)}
            </span>
          )}
          {capability.updated_at && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              Updated {formatRelativeTime(capability.updated_at)}
            </span>
          )}
        </div>
        {capability.tags.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5">
            <Tag className="h-3.5 w-3.5 text-muted-foreground" />
            {capability.tags.map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        )}
      </div>

      {/* Description */}
      <p className="text-base leading-relaxed text-muted-foreground">{capability.description}</p>

      {/* Flow Diagram */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Execution Pipeline</h2>
        <FlowDiagram capability={capability} />
      </section>

      {/* Per-step trust breakdown */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Steps</h2>
        <div className="space-y-2">
          {capability.steps.map((step, i) => {
            // Extract slug from loom://slug format
            const slug = step.skill_ref.replace(/^loom:\/\//, '')
            return (
              <Link
                key={i}
                to="/skills/$slug"
                params={{ slug }}
                className={cn(
                  'flex items-center gap-3 rounded-lg border px-3 py-2 hover:bg-accent/50 transition-colors',
                  !step.required && 'border-dashed',
                )}
              >
                <span className="text-sm font-medium font-mono">{step.skill_ref}</span>
                <span className="text-xs text-muted-foreground">{step.role}</span>
                <TrustBadge tier={capability.trust_tier} size="sm" />
                {!step.required && (
                  <Badge variant="secondary" className="text-[10px]">
                    optional
                  </Badge>
                )}
              </Link>
            )
          })}
        </div>
      </section>

      {/* Dependencies */}
      {hasDeps && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold">Dependencies</h2>
          <div className="space-y-2 text-sm">
            {deps.mcp_servers.length > 0 && (
              <div>
                <h3 className="font-medium text-muted-foreground">Prerequisites</h3>
                <ul className="mt-1 space-y-1">
                  {deps.mcp_servers.map((s) => (
                    <li key={s.uri} className="flex items-center gap-2">
                      <Package className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="font-mono text-xs">{s.uri}</span>
                      {s.required && (
                        <Badge variant="secondary" className="text-[10px]">
                          required
                        </Badge>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {deps.apis.length > 0 && (
              <div>
                <h3 className="font-medium text-muted-foreground">APIs</h3>
                <ul className="mt-1 space-y-1">
                  {deps.apis.map((a) => (
                    <li key={a.name} className="flex items-center gap-2">
                      <Package className="h-3.5 w-3.5 text-muted-foreground" />
                      <span>{a.name}</span>
                      <span className="text-xs text-muted-foreground">({a.auth_type})</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  )
}
