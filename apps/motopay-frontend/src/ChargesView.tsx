import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Receipt, Plus, Copy, CheckCircle, Clock, AlertTriangle, ExternalLink } from 'lucide-react';
import { useAuth } from './AuthContext';

const ChargesView = () => {
  const { apiBase, token } = useAuth();
  const [cobrancas, setCobrancas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [contratoId, setContratoId] = useState('');

  const fetchCobrancas = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${apiBase}/api/v1/cobrancas`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setCobrancas(r.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchCobrancas(); }, []);

  const handleCreateCharge = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${apiBase}/api/v1/cobrancas/manual`, { contrato_id: parseInt(contratoId) }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setShowModal(false);
      setContratoId('');
      fetchCobrancas();
    } catch (e) {
      alert("Erro ao gerar cobrança. Verifique o ID do contrato.");
    }
  };

  const copyPix = (text) => {
    navigator.clipboard.writeText(text);
    alert("Código PIX copiado!");
  };

  return (
    <div className="view-container animate-fade">
      <div className="view-header">
        <div>
          <h2>Gestão de Cobranças</h2>
          <p className="text-muted">Acompanhamento de pagamentos e faturamento</p>
        </div>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={20} /> Gerar Cobrança Avulsa
        </button>
      </div>

      <div className="glass table-container">
        <table className="custom-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Vencimento</th>
              <th>Valor</th>
              <th>Status</th>
              <th>Contrato</th>
              <th>Atraso / Multa</th>
              <th style={{ textAlign: 'right' }}>Ações</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan="6" style={{ textAlign: 'center', padding: '40px' }}>Carregando cobranças...</td></tr>
            ) : cobrancas.length === 0 ? (
              <tr><td colSpan="6" style={{ textAlign: 'center', padding: '40px' }}>Nenhuma cobrança encontrada.</td></tr>
            ) : cobrancas.map(cob => (
              <tr key={cob.id}>
                <td><span className="text-muted">#{cob.id}</span></td>
                <td>{new Date(cob.vencimento).toLocaleDateString('pt-BR')}</td>
                <td style={{ fontWeight: 700 }}>R$ {Number(cob.valor).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</td>
                <td>
                  <span className={`status-badge ${cob.status}`}>
                    {cob.status === 'recebido' ? <CheckCircle size={12} /> : cob.status === 'pendente' ? <Clock size={12} /> : <AlertTriangle size={12} />}
                    {cob.status.toUpperCase()}
                  </span>
                </td>
                <td><div className="contrato-tag">Doc #{cob.contrato_id}</div></td>
                <td>
                  {cob.dias_atraso > 0 ? (
                    <div style={{ fontSize: '0.8rem', color: 'var(--danger)' }}>
                      <div style={{ fontWeight: 700 }}>{cob.dias_atraso} dias</div>
                      <div>Total: R$ {Number(cob.valor_total).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</div>
                    </div>
                  ) : (
                    <span className="text-muted">—</span>
                  )}
                </td>
                <td style={{ textAlign: 'right' }}>
                  {cob.pix_copia_cola && cob.status === 'pendente' && (
                    <button className="action-btn-pix" onClick={() => copyPix(cob.pix_copia_cola)}>
                      <Copy size={14} /> PIX
                    </button>
                  )}
                  <button className="icon-btn"><ExternalLink size={16} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="glass modal-content animate-fade">
            <h3>Gerar Cobrança Manual</h3>
            <p className="text-muted" style={{ fontSize: '0.8rem', marginBottom: '20px' }}>
              Isso criará uma nova cobrança no Asaas para o contrato informado.
            </p>
            <form onSubmit={handleCreateCharge}>
              <div className="input-group">
                <label className="input-label">ID do Contrato</label>
                <input 
                  type="number"
                  className="input-field" 
                  value={contratoId}
                  onChange={e => setContratoId(e.target.value)}
                  placeholder="Ex: 12"
                  required
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>Cancelar</button>
                <button type="submit" className="btn-primary">Gerar no Asaas</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <style jsx>{`
        .view-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        .custom-table { width: 100%; border-collapse: collapse; }
        .custom-table th { text-align: left; padding: 15px 20px; color: var(--text-muted); font-size: 0.85rem; border-bottom: 1px solid var(--glass-border); }
        .custom-table td { padding: 15px 20px; border-bottom: 1px solid var(--glass-border); font-size: 0.9rem; }
        .status-badge { display: flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 6px; font-size: 0.7rem; font-weight: 700; width: fit-content; }
        .status-badge.recebido { background: rgba(16, 185, 129, 0.1); color: var(--accent); }
        .status-badge.pendente { background: rgba(245, 158, 11, 0.1); color: var(--warning); }
        .status-badge.atrasado { background: rgba(239, 68, 68, 0.1); color: var(--danger); }
        .contrato-tag { background: rgba(255,255,255,0.05); padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; border: 1px solid var(--glass-border); }
        .action-btn-pix { background: var(--primary-glow); color: var(--primary); border: 1px solid var(--primary); padding: 4px 10px; border-radius: 6px; cursor: pointer; font-size: 0.75rem; font-weight: 600; display: inline-flex; align-items: center; gap: 5px; margin-right: 8px; transition: 0.2s; }
        .action-btn-pix:hover { background: var(--primary); color: white; }
        .icon-btn { background: none; border: none; color: var(--text-muted); cursor: pointer; padding: 5px; transition: 0.2s; }
        .icon-btn:hover { color: var(--primary); }
        .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 1000; backdrop-filter: blur(4px); }
        .modal-content { width: 100%; max-width: 400px; padding: 30px; }
        .modal-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 20px; }
        .btn-secondary { background: var(--secondary); color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-family: 'Outfit'; }
      `}</style>
    </div>
  );
};

export default ChargesView;
