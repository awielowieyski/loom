import type { ReactNode } from 'react'

interface HeroContentProps {
  children: ReactNode
}

export function HeroContent({ children }: HeroContentProps) {
  return (
    <div className="text-center space-y-6 pt-8 pb-2">
      <div className="space-y-3">
        <h1 className="text-3xl md:text-4xl font-semibold tracking-tight text-foreground">
          The capability resolution layer
          <br />
          for agent systems.
        </h1>
        <p className="text-base md:text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
          Skills package task knowledge. Loom helps agents choose the right skill
          or composed capability for the current environment, given available tools,
          dependencies, trust boundaries, policy, and cost.
        </p>
      </div>

      {children}

      <p className="text-xs text-muted-foreground/60">
        Open registry. Search and resolve freely.{' '}
        <a href="/login" className="underline underline-offset-2 hover:text-muted-foreground transition-colors">
          Sign in
        </a>
        {' '}to contribute, set persistent filters, or opt out of logging.
      </p>
    </div>
  )
}
