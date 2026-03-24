import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/skills/$slug')({
  component: SkillInspect,
})

function SkillInspect() {
  const { slug } = Route.useParams()
  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-bold tracking-tight">Skill: {slug}</h1>
      <p className="text-muted-foreground">
        Detailed view for skill evaluation, usage signals, and behavioral assessment.
      </p>
    </div>
  )
}
