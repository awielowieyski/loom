import { useMutation } from '@tanstack/react-query'
import { resolve } from '@/api/resolve'
import type { ResolutionContext } from '@/types/api'

export function useResolve() {
  return useMutation({
    mutationFn: (params: {
      task_description: string
      context?: ResolutionContext
      type?: 'any' | 'skill' | 'capability'
    }) => resolve(params),
  })
}
