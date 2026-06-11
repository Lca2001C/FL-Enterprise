import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import {
  isBareLocalDevUrl,
  isLocalDevHostname,
  normalizeLocalDevOrigin,
  resolveApiBase,
} from './utils/apiBase'
import './index.css'

// Docker expõe o painel em :5173; http://localhost (porta 80) quebra /alerts e /api.
if (typeof window !== 'undefined') {
  const current = window.location.origin.replace(/\/$/, '')
  const expected = normalizeLocalDevOrigin(current)
  if (expected !== current) {
    const target = new URL(window.location.href)
    const fixed = new URL(expected)
    target.protocol = fixed.protocol
    target.host = fixed.host
    window.location.replace(target.toString())
  }

  if ('serviceWorker' in navigator && isLocalDevHostname(window.location.hostname)) {
    void navigator.serviceWorker.getRegistrations().then(async (regs) => {
      if (!regs.length) return
      await Promise.all(regs.map((r) => r.unregister()))
      if ('caches' in window) {
        const keys = await caches.keys()
        await Promise.all(keys.map((k) => caches.delete(k)))
      }
    })
  }
}

try {
  const stored = localStorage.getItem('apiBase')
  if (stored && isBareLocalDevUrl(stored)) {
    localStorage.removeItem('apiBase')
  }
  const resolved = resolveApiBase(
    import.meta.env.VITE_API_BASE_URL as string | undefined,
    localStorage.getItem('apiBase')
  )
  localStorage.setItem('apiBase', resolved)
  if (isLocalDevHostname(window.location.hostname)) {
    const build =
      (window as Window & { __MOTOPAY_BUILD__?: string }).__MOTOPAY_BUILD__ ?? 'unknown'
    const bundle =
      document.querySelector('script[src*="/assets/index-"]')?.getAttribute('src') ?? ''
    console.info('[MotoPay] build:', build, '| origem:', window.location.origin, '| apiBase:', resolved, '| bundle:', bundle)
    const staleBundles = ['INOovow5', 'BsFHlrCi', 'B-Fb7HtC', 'BANB5EUG', 'DSCgvHcv', 'Zvpo6RdN']
    if (staleBundles.some((h) => bundle.includes(h))) {
      console.error(
        '[MotoPay] Bundle antigo em cache — limpe dados do site (Application → Clear site data) e recarregue.'
      )
    }
  }
} catch {
  // ignore storage errors (private mode, etc.)
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
