import { Button } from '@/components/ui/button'
import { FileText } from 'lucide-react'

export function FinalCTA() {
  return (
    <section className="py-20 border-t">
      <div className="max-w-xl mx-auto text-center space-y-6">
        <h2 className="text-xl md:text-2xl font-semibold tracking-tight">
          Give your agents a better way to choose
        </h2>
        <p className="text-sm md:text-base text-muted-foreground leading-relaxed">
          The next bottleneck in agent systems is not tool access.
          It is deciding which path should be used under real-world constraints.
          Loom helps agents make that choice.
        </p>

        <div className="flex items-center justify-center gap-3 pt-2">
          <Button variant="outline" size="lg" className="gap-1.5">
            <FileText className="h-3.5 w-3.5" />
            Read the whitepaper
          </Button>
        </div>

        <p className="text-xs text-muted-foreground/60">
          Skills externalise know-how. Loom resolves it.
        </p>
      </div>
    </section>
  )
}
