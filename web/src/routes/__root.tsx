/* eslint-disable react-refresh/only-export-components */
import { createRootRoute, Outlet, useRouterState } from '@tanstack/react-router'
import { AnimatePresence, motion } from 'framer-motion'
import { AppShell } from '@/components/layout/AppShell'

export const Route = createRootRoute({
  component: RootLayout,
})

const pageVariants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -10 },
}

const pageTransition = { duration: 0.2, ease: 'easeOut' as const }

function RootLayout() {
  const routerState = useRouterState()
  const locationKey = routerState.location.pathname
  const isHome = locationKey === '/'

  return (
    <AppShell hideSidebar={isHome}>
      <AnimatePresence mode="wait">
        <motion.div
          key={locationKey}
          variants={pageVariants}
          initial="initial"
          animate="animate"
          exit="exit"
          transition={pageTransition}
        >
          <Outlet />
        </motion.div>
      </AnimatePresence>
    </AppShell>
  )
}
