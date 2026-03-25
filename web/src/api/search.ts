import { apiGet } from './client'
import type { SkillSummary, CapabilitySummary } from '@/types/api'

export type SearchResult = SkillSummary | CapabilitySummary

export function unifiedSearch(query: string, type?: 'any' | 'skill' | 'capability') {
  return apiGet<SearchResult[]>('/search', { query, type })
}
