import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// Dev server proxies the engine API so the SPA can fetch same-origin paths
// (/systems, /wormholes, …) without CORS. Override the target with HVSIM_API.
const api = process.env.HVSIM_API ?? 'http://localhost:4667';
const apiPaths = ['/systems', '/wormholes', '/junctions', '/fleet', '/bodies', '/clock', '/ships'];

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    proxy: Object.fromEntries(apiPaths.map((p) => [p, { target: api, changeOrigin: true }]))
  },
  test: {
    include: ['src/**/*.{test,spec}.{js,ts}'],
    environment: 'node'
  }
});
