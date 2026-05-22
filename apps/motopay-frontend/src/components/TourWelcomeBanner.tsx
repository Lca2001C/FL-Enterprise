import { BookOpen, X } from 'lucide-react';

type TourWelcomeBannerProps = {
  onStart: () => void;
  onDismiss: () => void;
};

const TourWelcomeBanner = ({ onStart, onDismiss }: TourWelcomeBannerProps) => (
  <div className="glass card tour-welcome animate-fade" data-tour="tour-welcome-banner">
    <div className="tour-welcome-body">
      <BookOpen size={22} color="var(--primary)" />
      <div>
        <h3>Conheça o sistema em 3 minutos</h3>
        <p className="text-muted">
          Tour guiado pelas telas do painel: frota, cobranças automáticas, Telegram e ajustes da operação.
        </p>
      </div>
    </div>
    <div className="tour-welcome-actions">
      <button type="button" className="btn-primary" onClick={onStart}>
        Iniciar tour
      </button>
      <button type="button" className="btn-secondary" onClick={onDismiss}>
        Depois
      </button>
      <button type="button" className="icon-btn tour-dismiss" onClick={onDismiss} aria-label="Fechar">
        <X size={16} />
      </button>
    </div>
    <style jsx>{`
      .tour-welcome {
        margin-bottom: 24px;
        padding: 20px 24px;
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        border: 1px solid rgba(99, 102, 241, 0.25);
      }
      .tour-welcome-body {
        display: flex;
        align-items: flex-start;
        gap: 14px;
        flex: 1;
        min-width: 220px;
      }
      .tour-welcome h3 {
        margin: 0 0 6px;
        font-size: 1rem;
      }
      .tour-welcome p {
        margin: 0;
        font-size: 0.85rem;
      }
      .tour-welcome-actions {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
      }
      .tour-dismiss {
        margin-left: 4px;
      }
    `}</style>
  </div>
);

export default TourWelcomeBanner;
