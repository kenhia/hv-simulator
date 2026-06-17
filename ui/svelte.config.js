import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

// Client-only SPA served by the engine under /ui (same-origin, no SSR). The
// galaxy graph is one prerendered page that hydrates and runs client-side.
const base = process.env.HVSIM_UI_BASE ?? '/ui';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter({ fallback: 'index.html' }),
    paths: { base, relative: false }
  }
};

export default config;
