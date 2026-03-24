import { apiGet } from './client'
import type { ActivityEvent } from '@/types/api'

export function getActivityFeed(params?: { limit?: number; since?: string }) {
  return apiGet<ActivityEvent[]>('/activity/feed', params)
}
