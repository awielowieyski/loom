import { cn } from '@/lib/utils'
import { TrustBadge } from '@/components/shared/TrustBadge'
import { Badge } from '@/components/ui/badge'
import type { SkillSummary } from '@/types/api'

interface AlternativesComparisonProps {
  primary: SkillSummary
  alternative: SkillSummary
  className?: string
}

export function AlternativesComparison({
  primary,
  alternative,
  className,
}: AlternativesComparisonProps) {
  return (
    <div className={cn('grid grid-cols-2 gap-4', className)}>
      <ComparisonColumn skill={primary} label="Selected" highlight />
      <ComparisonColumn skill={alternative} label="Alternative" />
    </div>
  )
}

function ComparisonColumn({
  skill,
  label,
  highlight,
}: {
  skill: SkillSummary
  label: string
  highlight?: boolean
}) {
  return (
    <div
      className={cn(
        'rounded-lg border p-4 space-y-3',
        highlight && 'ring-2 ring-primary/20',
      )}
    >
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <Badge variant={highlight ? 'default' : 'secondary'} className="text-[10px]">
            {label}
          </Badge>
        </div>
        <h3 className="font-medium">{skill.name}</h3>
        <p className="text-xs text-muted-foreground font-mono">{skill.slug}</p>
      </div>

      <p className="text-sm text-muted-foreground line-clamp-3">{skill.description}</p>

      <div className="flex flex-wrap items-center gap-2">
        <TrustBadge tier={skill.trust_tier} size="sm" />
        <Badge variant="secondary" className="text-[10px]">
          v{skill.version}
        </Badge>
        <Badge variant="secondary" className="text-[10px]">
          {skill.cost_profile}
        </Badge>
        <Badge variant="secondary" className="text-[10px]">
          {skill.estimated_duration}
        </Badge>
      </div>

      {skill.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {skill.tags.map((tag) => (
            <Badge key={tag} variant="outline" className="text-[10px]">
              {tag}
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}
