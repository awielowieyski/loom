import { apiPost } from './client'
import type { ResolvedResult, ResolutionContext } from '@/types/api'

export function resolve(params: {
  task_description: string
  context?: ResolutionContext
  type?: 'any' | 'skill' | 'capability'
}) {
  return apiPost<ResolvedResult>('/resolve', params)
}
