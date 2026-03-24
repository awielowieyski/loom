import { useQuery } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { searchSkills } from '@/api/skills'
import { searchCapabilities } from '@/api/capabilities'
import type { SkillSummary, CapabilitySummary } from '@/types/api'

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}

export function useSearch(query: string, type: 'skill' | 'capability' | 'all' = 'all') {
  const debouncedQuery = useDebounce(query, 300)

  const skills = useQuery({
    queryKey: ['search', 'skills', debouncedQuery],
    queryFn: () => searchSkills(debouncedQuery),
    enabled: !!debouncedQuery && (type === 'all' || type === 'skill'),
  })

  const capabilities = useQuery({
    queryKey: ['search', 'capabilities', debouncedQuery],
    queryFn: () => searchCapabilities(debouncedQuery),
    enabled: !!debouncedQuery && (type === 'all' || type === 'capability'),
  })

  return {
    skills: (skills.data ?? []) as SkillSummary[],
    capabilities: (capabilities.data ?? []) as CapabilitySummary[],
    isLoading: skills.isLoading || capabilities.isLoading,
    query: debouncedQuery,
  }
}
