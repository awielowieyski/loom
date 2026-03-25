import { useQuery } from '@tanstack/react-query'
import { getActivityFeed } from '@/api/activity'

export function useActivityFeed(params?: { limit?: number; since?: string }) {
  return useQuery({
    queryKey: ['activity', params],
    queryFn: () => getActivityFeed(params),
    refetchInterval: 30_000,
  })
}
