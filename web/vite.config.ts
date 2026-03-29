import { defineConfig } from 'vitest/config'
import { loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { TanStackRouterVite } from '@tanstack/router-plugin/vite'
import path from 'path'

export default defineConfig(({ mode }) => {
  // Load env from project root so we can read LOOM_API__PORT
  const env = loadEnv(mode, path.resolve(__dirname, '..'), 'LOOM_')
  const apiPort = env.LOOM_API__PORT || '8000'

  return {
    plugins: [TanStackRouterVite(), react(), tailwindcss()],
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) return

            if (id.includes('react-markdown') || id.includes('remark-gfm')) {
              return 'markdown'
            }

            if (
              id.includes('@xyflow/react') ||
              id.includes('reactflow') ||
              id.includes('d3') ||
              id.includes('dagre')
            ) {
              return 'visualization'
            }

            if (id.includes('recharts')) {
              return 'charts'
            }

            if (id.includes('framer-motion')) {
              return 'motion'
            }

            if (
              id.includes('@tanstack/react-router') ||
              id.includes('@tanstack/react-query')
            ) {
              return 'tanstack'
            }

            if (id.includes('react') || id.includes('react-dom')) {
              return 'react-vendor'
            }

            return 'vendor'
          },
        },
      },
    },
    test: {
      exclude: ['e2e/**', 'node_modules/**'],
      passWithNoTests: true,
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: `http://localhost:${apiPort}`,
          changeOrigin: true,
          headers: {
            'X-API-Key': env.LOOM_DEV_API_KEY || 'loom-dev',
          },
        },
      },
    },
  }
})
