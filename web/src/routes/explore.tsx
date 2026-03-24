import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/explore')({
  component: ExploreView,
})

function ExploreView() {
  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-bold tracking-tight">Explore</h1>
      <p className="text-muted-foreground">
        Browse the semantic landscape of skills and capabilities in the registry.
      </p>
    </div>
  )
}
