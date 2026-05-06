import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Bike, Plus, Search, Filter, MoreVertical, Trash2, Edit2 } from 'lucide-react';
import { useAuth } from './AuthContext';

const FleetView = () => {
  const { apiBase, token } = useAuth();
  const [motos, setMotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({ placa: '', modelo: '', status: 'disponivel' });

  const fetchMotos = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${apiBase}/api/v1/motos`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMotos(r.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchMotos(); }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${apiBase}/api/v1/motos`, formData, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setShowModal(false);
      setFormData({ placa: '', modelo: '', status: 'disponivel' });
      fetchMotos();
    } catch (e) {
      alert("Erro ao cadastrar moto");
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Deseja realmente excluir esta moto?")) return;
    try {
      await axios.delete(`${apiBase}/api/v1/motos/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchMotos();
    } catch (e) {
      alert("Erro ao excluir moto. Verifique se há contratos ativos.");
    }
  };

  return (
    <div className="view-container animate-fade">
      <div className="view-header">
        <div>
          <h2>Gestão de Frota</h2>
          <p className="text-muted">Total de {motos.length} veículos cadastrados</p>
        </div>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={20} /> Nova Moto
        </button>
      </div>

      <div className="table-actions glass">
        <div className="search-box">
          <Search size={18} />
          <input type="text" placeholder="Buscar por placa ou modelo..." />
        </div>
        <button className="btn-secondary"><Filter size={18} /> Filtros</button>
      </div>

      <div className="glass table-container">
        <table className="custom-table">
          <thead>
            <tr>
              <th>Placa</th>
              <th>Modelo</th>
              <th>Status</th>
              <th>Motorista</th>
              <th style={{ textAlign: 'right' }}>Ações</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan="5" style={{ textAlign: 'center', padding: '40px' }}>Carregando frota...</td></tr>
            ) : motos.map(moto => (
              <tr key={moto.id}>
                <td className="font-mono">{moto.placa}</td>
                <td>{moto.modelo}</td>
                <td>
                  <span className={`status-badge ${moto.status}`}>
                    {moto.status.toUpperCase()}
                  </span>
                </td>
                <td className={moto.cliente_nome ? "text-primary" : "text-muted"}>
                  {moto.cliente_nome || "—"}
                </td>
                <td style={{ textAlign: 'right' }}>
                  <button className="icon-btn"><Edit2 size={16} /></button>
                  <button className="icon-btn danger" onClick={() => handleDelete(moto.id)}><Trash2 size={16} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="glass modal-content animate-fade">
            <h3>Cadastrar Nova Moto</h3>
            <form onSubmit={handleCreate}>
              <div className="input-group">
                <label className="input-label">Placa</label>
                <input 
                  className="input-field" 
                  value={formData.placa}
                  onChange={e => setFormData({...formData, placa: e.target.value.toUpperCase()})}
                  placeholder="ABC-1234"
                  required
                />
              </div>
              <div className="input-group">
                <label className="input-label">Modelo</label>
                <input 
                  className="input-field" 
                  value={formData.modelo}
                  onChange={e => setFormData({...formData, modelo: e.target.value})}
                  placeholder="Honda CG 160"
                  required
                />
              </div>
              <div className="input-group">
                <label className="input-label">Status Inicial</label>
                <select 
                  className="input-field" 
                  value={formData.status}
                  onChange={e => setFormData({...formData, status: e.target.value})}
                >
                  <option value="disponivel">Disponível</option>
                  <option value="manutencao">Manutenção</option>
                  <option value="inativa">Inativa</option>
                </select>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>Cancelar</button>
                <button type="submit" className="btn-primary">Salvar Moto</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <style jsx>{`
        .view-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        .table-actions { padding: 15px; display: flex; gap: 15px; margin-bottom: 20px; border-radius: 12px; }
        .search-box { flex: 1; display: flex; align-items: center; gap: 10px; background: rgba(0,0,0,0.2); padding: 0 15px; border-radius: 8px; border: 1px solid var(--glass-border); }
        .search-box input { background: none; border: none; color: white; width: 100%; padding: 10px 0; outline: none; }
        .table-container { overflow: hidden; }
        .custom-table { width: 100%; border-collapse: collapse; }
        .custom-table th { text-align: left; padding: 15px 20px; color: var(--text-muted); font-size: 0.85rem; border-bottom: 1px solid var(--glass-border); }
        .custom-table td { padding: 15px 20px; border-bottom: 1px solid var(--glass-border); font-size: 0.9rem; }
        .font-mono { font-family: monospace; font-weight: 600; letter-spacing: 1px; }
        .status-badge { padding: 4px 10px; border-radius: 6px; font-size: 0.7rem; font-weight: 700; }
        .status-badge.disponivel { background: rgba(16, 185, 129, 0.1); color: var(--accent); }
        .status-badge.alugada { background: rgba(99, 102, 241, 0.1); color: var(--primary); }
        .status-badge.manutencao { background: rgba(245, 158, 11, 0.1); color: var(--warning); }
        .status-badge.inativa { background: rgba(239, 68, 68, 0.1); color: var(--danger); }
        .icon-btn { background: none; border: none; color: var(--text-muted); cursor: pointer; padding: 5px; transition: 0.2s; }
        .icon-btn:hover { color: var(--primary); }
        .icon-btn.danger:hover { color: var(--danger); }
        .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 1000; backdrop-filter: blur(4px); }
        .modal-content { width: 100%; max-width: 450px; padding: 30px; }
        .modal-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 20px; }
        .btn-secondary { background: var(--secondary); color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-family: 'Outfit'; }
      `}</style>
    </div>
  );
};

export default FleetView;
