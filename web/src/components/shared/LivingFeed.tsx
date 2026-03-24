import { useState } from 'react'
import { Link } from '@tanstack/react-router'
import {
  Activity,
  ChevronRight,
  PanelRightClose,
  PanelRightOpen,
  Plus,
  ArrowUpCircle,
  ArrowDownCircle,
  Ban,
  CheckCircle2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { formatRelativeTime } from '@/lib/format'
import { useActivityFeed } from '@/hooks/useActivityFeed'
import type { ActivityEvent } from '@/types/api'

function eventIcon(type: ActivityEvent['type']) {
  switch (type) {
    case 'skill_created':
      return <Plus className="h-3.5 w-3.5 text-green-500" />
    case 'skill_updated':
      return <ArrowUpCircle className="h-3.5 w-3.5 text-blue-500" />
    case 'eval_completed':
      return <CheckCircle2 className="h-3.5 w-3.5 text-purple-500" />
    case 'resolution':
      return <ChevronRight className="h-3.5 w-3.5 text-foreground/60" />
    case 'usage_report':
      return <Activity className="h-3.5 w-3.5 text-foreground/60" />
    default:
      return <Activity className="h-3.5 w-3.5 text-foreground/60" />
  }
}

function eventLink(event: ActivityEvent): string | null {
  if (event.slug) return `/skills/${event.slug}`
  return null
}

function FeedItem({ event }: { event: ActivityEvent }) {
  const link = eventLink(event)
  const nameEl = link ? (
    <Link to={link} className="font-medium hover:underline truncate">
      {event.title}
    </Link>
  ) : (
    <span className="font-medium truncate">{event.title}</span>
  )

  return (
    <div className="flex items-start gap-2 py-1.5 text-xs">
      <span className="mt-0.5 shrink-0">{eventIcon(event.type)}</span>
      <div className="flex-1 min-w-0">
        {nameEl}
        {event.description && (
          <p className="text-muted-foreground line-clamp-1">{event.description}</p>
        )}
      </div>
      <span className="text-muted-foreground shrink-0 text-[10px]">
        {formatRelativeTime(event.timestamp)}
      </span>
    </div>
  )
}

interface LivingFeedProps {
  className?: string
}

export function LivingFeed({ className }: LivingFeedProps) {
  const [collapsed, setCollapsed] = useState(false)
  const { data, isLoading } = useActivityFeed({ limit: 20 })

  const events = data?.events ?? []

  return (
    <div className={cn('flex flex-col', className)}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Activity
        </h3>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setCollapsed((v) => !v)}
          className="h-6 w-6 p-0"
          aria-label={collapsed ? 'Expand feed' : 'Collapse feed'}
        >
          {collapsed ? (
            <PanelRightOpen className="h-3.5 w-3.5" />
          ) : (
            <PanelRightClose className="h-3.5 w-3.5" />
          )}
        </Button>
      </div>

      {!collapsed && (
        <div className="overflow-y-auto max-h-[calc(100vh-12rem)] divide-y divide-border/50">
          {isLoading && events.length === 0 && (
            <div className="space-y-3 py-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex gap-2 animate-pulse">
                  <div className="h-3.5 w-3.5 rounded-full bg-muted" />
                  <div className="flex-1 space-y-1">
                    <div className="h-3 w-3/4 rounded bg-muted" />
                    <div className="h-2.5 w-1/2 rounded bg-muted" />
                  </div>
                </div>
              ))}
            </div>
          )}
          {!isLoading && events.length === 0 && (
            <p className="text-xs text-muted-foreground py-4 text-center">No recent activity</p>
          )}
          {events.map((event) => (
            <FeedItem key={event.id} event={event} />
          ))}
        </div>
      )}
    </div>
  )
}
