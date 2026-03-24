import { apiGet } from './client'
import type { ActivityFeedResponse } from '@/types/api'

export function getActivityFeed(params?: { cursor?: string; limit?: number }) {
  return apiGet<ActivityFeedResponse>('/activity', params)
}
