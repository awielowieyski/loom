const constraints = [
  {
    label: 'Available dependencies',
    detail: 'Which MCP servers, APIs, and data sources does the agent actually have right now?',
  },
  {
    label: 'Trust boundaries',
    detail: 'Can internal data flow to an external service? What provenance is required?',
  },
  {
    label: 'Policy constraints',
    detail: 'Which providers are approved? Which data classifications restrict the workflow?',
  },
  {
    label: 'Cost limits',
    detail: 'Is a premium data provider justified, or should the agent use a cheaper path?',
  },
  {
    label: 'Acceptable fallbacks',
    detail: 'If the best path is unavailable, what degrades gracefully and what does not?',
  },
  {
    label: 'Data-flow rules',
    detail: 'Which steps produce outputs that subsequent steps consume, and what are the classification implications?',
  },
] as const

export function ProblemSection() {
  return (
    <section className="py-16 border-t">
      <div className="max-w-2xl mx-auto space-y-6">
        <h2 className="text-xl md:text-2xl font-semibold tracking-tight text-foreground">
          Tools expose options. Skills package know-how.
          <br />
          <span className="text-muted-foreground">Agents still need to choose.</span>
        </h2>

        <div className="space-y-4 text-sm md:text-base text-muted-foreground leading-relaxed">
          <p>
            Modern agent systems do not fail only because they lack tool access.
            They fail because they do not always know which path they should use now.
          </p>
          <p>
            A tool catalogue can show what is available. A skill directory can store
            reusable task knowledge. But neither tells an agent which skill or workflow
            best fits the current environment.
          </p>
          <p>
            That decision depends on runtime reality:
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {constraints.map((c) => (
            <div
              key={c.label}
              className="rounded-lg border bg-card px-4 py-3 space-y-1"
            >
              <p className="text-sm font-medium text-foreground">{c.label}</p>
              <p className="text-xs text-muted-foreground leading-relaxed">{c.detail}</p>
            </div>
          ))}
        </div>

        <p className="text-sm md:text-base text-muted-foreground leading-relaxed">
          That is the gap Loom fills.
        </p>
      </div>
    </section>
  )
}
