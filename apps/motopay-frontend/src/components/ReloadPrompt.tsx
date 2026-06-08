import { useEffect } from 'react';
import { useRegisterSW } from 'virtual:pwa-register/react';

/**
 * Prompt de atualização quando nova build do PWA está disponível.
 */
export default function ReloadPrompt() {
  const {
    offlineReady: [offlineReady, setOfflineReady],
    needRefresh: [needRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    immediate: true,
  });

  useEffect(() => {
    if (!offlineReady) return;
    const t = window.setTimeout(() => setOfflineReady(false), 4500);
    return () => window.clearTimeout(t);
  }, [offlineReady, setOfflineReady]);

  return (
    <>
      {offlineReady && (
        <div className="reload-prompt reload-prompt--info" role="status">
          <span>App instalado. Conexão necessária para dados ao vivo.</span>
          <button type="button" onClick={() => setOfflineReady(false)}>
            OK
          </button>
          <style jsx>{`
            .reload-prompt {
              position: fixed;
              bottom: calc(12px + env(safe-area-inset-bottom, 0px));
              left: 50%;
              transform: translateX(-50%);
              z-index: 400;
              width: calc(100% - 24px - env(safe-area-inset-right, 0px) - env(safe-area-inset-left, 0px));
              max-width: 420px;
              display: flex;
              align-items: center;
              justify-content: space-between;
              gap: 12px;
              padding: 14px 16px;
              border-radius: 12px;
              font-size: 0.875rem;
              box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5);
              border: 1px solid rgba(148, 163, 184, 0.3);
              background: rgba(15, 23, 42, 0.95);
              backdrop-filter: blur(10px);
            }
            .reload-prompt--info {
              color: var(--text-muted, #94a3b8);
            }
            .reload-prompt span {
              flex: 1;
              color: inherit;
              line-height: 1.4;
            }
            .reload-prompt button {
              flex-shrink: 0;
              min-height: 44px;
              min-width: 44px;
              padding: 8px 16px;
              border-radius: 8px;
              border: none;
              font-weight: 600;
              font-family: Outfit, sans-serif;
              cursor: pointer;
              background: rgba(99, 102, 241, 0.2);
              color: #818cf8;
            }
          `}</style>
        </div>
      )}
      {needRefresh && (
        <div className="reload-prompt reload-prompt--accent" role="alert">
          <span>Nova versão disponível. Atualize para receber correções recentes.</span>
          <div className="actions">
            <button
              type="button"
              onClick={() => {
                void updateServiceWorker(true);
              }}
              className="primary"
            >
              Atualizar
            </button>
          </div>
          <style jsx>{`
            .reload-prompt {
              position: fixed;
              bottom: calc(12px + env(safe-area-inset-bottom, 0px));
              left: 50%;
              transform: translateX(-50%);
              z-index: 400;
              width: calc(100% - 24px - env(safe-area-inset-right, 0px) - env(safe-area-inset-left, 0px));
              max-width: 420px;
              display: flex;
              flex-direction: column;
              gap: 12px;
              padding: 16px;
              border-radius: 14px;
              font-size: 0.875rem;
              box-shadow: 0 14px 40px rgba(0, 0, 0, 0.55);
              border: 1px solid rgba(129, 140, 248, 0.45);
              background: rgba(15, 23, 42, 0.98);
              backdrop-filter: blur(12px);
              color: #f8fafc;
            }
            .reload-prompt span {
              line-height: 1.45;
            }
            .actions {
              display: flex;
              justify-content: flex-end;
            }
            .reload-prompt button.primary {
              min-height: 46px;
              padding: 0 22px;
              border-radius: 10px;
              border: none;
              font-weight: 600;
              font-family: Outfit, sans-serif;
              cursor: pointer;
              background: linear-gradient(135deg, #6366f1, #4f46e5);
              color: white;
              width: 100%;
              max-width: 100%;
              min-width: unset;
              -webkit-tap-highlight-color: transparent;
              touch-action: manipulation;
            }
            @media (min-width: 480px) {
              .reload-prompt button.primary {
                width: auto;
                min-width: 160px;
              }
            }
          `}</style>
        </div>
      )}
    </>
  );
}
