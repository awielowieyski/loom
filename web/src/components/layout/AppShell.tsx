import type { ReactNode } from 'react'
import { Header } from './Header'
import { LivingFeed } from '@/components/shared/LivingFeed'

interface AppShellProps {
  children: ReactNode
  sidebar?: ReactNode
  hideSidebar?: boolean
}

export function AppShell({ children, sidebar, hideSidebar }: AppShellProps) {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <div className="flex flex-1">
        <main className="flex-1 p-4 md:p-6">{children}</main>
        {!hideSidebar && (
          <aside className="hidden lg:block w-[280px] border-l p-4 shrink-0">
            {sidebar ?? <LivingFeed />}
          </aside>
        )}
      </div>
    </div>
  )
}
