import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ChevronDown, ChevronRight, Calendar, Tag, Package } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useSkill } from '@/hooks/useSkill'
import { formatRelativeTime } from '@/lib/format'
import { TrustBadge } from '@/components/shared/TrustBadge'
import { Fingerprint } from '@/components/shared/Fingerprint'
import { EvalHistory } from '@/components/inspect/EvalHistory'
import { UsageStatsDisplay } from '@/components/inspect/UsageStatsDisplay'
import { Badge } from '@/components/ui/badge'
import type { FingerprintScores } from '@/lib/fingerprint'

interface SkillDetailProps {
  slug: string
  className?: string
}

export function SkillDetail({ slug, className }: SkillDetailProps) {
  const { data: skill, isLoading, error } = useSkill(slug)
  const [contentExpanded, setContentExpanded] = useState(false)

  if (isLoading) {
    return (
      <div className={cn('space-y-6', className)}>
        <div className="h-8 w-64 animate-pulse rounded bg-muted" />
        <div className="h-4 w-96 animate-pulse rounded bg-muted" />
        <div className="h-48 animate-pulse rounded bg-muted" />
      </div>
    )
  }

  if (error || !skill) {
    return (
      <div className={cn('py-12 text-center', className)}>
        <p className="text-lg font-medium text-muted-foreground">
          {error ? 'Failed to load skill' : 'Skill not found'}
        </p>
      </div>
    )
  }

  const fingerprintScores: FingerprintScores = {
    clarity: skill.composite_score ?? 0,
    completeness: skill.composite_score ?? 0,
    correctness: skill.composite_score ?? 0,
    safety: skill.composite_score ?? 0,
    behavioral: skill.behavioral_score ?? 0,
  }

  const deps = skill.dependencies
  const hasDeps =
    deps &&
    (deps.mcp_servers.length > 0 || deps.apis.length > 0 || deps.trust_requirements.network_access)

  return (
    <div className={cn('space-y-8', className)}>
      {/* Header */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold tracking-tight">{skill.name}</h1>
          <TrustBadge tier={skill.trust_tier} size="lg" />
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          <span className="font-mono">{skill.slug}</span>
          <span>v{skill.version}</span>
          {skill.created_at && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              Created {formatRelativeTime(skill.created_at)}
            </span>
          )}
          {skill.updated_at && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              Updated {formatRelativeTime(skill.updated_at)}
            </span>
          )}
        </div>
        {skill.tags.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5">
            <Tag className="h-3.5 w-3.5 text-muted-foreground" />
            {skill.tags.map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        )}
      </div>

      {/* Description */}
      <p className="text-base leading-relaxed text-muted-foreground">{skill.description}</p>

      {/* Hero Fingerprint */}
      <div className="flex justify-center">
        <Fingerprint scores={fingerprintScores} size="hero" />
      </div>

      {/* Content Preview (collapsible) */}
      {skill.content && (
        <div className="rounded-lg border">
          <button
            onClick={() => setContentExpanded(!contentExpanded)}
            className="flex w-full items-center gap-2 px-4 py-3 text-left text-sm font-medium hover:bg-muted/50 transition-colors"
          >
            {contentExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            Skill Content
          </button>
          {contentExpanded && (
            <div className="border-t px-4 py-3 prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{skill.content}</ReactMarkdown>
            </div>
          )}
        </div>
      )}

      {/* Eval History */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Evaluation</h2>
        <EvalHistory slug={slug} />
      </section>

      {/* Usage Stats */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Usage</h2>
        <UsageStatsDisplay slug={slug} />
      </section>

      {/* Dependencies */}
      {hasDeps && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold">Dependencies</h2>
          <div className="space-y-2 text-sm">
            {deps.mcp_servers.length > 0 && (
              <div>
                <h3 className="font-medium text-muted-foreground">MCP Servers</h3>
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
            {deps.trust_requirements.network_access && (
              <p className="text-muted-foreground">Requires network access</p>
            )}
          </div>
        </section>
      )}
    </div>
  )
}
