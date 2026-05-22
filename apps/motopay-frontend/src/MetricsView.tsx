import { useState, useEffect, useCallback, type ReactNode } from 'react';
import { Calendar, TrendingUp, AlertCircle } from 'lucide-react';
import { useAuth } from './AuthContext';
import type { MotoAnalyticsRow } from './apiTypes';
import { formatBrl } from './utils/format';
import { parseApiError } from './utils/apiError';
import ErrorBanner from './components/ErrorBanner';
import AdminScopeBanner from './components/AdminScopeBanner';

const renderStatus = (item: MotoAnalyticsRow) =>
  item.prejuizo ? (
    <div className="alert-badge">
      <AlertCircle size={12} /> Alerta Prejuízo
    </div>
  ) : (
    <div className="success-badge">
      <TrendingUp size={12} /> Saudável
    </div>
  );

const renderRoi = (item: MotoAnalyticsRow) =>
  item.roi ? (
    <span className={`roi-tag ${item.roi > 0.5 ? 'high' : ''}`}>
      {(item.roi * 100).toFixed(1)}%
    </span>
  ) : (
    '—'
  );

const MetricMotoCard = ({ item }: { item: MotoAnalyticsRow }) => (
  <div className="glass metric-card">
    <div className="metric-card-header">
      <div className="metric-card-identity">
        <div className="metric-card-title">{item.modelo}</div>
        <div className="text-muted metric-card-placa">{item.placa}</div>
      </div>
      {renderStatus(item)}
    </div>

    <div className={`metric-hero ${item.prejuizo ? 'metric-hero-loss' : 'metric-hero-profit'}`}>
      <span className="metric-hero-label">Lucro líquido</span>
      <span className="metric-hero-value">{formatBrl(item.lucro_liquido)}</span>
    </div>

    <div className="metric-footer">
      <div className="metric-stat">
        <span className="metric-stat-label">Receita</span>
        <span className="metric-stat-value text-accent">{formatBrl(item.receita)}</span>
      </div>
      <div className="metric-stat">
        <span className="metric-stat-label">Despesa</span>
        <span className="metric-stat-value text-danger">{formatBrl(item.despesa)}</span>
      </div>
      <div className="metric-stat">
        <span className="metric-stat-label">ROI</span>
        <span className="metric-stat-value">{renderRoi(item)}</span>
      </div>
    </div>

    <style jsx>{`
      .metric-card {
        padding: 16px;
        display: flex;
        flex-direction: column;
        gap: 14px;
      }
      .metric-card-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 10px;
      }
      .metric-card-identity {
        min-width: 0;
        flex: 1;
      }
      .metric-card-title {
        font-weight: 600;
        font-size: 1rem;
        line-height: 1.3;
      }
      .metric-card-placa {
        font-size: 0.8rem;
        margin-top: 2px;
      }
      .metric-hero {
        border-radius: 12px;
        padding: 14px 16px;
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      .metric-hero-profit {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.2);
      }
      .metric-hero-loss {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.2);
      }
      .metric-hero-label {
        font-size: 0.72rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }
      .metric-hero-value {
        font-size: 1.35rem;
        font-weight: 700;
        font-family: 'Outfit', sans-serif;
        line-height: 1.2;
        word-break: break-word;
      }
      .metric-hero-profit .metric-hero-value {
        color: var(--accent);
      }
      .metric-hero-loss .metric-hero-value {
        color: var(--danger);
      }
      .metric-footer {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
      }
      .metric-stat {
        display: flex;
        flex-direction: column;
        gap: 4px;
        min-width: 0;
      }
      .metric-stat-label {
        font-size: 0.68rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }
      .metric-stat-value {
        font-size: 0.85rem;
        font-weight: 600;
        word-break: break-word;
      }
      .text-accent {
        color: var(--accent);
      }
      .text-danger {
        color: var(--danger);
      }
      .roi-tag {
        background: rgba(255, 255, 255, 0.05);
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
      }
      .roi-tag.high {
        color: var(--accent);
        background: rgba(16, 185, 129, 0.1);
      }
      .alert-badge {
        display: flex;
        align-items: center;
        gap: 5px;
        color: var(--danger);
        font-size: 0.72rem;
        font-weight: 600;
        flex-shrink: 0;
        text-align: right;
      }
      .success-badge {
        display: flex;
        align-items: center;
        gap: 5px;
        color: var(--accent);
        font-size: 0.72rem;
        font-weight: 600;
        flex-shrink: 0;
        text-align: right;
      }
      @media (max-width: 480px) {
        .metric-card {
          padding: 14px;
        }
        .metric-hero-value {
          font-size: 1.2rem;
        }
        .metric-stat-value {
          font-size: 0.8rem;
        }
      }
    `}</style>
  </div>
);

type DateFiltersProps = {
  inicio: string;
  fim: string;
  onChange: (field: 'inicio' | 'fim', value: string) => void;
};

const DateFiltersDesktop = ({ inicio, fim, onChange }: DateFiltersProps) => (
  <div className="date-filters-desktop glass">
    <div className="filter-item">
      <Calendar size={14} />
      <input
        type="date"
        value={inicio}
        onChange={(e) => onChange('inicio', e.target.value)}
      />
    </div>
    <span className="separator">até</span>
    <div className="filter-item">
      <Calendar size={14} />
      <input type="date" value={fim} onChange={(e) => onChange('fim', e.target.value)} />
    </div>
    <style jsx>{`
      .date-filters-desktop {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
        padding: 10px 20px;
        border-radius: 12px;
      }
      .filter-item {
        display: flex;
        align-items: center;
        gap: 8px;
        min-width: 0;
      }
      .filter-item input {
        background: none;
        border: none;
        color: white;
        outline: none;
        font-size: 0.9rem;
        cursor: pointer;
        min-width: 0;
      }
      .separator {
        color: var(--text-muted);
        font-size: 0.8rem;
      }
      @media (max-width: 768px) {
        .date-filters-desktop {
          display: none;
        }
      }
    `}</style>
  </div>
);

const DateFiltersMobile = ({ inicio, fim, onChange }: DateFiltersProps) => (
  <div className="date-filters-mobile glass">
    <p className="period-label">Período</p>
    <div className="input-group period-field">
      <label className="input-label" htmlFor="metrics-inicio">
        De
      </label>
      <input
        id="metrics-inicio"
        type="date"
        className="input-field"
        value={inicio}
        onChange={(e) => onChange('inicio', e.target.value)}
      />
    </div>
    <div className="input-group period-field">
      <label className="input-label" htmlFor="metrics-fim">
        Até
      </label>
      <input
        id="metrics-fim"
        type="date"
        className="input-field"
        value={fim}
        onChange={(e) => onChange('fim', e.target.value)}
      />
    </div>
    <style jsx>{`
      .date-filters-mobile {
        display: none;
        flex-direction: column;
        gap: 12px;
        padding: 14px 16px;
        border-radius: 12px;
        width: 100%;
      }
      .period-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: var(--text-muted);
        margin: 0;
      }
      .period-field {
        margin-bottom: 0;
      }
      @media (max-width: 768px) {
        .date-filters-mobile {
          display: flex;
          margin-bottom: 16px;
        }
      }
    `}</style>
  </div>
);

const MetricsView = () => {
  const { api } = useAuth();
  const [ranking, setRanking] = useState<MotoAnalyticsRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [dates, setDates] = useState({
    inicio: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0],
    fim: new Date().toISOString().split('T')[0],
  });

  const fetchRanking = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const r = await api.get<MotoAnalyticsRow[]>('/api/v1/analytics/motos/ranking', {
        params: { data_inicio: dates.inicio, data_fim: dates.fim },
      });
      setRanking(r.data);
    } catch (e) {
      setError(parseApiError(e, 'Erro ao carregar métricas'));
    } finally {
      setLoading(false);
    }
  }, [api, dates]);

  useEffect(() => {
    void fetchRanking();
  }, [fetchRanking]);

  const handleDateChange = (field: 'inicio' | 'fim', value: string) => {
    setDates((prev) => ({ ...prev, [field]: value }));
  };

  const emptyMessage = loading
    ? 'Analisando dados financeiros...'
    : 'Nenhum dado encontrado no período.';

  const dateFilterProps: DateFiltersProps = {
    inicio: dates.inicio,
    fim: dates.fim,
    onChange: handleDateChange,
  };

  let mobileList: ReactNode;
  if (loading || ranking.length === 0) {
    mobileList = <div className="glass metric-card-empty">{emptyMessage}</div>;
  } else {
    mobileList = ranking.map((item) => <MetricMotoCard key={item.moto_id} item={item} />);
  }

  return (
    <div className="view-container animate-fade">
      <div className="view-header">
        <div>
          <h2>Inteligência de Frota</h2>
          <p className="text-muted">Análise de rentabilidade por veículo</p>
        </div>
        <DateFiltersDesktop {...dateFilterProps} />
      </div>

      <DateFiltersMobile {...dateFilterProps} />

      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}
      <AdminScopeBanner />

      <div className="metrics-grid" data-tour="metrics-ranking">
        <div className="glass table-container metrics-table-wrap">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Moto / Placa</th>
                <th>Receita</th>
                <th>Despesa</th>
                <th>Lucro Líquido</th>
                <th>ROI</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {loading || ranking.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '40px' }}>
                    {emptyMessage}
                  </td>
                </tr>
              ) : (
                ranking.map((item) => (
                  <tr key={item.moto_id}>
                    <td>
                      <div style={{ fontWeight: 600 }}>{item.modelo}</div>
                      <div className="text-muted" style={{ fontSize: '0.8rem' }}>
                        {item.placa}
                      </div>
                    </td>
                    <td className="text-accent">{formatBrl(item.receita)}</td>
                    <td className="text-danger">{formatBrl(item.despesa)}</td>
                    <td
                      style={{
                        fontWeight: 700,
                        color: item.prejuizo ? 'var(--danger)' : 'white',
                      }}
                    >
                      {formatBrl(item.lucro_liquido)}
                    </td>
                    <td>{renderRoi(item)}</td>
                    <td>{renderStatus(item)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="metrics-cards">{mobileList}</div>
      </div>

      <style jsx>{`
        .view-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          flex-wrap: wrap;
          gap: 16px;
          margin-bottom: 30px;
        }
        .table-container {
          overflow-x: auto;
          -webkit-overflow-scrolling: touch;
        }
        .custom-table {
          width: 100%;
          border-collapse: collapse;
          min-width: 720px;
        }
        .custom-table th {
          text-align: left;
          padding: 15px 20px;
          color: var(--text-muted);
          font-size: 0.85rem;
          border-bottom: 1px solid var(--glass-border);
        }
        .custom-table td {
          padding: 15px 20px;
          border-bottom: 1px solid var(--glass-border);
          font-size: 0.9rem;
        }
        .text-accent {
          color: var(--accent);
        }
        .text-danger {
          color: var(--danger);
        }
        .roi-tag {
          background: rgba(255, 255, 255, 0.05);
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 0.8rem;
          font-weight: 600;
        }
        .roi-tag.high {
          color: var(--accent);
          background: rgba(16, 185, 129, 0.1);
        }
        .alert-badge {
          display: flex;
          align-items: center;
          gap: 5px;
          color: var(--danger);
          font-size: 0.75rem;
          font-weight: 600;
        }
        .success-badge {
          display: flex;
          align-items: center;
          gap: 5px;
          color: var(--accent);
          font-size: 0.75rem;
          font-weight: 600;
        }
        .metrics-cards {
          display: none;
          flex-direction: column;
          gap: 12px;
        }
        .metric-card-empty {
          text-align: center;
          color: var(--text-muted);
          padding: 32px 16px;
          border-radius: 16px;
        }
        @media (max-width: 768px) {
          .view-header {
            margin-bottom: 12px;
          }
          .metrics-table-wrap {
            display: none;
          }
          .metrics-cards {
            display: flex;
          }
        }
        @media (max-width: 480px) {
          .view-header {
            flex-direction: column;
            align-items: stretch;
          }
        }
      `}</style>
    </div>
  );
};

export default MetricsView;
