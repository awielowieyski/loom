import { useQuery } from '@tanstack/react-query'
import { getActivityFeed } from '@/api/activity'

export function useActivityFeed(params?: { cursor?: string; limit?: number }) {
  return useQuery({
    queryKey: ['activity', params],
    queryFn: () => getActivityFeed(params),
    refetchInterval: 30_000,
  })
}
