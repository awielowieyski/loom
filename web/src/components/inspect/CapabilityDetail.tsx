import { Calendar, Tag, Package } from 'lucide-react'
import { Link } from '@tanstack/react-router'
import { cn } from '@/lib/utils'
import { useCapability } from '@/hooks/useCapability'
import { formatRelativeTime } from '@/lib/format'
import { TrustBadge } from '@/components/shared/TrustBadge'
import { FlowDiagram } from '@/components/inspect/FlowDiagram'
import { Badge } from '@/components/ui/badge'
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

  const deps = capability.dependencies
  const hasDeps =
    deps &&
    (deps.mcp_servers.length > 0 || deps.apis.length > 0 || deps.trust_requirements.network_access)
  const authorshipLabel =
    capability.authorship_status === 'loom_derived'
      ? 'Derived by Loom'
      : capability.authorship_status === 'loom_amended'
        ? 'Normalized by Loom'
        : 'Authored by source submitter'

  return (
    <div className={cn('space-y-8', className)}>
      {/* Header */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold tracking-tight">{capability.name}</h1>
          <TrustBadge tier={capability.trust_tier} size="lg" />
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          <span className="font-mono">{capability.slug}</span>
          <span>v{capability.version}</span>
          <span>{capability.lifecycle_state}</span>
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

      <section className="rounded-lg border bg-muted/20 p-4 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">{authorshipLabel}</Badge>
          {capability.canonicalization_level && (
            <Badge variant="secondary">{capability.canonicalization_level}</Badge>
          )}
          {capability.published_version_id && (
            <Badge variant="secondary">published revision</Badge>
          )}
        </div>
        {capability.provenance_summary && Object.keys(capability.provenance_summary).length > 0 && (
          <pre className="rounded-md bg-background p-3 text-[11px] whitespace-pre-wrap overflow-x-auto">
            {JSON.stringify(capability.provenance_summary, null, 2)}
          </pre>
        )}
        <div className="grid gap-2 text-xs text-muted-foreground md:grid-cols-2">
          {capability.current_version_id && <div>Current revision: <span className="font-mono">{capability.current_version_id}</span></div>}
          {capability.published_version_id && <div>Published revision: <span className="font-mono">{capability.published_version_id}</span></div>}
          {capability.capability_root_hash && <div>Capability root hash: <span className="font-mono">{capability.capability_root_hash}</span></div>}
          {capability.execution_bundle_hash && <div>Bundle hash: <span className="font-mono">{capability.execution_bundle_hash}</span></div>}
        </div>
      </section>

      {/* Flow Diagram */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Execution Pipeline</h2>
        <FlowDiagram capability={capability} />
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Steps</h2>
        <div className="space-y-2">
          {capability.steps.map((step, i) => {
            const isLocalSkillRef = step.skill_ref.startsWith('loom://')
            const slug = step.skill_ref.replace(/^loom:\/\//, '')
            const itemClassName = cn(
              'flex items-center gap-3 rounded-lg border px-3 py-2 transition-colors',
              !step.required && 'border-dashed',
              isLocalSkillRef && 'hover:bg-accent/50',
            )

            const content = (
              <>
                <span className="text-sm font-medium font-mono">{step.skill_ref}</span>
                <span className="text-xs text-muted-foreground">{step.role}</span>
                {!step.required && (
                  <Badge variant="secondary" className="text-[10px]">
                    optional
                  </Badge>
                )}
              </>
            )

            return isLocalSkillRef ? (
              <Link
                key={i}
                to="/skills/$slug"
                params={{ slug }}
                className={itemClassName}
              >
                {content}
              </Link>
            ) : (
              <div key={i} className={itemClassName}>
                {content}
              </div>
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
