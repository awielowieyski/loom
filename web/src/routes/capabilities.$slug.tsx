import { createFileRoute } from '@tanstack/react-router'
import { CapabilityDetail } from '@/components/inspect/CapabilityDetail'
import { useCapability } from '@/hooks/useCapability'

export const Route = createFileRoute('/capabilities/$slug')({
  component: CapabilityInspect,
})

function CapabilityInspect() {
  const { slug } = Route.useParams()
  const { isLoading, error } = useCapability(slug)

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 w-64 rounded bg-muted" />
        <div className="h-4 w-96 rounded bg-muted" />
        <div className="h-[400px] rounded bg-muted" />
      </div>
    )
  }

  if (error) {
    const is404 = error instanceof Error && error.message.includes('not found')
    return (
      <div className="py-12 text-center">
        <h1 className="text-2xl font-bold">
          {is404 ? 'Capability Not Found' : 'Error'}
        </h1>
        <p className="mt-2 text-muted-foreground">
          {is404
            ? `No capability with slug "${slug}" exists.`
            : 'Failed to load capability details.'}
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-10">
      <CapabilityDetail slug={slug} />
    </div>
  )
}
