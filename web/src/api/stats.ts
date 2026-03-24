import { apiGet, apiPost } from './client'
import type {
  StatsOverview,
  EvalTrendPoint,
  UsageHeatmapEntry,
  GovernanceQueueItem,
  GovernanceReviewSubmission,
  EmbeddingMapPoint,
  EmbeddingMapData,
} from '@/types/api'

export function getStatsOverview() {
  return apiGet<StatsOverview>('/stats/overview')
}

export function getEvalTrends(params?: { days?: number }) {
  return apiGet<EvalTrendPoint[]>('/stats/eval-trends', params)
}

export function getUsageHeatmap(params?: { limit?: number }) {
  return apiGet<UsageHeatmapEntry[]>('/stats/usage-heatmap', params)
}

export function getGovernanceQueue() {
  return apiGet<GovernanceQueueItem[]>('/governance/queue')
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
