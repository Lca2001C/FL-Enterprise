import { AlertTriangle, X } from 'lucide-react';

type ErrorBannerProps = {
  message: string;
  onDismiss?: () => void;
};

const ErrorBanner = ({ message, onDismiss }: ErrorBannerProps) => (
  <div className="error-banner" role="alert">
    <AlertTriangle size={18} />
    <span>{message}</span>
    {onDismiss && (
      <button type="button" className="dismiss" onClick={onDismiss} aria-label="Fechar">
        <X size={16} />
      </button>
    )}
    <style jsx>{`
      .error-banner {
        display: flex;
        align-items: center;
        gap: 10px;
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.3);
        color: var(--danger);
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 20px;
        font-size: 0.9rem;
      }
      .error-banner span {
        flex: 1;
      }
      .dismiss {
        background: none;
        border: none;
        color: inherit;
        cursor: pointer;
        padding: 4px;
        display: flex;
      }
    `}</style>
  </div>
);

export default ErrorBanner;
