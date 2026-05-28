import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import { PWA_MANIFEST_ICONS, PWA_SCREENSHOTS } from './src/pwa.config';

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
        includeAssets: [
          'favicon.ico',
          'favicon.svg',
          'favicon-16.png',
          'favicon-32.png',
          'icons/*.png',
          'splash/*.png',
          'screenshots/*.png',
        ],
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
          prefer_related_applications: false,
          icons: PWA_MANIFEST_ICONS,
          screenshots: PWA_SCREENSHOTS,
        },
        workbox: {
          globPatterns: ['**/*.{js,css,html,ico,png,svg,webmanifest}'],
          navigateFallback: 'index.html',
          navigateFallbackDenylist: [/^\/api\/?/],
          runtimeCaching: [
            {
              urlPattern: /^\/api\/.*/i,
              handler: 'NetworkFirst',
              options: {
                cacheName: 'api-cache',
                networkTimeoutSeconds: 10,
                expiration: {
                  maxEntries: 50,
                  maxAgeSeconds: 60 * 5,
                },
                cacheableResponse: {
                  statuses: [0, 200],
                },
              },
            },
            {
              urlPattern: /^\/api\/motos\/[^/]+\/imagem$/i,
              handler: 'StaleWhileRevalidate',
              options: {
                cacheName: 'moto-images',
                expiration: {
                  maxEntries: 64,
                  maxAgeSeconds: 60 * 60 * 24 * 7,
                },
                cacheableResponse: {
                  statuses: [0, 200],
                },
              },
            },
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
      host: true,
      port: 5173,
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
        },
        '/health': {
          target: proxyTarget,
          changeOrigin: true,
        },
        '/alerts': {
          target: proxyTarget,
          changeOrigin: true,
        },
        '/socket.io': {
          target: proxyTarget,
          changeOrigin: true,
          ws: true,
        },
      },
    },
  };
});
