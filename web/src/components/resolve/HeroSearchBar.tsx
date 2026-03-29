import { useState, useEffect, useCallback, useRef } from 'react'
import { Search, Loader2, X } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

interface HeroSearchBarProps {
  /** Fires on debounced keystroke — use for lightweight search/typeahead */
  onSearch?: (query: string) => void
  /** Fires on Enter — use for full LLM-powered resolve */
  onResolve: (query: string) => void
  /** Fires when the search is cleared — use to reset parent state */
  onClear?: () => void
  isLoading?: boolean
  className?: string
}

export function HeroSearchBar({ onSearch, onResolve, onClear, isLoading, className }: HeroSearchBarProps) {
  const [value, setValue] = useState('')
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const searchRef = useRef(onSearch)
  useEffect(() => {
    searchRef.current = onSearch
  }, [onSearch])

  // Debounced typeahead — lightweight search on every keystroke
  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current)

    if (value.trim() && searchRef.current) {
      timerRef.current = setTimeout(() => {
        searchRef.current?.(value.trim())
      }, 200)
    }

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [value])

  const handleSubmit = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    if (value.trim()) {
      onResolve(value.trim())
    }
  }, [value, onResolve])

  const clear = useCallback(() => {
    setValue('')
    onClear?.()
    inputRef.current?.focus()
  }, [onClear])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleSubmit()
    } else if (e.key === 'Escape') {
      e.preventDefault()
      clear()
    }
  }

  return (
    <div className={cn('relative w-full', className)}>
      <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground pointer-events-none" />
      <Input
        ref={inputRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="What do you need to do?"
        className="h-14 w-full pl-12 pr-12 text-lg rounded-xl border-2 border-border bg-background shadow-sm transition-shadow focus-visible:shadow-md focus-visible:border-ring focus-visible:ring-4 focus-visible:ring-ring/20 md:text-lg"
      />
      <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-1">
        {isLoading && <Loader2 className="h-5 w-5 text-muted-foreground animate-spin" />}
        {value && !isLoading && (
          <button
            type="button"
            onClick={clear}
            className="p-0.5 rounded-sm text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Clear search"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  )
}
