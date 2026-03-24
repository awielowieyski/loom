import { useGovernanceQueue as useQueue, useSubmitReview } from './useStats'

export function useGovernanceQueueWithReview() {
  const queue = useQueue()
  const review = useSubmitReview()
  return { queue, review }
}
