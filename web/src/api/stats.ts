import { apiGet, apiPost } from './client'
import type {
  StatsOverview,
  EvalTrendsResponse,
  UsageHeatmapResponse,
  GovernanceQueueItem,
  GovernanceReviewSubmission,
  EmbeddingMapPoint,
  EmbeddingMapData,
} from '@/types/api'

export function getStatsOverview() {
  return apiGet<StatsOverview>('/stats/overview')
}

export function getEvalTrends(params?: { category?: string; weeks?: number }) {
  return apiGet<EvalTrendsResponse>('/stats/eval-trends', params)
}

export function getUsageHeatmap(params?: { period_type?: string; periods?: number }) {
  return apiGet<UsageHeatmapResponse>('/stats/usage-heatmap', params)
}

export function getGovernanceQueue(params?: { reason?: string; limit?: number; offset?: number }) {
  return apiGet<GovernanceQueueItem[]>('/governance/queue', params)
}

export function submitReview(submission: GovernanceReviewSubmission) {
  return apiPost<{ success: boolean }>('/governance/review', submission)
}

export function getEmbeddingMap() {
  return apiGet<EmbeddingMapPoint[]>('/stats/embedding-map')
}

export function getEmbeddingMapV2() {
  return apiGet<EmbeddingMapData>('/embeddings/map')
}
