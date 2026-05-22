import { useState, useEffect, useCallback } from 'react';
import { Calendar, TrendingUp, AlertCircle } from 'lucide-react';
import { useAuth } from './AuthContext';
import type { MotoAnalyticsRow } from './apiTypes';
import { parseApiError } from './utils/apiError';
import ErrorBanner from './components/ErrorBanner';
import AdminScopeBanner from './components/AdminScopeBanner';

const MetricsView = () => {
  const { api } = useAuth();
  const [ranking, setRanking] = useState<MotoAnalyticsRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [dates, setDates] = useState({
    inicio: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0],
    fim: new Date().toISOString().split('T')[0]
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

  return (
    <div className="view-container animate-fade">
      <div className="view-header">
        <div>
          <h2>Inteligência de Frota</h2>
          <p className="text-muted">Análise de rentabilidade por veículo</p>
        </div>
        <div className="date-filters glass">
          <div className="filter-item">
            <Calendar size={14} />
            <input type="date" value={dates.inicio} onChange={e => setDates({...dates, inicio: e.target.value})} />
          </div>
          <span className="separator">até</span>
          <div className="filter-item">
            <Calendar size={14} />
            <input type="date" value={dates.fim} onChange={e => setDates({...dates, fim: e.target.value})} />
          </div>
        </div>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}
      <AdminScopeBanner />

      <div className="metrics-grid" data-tour="metrics-ranking">
        <div className="glass table-container">
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
              {loading ? (
                <tr><td colSpan={6} style={{ textAlign: 'center', padding: '40px' }}>Analisando dados financeiros...</td></tr>
              ) : ranking.length === 0 ? (
                <tr><td colSpan={6} style={{ textAlign: 'center', padding: '40px' }}>Nenhum dado encontrado no período.</td></tr>
              ) : ranking.map((item) => (
                <tr key={item.moto_id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{item.modelo}</div>
                    <div className="text-muted" style={{ fontSize: '0.8rem' }}>{item.placa}</div>
                  </td>
                  <td className="text-accent">R$ {Number(item.receita).toLocaleString('pt-BR')}</td>
                  <td className="text-danger">R$ {Number(item.despesa).toLocaleString('pt-BR')}</td>
                  <td style={{ fontWeight: 700, color: item.prejuizo ? 'var(--danger)' : 'white' }}>
                    R$ {Number(item.lucro_liquido).toLocaleString('pt-BR')}
                  </td>
                  <td>
                    {item.roi ? (
                      <span className={`roi-tag ${item.roi > 0.5 ? 'high' : ''}`}>
                        {(item.roi * 100).toFixed(1)}%
                      </span>
                    ) : '-'}
                  </td>
                  <td>
                    {item.prejuizo ? (
                      <div className="alert-badge"><AlertCircle size={12} /> Alerta Prejuízo</div>
                    ) : (
                      <div className="success-badge"><TrendingUp size={12} /> Saudável</div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <style jsx>{`
        .view-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        .date-filters { display: flex; align-items: center; gap: 15px; padding: 10px 20px; border-radius: 12px; }
        .filter-item { display: flex; align-items: center; gap: 8px; }
        .filter-item input { background: none; border: none; color: white; outline: none; font-size: 0.9rem; cursor: pointer; }
        .separator { color: var(--text-muted); font-size: 0.8rem; }
        .custom-table { width: 100%; border-collapse: collapse; }
        .custom-table th { text-align: left; padding: 15px 20px; color: var(--text-muted); font-size: 0.85rem; border-bottom: 1px solid var(--glass-border); }
        .custom-table td { padding: 15px 20px; border-bottom: 1px solid var(--glass-border); font-size: 0.9rem; }
        .text-accent { color: var(--accent); }
        .text-danger { color: var(--danger); }
        .roi-tag { background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
        .roi-tag.high { color: var(--accent); background: rgba(16, 185, 129, 0.1); }
        .alert-badge { display: flex; align-items: center; gap: 5px; color: var(--danger); font-size: 0.75rem; font-weight: 600; }
        .success-badge { display: flex; align-items: center; gap: 5px; color: var(--accent); font-size: 0.75rem; font-weight: 600; }
      `}</style>
    </div>
  );
};

export default MetricsView;
