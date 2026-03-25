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
