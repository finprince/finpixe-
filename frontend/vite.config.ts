import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file from current directory
  const env = loadEnv(mode, process.cwd(), '');
  const port = parseInt(env.VITE_PORT || '5173');
  const apiTarget = env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000';

  return {
    plugins: [
      react({
        babel: {
          compact: true,
        },
      }),
    ],
    optimizeDeps: {
      include: ['country-state-city', 'react', 'react-dom', 'axios', 'lucide-react'],
    },
    server: {
      port: port,
      host: '0.0.0.0',
      allowedHosts: true,
      hmr: {
        overlay: false
      },
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          secure: false,
          configure: (proxy, _options) => {
            proxy.on('error', (err, _req, _res) => {
              console.log('proxy error', err);
            });
          },
        }
      }
    },
    preview: {
      port: port,
      host: '0.0.0.0',
    },
    build: {
      outDir: './dist',
      emptyOutDir: true,
      sourcemap: false,
      minify: 'esbuild',
      chunkSizeWarningLimit: 2000,
    }
  }
})

