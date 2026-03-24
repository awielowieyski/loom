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

export function useEvalTrends(days?: number) {
  return useQuery({
    queryKey: ['stats', 'eval-trends', days],
    queryFn: () => getEvalTrends({ days }),
  })
}

export function useUsageHeatmap(limit?: number) {
  return useQuery({
    queryKey: ['stats', 'usage-heatmap', limit],
    queryFn: () => getUsageHeatmap({ limit }),
  })
}

export function useGovernanceQueue() {
  return useQuery({
    queryKey: ['governance', 'queue'],
    queryFn: getGovernanceQueue,
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
