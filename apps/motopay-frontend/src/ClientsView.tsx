import { useState, useEffect, type FormEvent } from 'react';
import { Plus, Search, Star, Phone, CreditCard, Trash2, Bike } from 'lucide-react';
import { useAuth } from './AuthContext';
import type { ClienteOut } from './apiTypes';

const ClientsView = () => {
  const { api } = useAuth();
  const [clientes, setClientes] = useState<ClienteOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({ nome: '', cpf: '', telefone: '', telegram_id: '' });

  const fetchClientes = async () => {
    setLoading(true);
    try {
      const r = await api.get<ClienteOut[]>('/api/v1/clientes');
      setClientes(r.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchClientes(); }, []);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/api/v1/clientes', formData);
      setShowModal(false);
      setFormData({ nome: '', cpf: '', telefone: '', telegram_id: '' });
      fetchClientes();
    } catch (e) {
      alert("Erro ao cadastrar cliente");
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Deseja realmente excluir este cliente?")) return;
    try {
      await api.delete(`/api/v1/clientes/${id}`);
      fetchClientes();
    } catch (e) {
      alert("Erro ao excluir cliente. Verifique se há contratos ativos.");
    }
  };

  return (
    <div className="view-container animate-fade">
      <div className="view-header">
        <div>
          <h2>Base de Clientes</h2>
          <p className="text-muted">{clientes.length} motoristas parceiros</p>
        </div>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={20} /> Novo Cliente
        </button>
      </div>

      <div className="table-actions glass">
        <div className="search-box">
          <Search size={18} />
          <input type="text" placeholder="Buscar por nome ou CPF..." />
        </div>
      </div>

      <div className="glass table-container">
        <table className="custom-table">
          <thead>
            <tr>
              <th>Nome</th>
              <th>CPF</th>
              <th>Telefone</th>
              <th>Score</th>
              <th style={{ textAlign: 'right' }}>Ações</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} style={{ textAlign: 'center', padding: '40px' }}>Carregando clientes...</td></tr>
            ) : clientes.map(c => (
              <tr key={c.id}>
                <td>
                  <div style={{ fontWeight: 600 }}>{c.nome}</div>
                  {c.moto_placa && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--primary)', display: 'flex', alignItems: 'center', gap: 4 }}>
                      <Bike size={12} /> {c.moto_placa} - {c.moto_modelo}
                    </div>
                  )}
                </td>
                <td className="text-muted">{c.cpf}</td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Phone size={14} color="#94a3b8" /> {c.telefone}
                  </div>
                </td>
                <td>
                  <div className="score-badge">
                    <Star size={12} fill={c.score > 80 ? "#10b981" : "#f59e0b"} stroke="none" />
                    {c.score} pts
                  </div>
                </td>
                <td style={{ textAlign: 'right' }}>
                  <button className="icon-btn"><CreditCard size={16} /></button>
                  <button className="icon-btn danger" onClick={() => handleDelete(c.id)}><Trash2 size={16} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="glass modal-content animate-fade">
            <h3>Cadastrar Novo Cliente</h3>
            <form onSubmit={handleCreate}>
              <div className="input-group">
                <label className="input-label">Nome Completo</label>
                <input 
                  className="input-field" 
                  value={formData.nome}
                  onChange={e => setFormData({...formData, nome: e.target.value})}
                  required
                />
              </div>
              <div className="input-group">
                <label className="input-label">CPF</label>
                <input 
                  className="input-field" 
                  value={formData.cpf}
                  onChange={e => setFormData({...formData, cpf: e.target.value})}
                  placeholder="000.000.000-00"
                  required
                />
              </div>
              <div className="input-group">
                <label className="input-label">Telefone (WhatsApp)</label>
                <input 
                  className="input-field" 
                  value={formData.telefone}
                  onChange={e => setFormData({...formData, telefone: e.target.value})}
                  placeholder="(00) 00000-0000"
                  required
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>Cancelar</button>
                <button type="submit" className="btn-primary">Salvar Cliente</button>
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
        .custom-table { width: 100%; border-collapse: collapse; }
        .custom-table th { text-align: left; padding: 15px 20px; color: var(--text-muted); font-size: 0.85rem; border-bottom: 1px solid var(--glass-border); }
        .custom-table td { padding: 15px 20px; border-bottom: 1px solid var(--glass-border); font-size: 0.9rem; }
        .score-badge { display: flex; alignItems: center; gap: 6px; background: rgba(255,255,255,0.05); padding: 4px 10px; border-radius: 20px; width: fit-content; font-size: 0.8rem; font-weight: 600; }
        .icon-btn { background: none; border: none; color: var(--text-muted); cursor: pointer; padding: 5px; transition: 0.2s; }
        .icon-btn:hover { color: var(--primary); }
        .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 1000; backdrop-filter: blur(4px); }
        .modal-content { width: 100%; max-width: 450px; padding: 30px; }
        .modal-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 20px; }
        .btn-secondary { background: var(--secondary); color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-family: 'Outfit'; }
      `}</style>
    </div>
  );
};

export default ClientsView;
