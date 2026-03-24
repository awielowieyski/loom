import { FlaskConical, Users, ShieldCheck, AlertTriangle, Archive, Activity } from 'lucide-react'
import { useStatsOverview } from '@/hooks/useStats'
import { StatCard } from './StatCard'
import { ProgressRing } from './ProgressRing'

export function HealthDashboard() {
  const { data, isLoading, error } = useStatsOverview()

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="h-24 animate-pulse rounded-xl bg-muted"
          />
        ))}
      </div>
    )
  }

  if (error || !data) {
    return (
      <p className="text-sm text-muted-foreground">
        Failed to load registry health data.
      </p>
    )
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          title="Experimental"
          value={data.skill_counts.experimental}
          icon={<FlaskConical className="h-5 w-5" />}
        />
        <StatCard
          title="Community"
          value={data.skill_counts.community}
          icon={<Users className="h-5 w-5" />}
        />
        <StatCard
          title="Verified"
          value={data.skill_counts.verified}
          icon={<ShieldCheck className="h-5 w-5" />}
        />
        <StatCard
          title="Stale (no eval 30d)"
          value={data.stale_count}
          trend={data.stale_count > 0 ? 'down' : 'flat'}
          icon={<AlertTriangle className="h-5 w-5" />}
        />
        <StatCard
          title="Deprecated"
          value={data.deprecated_count}
          icon={<Archive className="h-5 w-5" />}
        />
        <StatCard
          title="Resolutions (7d)"
          value={data.total_resolutions_7d}
          icon={<Activity className="h-5 w-5" />}
        />
      </div>
      <div className="flex items-center gap-6">
        <div className="relative">
          <ProgressRing
            value={data.behavioral_eval_coverage}
            label="Behavioral Eval Coverage"
          />
        </div>
        <div className="space-y-1 text-sm text-muted-foreground">
          <p>
            <span className="font-medium text-foreground">{data.capability_count}</span>{' '}
            capabilities registered
          </p>
          <p>
            <span className="font-medium text-foreground">{data.total_resolutions_30d}</span>{' '}
            resolutions (30d)
          </p>
        </div>
      </div>
    </div>
  )
}
