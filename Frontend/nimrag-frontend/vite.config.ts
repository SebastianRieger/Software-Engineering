import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }: { mode: string }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendHttpOrigin = env.VITE_BACKEND_HTTP_ORIGIN || 'http://localhost:8000'
  const backendWsOrigin = env.VITE_BACKEND_WS_ORIGIN || 'ws://localhost:8000'

  const config = {
    plugins: [vue(), tailwindcss()],
    resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
    server: {
      host: true,
      port: 5173,
      open: true,
      proxy: {
        '/api': {
          target: backendHttpOrigin,
          changeOrigin: true,
        },
        '/ws': {
          target: backendWsOrigin,
          changeOrigin: true,
          ws: true,
        },
      },
    },
    build: { outDir: 'dist', sourcemap: true, emptyOutDir: true },
    test: {
      environment: 'jsdom',
      globals: true,
      coverage: {
        provider: 'v8',
        reporter: ['text', 'lcov', 'html'],
        reportsDirectory: './coverage',
        include: ['src/**/*.{ts,vue}'],
        exclude: [
          'src/main.ts',
          'src/shims-vue.d.ts',
          'src/types/**',
          'coverage/**',
          'dist/**',
          '**/node_modules/**',
        ],
        thresholds: {
          statements: 80,
          branches: 80,
          functions: 80,
          lines: 80,
        },
      },
    },
  }

  return config
})
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  base: '/Software-Engineering/',
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: { host: true, port: 5173, open: true },
  build: { outDir: 'dist', sourcemap: true, emptyOutDir: true },
})
