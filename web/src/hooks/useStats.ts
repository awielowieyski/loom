import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getStatsOverview,
  getEvalTrends,
  getUsageHeatmap,
  getGovernanceQueue,
  submitReview,
} from '@/api/stats'
import type { GovernanceReviewSubmission } from '@/types/api'

export function useStatsOverview() {
  return useQuery({
    queryKey: ['stats', 'overview'],
    queryFn: getStatsOverview,
  })
}

export function useEvalTrends(params?: { category?: string; weeks?: number }) {
  return useQuery({
    queryKey: ['stats', 'eval-trends', params?.category, params?.weeks],
    queryFn: () => getEvalTrends(params),
  })
}

export function useUsageHeatmap(params?: { period_type?: string; periods?: number }) {
  return useQuery({
    queryKey: ['stats', 'usage-heatmap', params?.period_type, params?.periods],
    queryFn: () => getUsageHeatmap(params),
  })
}

export function useGovernanceQueue(params?: { reason?: string }) {
  return useQuery({
    queryKey: ['governance', 'queue', params?.reason],
    queryFn: () => getGovernanceQueue(params),
  })
}

export function useSubmitReview() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (submission: GovernanceReviewSubmission) => submitReview(submission),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['governance', 'queue'] })
    },
  })
}
