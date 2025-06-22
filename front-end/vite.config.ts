import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
   server: {
    host: '0.0.0.0', // Listen on all interfaces
    port: 8080,
    strictPort: true,
    hmr: {
      host: 'preview.musicbrasileiro.xyz'
    }
  },
 preview: {
    host: '0.0.0.0', // Listen on all interfaces
    port: 8080,
    strictPort: true,
    allowedHosts: ['preview.mysite.com', 'localhost']
  }
})
