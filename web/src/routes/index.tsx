/* eslint-disable react-refresh/only-export-components */
import { useState, useCallback } from 'react'
import { createFileRoute, Link } from '@tanstack/react-router'
import { useResolve } from '@/hooks/useResolve'
import { HeroSearchBar } from '@/components/resolve/HeroSearchBar'
import { PrimaryResult } from '@/components/resolve/PrimaryResult'
import { AlternativeList } from '@/components/resolve/AlternativeList'
import { ContextToggles } from '@/components/resolve/ContextToggles'
import { ResolutionHistory, notifyHistoryChange } from '@/components/resolve/ResolutionHistory'
import { addToHistory } from '@/lib/storage'
import { unifiedSearch, type SearchResult } from '@/api/search'
import type { ResolutionContext, ResolvedResult, Alternative } from '@/types/api'

export const Route = createFileRoute('/')({
  component: ResolveView,
})

function LoadingSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="rounded-xl border bg-card p-6 space-y-3">
        <div className="flex items-start gap-4">
          <div className="h-16 w-16 rounded-full bg-muted" />
          <div className="flex-1 space-y-2">
            <div className="h-5 w-1/3 rounded bg-muted" />
            <div className="h-4 w-2/3 rounded bg-muted" />
          </div>
        </div>
        <div className="h-3 w-1/4 rounded bg-muted" />
      </div>
      <div className="space-y-2">
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="rounded-xl border bg-card p-4">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-full bg-muted" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3.5 w-1/4 rounded bg-muted" />
                <div className="h-3 w-1/2 rounded bg-muted" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="text-center py-16 space-y-3">
      <h2 className="text-xl font-semibold text-foreground/80">Find the right skill</h2>
      <p className="text-muted-foreground max-w-md mx-auto">
        Describe a task in natural language and Loom will resolve the best-matching skill or
        capability from the registry, ranked by trust, quality, and fit.
      </p>
      <p className="text-xs text-muted-foreground/60">
        Type to search · Press Enter to resolve with AI
      </p>
    </div>
  )
}

function isCapability(r: SearchResult): boolean {
  return 'steps' in r || !('content' in r && 'eval_spec' in r)
}

function QuickResults({ results, onSelect }: { results: SearchResult[]; onSelect: (name: string) => void }) {
  if (results.length === 0) return null

  return (
    <div className="rounded-xl border bg-card p-3 space-y-1">
      <p className="text-xs text-muted-foreground px-2 pb-1">Quick matches — press Enter to resolve with AI</p>
      {results.slice(0, 8).map((r) => {
        const isCap = isCapability(r)
        const route = isCap ? '/capabilities/$slug' as const : '/skills/$slug' as const
        return (
          <Link
            key={r.slug}
            to={route}
            params={{ slug: r.slug }}
            className="flex items-center gap-3 px-2 py-1.5 rounded-md hover:bg-accent/50 transition-colors"
          >
            <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${isCap ? 'bg-chart-2/20 text-chart-2' : 'bg-primary/10 text-primary'}`}>
              {isCap ? 'cap' : 'skill'}
            </span>
            <span className="text-sm font-medium truncate">{r.name}</span>
            <span className="text-xs text-muted-foreground truncate ml-auto">{r.description?.slice(0, 60)}</span>
          </Link>
        )
      })}
    </div>
  )
}

function ResolveView() {
  const [context, setContext] = useState<ResolutionContext>({})
  const [result, setResult] = useState<ResolvedResult | null>(null)
  const [quickResults, setQuickResults] = useState<SearchResult[] | null>(null)

  const { mutate, isPending } = useResolve()

  // Lightweight DB search on keystroke (no auth, fast)
  const handleSearch = useCallback(async (query: string) => {
    try {
      const results = await unifiedSearch(query)
      setQuickResults(results)
    } catch {
      // Silently fail — typeahead is best-effort
    }
  }, [])

  // Full LLM resolve on Enter
  const handleResolve = useCallback(
    (query: string) => {
      setQuickResults(null) // clear typeahead
      mutate(
        { task_description: query, context },
        {
          onSuccess: (data) => {
            setResult(data)
            addToHistory(query)
            notifyHistoryChange()
          },
        },
      )
    },
    [context, mutate],
  )

  const handleAlternativeSelect = useCallback(
    (alt: Alternative) => {
      setQuickResults(null)
      mutate(
        { task_description: alt.skill.name, context },
        {
          onSuccess: (data) => {
            setResult(data)
            addToHistory(alt.skill.name)
            notifyHistoryChange()
          },
        },
      )
    },
    [context, mutate],
  )

  const alternatives = result?.type === 'skill'
    ? result.skill?.alternatives ?? []
    : result?.capability?.alternatives ?? []

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <HeroSearchBar
        onSearch={handleSearch}
        onResolve={handleResolve}
        isLoading={isPending}
      />

      <ContextToggles context={context} onContextChange={setContext} />

      {quickResults && !isPending && !result && (
        <QuickResults results={quickResults} onSelect={handleResolve} />
      )}

      {isPending && !result && <LoadingSkeleton />}

      {result && !isPending && (
        <div className="space-y-4">
          <PrimaryResult result={result} />
          <AlternativeList alternatives={alternatives} onSelect={handleAlternativeSelect} />
        </div>
      )}

      {!result && !isPending && !quickResults && <EmptyState />}

      <ResolutionHistory onSelect={handleResolve} />
    </div>
  )
}
