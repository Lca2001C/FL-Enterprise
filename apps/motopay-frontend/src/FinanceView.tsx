import { useState, useEffect } from 'react';
import { ArrowUpCircle, ArrowDownCircle, Download } from 'lucide-react';
import { useAuth } from './AuthContext';
import type { FinanceiroOut } from './apiTypes';

const FinanceView = () => {
  const { api } = useAuth();
  const [entries, setEntries] = useState<FinanceiroOut[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchFinance = async () => {
    setLoading(true);
    try {
      const r = await api.get<FinanceiroOut[]>('/api/v1/financeiro');
      setEntries(r.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchFinance(); }, []);

  return (
    <div className="view-container animate-fade">
      <div className="view-header">
        <div>
          <h2>Movimentação Financeira</h2>
          <p className="text-muted">Histórico de entradas e saídas</p>
        </div>
        <button className="btn-primary">
          <Download size={20} /> Exportar Relatório
        </button>
      </div>

      <div className="glass table-container">
        <table className="custom-table">
          <thead>
            <tr>
              <th>Data</th>
              <th>Descrição</th>
              <th>Tipo</th>
              <th>Valor</th>
              <th>Moto ID</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} style={{ textAlign: 'center', padding: '40px' }}>Carregando extrato...</td></tr>
            ) : entries.map(e => (
              <tr key={e.id}>
                <td>{new Date(e.data).toLocaleDateString('pt-BR')}</td>
                <td style={{ maxWidth: '300px' }}>{e.descricao}</td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: e.tipo === 'receita' ? 'var(--accent)' : 'var(--danger)' }}>
                    {e.tipo === 'receita' ? <ArrowUpCircle size={16} /> : <ArrowDownCircle size={16} />}
                    {e.tipo.toUpperCase()}
                  </div>
                </td>
                <td style={{ fontWeight: 700 }}>
                  R$ {Number(e.valor).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                </td>
                <td className="text-muted">#{e.moto_id || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <style jsx>{`
        .view-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        .custom-table { width: 100%; border-collapse: collapse; }
        .custom-table th { text-align: left; padding: 15px 20px; color: var(--text-muted); font-size: 0.85rem; border-bottom: 1px solid var(--glass-border); }
        .custom-table td { padding: 15px 20px; border-bottom: 1px solid var(--glass-border); font-size: 0.9rem; }
      `}</style>
    </div>
  );
};

export default FinanceView;
