import { apiGet } from './client'
import type { Capability, CapabilitySummary } from '@/types/api'

export function listCapabilities(params?: {
  category?: string
  trust_tier?: string
  limit?: number
  offset?: number
}) {
  return apiGet<CapabilitySummary[]>('/capabilities', params)
}

export function getCapability(slug: string) {
  return apiGet<Capability>(`/capabilities/${slug}`)
}

export function searchCapabilities(query: string) {
  return apiGet<CapabilitySummary[]>('/capabilities/search', { query })
}
