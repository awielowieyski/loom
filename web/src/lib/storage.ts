const HISTORY_KEY = 'loom-history'
const MAX_ITEMS = 20

export interface HistoryEntry {
  query: string
  timestamp: number
}

export function getHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    if (!raw) return []
    return JSON.parse(raw) as HistoryEntry[]
  } catch {
    return []
  }
}

export function addToHistory(query: string): void {
  const existing = getHistory().filter((e) => e.query !== query)
  const next: HistoryEntry[] = [{ query, timestamp: Date.now() }, ...existing].slice(0, MAX_ITEMS)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(next))
}

export function clearHistory(): void {
  localStorage.removeItem(HISTORY_KEY)
}
