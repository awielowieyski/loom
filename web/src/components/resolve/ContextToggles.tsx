import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Slider } from '@/components/ui/slider'
import { cn } from '@/lib/utils'
import type { ResolutionContext, TrustTier, CostProfile } from '@/types/api'

interface ContextTogglesProps {
  context: ResolutionContext
  onContextChange: (ctx: ResolutionContext) => void
  className?: string
}

const TOOL_SETS = ['git', 'filesystem', 'network', 'browser'] as const

const TRUST_TIERS: TrustTier[] = ['experimental', 'community', 'verified']

const COST_LEVELS: CostProfile[] = ['free', 'low', 'moderate', 'high']

export function ContextToggles({ context, onContextChange, className }: ContextTogglesProps) {
  const [open, setOpen] = useState(false)

  const tools = context.available_tools ?? []
  const trustFloor = context.trust_floor ?? 'experimental'
  const costIndex = COST_LEVELS.indexOf(context.cost_budget ?? 'high')

  const toggleTool = (tool: string) => {
    const next = tools.includes(tool) ? tools.filter((t) => t !== tool) : [...tools, tool]
    onContextChange({ ...context, available_tools: next })
  }

  return (
    <div className={cn('rounded-lg border bg-card', className)}>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setOpen((v) => !v)}
        className="w-full justify-between px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground"
      >
        Filters
        <ChevronDown
          className={cn('h-4 w-4 transition-transform', open && 'rotate-180')}
        />
      </Button>

      {open && (
        <div className="px-3 pb-3 grid gap-4 sm:grid-cols-3">
          {/* Tools */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground">Available Tools</label>
            <div className="flex flex-wrap gap-x-3 gap-y-1.5">
              {TOOL_SETS.map((tool) => (
                <label key={tool} className="flex items-center gap-1.5 text-sm cursor-pointer">
                  <Checkbox
                    checked={tools.includes(tool)}
                    onCheckedChange={() => toggleTool(tool)}
                  />
                  <span className="capitalize">{tool}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Trust floor */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground">Trust Floor</label>
            <select
              value={trustFloor}
              onChange={(e) =>
                onContextChange({ ...context, trust_floor: e.target.value as TrustTier })
              }
              className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm"
            >
              {TRUST_TIERS.map((tier) => (
                <option key={tier} value={tier}>
                  {tier.charAt(0).toUpperCase() + tier.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* Cost budget */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground">
              Cost Budget: <span className="capitalize">{COST_LEVELS[costIndex]}</span>
            </label>
            <Slider
              value={[costIndex]}
              min={0}
              max={3}
              step={1}
              onValueChange={(val: number[]) => {
                onContextChange({ ...context, cost_budget: COST_LEVELS[val[0]] })
              }}
            />
          </div>
        </div>
      )}
    </div>
  )
}
