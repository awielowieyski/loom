import { useMemo } from 'react'
import { diffLines } from 'diff'
import { cn } from '@/lib/utils'

interface DiffViewProps {
  oldText: string
  newText: string
  title?: string
  className?: string
}

export function DiffView({ oldText, newText, title, className }: DiffViewProps) {
  const changes = useMemo(() => diffLines(oldText, newText), [oldText, newText])

  return (
    <div className={cn('rounded-lg border overflow-hidden', className)}>
      {title && (
        <div className="border-b bg-muted/50 px-3 py-2 text-sm font-medium">{title}</div>
      )}
      <div className="overflow-x-auto">
        <pre className="text-xs leading-relaxed">
          {changes.map((change, i) => {
            const lines = change.value.split('\n')
            // Remove trailing empty line from split
            if (lines[lines.length - 1] === '') lines.pop()

            return lines.map((line, j) => (
              <div
                key={`${i}-${j}`}
                className={cn(
                  'px-3 py-0.5',
                  change.added && 'bg-green-50 text-green-900 dark:bg-green-900/20 dark:text-green-300',
                  change.removed && 'bg-red-50 text-red-900 dark:bg-red-900/20 dark:text-red-300',
                )}
              >
                <span className="mr-2 inline-block w-4 select-none text-muted-foreground">
                  {change.added ? '+' : change.removed ? '-' : ' '}
                </span>
                {line}
              </div>
            ))
          })}
        </pre>
      </div>
    </div>
  )
}
