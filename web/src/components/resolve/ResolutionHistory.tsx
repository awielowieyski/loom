import { useState, useSyncExternalStore, useCallback } from 'react'
import { ChevronDown, Clock, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { getHistory, clearHistory, type HistoryEntry } from '@/lib/storage'

interface ResolutionHistoryProps {
  onSelect: (query: string) => void
  className?: string
}

function formatTimestamp(ts: number): string {
  const diffMs = Date.now() - ts
  if (diffMs < 0) return 'just now'
  const seconds = Math.floor(diffMs / 1000)
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

// Simple external store subscription for localStorage changes within same tab
let historyVersion = 0
const listeners = new Set<() => void>()

export function notifyHistoryChange() {
  historyVersion++
  listeners.forEach((l) => l())
}

function useHistory(): HistoryEntry[] {
  const subscribe = useCallback((cb: () => void) => {
    listeners.add(cb)
    return () => listeners.delete(cb)
  }, [])
  const getSnapshot = useCallback(() => {
    // Trigger re-read on version change
    void historyVersion
    return getHistory()
  }, [])
  return useSyncExternalStore(subscribe, getSnapshot, () => [])
}

export function ResolutionHistory({ onSelect, className }: ResolutionHistoryProps) {
  const [open, setOpen] = useState(false)
  const history = useHistory()

  const handleClear = () => {
    clearHistory()
    notifyHistoryChange()
  }

  return (
    <div className={cn('rounded-lg border bg-card', className)}>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setOpen((v) => !v)}
        className="w-full justify-between px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground"
      >
        <span className="flex items-center gap-1.5">
          <Clock className="h-3.5 w-3.5" />
          Recent Queries
        </span>
        <ChevronDown
          className={cn('h-4 w-4 transition-transform', open && 'rotate-180')}
        />
      </Button>

      {open && (
        <div className="px-3 pb-3 space-y-1">
          {history.length === 0 ? (
            <p className="text-xs text-muted-foreground py-2">No recent queries</p>
          ) : (
            <>
              {history.map((entry) => (
                <button
                  key={entry.timestamp}
                  type="button"
                  onClick={() => onSelect(entry.query)}
                  className="w-full flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted transition-colors text-left"
                >
                  <span className="truncate">{entry.query}</span>
                  <span className="text-xs text-muted-foreground shrink-0">
                    {formatTimestamp(entry.timestamp)}
                  </span>
                </button>
              ))}
              <div className="pt-1 border-t">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleClear}
                  className="text-xs text-muted-foreground h-7 px-2"
                >
                  <Trash2 className="h-3 w-3 mr-1" />
                  Clear all
                </Button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
