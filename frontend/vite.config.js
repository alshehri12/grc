import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [vue()],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url))
        }
    },
    server: {
        port: 5173,
        host: true, // listen on the LAN too (http://<your-ip>:5173)
        // Allow access through common tunnel domains (Vite blocks unknown hosts by default)
        allowedHosts: [
            '.ngrok-free.app', '.ngrok-free.dev', '.ngrok.app', '.ngrok.dev',
            '.trycloudflare.com', '.ts.net'
        ],
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true
            },
            '/media': {
                target: 'http://localhost:8000',
                changeOrigin: true
            }
        }
    },
    build: {
        outDir: 'dist',
        assetsDir: 'assets',
        sourcemap: true
    }
})
