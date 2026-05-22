import { ArrowRight, Sparkles, X, Zap } from 'lucide-react';

type TourWelcomeBannerProps = {
  onStart: () => void;
  onDismiss: () => void;
};

const TourWelcomeBanner = ({ onStart, onDismiss }: TourWelcomeBannerProps) => (
  <div className="tour-welcome animate-fade" data-tour="tour-welcome-banner">
    <div className="tour-welcome-orb tour-welcome-orb--a" aria-hidden />
    <div className="tour-welcome-orb tour-welcome-orb--b" aria-hidden />
    <div className="tour-welcome-shimmer" aria-hidden />

    <div className="tour-welcome-inner">
      <div className="tour-welcome-icon" aria-hidden>
        <Sparkles size={26} strokeWidth={1.75} />
      </div>

      <div className="tour-welcome-copy">
        <span className="tour-welcome-badge">
          <Zap size={12} strokeWidth={2.5} />
          Tour interativo
        </span>
        <h3>Descubra o MotoPay em poucos minutos</h3>
        <p>
          Um passeio guiado pelas telas do painel — frota, cobranças Pix, Telegram e ajustes da
          operação. Leva cerca de 3 minutos.
        </p>
      </div>

      <div className="tour-welcome-actions">
        <button type="button" className="tour-welcome-cta" onClick={onStart}>
          Iniciar tour
          <ArrowRight size={18} strokeWidth={2.25} />
        </button>
        <button type="button" className="tour-welcome-skip" onClick={onDismiss}>
          Agora não
        </button>
      </div>
    </div>

    <button
      type="button"
      className="tour-welcome-close"
      onClick={onDismiss}
      aria-label="Fechar convite do tour"
    >
      <X size={16} />
    </button>
  </div>
);

export default TourWelcomeBanner;
