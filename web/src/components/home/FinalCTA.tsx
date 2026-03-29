import { Button } from '@/components/ui/button'
import { FileText } from 'lucide-react'
import { Link } from '@tanstack/react-router'

export function FinalCTA() {
  return (
    <section className="border-t py-22 md:py-24">
      <div className="max-w-xl mx-auto text-center space-y-7 md:space-y-8">
        <h2 className="text-xl md:text-2xl font-semibold tracking-tight">
          Better capability choice makes agents more useful
        </h2>
        <p className="text-sm md:text-base text-muted-foreground leading-relaxed">
          Loom helps runtimes choose paths that are executable, policy-aware, and easier to audit,
          instead of relying on whichever workflow the model happens to improvise in the moment.
        </p>

        <div className="flex items-center justify-center gap-3 pt-2">
          <Button
            variant="outline"
            size="lg"
            className="gap-1.5"
            render={
              <Link to="/whitepaper" />
            }
          >
            <FileText className="h-3.5 w-3.5" />
            Read the whitepaper
          </Button>
        </div>

        <p className="text-xs text-muted-foreground/60">
          Skills externalise know-how. Loom turns that know-how into runtime decisions.
        </p>
      </div>
    </section>
  )
}
