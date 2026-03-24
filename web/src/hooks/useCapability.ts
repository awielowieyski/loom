import { useQuery } from '@tanstack/react-query'
import { getCapability } from '@/api/capabilities'

export function useCapability(slug: string) {
  return useQuery({
    queryKey: ['capability', slug],
    queryFn: () => getCapability(slug),
    enabled: !!slug,
  })
}
