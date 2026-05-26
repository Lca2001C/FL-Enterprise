import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { Activity, AlertTriangle, Clock, Layers, Server, Wifi, WifiOff } from 'lucide-react';
import { useAuth } from './AuthContext';
import type { CelerySummary } from './apiTypes';
import { parseApiError } from './utils/apiError';
import ErrorBanner from './components/ErrorBanner';

const OpsDashboardView = () => {
  const { api } = useAuth();
  const [summary, setSummary] = useState<CelerySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchSummary = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get<CelerySummary>('/api/v1/ops/celery/summary');
      setSummary(r.data);
      setError('');
    } catch (e) {
      setError(parseApiError(e, 'Erro ao carregar filas Celery'));
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    void fetchSummary();
    const id = setInterval(() => void fetchSummary(), 15000);
    return () => clearInterval(id);
  }, [fetchSummary]);

  const backlog = summary?.queue_backlog ?? {};
  const totalBacklog = Object.values(backlog).reduce((a, b) => a + b, 0);

  return (
    <div className="view-container animate-fade">
      <div className="view-header">
        <div>
          <h2>Operações — Filas Celery</h2>
          <p className="text-muted">Monitoramento de workers, backlog e dead letter queue</p>
        </div>
        <button type="button" className="btn-primary" onClick={() => void fetchSummary()} disabled={loading}>
          {loading ? 'Atualizando...' : 'Atualizar'}
        </button>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

      <div className="stats-grid">
        <StatCard
          icon={<Server size={22} />}
          label="Workers online"
          value={String(summary?.workers_online ?? '—')}
          tone={summary && summary.workers_online > 0 ? 'ok' : 'danger'}
        />
        <StatCard
          icon={<Activity size={22} />}
          label="Tasks ativas"
          value={String(summary?.active_tasks ?? '—')}
        />
        <StatCard
          icon={<Layers size={22} />}
          label="Backlog total"
          value={String(totalBacklog)}
          tone={totalBacklog > 50 ? 'warn' : 'ok'}
        />
        <StatCard
          icon={<AlertTriangle size={22} />}
          label="DLQ"
          value={String(summary?.dlq_size ?? '—')}
          tone={(summary?.dlq_size ?? 0) > 0 ? 'warn' : 'ok'}
        />
        <StatCard
          icon={summary?.bot_online ? <Wifi size={22} /> : <WifiOff size={22} />}
          label="Bot Telegram"
          value={summary?.bot_online ? 'Online' : 'Offline'}
          tone={summary?.bot_online ? 'ok' : 'danger'}
        />
        <StatCard
          icon={<Clock size={22} />}
          label="Tasks travadas"
          value={String(summary?.stuck_tasks?.length ?? 0)}
          tone={(summary?.stuck_tasks?.length ?? 0) > 0 ? 'warn' : 'ok'}
        />
      </div>

      <div className="glass card section">
        <h3>Backlog por fila</h3>
        {Object.keys(backlog).length === 0 ? (
          <p className="text-muted">Nenhuma fila com backlog registrado.</p>
        ) : (
          <table className="ops-table">
            <thead>
              <tr>
                <th>Fila</th>
                <th>Pendentes (Redis)</th>
                <th>Ativas (workers)</th>
              </tr>
            </thead>
            <tbody>
              {Object.keys({ ...backlog, ...(summary?.queue_active ?? {}) }).map((q) => (
                <tr key={q}>
                  <td>{q}</td>
                  <td>{backlog[q] ?? 0}</td>
                  <td>{summary?.queue_active?.[q] ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {(summary?.stuck_tasks?.length ?? 0) > 0 && (
        <div className="glass card section warn">
          <h3>Tasks possivelmente travadas</h3>
          <ul>
            {summary!.stuck_tasks.map((t) => (
              <li key={t.task_id}>
                <strong>{t.task_name}</strong> — {t.seconds_running}s em {t.worker}
              </li>
            ))}
          </ul>
        </div>
      )}

      <style jsx>{`
        .view-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 16px;
          margin-bottom: 20px;
          flex-wrap: wrap;
        }
        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
          gap: 16px;
          margin-bottom: 20px;
        }
        .stat-card {
          padding: 18px;
          border-radius: 12px;
          border: 1px solid var(--glass-border);
        }
        .stat-card.ok {
          border-color: rgba(16, 185, 129, 0.3);
        }
        .stat-card.warn {
          border-color: rgba(245, 158, 11, 0.4);
        }
        .stat-card.danger {
          border-color: rgba(239, 68, 68, 0.4);
        }
        .stat-label {
          font-size: 0.85rem;
          color: var(--text-muted);
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 8px;
        }
        .stat-value {
          font-size: 1.5rem;
          font-weight: 700;
        }
        .section {
          padding: 20px;
          margin-bottom: 16px;
        }
        .section.warn {
          border: 1px solid rgba(245, 158, 11, 0.3);
        }
        .ops-table {
          width: 100%;
          border-collapse: collapse;
        }
        .ops-table th,
        .ops-table td {
          text-align: left;
          padding: 10px 12px;
          border-bottom: 1px solid var(--glass-border);
        }
      `}</style>
    </div>
  );
};

function StatCard({
  icon,
  label,
  value,
  tone = 'ok',
}: {
  icon: ReactNode;
  label: string;
  value: string;
  tone?: 'ok' | 'warn' | 'danger';
}) {
  return (
    <div className={`glass stat-card ${tone}`}>
      <div className="stat-label">
        {icon} {label}
      </div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

export default OpsDashboardView;
