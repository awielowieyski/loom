import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/capabilities/$slug')({
  component: CapabilityInspect,
})

function CapabilityInspect() {
  const { slug } = Route.useParams()
  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-bold tracking-tight">Capability: {slug}</h1>
      <p className="text-muted-foreground">
        Execution plan visualization and step-by-step skill resolution details.
      </p>
    </div>
  )
}
