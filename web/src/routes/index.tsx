import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/')({
  component: ResolveView,
})

function ResolveView() {
  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-bold tracking-tight">Resolve</h1>
      <p className="text-muted-foreground">
        Describe a task and find the best skill or capability to accomplish it.
      </p>
    </div>
  )
}
