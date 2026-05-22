import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const proxyTarget = env.VITE_DEV_PROXY_TARGET || 'http://localhost:8000';
  const enablePwaInDev = env.VITE_PWA_DEV === 'true';

  return {
    plugins: [
      react({
        babel: {
          plugins: ['styled-jsx/babel'],
        },
      }),
      VitePWA({
        registerType: 'autoUpdate',
        injectRegister: false,
        strategies: 'generateSW',
        includeAssets: ['favicon.svg', 'icons/*.png'],
        manifestFilename: 'manifest.webmanifest',
        manifest: {
          id: '/',
          name: 'MotoPay Painel',
          short_name: 'MotoPay',
          description:
            'Gestão de frotas, cobranças Pix, clientes e Operação MotoPay',
          lang: 'pt-BR',
          dir: 'ltr',
          scope: '/',
          start_url: '/',
          display: 'standalone',
          display_override: ['standalone', 'minimal-ui'],
          background_color: '#020617',
          theme_color: '#020617',
          orientation: 'portrait-primary',
          categories: ['business', 'utilities'],
          icons: [
            {
              src: 'icons/pwa-192.png',
              sizes: '192x192',
              type: 'image/png',
              purpose: 'any',
            },
            {
              src: 'icons/pwa-512.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'any maskable',
            },
          ],
        },
        workbox: {
          globPatterns: ['**/*.{js,css,html,ico,png,svg,webmanifest}'],
          navigateFallback: 'index.html',
          navigateFallbackDenylist: [/^\/api\/?/],
          runtimeCaching: [
            {
              urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
              handler: 'CacheFirst',
              options: {
                cacheName: 'google-fonts-stylesheets',
                expiration: {
                  maxEntries: 4,
                  maxAgeSeconds: 60 * 60 * 24 * 365,
                },
              },
            },
            {
              urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/i,
              handler: 'CacheFirst',
              options: {
                cacheName: 'google-fonts-webfonts',
                expiration: {
                  maxEntries: 8,
                  maxAgeSeconds: 60 * 60 * 24 * 365,
                },
              },
            },
          ],
        },
        devOptions: {
          enabled: enablePwaInDev,
          navigateFallback: 'index.html',
        },
      }),
    ],
    test: {
      environment: 'node',
    },
    server: {
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
