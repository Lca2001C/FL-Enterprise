import { useCallback, useEffect, useState } from 'react';
import { Download, Share, X } from 'lucide-react';
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

  const refreshVisibility = useCallback(
    (hasNativePrompt: boolean) => {
      const nextMode = resolveInstallPromptMode({ hasNativePrompt }) ?? 'manual';
      setMode(nextMode);
      setVisible(
        shouldShowInstallPrompt({
          hasNativePrompt,
          forceManual: nextMode === 'manual' || nextMode === 'ios',
        }),
      );
    },
    [],
  );

  useEffect(() => {
    refreshVisibility(false);

    const onBeforeInstallPrompt = (event: Event) => {
      event.preventDefault();
      setDeferredPrompt(event as BeforeInstallPromptEvent);
      refreshVisibility(true);
    };

    const onAppInstalled = () => {
      setDeferredPrompt(null);
      setVisible(false);
    };

    window.addEventListener('beforeinstallprompt', onBeforeInstallPrompt);
    window.addEventListener('appinstalled', onAppInstalled);
    return () => {
      window.removeEventListener('beforeinstallprompt', onBeforeInstallPrompt);
      window.removeEventListener('appinstalled', onAppInstalled);
    };
  }, [refreshVisibility]);

  const handleDismiss = () => {
    dismissInstallPrompt();
    setVisible(false);
  };

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
    <div className="install-prompt" role="dialog" aria-label="Instalar MotoPay no celular">
      <div className="install-prompt__content">
        <div className="install-prompt__header">
          <Download size={20} aria-hidden />
          <strong>Instalar MotoPay</strong>
          <button type="button" className="install-prompt__close" onClick={handleDismiss} aria-label="Fechar">
            <X size={18} />
          </button>
        </div>
        {mode === 'native' ? (
          <p className="install-prompt__text">
            Adicione o painel à tela inicial para abrir como app, com ícone e tela cheia.
          </p>
        ) : ios ? (
          <p className="install-prompt__text">
            Toque em <Share size={14} className="inline-icon" aria-hidden /> <strong>Compartilhar</strong> e depois em{' '}
            <strong>Adicionar à Tela de Início</strong>.
          </p>
        ) : (
          <p className="install-prompt__text">
            No menu do navegador (⋮), escolha <strong>Instalar app</strong> ou{' '}
            <strong>Adicionar à tela inicial</strong>.
          </p>
        )}
        <div className="install-prompt__actions">
          {mode === 'native' && (
            <button type="button" className="install-prompt__primary" onClick={() => void handleInstall()}>
              Instalar app
            </button>
          )}
          <button type="button" className="install-prompt__secondary" onClick={handleDismiss}>
            Agora não
          </button>
        </div>
      </div>
      <style jsx>{`
        .install-prompt {
          position: fixed;
          bottom: calc(12px + env(safe-area-inset-bottom, 0px));
          left: 50%;
          transform: translateX(-50%);
          z-index: 390;
          width: calc(100% - 24px - env(safe-area-inset-right, 0px) - env(safe-area-inset-left, 0px));
          max-width: 420px;
        }
        .install-prompt__content {
          padding: 16px;
          border-radius: 14px;
          border: 1px solid rgba(129, 140, 248, 0.45);
          background: rgba(15, 23, 42, 0.98);
          backdrop-filter: blur(12px);
          box-shadow: 0 14px 40px rgba(0, 0, 0, 0.55);
          color: #f8fafc;
        }
        .install-prompt__header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 10px;
          font-family: Outfit, sans-serif;
        }
        .install-prompt__header strong {
          flex: 1;
          font-size: 0.95rem;
        }
        .install-prompt__close {
          display: grid;
          place-items: center;
          min-width: 44px;
          min-height: 44px;
          border: none;
          border-radius: 8px;
          background: transparent;
          color: #94a3b8;
          cursor: pointer;
        }
        .install-prompt__text {
          margin: 0 0 14px;
          font-size: 0.875rem;
          line-height: 1.45;
          color: #cbd5e1;
        }
        .install-prompt__text :global(.inline-icon) {
          vertical-align: -2px;
          display: inline;
        }
        .install-prompt__actions {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .install-prompt__primary,
        .install-prompt__secondary {
          min-height: 46px;
          border-radius: 10px;
          font-weight: 600;
          font-family: Outfit, sans-serif;
          cursor: pointer;
          -webkit-tap-highlight-color: transparent;
          touch-action: manipulation;
        }
        .install-prompt__primary {
          border: none;
          background: linear-gradient(135deg, #6366f1, #4f46e5);
          color: white;
        }
        .install-prompt__secondary {
          border: 1px solid rgba(148, 163, 184, 0.35);
          background: transparent;
          color: #94a3b8;
        }
      `}</style>
    </div>
  );
}
