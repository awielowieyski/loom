import { useQuery } from '@tanstack/react-query'
import { getEmbeddingMap } from '@/api/stats'

export function useEmbeddingMap() {
  return useQuery({
    queryKey: ['stats', 'embedding-map'],
    queryFn: getEmbeddingMap,
    staleTime: 60_000,
  })
}
