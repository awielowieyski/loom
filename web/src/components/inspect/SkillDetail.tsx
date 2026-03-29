import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  ChevronDown,
  ChevronRight,
  Calendar,
  Tag,
  Package,
  ExternalLink,
  CreditCard,
  KeyRound,
  Globe,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useSkill } from '@/hooks/useSkill'
import { useRequestRerun } from '@/hooks/useStats'
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
  const [runtimeExpanded, setRuntimeExpanded] = useState(false)
  const [auditExpanded, setAuditExpanded] = useState(false)
  const [rerunMessage, setRerunMessage] = useState<string | null>(null)
  const { mutate: requestRerun, isPending: isRerunPending } = useRequestRerun()

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
  const hasExternalServices = skill.external_services.length > 0
  const hasPricing = skill.pricing.length > 0
  const hasSetupRequirements = skill.setup_requirements.length > 0
  const primaryService = skill.external_services[0]
  const primaryPricing = skill.pricing[0]
  const requiredSetupCount = skill.setup_requirements.filter((item) => item.required).length

  const authorshipLabel =
    skill.authorship_status === 'loom_derived'
      ? 'Derived by Loom'
      : skill.authorship_status === 'loom_amended'
        ? 'Normalized by Loom'
        : 'Authored by source submitter'

  return (
    <div className={cn('space-y-8', className)}>
      {/* Header */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold tracking-tight">{skill.name}</h1>
          <TrustBadge tier={skill.trust_tier} size="lg" />
          <Badge variant="secondary">{authorshipLabel}</Badge>
          {skill.requires_paid_service && <Badge variant="secondary">paid external service</Badge>}
          {skill.requires_network && <Badge variant="secondary">network access</Badge>}
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          <span className="font-mono">{skill.slug}</span>
          <span>v{skill.version}</span>
          <span>{skill.lifecycle_state}</span>
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

      <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px] lg:items-start">
        <div className="space-y-4">
          <p className="text-base leading-relaxed text-muted-foreground">{skill.description}</p>

          <div className="rounded-lg border bg-muted/20">
            <button
              type="button"
              onClick={() => setAuditExpanded(!auditExpanded)}
              className="flex w-full flex-wrap items-center justify-between gap-3 px-4 py-3 text-left hover:bg-muted/30 transition-colors"
            >
              <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
                {auditExpanded ? (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                )}
                <span className="font-semibold">Registry Audit</span>
                {skill.canonicalization_level && (
                  <Badge variant="secondary">{skill.canonicalization_level}</Badge>
                )}
                {skill.published_version_id && (
                  <Badge variant="secondary">published revision</Badge>
                )}
              </div>
              <span className="text-xs text-muted-foreground">
                {auditExpanded ? 'Hide details' : 'Show details'}
              </span>
            </button>

            {auditExpanded && (
              <div className="border-t px-4 py-4 space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() =>
                      requestRerun(
                        {
                          skill_id: skill.id,
                          request_mode: 'canonicalize',
                          note: 'Requested from skill detail page',
                        },
                        {
                          onSuccess: (response) =>
                            setRerunMessage(response.message ?? 'Canonicalization rerun requested.'),
                        },
                      )
                    }
                    disabled={isRerunPending}
                    className="rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-background disabled:opacity-50"
                  >
                    Re-run Canonicalization
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      requestRerun(
                        {
                          skill_id: skill.id,
                          request_mode: 'evaluate',
                          note: 'Requested from skill detail page',
                        },
                        {
                          onSuccess: (response) =>
                            setRerunMessage(response.message ?? 'Evaluation rerun requested.'),
                        },
                      )
                    }
                    disabled={isRerunPending}
                    className="rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-background disabled:opacity-50"
                  >
                    Queue Eval
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      requestRerun(
                        {
                          skill_id: skill.id,
                          request_mode: 'full_pipeline',
                          note: 'Requested from skill detail page',
                        },
                        {
                          onSuccess: (response) =>
                            setRerunMessage(response.message ?? 'Full pipeline rerun requested.'),
                        },
                      )
                    }
                    disabled={isRerunPending}
                    className="rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-background disabled:opacity-50"
                  >
                    Queue Full Pipeline
                  </button>
                </div>
                {rerunMessage && <p className="text-xs text-muted-foreground">{rerunMessage}</p>}
                {skill.provenance_summary && Object.keys(skill.provenance_summary).length > 0 && (
                  <pre className="rounded-md bg-background p-3 text-[11px] whitespace-pre-wrap overflow-x-auto">
                    {JSON.stringify(skill.provenance_summary, null, 2)}
                  </pre>
                )}
                <div className="grid gap-2 text-xs text-muted-foreground md:grid-cols-2">
                  {skill.current_version_id && (
                    <div>
                      Current revision: <span className="font-mono">{skill.current_version_id}</span>
                    </div>
                  )}
                  {skill.published_version_id && (
                    <div>
                      Published revision:{' '}
                      <span className="font-mono">{skill.published_version_id}</span>
                    </div>
                  )}
                  {skill.canonical_hash && (
                    <div>
                      Canonical hash: <span className="font-mono">{skill.canonical_hash}</span>
                    </div>
                  )}
                  {skill.execution_bundle_hash && (
                    <div>
                      Bundle hash: <span className="font-mono">{skill.execution_bundle_hash}</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="flex justify-center lg:justify-end">
          <div className="rounded-2xl border bg-muted/10 p-4">
            <Fingerprint scores={fingerprintScores} size="hero" />
          </div>
        </div>
      </section>

      {(hasExternalServices || hasPricing || hasSetupRequirements) && (
        <section className="rounded-lg border bg-muted/20">
          <button
            type="button"
            onClick={() => setRuntimeExpanded(!runtimeExpanded)}
            className="flex w-full flex-wrap items-center justify-between gap-3 px-4 py-3 text-left hover:bg-muted/30 transition-colors"
          >
            <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
              {runtimeExpanded ? (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              )}
              <span className="font-semibold">Runtime Requirements</span>
              {primaryService && (
                <Badge variant="secondary" className="gap-1">
                  <Globe className="h-3 w-3" />
                  {primaryService.service.display_name}
                </Badge>
              )}
              {primaryPricing && (
                <Badge variant="secondary" className="gap-1">
                  <CreditCard className="h-3 w-3" />
                  {primaryPricing.unit_cost_usd !== null
                    ? `$${primaryPricing.unit_cost_usd.toFixed(4)}${primaryPricing.unit_name ? `/${primaryPricing.unit_name}` : ''}`
                    : primaryPricing.pricing_model.replaceAll('_', ' ')}
                </Badge>
              )}
              {requiredSetupCount > 0 && (
                <Badge variant="secondary" className="gap-1">
                  <KeyRound className="h-3 w-3" />
                  {requiredSetupCount} setup {requiredSetupCount === 1 ? 'step' : 'steps'}
                </Badge>
              )}
              {skill.requires_paid_service && <Badge variant="secondary">paid</Badge>}
            </div>
            <span className="text-xs text-muted-foreground">
              {runtimeExpanded ? 'Hide details' : 'Show details'}
            </span>
          </button>

          {runtimeExpanded && (
            <div className="border-t px-4 py-4">
              <div className="grid gap-4 lg:grid-cols-3">
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <Globe className="h-4 w-4 text-muted-foreground" />
                    <h2 className="text-base font-semibold">External Services</h2>
                  </div>
                  {hasExternalServices ? (
                    <div className="space-y-3">
                      {skill.external_services.map((dependency) => (
                        <div key={dependency.id} className="rounded-md border bg-background p-3 space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-medium">{dependency.service.display_name}</span>
                            <Badge variant="secondary" className="text-[10px]">
                              {dependency.service.service_type}
                            </Badge>
                            {dependency.required && (
                              <Badge variant="secondary" className="text-[10px]">
                                required
                              </Badge>
                            )}
                          </div>
                          <div className="text-xs text-muted-foreground space-y-1">
                            <p>{dependency.service.service_key}</p>
                            <p>Role: {dependency.dependency_role.replaceAll('_', ' ')}</p>
                            {dependency.operations.length > 0 && (
                              <p>Operations: {dependency.operations.join(', ')}</p>
                            )}
                          </div>
                          <div className="flex flex-wrap gap-2 text-xs">
                            {dependency.service.default_auth_methods.map((method) => (
                              <Badge key={method} variant="outline" className="text-[10px]">
                                {method}
                              </Badge>
                            ))}
                            {dependency.service.default_env_vars.map((envVar) => (
                              <Badge key={envVar} variant="outline" className="font-mono text-[10px]">
                                {envVar}
                              </Badge>
                            ))}
                          </div>
                          <div className="flex flex-wrap gap-3 text-xs">
                            {dependency.service.docs_url && (
                              <a
                                href={dependency.service.docs_url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 text-primary hover:underline"
                              >
                                Docs
                                <ExternalLink className="h-3 w-3" />
                              </a>
                            )}
                            {dependency.service.pricing_url && (
                              <a
                                href={dependency.service.pricing_url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 text-primary hover:underline"
                              >
                                Pricing
                                <ExternalLink className="h-3 w-3" />
                              </a>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No external service metadata recorded yet.</p>
                  )}
                </div>

                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <CreditCard className="h-4 w-4 text-muted-foreground" />
                    <h2 className="text-base font-semibold">Pricing</h2>
                  </div>
                  {hasPricing ? (
                    <div className="space-y-3">
                      {skill.pricing.map((fact) => (
                        <div key={fact.id} className="rounded-md border bg-background p-3 space-y-1.5">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-medium">{fact.operation_name ?? fact.fact_type}</span>
                            <Badge variant="secondary" className="text-[10px]">
                              {fact.pricing_model.replaceAll('_', ' ')}
                            </Badge>
                          </div>
                          {fact.unit_cost_usd !== null && (
                            <p className="text-sm">
                              ${fact.unit_cost_usd.toFixed(4)}
                              {fact.unit_name ? ` / ${fact.unit_name}` : ''}
                            </p>
                          )}
                          {fact.price_text_raw && (
                            <p className="text-sm text-muted-foreground">{fact.price_text_raw}</p>
                          )}
                          <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                            <span>Source: {fact.source_kind}</span>
                            {fact.observed_at && <span>Observed {formatRelativeTime(fact.observed_at)}</span>}
                            {typeof fact.confidence === 'number' && (
                              <span>Confidence {Math.round(fact.confidence * 100)}%</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No pricing evidence recorded yet.</p>
                  )}
                </div>

                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <KeyRound className="h-4 w-4 text-muted-foreground" />
                    <h2 className="text-base font-semibold">Setup Requirements</h2>
                  </div>
                  {hasSetupRequirements ? (
                    <div className="space-y-3">
                      {skill.setup_requirements.map((requirement) => (
                        <div key={requirement.id} className="rounded-md border bg-background p-3 space-y-1.5">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-medium">
                              {requirement.requirement_type.replaceAll('_', ' ')}
                            </span>
                            {requirement.required && (
                              <Badge variant="secondary" className="text-[10px]">
                                required
                              </Badge>
                            )}
                          </div>
                          {requirement.key && (
                            <p className="font-mono text-xs text-muted-foreground">{requirement.key}</p>
                          )}
                          {requirement.instructions && (
                            <p className="text-sm text-muted-foreground">{requirement.instructions}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No setup requirements recorded yet.</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </section>
      )}

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
            {deps.trust_requirements.network_access && (
              <p className="text-muted-foreground">Requires network access</p>
            )}
          </div>
        </section>
      )}
    </div>
  )
}
