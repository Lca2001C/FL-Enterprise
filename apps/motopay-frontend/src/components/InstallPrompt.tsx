import { useCallback, useEffect, useState } from 'react';
import { Download, Share, MoreVertical, X } from 'lucide-react';
import {
  dismissInstallPrompt,
  isIosSafari,
  resolveInstallPromptMode,
  shouldShowInstallPrompt,
  type InstallPromptMode,
} from '../utils/pwaInstall';

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
};

export default function InstallPrompt() {
  const [visible, setVisible] = useState(false);
  const [mode, setMode] = useState<InstallPromptMode>('manual');
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);

  const refreshVisibility = useCallback((hasNativePrompt: boolean) => {
    const nextMode = resolveInstallPromptMode({ hasNativePrompt }) ?? 'manual';
    setMode(nextMode);
    setVisible(
      shouldShowInstallPrompt({
        hasNativePrompt,
        forceManual: nextMode === 'manual' || nextMode === 'ios',
      }),
    );
  }, []);

  useEffect(() => {
    refreshVisibility(false);

    const onBefore = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      refreshVisibility(true);
    };
    const onInstalled = () => { setDeferredPrompt(null); setVisible(false); };

    window.addEventListener('beforeinstallprompt', onBefore);
    window.addEventListener('appinstalled', onInstalled);
    return () => {
      window.removeEventListener('beforeinstallprompt', onBefore);
      window.removeEventListener('appinstalled', onInstalled);
    };
  }, [refreshVisibility]);

  const handleDismiss = () => { dismissInstallPrompt(); setVisible(false); };

  const handleInstall = async () => {
    if (mode !== 'native' || !deferredPrompt) return;
    await deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    setDeferredPrompt(null);
    setVisible(false);
  };

  if (!visible) return null;

  const ios = isIosSafari() || mode === 'ios';

  return (
    <div className="ip-wrap" role="dialog" aria-label="Instalar MotoPay">
      <div className="ip-card">
        {/* Header */}
        <div className="ip-header">
          <img src="/icons/apple-touch-icon.png" alt="" className="ip-appicon" />
          <div className="ip-title-block">
            <strong className="ip-title">Instalar MotoPay</strong>
            <span className="ip-sub">Acesso rápido, sem navegador</span>
          </div>
          <button type="button" className="ip-close" onClick={handleDismiss} aria-label="Fechar">
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        {mode === 'native' ? (
          <p className="ip-text">
            Adicione à tela inicial para abrir como aplicativo, com ícone e tela cheia.
          </p>
        ) : ios ? (
          <ol className="ip-steps">
            <li className="ip-step">
              <span className="ip-step-num">1</span>
              <span className="ip-step-text">
                Toque em <span className="ip-chip"><Share size={13} />  Compartilhar</span> na barra inferior do Safari
              </span>
            </li>
            <li className="ip-step">
              <span className="ip-step-num">2</span>
              <span className="ip-step-text">
                Role para baixo e toque em <span className="ip-chip ip-chip--add">+ Adicionar à Tela de Início</span>
              </span>
            </li>
            <li className="ip-step">
              <span className="ip-step-num">3</span>
              <span className="ip-step-text">
                Confirme tocando em <strong>Adicionar</strong> no canto superior direito
              </span>
            </li>
          </ol>
        ) : (
          <p className="ip-text">
            Abra o menu <span className="ip-chip"><MoreVertical size={13} /></span> do navegador e escolha{' '}
            <strong>Instalar app</strong> ou <strong>Adicionar à tela inicial</strong>.
          </p>
        )}

        {/* Actions */}
        <div className="ip-actions">
          {mode === 'native' && (
            <button type="button" className="ip-btn ip-btn--primary" onClick={() => void handleInstall()}>
              <Download size={15} />
              Instalar app
            </button>
          )}
          <button type="button" className="ip-btn ip-btn--ghost" onClick={handleDismiss}>
            Agora não
          </button>
        </div>
      </div>

      <style jsx>{`
        .ip-wrap {
          position: fixed;
          bottom: calc(16px + env(safe-area-inset-bottom, 0px));
          left: 50%;
          transform: translateX(-50%);
          z-index: 390;
          width: calc(100% - 32px);
          max-width: 400px;
        }
        .ip-card {
          padding: 16px;
          border-radius: 18px;
          border: 1px solid rgba(129, 140, 248, 0.3);
          background: rgba(10, 10, 20, 0.97);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.7), 0 0 0 0.5px rgba(255,255,255,0.06);
          color: #f1f5f9;
        }
        .ip-header {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 14px;
        }
        .ip-appicon {
          width: 44px;
          height: 44px;
          border-radius: 10px;
          flex-shrink: 0;
        }
        .ip-title-block {
          flex: 1;
          min-width: 0;
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        .ip-title {
          font-size: 0.95rem;
          font-family: Outfit, sans-serif;
          line-height: 1.2;
        }
        .ip-sub {
          font-size: 0.75rem;
          color: #64748b;
        }
        .ip-close {
          display: grid;
          place-items: center;
          width: 32px;
          height: 32px;
          min-width: 44px;
          min-height: 44px;
          border: none;
          border-radius: 50%;
          background: rgba(255,255,255,0.07);
          color: #94a3b8;
          cursor: pointer;
          flex-shrink: 0;
          -webkit-tap-highlight-color: transparent;
        }
        .ip-text {
          margin: 0 0 14px;
          font-size: 0.875rem;
          line-height: 1.5;
          color: #cbd5e1;
        }
        .ip-steps {
          list-style: none;
          margin: 0 0 14px;
          padding: 0;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .ip-step {
          display: flex;
          align-items: flex-start;
          gap: 10px;
        }
        .ip-step-num {
          flex-shrink: 0;
          width: 22px;
          height: 22px;
          border-radius: 50%;
          background: rgba(99, 102, 241, 0.3);
          border: 1px solid rgba(99, 102, 241, 0.5);
          color: #a5b4fc;
          font-size: 0.75rem;
          font-weight: 700;
          display: grid;
          place-items: center;
        }
        .ip-step-text {
          font-size: 0.82rem;
          line-height: 1.5;
          color: #cbd5e1;
          padding-top: 2px;
        }
        .ip-chip {
          display: inline-flex;
          align-items: center;
          gap: 3px;
          padding: 1px 7px;
          border-radius: 6px;
          background: rgba(99, 102, 241, 0.15);
          border: 1px solid rgba(99, 102, 241, 0.35);
          color: #a5b4fc;
          font-size: 0.78rem;
          font-weight: 600;
          white-space: nowrap;
          vertical-align: middle;
        }
        .ip-chip--add {
          background: rgba(34, 197, 94, 0.12);
          border-color: rgba(34, 197, 94, 0.3);
          color: #86efac;
        }
        .ip-actions {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .ip-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          min-height: 46px;
          border-radius: 12px;
          font-size: 0.9rem;
          font-weight: 600;
          font-family: Outfit, sans-serif;
          cursor: pointer;
          -webkit-tap-highlight-color: transparent;
          touch-action: manipulation;
        }
        .ip-btn--primary {
          border: none;
          background: linear-gradient(135deg, #6366f1, #4f46e5);
          color: white;
          box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
        }
        .ip-btn--ghost {
          border: 1px solid rgba(148, 163, 184, 0.2);
          background: transparent;
          color: #64748b;
        }
      `}</style>
    </div>
  );
}
