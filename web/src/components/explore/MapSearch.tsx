import { Search, X } from 'lucide-react'

interface MapSearchProps {
  value: string
  onChange: (value: string) => void
}

export function MapSearch({ value, onChange }: MapSearchProps) {
  return (
    <div className="absolute top-4 left-4 right-4 sm:right-auto z-10 flex items-center gap-2 bg-background/90 backdrop-blur-sm border rounded-lg px-3 py-2 shadow-sm sm:w-64">
      <Search className="h-4 w-4 text-muted-foreground shrink-0" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Filter by name or slug..."
        className="bg-transparent text-sm outline-none flex-1 placeholder:text-muted-foreground"
      />
      {value && (
        <button
          onClick={() => onChange('')}
          className="text-muted-foreground hover:text-foreground transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  )
}
