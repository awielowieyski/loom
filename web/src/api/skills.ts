import { apiGet } from './client'
import type {
  Skill,
  SkillSummary,
  UsageStats,
  BehavioralEvalResult,

  SkillTimelineResponse,
} from '@/types/api'

export function listSkills(params?: {
  category?: string
  trust_tier?: string
  limit?: number
  offset?: number
}) {
  return apiGet<SkillSummary[]>('/skills', params)
}

export function getSkill(slug: string) {
  return apiGet<Skill>(`/skills/${slug}`)
}

export function searchSkills(query: string, type?: string) {
  return apiGet<SkillSummary[]>('/skills/search', { q: query, type })
}

export function getSkillUsage(slug: string) {
  return apiGet<UsageStats>(`/skills/${slug}/usage`)
}

export function getSkillBehavioral(slug: string) {
  return apiGet<BehavioralEvalResult>(`/skills/${slug}/behavioral`)
}

export function getSkillTimeline(slug: string) {
  return apiGet<SkillTimelineResponse>(`/skills/${slug}/timeline`)
}
