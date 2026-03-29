import { ShieldCheck, Users, FlaskConical, ShieldOff } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { TrustTier } from '@/types/api'

const TIER_CONFIG: Record<
  TrustTier,
  {
    label: string
    icon: typeof ShieldCheck
    className: string
  }
> = {
  unvetted: {
    label: 'Unvetted',
    icon: ShieldOff,
    className: 'bg-slate-100 text-slate-800 dark:bg-slate-900/30 dark:text-slate-300',
  },
  experimental: {
    label: 'Experimental',
    icon: FlaskConical,
    className: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  },
  community: {
    label: 'Community',
    icon: Users,
    className: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  },
  verified: {
    label: 'Verified',
    icon: ShieldCheck,
    className: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  },
}

const SIZE_MAP = {
  sm: { badge: 'text-[10px] px-1.5 py-0', icon: 'h-3 w-3' },
  md: { badge: 'text-xs px-2 py-0.5', icon: 'h-3.5 w-3.5' },
  lg: { badge: 'text-sm px-2.5 py-1', icon: 'h-4 w-4' },
} as const

interface TrustBadgeProps {
  tier: TrustTier
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function TrustBadge({ tier, size = 'md', className }: TrustBadgeProps) {
  const config = TIER_CONFIG[tier]
  const sizeConfig = SIZE_MAP[size]
  const Icon = config.icon

  return (
    <Badge
      variant="secondary"
      className={cn(
        'inline-flex items-center gap-1 font-medium border-0',
        config.className,
        sizeConfig.badge,
        className,
      )}
    >
      <Icon className={sizeConfig.icon} />
      {config.label}
    </Badge>
  )
}
