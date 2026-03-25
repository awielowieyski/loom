import { GitBranch } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useSkill } from '@/hooks/useSkill'
import { formatRelativeTime } from '@/lib/format'
import { Badge } from '@/components/ui/badge'

interface VersionTimelineProps {
  slug: string
  className?: string
}

export function VersionTimeline({ slug, className }: VersionTimelineProps) {
  const { data: skill, isLoading } = useSkill(slug)

  if (isLoading) {
    return (
      <div className={cn('space-y-2', className)}>
        {[1, 2].map((i) => (
          <div key={i} className="h-8 animate-pulse rounded bg-muted" />
        ))}
      </div>
    )
  }

  if (!skill) return null

  // Currently, the skill model only exposes the current version.
  // In the future this would come from a dedicated versions endpoint.
  const versions = [
    {
      version: skill.version,
      created_at: skill.updated_at ?? skill.created_at,
      isCurrent: true,
    },
  ]

  return (
    <div className={cn('space-y-2', className)}>
      {versions.map((v) => (
        <div
          key={v.version}
          className="flex items-center gap-3 rounded-lg border px-3 py-2"
        >
          <GitBranch className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className="font-mono text-sm">v{v.version}</span>
          {v.isCurrent && (
            <Badge variant="secondary" className="text-[10px]">
              current
            </Badge>
          )}
          <span className="ml-auto text-xs text-muted-foreground">
            {formatRelativeTime(v.created_at)}
          </span>
        </div>
      ))}
    </div>
  )
}
