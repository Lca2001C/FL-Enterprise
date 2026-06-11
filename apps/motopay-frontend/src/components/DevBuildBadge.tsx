import { useEffect, useState } from 'react';
import { isLocalDevHostname } from '../utils/apiBase';

/** Indicador visível em dev local — confirma build e origem corretos (evita cache antigo). */
export function DevBuildBadge() {
  const [label, setLabel] = useState('');

  useEffect(() => {
    if (!isLocalDevHostname(window.location.hostname)) return;
    const build =
      (window as Window & { __MOTOPAY_BUILD__?: string }).__MOTOPAY_BUILD__ ?? 'unknown';
    const bundle =
      document.querySelector('script[src*="/assets/index-"]')?.getAttribute('src')?.split('/').pop() ??
      '?';
    setLabel(`${build} | ${bundle} | ${window.location.origin}`);
  }, []);

  if (!label) return null;

  return (
    <div className="dev-build-badge" aria-hidden="true">
      {label}
    </div>
  );
}
