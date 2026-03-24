import { createFileRoute } from '@tanstack/react-router'
import { SkillDetail } from '@/components/inspect/SkillDetail'
import { TrustJourney } from '@/components/inspect/TrustJourney'
import { VersionTimeline } from '@/components/inspect/VersionTimeline'
import { WhyThisWorks } from '@/components/inspect/WhyThisWorks'
import { useSkill } from '@/hooks/useSkill'

export const Route = createFileRoute('/skills/$slug')({
  component: SkillInspect,
})

function SkillInspect() {
  const { slug } = Route.useParams()
  const { isLoading, error } = useSkill(slug)

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 w-64 rounded bg-muted" />
        <div className="h-4 w-96 rounded bg-muted" />
        <div className="h-48 rounded bg-muted" />
        <div className="h-32 rounded bg-muted" />
      </div>
    )
  }

  if (error) {
    const is404 = error instanceof Error && error.message.includes('not found')
    return (
      <div className="py-12 text-center">
        <h1 className="text-2xl font-bold">
          {is404 ? 'Skill Not Found' : 'Error'}
        </h1>
        <p className="mt-2 text-muted-foreground">
          {is404
            ? `No skill with slug "${slug}" exists.`
            : 'Failed to load skill details.'}
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-10">
      <SkillDetail slug={slug} />

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Why This Works</h2>
        <WhyThisWorks />
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Trust Journey</h2>
        <TrustJourney slug={slug} />
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Versions</h2>
        <VersionTimeline slug={slug} />
      </section>
    </div>
  )
}
