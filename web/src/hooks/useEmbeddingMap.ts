import { useQuery } from '@tanstack/react-query'
import { getEmbeddingMapV2 } from '@/api/stats'

export function useEmbeddingMap() {
  return useQuery({
    queryKey: ['embeddings', 'map'],
    queryFn: getEmbeddingMapV2,
    staleTime: 60_000,
  })
}
