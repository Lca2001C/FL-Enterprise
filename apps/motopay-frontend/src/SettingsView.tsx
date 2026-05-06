import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Settings, Save, Percent, Calendar, ShieldCheck } from 'lucide-react';
import { useAuth } from './AuthContext';

const SettingsView = () => {
  const { apiBase, token } = useAuth();
  const [config, setConfig] = useState({
    nome: '',
    multa_fixa_percentual: 0,
    juros_diario_percentual: 0
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchConfig = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${apiBase}/api/v1/operacoes/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setConfig(r.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchConfig(); }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await axios.patch(`${apiBase}/api/v1/operacoes/me`, config, {
        headers: { Authorization: `Bearer ${token}` }
      });
      alert("Configurações salvas com sucesso!");
    } catch (e) {
      alert("Erro ao salvar configurações.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="animate-pulse">Carregando configurações...</div>;

  return (
    <div className="view-container animate-fade">
      <div className="view-header">
        <div>
          <h2>Ajustes da Operação</h2>
          <p className="text-muted">Configure as regras de negócio e cobrança</p>
        </div>
      </div>

      <div className="glass card" style={{ maxWidth: '600px' }}>
        <form onSubmit={handleSave}>
          <div className="settings-section">
            <h3 style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
              <ShieldCheck size={20} color="var(--primary)" /> Identificação
            </h3>
            <div className="input-group">
              <label className="input-label">Nome da Operação</label>
              <input 
                type="text" 
                className="input-field"
                value={config.nome}
                onChange={e => setConfig({...config, nome: e.target.value})}
              />
            </div>
          </div>

          <div className="settings-section" style={{ marginTop: 40 }}>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
              <Percent size={20} color="var(--warning)" /> Regras de Multa e Juros
            </h3>
            <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: 20 }}>
              Essas taxas serão aplicadas automaticamente em todas as cobranças que ultrapassarem o vencimento.
            </p>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
              <div className="input-group">
                <label className="input-label">Multa Fixa (%)</label>
                <div style={{ position: 'relative' }}>
                  <input 
                    type="number" 
                    step="0.01"
                    className="input-field"
                    value={config.multa_fixa_percentual}
                    onChange={e => setConfig({...config, multa_fixa_percentual: parseFloat(e.target.value)})}
                    style={{ paddingRight: '35px' }}
                  />
                  <span style={{ position: 'absolute', right: 15, top: 12, color: 'var(--text-muted)' }}>%</span>
                </div>
                <small className="text-muted">Aplicada uma única vez no atraso</small>
              </div>

              <div className="input-group">
                <label className="input-label">Juros Diários (%)</label>
                <div style={{ position: 'relative' }}>
                  <input 
                    type="number" 
                    step="0.01"
                    className="input-field"
                    value={config.juros_diario_percentual}
                    onChange={e => setConfig({...config, juros_diario_percentual: parseFloat(e.target.value)})}
                    style={{ paddingRight: '35px' }}
                  />
                  <span style={{ position: 'absolute', right: 15, top: 12, color: 'var(--text-muted)' }}>%</span>
                </div>
                <small className="text-muted">Acumulado por dia de atraso</small>
              </div>
            </div>
          </div>

          <div style={{ marginTop: 40, borderTop: '1px solid var(--glass-border)', paddingTop: 20, display: 'flex', justifyContent: 'flex-end' }}>
            <button type="submit" className="btn-primary" disabled={saving} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <Save size={20} /> {saving ? 'Salvando...' : 'Salvar Alterações'}
            </button>
          </div>
        </form>
      </div>

      <style jsx>{`
        .settings-section h3 { font-family: 'Outfit'; font-size: 1.1rem; }
        .input-group { margin-bottom: 15px; }
      `}</style>
    </div>
  );
};

export default SettingsView;
