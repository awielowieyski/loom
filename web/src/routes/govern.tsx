import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/govern')({
  component: GovernView,
})

function GovernView() {
  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-bold tracking-tight">Govern</h1>
      <p className="text-muted-foreground">
        Review governance queue, trust tier management, and registry health metrics.
      </p>
    </div>
  )
}
