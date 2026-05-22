import { useState, useEffect, type FormEvent } from 'react';
import { MessageSquare, RotateCcw, Save, Percent, ShieldCheck, Eye, CreditCard } from 'lucide-react';
import { useAuth } from './AuthContext';
import type { OperacaoConfig, TelegramTemplateMeta, TelegramTemplatePreviewOut } from './apiTypes';
import { parseApiError } from './utils/apiError';
import ErrorBanner from './components/ErrorBanner';
import AdminCustomMessagesPanel from './components/AdminCustomMessagesPanel';

const GROUP_LABELS: Record<string, string> = {
  notificacoes: 'Notificações automáticas',
  bot: 'Comandos do bot',
};

const SettingsView = () => {
  const { api, user, operacaoScopeId } = useAuth();
  const [config, setConfig] = useState<OperacaoConfig>({
    nome: '',
    multa_fixa_percentual: 0,
    juros_diario_percentual: 0,
    telegram_templates: {},
    telegram_custom_messages: [],
    payment_provider: 'asaas',
  });
  const [mpToken, setMpToken] = useState('');
  const [templateMeta, setTemplateMeta] = useState<TelegramTemplateMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState<string | null>(null);
  const [previewResult, setPreviewResult] = useState<{ key: string; text: string } | null>(null);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');

  const isAdmin = user?.tipo === 'admin';
  const isDono = user?.tipo === 'dono';
  const adminTargetId = isAdmin && operacaoScopeId != null && operacaoScopeId > 0 ? operacaoScopeId : null;

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(''), 4000);
  };

  const fetchConfig = async () => {
    setLoading(true);
    try {
      const metaRes = await api.get<TelegramTemplateMeta[]>('/api/v1/operacoes/telegram-template-meta');
      setTemplateMeta(metaRes.data);

      if (isAdmin) {
        if (adminTargetId == null) {
          setConfig({
            nome: '',
            multa_fixa_percentual: 0,
            juros_diario_percentual: 0,
            telegram_templates: {},
            telegram_custom_messages: [],
            payment_provider: 'asaas',
          });
          setMpToken('');
          setLoading(false);
          return;
        }
        const r = await api.get<OperacaoConfig>(`/api/v1/operacoes/${adminTargetId}`);
        setConfig({
          ...r.data,
          payment_provider: r.data.payment_provider ?? 'asaas',
          telegram_custom_messages: r.data.telegram_custom_messages ?? [],
        });
        setMpToken('');
      } else {
        const r = await api.get<OperacaoConfig>('/api/v1/operacoes/me');
        setConfig({
          nome: r.data.nome,
          multa_fixa_percentual: r.data.multa_fixa_percentual,
          juros_diario_percentual: r.data.juros_diario_percentual,
          telegram_templates: r.data.telegram_templates,
          telegram_custom_messages: [],
          payment_provider: r.data.payment_provider ?? 'asaas',
        });
        setMpToken('');
      }
    } catch (e) {
      setError(parseApiError(e, 'Erro ao carregar configurações'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchConfig();
  }, [user?.tipo, adminTargetId, api]);

  const buildPatchBody = () => {
    if (isDono) {
      return {
        multa_fixa_percentual: config.multa_fixa_percentual,
        juros_diario_percentual: config.juros_diario_percentual,
        telegram_templates: config.telegram_templates,
      };
    }
    const body: Record<string, unknown> = {
      nome: config.nome,
      multa_fixa_percentual: config.multa_fixa_percentual,
      juros_diario_percentual: config.juros_diario_percentual,
      telegram_templates: config.telegram_templates,
      telegram_custom_messages: config.telegram_custom_messages,
      payment_provider: config.payment_provider,
    };
    if (mpToken.trim()) {
      body.mercadopago_access_token = mpToken.trim();
    }
    return body;
  };

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      if (isAdmin) {
        if (adminTargetId == null) {
          showToast('Selecione uma operação no topo da página.');
          return;
        }
        await api.patch(`/api/v1/operacoes/${adminTargetId}`, buildPatchBody());
      } else {
        await api.patch('/api/v1/operacoes/me', buildPatchBody());
      }
      showToast('Configurações salvas com sucesso!');
    } catch (e) {
      setError(parseApiError(e, 'Erro ao salvar configurações'));
    } finally {
      setSaving(false);
    }
  };

  const updateTemplate = (key: string, value: string) => {
    setConfig((prev) => ({
      ...prev,
      telegram_templates: { ...prev.telegram_templates, [key]: value },
    }));
  };

  const restoreTemplate = (key: string) => {
    const meta = templateMeta.find((m) => m.key === key);
    if (!meta) return;
    updateTemplate(key, meta.default);
  };

  const restoreAllTemplates = () => {
    const defaults = Object.fromEntries(templateMeta.map((m) => [m.key, m.default]));
    setConfig((prev) => ({ ...prev, telegram_templates: defaults }));
  };

  const handlePreview = async (key: string) => {
    setPreviewing(key);
    setError('');
    try {
      const template = config.telegram_templates[key] ?? templateMeta.find((m) => m.key === key)?.default;
      const r = await api.post<TelegramTemplatePreviewOut>('/api/v1/operacoes/telegram-template-preview', {
        key,
        template,
      });
      setPreviewResult({ key, text: r.data.text });
    } catch (e) {
      setError(parseApiError(e, 'Erro ao pré-visualizar template'));
    } finally {
      setPreviewing(null);
    }
  };

  const groupedMeta = templateMeta.reduce<Record<string, TelegramTemplateMeta[]>>((acc, item) => {
    if (!acc[item.group]) acc[item.group] = [];
    acc[item.group].push(item);
    return acc;
  }, {});

  if (loading) return <div className="animate-pulse">Carregando configurações...</div>;

  if (isAdmin && adminTargetId == null) {
    return (
      <div className="view-container animate-fade" data-tour="settings-billing">
        <div className="view-header">
          <div>
            <h2>Ajustes da Operação</h2>
            <p className="text-muted">
              Selecione uma operação no seletor do topo para carregar e editar as configurações.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="view-container animate-fade">
      <div className="view-header">
        <div>
          <h2>Ajustes da Operação</h2>
          <p className="text-muted">
            {isDono
              ? 'Configure multas, juros e mensagens do Telegram'
              : 'Configure regras de cobrança, gateway e mensagens do Telegram'}
          </p>
        </div>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}
      {toast && <div className="toast success">{toast}</div>}

      <div className="glass card" style={{ maxWidth: '720px' }}>
        <form onSubmit={handleSave}>
          {isAdmin && (
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
                  onChange={(e) => setConfig({ ...config, nome: e.target.value })}
                />
              </div>
            </div>
          )}

          {isAdmin && (
            <div className="settings-section" style={{ marginTop: 40 }}>
              <h3 style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
                <CreditCard size={20} color="var(--primary)" /> Gateway de pagamento
              </h3>
              <div className="input-group">
                <label className="input-label">Provedor</label>
                <select
                  className="input-field"
                  value={config.payment_provider}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      payment_provider: e.target.value as 'asaas' | 'mercadopago',
                    })
                  }
                >
                  <option value="asaas">Asaas</option>
                  <option value="mercadopago">Mercado Pago</option>
                </select>
              </div>
              {config.payment_provider === 'mercadopago' && (
                <div className="input-group">
                  <label className="input-label">Access Token Mercado Pago</label>
                  <input
                    type="password"
                    className="input-field"
                    value={mpToken}
                    onChange={(e) => setMpToken(e.target.value)}
                    placeholder="Deixe em branco para manter o token atual"
                    autoComplete="off"
                  />
                  <small className="text-muted">
                    O token não é exibido após salvar. Informe novamente apenas para alterar.
                  </small>
                </div>
              )}
            </div>
          )}

          <div className="settings-section" style={{ marginTop: isDono ? 0 : 40 }} data-tour="settings-billing">
            <h3 style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
              <Percent size={20} color="var(--warning)" /> Regras de Multa e Juros
            </h3>
            <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: 20 }}>
              Essas taxas serão aplicadas automaticamente em todas as cobranças que ultrapassarem o vencimento.
            </p>

            <div className="fee-grid">
              <div className="input-group">
                <label className="input-label">Multa Fixa (%)</label>
                <div className="input-suffix-wrap">
                  <input
                    type="number"
                    step="0.01"
                    className="input-field"
                    value={config.multa_fixa_percentual}
                    onChange={(e) =>
                      setConfig({ ...config, multa_fixa_percentual: parseFloat(e.target.value) })
                    }
                  />
                  <span className="input-suffix">%</span>
                </div>
                <small className="text-muted">Aplicada uma única vez no atraso</small>
              </div>

              <div className="input-group">
                <label className="input-label">Juros Diários (%)</label>
                <div className="input-suffix-wrap">
                  <input
                    type="number"
                    step="0.01"
                    className="input-field"
                    value={config.juros_diario_percentual}
                    onChange={(e) =>
                      setConfig({ ...config, juros_diario_percentual: parseFloat(e.target.value) })
                    }
                  />
                  <span className="input-suffix">%</span>
                </div>
                <small className="text-muted">Acumulado por dia de atraso</small>
              </div>
            </div>
          </div>

          <div className="settings-section" style={{ marginTop: 40 }}>
            <div className="section-title-row">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: 10, margin: 0 }}>
                <MessageSquare size={20} color="var(--primary)" /> Mensagens Telegram
              </h3>
              <button
                type="button"
                className="btn-secondary"
                onClick={restoreAllTemplates}
                style={{ display: 'flex', alignItems: 'center', gap: 8 }}
              >
                <RotateCcw size={16} /> Restaurar todos
              </button>
            </div>
            <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: 24 }}>
              Textos enviados pelo bot e pelas notificações automáticas. Use placeholders como{' '}
              <code>{'{placa}'}</code> ou <code>{'{valor_total}'}</code> onde indicado.
            </p>

            {Object.entries(groupedMeta).map(([group, items]) => (
              <div key={group} style={{ marginBottom: 32 }}>
                <h4 style={{ fontFamily: 'Outfit', marginBottom: 16 }}>{GROUP_LABELS[group] ?? group}</h4>
                {items.map((meta) => {
                  const value = config.telegram_templates[meta.key] ?? meta.default;
                  const isCustom = value !== meta.default;
                  return (
                    <div key={meta.key} className="input-group" style={{ marginBottom: 20 }}>
                      <div className="section-title-row" style={{ marginBottom: 6 }}>
                        <label className="input-label" style={{ marginBottom: 0 }}>
                          {meta.label}
                          {isCustom && (
                            <span className="text-muted" style={{ fontWeight: 400, marginLeft: 8 }}>
                              (personalizado)
                            </span>
                          )}
                        </label>
                        <div style={{ display: 'flex', gap: 8 }}>
                          <button
                            type="button"
                            className="btn-secondary"
                            disabled={previewing === meta.key}
                            onClick={() => void handlePreview(meta.key)}
                            style={{ fontSize: '0.8rem', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: 6 }}
                          >
                            <Eye size={14} />
                            {previewing === meta.key ? '...' : 'Pré-visualizar'}
                          </button>
                          <button
                            type="button"
                            className="btn-secondary"
                            onClick={() => restoreTemplate(meta.key)}
                            style={{ fontSize: '0.8rem', padding: '4px 10px' }}
                          >
                            Restaurar padrão
                          </button>
                        </div>
                      </div>
                      <textarea
                        className="input-field"
                        rows={meta.key === 'overdue_body' ? 5 : 3}
                        value={value}
                        onChange={(e) => updateTemplate(meta.key, e.target.value)}
                      />
                      {previewResult?.key === meta.key && (
                        <div className="preview-box">
                          <strong>Pré-visualização:</strong>
                          <pre>{previewResult.text}</pre>
                        </div>
                      )}
                      <small className="text-muted">
                        {meta.description}
                        {meta.placeholders.length > 0 && (
                          <> Placeholders: {meta.placeholders.map((p) => `{${p}}`).join(', ')}.</>
                        )}
                      </small>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>

          {isAdmin && (
            <AdminCustomMessagesPanel
              api={api}
              config={config}
              setConfig={setConfig}
              onError={setError}
            />
          )}

          <div className="form-footer">
            <button
              type="submit"
              className="btn-primary"
              disabled={saving}
              style={{ display: 'flex', alignItems: 'center', gap: 10 }}
            >
              <Save size={20} /> {saving ? 'Salvando...' : 'Salvar Alterações'}
            </button>
          </div>
        </form>
      </div>

      <style jsx>{`
        .settings-section h3 {
          font-family: 'Outfit';
          font-size: 1.1rem;
        }
        .input-group {
          margin-bottom: 15px;
        }
        .section-title-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 20px;
          flex-wrap: wrap;
        }
        .fee-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
        }
        .input-suffix-wrap {
          position: relative;
        }
        .input-suffix-wrap .input-field {
          padding-right: 35px;
        }
        .input-suffix {
          position: absolute;
          right: 15px;
          top: 12px;
          color: var(--text-muted);
        }
        .btn-secondary {
          background: var(--secondary);
          color: white;
          border: none;
          padding: 8px 14px;
          border-radius: 8px;
          cursor: pointer;
        }
        .toast {
          padding: 12px 16px;
          border-radius: 8px;
          margin-bottom: 16px;
          font-size: 0.9rem;
        }
        .toast.success {
          background: rgba(16, 185, 129, 0.1);
          color: var(--accent);
          border: 1px solid rgba(16, 185, 129, 0.2);
        }
        .preview-box {
          margin-top: 10px;
          padding: 12px;
          background: rgba(0, 0, 0, 0.2);
          border-radius: 8px;
          border: 1px solid var(--glass-border);
          font-size: 0.85rem;
        }
        .preview-box pre {
          margin-top: 8px;
          white-space: pre-wrap;
          font-family: inherit;
        }
        .form-footer {
          margin-top: 40px;
          border-top: 1px solid var(--glass-border);
          padding-top: 20px;
          display: flex;
          justify-content: flex-end;
        }
        @media (max-width: 640px) {
          .fee-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
};

export default SettingsView;
