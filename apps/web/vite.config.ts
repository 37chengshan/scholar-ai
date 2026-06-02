import { defineConfig } from 'vite'
import path from 'path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'

const DEV_PROXY_UNAVAILABLE_HEADER = 'x-scholarai-dev-proxy-error'

export default defineConfig({
  plugins: [
    // The React and Tailwind plugins are both required for Make, even if
    // Tailwind is not being actively used – do not remove them
    react(),
    tailwindcss(),
    // Bundle analysis: run with ANALYZE=true npm run build
    ...(process.env.ANALYZE === 'true'
      ? [
          (() => {
            const { visualizer } = require('rollup-plugin-visualizer')
            return visualizer({
              filename: 'stats.html',
              open: false,
              gzipSize: true,
              brotliSize: true,
            })
          })(),
        ]
      : []),
  ],
  resolve: {
    alias: {
      // Alias @ to the src directory
      '@': path.resolve(__dirname, './src'),
      '@scholar-ai/types': path.resolve(__dirname, '../../packages/types/src'),
      '@scholar-ai/sdk': path.resolve(__dirname, '../../packages/sdk/src'),
    },
  },

  // Proxy API requests to backend
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api\/(?!v1)/, '/api/v1/'),
        cookiePathRewrite: {
          '*': '/',
        },
        configure: (proxy) => {
          proxy.on('error', (_error, req, res) => {
            if (!res || res.headersSent) {
              return
            }

            const body = JSON.stringify({
              error: {
                title: 'Upstream Unavailable',
                detail: `Development API proxy could not reach backend for ${req.url || 'unknown request'}`,
                status: 503,
                type: 'dev-proxy-upstream-unavailable',
              },
            })

            res.writeHead(503, {
              'Content-Type': 'application/json',
              [DEV_PROXY_UNAVAILABLE_HEADER]: 'upstream-unavailable',
            })
            res.end(body)
          })
        },
      },
    },
  },

  // File types to support raw imports. Never add .css, .tsx, or .ts files to this.
  assetsInclude: ['**/*.svg', '**/*.csv'],

  // Build configuration
  build: {
    chunkSizeWarningLimit: 500,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router'],
          'vendor-query': ['@tanstack/react-query'],
          'vendor-radix': [
            '@radix-ui/react-accordion',
            '@radix-ui/react-alert-dialog',
            '@radix-ui/react-checkbox',
            '@radix-ui/react-collapsible',
            '@radix-ui/react-context-menu',
            '@radix-ui/react-dialog',
            '@radix-ui/react-dropdown-menu',
            '@radix-ui/react-hover-card',
            '@radix-ui/react-label',
            '@radix-ui/react-menubar',
            '@radix-ui/react-navigation-menu',
            '@radix-ui/react-popover',
            '@radix-ui/react-progress',
            '@radix-ui/react-radio-group',
            '@radix-ui/react-scroll-area',
            '@radix-ui/react-select',
            '@radix-ui/react-separator',
            '@radix-ui/react-slider',
            '@radix-ui/react-slot',
            '@radix-ui/react-switch',
            '@radix-ui/react-tabs',
            '@radix-ui/react-toggle',
            '@radix-ui/react-toggle-group',
            '@radix-ui/react-tooltip',
          ],
          'vendor-motion': ['motion'],
          'vendor-icons': ['lucide-react'],
        },
      },
    },
  },
})
