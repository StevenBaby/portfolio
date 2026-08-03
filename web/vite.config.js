import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    assetsInlineLimit: 0,
  },
  server: {
    port: 5174,
    host: true,
    proxy: {
      '/api/quote': {
        target: 'https://hq.sinajs.cn',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/quote/, ''),
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            proxyReq.setHeader('Referer', 'https://finance.sina.com.cn')
          })
        },
      },
    },
  },
})
