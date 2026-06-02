import { useState, useEffect, type FormEvent } from 'react';
import { MessageSquare, RotateCcw, Save, Percent, ShieldCheck, Eye, CreditCard, Plus, Trash2 } from 'lucide-react';
import { useAuth } from './AuthContext';
import {
  BOT_MENU_BUILTIN_COMMANDS,
  isBuiltinBotMenuCommand,
  type OperacaoConfig,
  type TelegramBotMenuButton,
  type TelegramTemplateMeta,
  type PaymentsConfig,
  type TelegramTemplatePreviewOut,
} from './apiTypes';
import { parseApiError } from './utils/apiError';
import ErrorBanner from './components/ErrorBanner';
import AdminCustomMessagesPanel from './components/AdminCustomMessagesPanel';

const GROUP_LABELS: Record<string, string> = {
  notificacoes: 'Notificações automáticas',
  bot: 'Comandos do bot',
};


const DEFAULT_BOT_MENU_CONTACT_BUTTON: TelegramBotMenuButton = {
  label: 'Quero falar com alguém',
  command: 'contato',
  response: 'Entendido, {cliente}. Nossa equipe entrará em contato em breve.',
};

const DEFAULT_BOT_MENU_BUTTONS: TelegramBotMenuButton[] = [
  { label: 'Status', command: 'status' },
  { label: 'Pix', command: 'pix' },
  { label: 'Ajuda', command: 'ajuda' },
  DEFAULT_BOT_MENU_CONTACT_BUTTON,
];

const SettingsView = () => {
  const { api, user, operacaoScopeId } = useAuth();
  const [config, setConfig] = useState<OperacaoConfig>({
    nome: '',
    multa_fixa_percentual: 0,
    juros_diario_percentual: 0,
    telegram_templates: {},
    telegram_custom_messages: [],
    telegram_bot_menu_buttons: DEFAULT_BOT_MENU_BUTTONS,
    telegram_owner_notify_id: null,
    telegram_owner_notify_enabled: false,
  });
  const [mpToken, setMpToken] = useState('');
  const [mpPublicKey, setMpPublicKey] = useState('');
  const [mpWebhookSecret, setMpWebhookSecret] = useState('');
  const [paymentsConfig, setPaymentsConfig] = useState<PaymentsConfig | null>(null);
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

  const fetchPaymentsConfig = async () => {
    if (isAdmin && adminTargetId == null) {
      setPaymentsConfig(null);
      return;
    }
    try {
      const params =
        isAdmin && adminTargetId != null ? { operacao_id: adminTargetId } : undefined;
      const r = await api.get<PaymentsConfig>('/api/v1/config/payments', { params });
      setPaymentsConfig(r.data);
    } catch {
      setPaymentsConfig(null);
    }
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
            telegram_bot_menu_buttons: DEFAULT_BOT_MENU_BUTTONS,
            telegram_owner_notify_id: null,
            telegram_owner_notify_enabled: false,
          });
          setMpToken('');
          setPaymentsConfig(null);
          setLoading(false);
          return;
        }
        const r = await api.get<OperacaoConfig>(`/api/v1/operacoes/${adminTargetId}`);
        setConfig({
          ...r.data,
          telegram_custom_messages: r.data.telegram_custom_messages ?? [],
          telegram_bot_menu_buttons: r.data.telegram_bot_menu_buttons ?? DEFAULT_BOT_MENU_BUTTONS,
          telegram_owner_notify_id: r.data.telegram_owner_notify_id ?? null,
          telegram_owner_notify_enabled: r.data.telegram_owner_notify_enabled ?? false,
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
          telegram_bot_menu_buttons: r.data.telegram_bot_menu_buttons ?? DEFAULT_BOT_MENU_BUTTONS,
          telegram_owner_notify_id: r.data.telegram_owner_notify_id ?? null,
          telegram_owner_notify_enabled: r.data.telegram_owner_notify_enabled ?? false,
        });
        setMpToken('');
      }
      await fetchPaymentsConfig();
    } catch (e) {
      setError(parseApiError(e, 'Erro ao carregar configurações'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchConfig();
  }, [user?.tipo, adminTargetId, api]);

  const appendMercadoPagoFields = (body: Record<string, unknown>) => {
    if (mpToken.trim()) body.mercadopago_access_token = mpToken.trim();
    if (mpPublicKey.trim()) body.mercadopago_public_key = mpPublicKey.trim();
    if (mpWebhookSecret.trim()) body.mercadopago_webhook_secret = mpWebhookSecret.trim();
  };

  const buildPatchBody = () => {
    if (isDono) {
      const body: Record<string, unknown> = {
        multa_fixa_percentual: config.multa_fixa_percentual,
        juros_diario_percentual: config.juros_diario_percentual,
        telegram_templates: config.telegram_templates,
        telegram_bot_menu_buttons: config.telegram_bot_menu_buttons,
        telegram_owner_notify_id: config.telegram_owner_notify_id,
        telegram_owner_notify_enabled: config.telegram_owner_notify_enabled,
      };
      appendMercadoPagoFields(body);
      return body;
    }
    const body: Record<string, unknown> = {
      nome: config.nome,
      multa_fixa_percentual: config.multa_fixa_percentual,
      juros_diario_percentual: config.juros_diario_percentual,
      telegram_templates: config.telegram_templates,
      telegram_custom_messages: config.telegram_custom_messages,
      telegram_bot_menu_buttons: config.telegram_bot_menu_buttons,
      telegram_owner_notify_id: config.telegram_owner_notify_id,
      telegram_owner_notify_enabled: config.telegram_owner_notify_enabled,
    };
    appendMercadoPagoFields(body);
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
    setConfig((prev) => ({
      ...prev,
      telegram_templates: defaults,
      telegram_bot_menu_buttons: DEFAULT_BOT_MENU_BUTTONS,
    }));
  };

  const updateMenuButton = (index: number, patch: Partial<TelegramBotMenuButton>) => {
    setConfig((prev) => ({
      ...prev,
      telegram_bot_menu_buttons: prev.telegram_bot_menu_buttons.map((btn, i) =>
        i === index ? { ...btn, ...patch } : btn
      ),
    }));
  };

  const addMenuButton = () => {
    setConfig((prev) => {
      if (prev.telegram_bot_menu_buttons.length >= 6) return prev;
      return {
        ...prev,
        telegram_bot_menu_buttons: [
          ...prev.telegram_bot_menu_buttons,
          { label: 'Novo botão', command: 'ajuda' },
        ],
      };
    });
  };

  const removeMenuButton = (index: number) => {
    setConfig((prev) => {
      if (prev.telegram_bot_menu_buttons.length <= 1) return prev;
      return {
        ...prev,
        telegram_bot_menu_buttons: prev.telegram_bot_menu_buttons.filter((_, i) => i !== index),
      };
    });
  };

  const restoreMenuButtons = () => {
    setConfig((prev) => ({ ...prev, telegram_bot_menu_buttons: DEFAULT_BOT_MENU_BUTTONS }));
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

          {(isAdmin || isDono) && paymentsConfig && (
            <div className="settings-section" style={{ marginTop: isAdmin ? 40 : 0 }}>
              <h3 style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                <CreditCard size={20} color="var(--primary)" /> Mercado Pago
              </h3>
              <ul className="mp-status-list" style={{ margin: '0 0 20px', paddingLeft: 18, fontSize: '0.9rem' }}>
                <li>
                  Modo API:{' '}
                  <strong>
                    {paymentsConfig.credentials_mode === 'test' ? 'Teste' : 'Produção'}
                  </strong>
                </li>
                <li>
                  Origem das credenciais:{' '}
                  <strong>
                    {paymentsConfig.mercadopago_credentials_source === 'operacao'
                      ? 'Conta desta operação'
                      : paymentsConfig.mercadopago_credentials_source === 'global'
                        ? 'Conta global (.env)'
                        : 'Não configurado'}
                  </strong>
                </li>
                <li>
                  Credenciais completas:{' '}
                  <strong>
                    {paymentsConfig.mercadopago_credentials_complete ? 'sim' : 'não'}
                  </strong>
                </li>
                <li>
                  Cobranças ativas:{' '}
                  <strong>{paymentsConfig.mercadopago_configured ? 'sim' : 'pendente'}</strong>
                </li>
                {paymentsConfig.webhook_url && (
                  <li>
                    URL do webhook (cadastre no painel MP):{' '}
                    <code style={{ fontSize: '0.8rem', wordBreak: 'break-all' }}>
                      {paymentsConfig.webhook_url}
                    </code>
                  </li>
                )}
              </ul>
              <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: 16 }}>
                Cada operação pode usar sua própria conta Mercado Pago. Preencha os três campos abaixo
                (Access Token, Public Key e Webhook Secret do painel da sua aplicação MP). Deixe em
                branco para manter o valor atual.
              </p>
              <div className="input-group">
                <label className="input-label">Access Token</label>
                <input
                  type="password"
                  className="input-field"
                  value={mpToken}
                  onChange={(e) => setMpToken(e.target.value)}
                  placeholder="Deixe em branco para manter"
                  autoComplete="off"
                />
              </div>
              <div className="input-group">
                <label className="input-label">Public Key</label>
                <input
                  type="password"
                  className="input-field"
                  value={mpPublicKey}
                  onChange={(e) => setMpPublicKey(e.target.value)}
                  placeholder={
                    paymentsConfig.mercadopago_public_key
                      ? 'Definida — deixe em branco para manter'
                      : 'Cole a Public Key do painel MP'
                  }
                  autoComplete="off"
                />
              </div>
              <div className="input-group">
                <label className="input-label">Webhook Secret</label>
                <input
                  type="password"
                  className="input-field"
                  value={mpWebhookSecret}
                  onChange={(e) => setMpWebhookSecret(e.target.value)}
                  placeholder="Secret exibido ao cadastrar o webhook no MP"
                  autoComplete="off"
                />
              </div>
              {!paymentsConfig.mercadopago_credentials_complete && (
                <p className="text-muted" style={{ fontSize: '0.85rem' }}>
                  {paymentsConfig.mercadopago_has_operacao_token
                    ? 'Há credenciais parciais desta operação — complete os três campos para ativar.'
                    : 'Configure as credenciais desta operação ou MERCADOPAGO_* no .env da API (conta global).'}
                </p>
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
                  const isBotStart = meta.key === 'bot_start';
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
                        rows={meta.key === 'overdue_body' ? 5 : isBotStart ? 6 : 3}
                        value={value}
                        onChange={(e) => updateTemplate(meta.key, e.target.value)}
                      />
                      {previewResult?.key === meta.key && (
                        <div className="preview-box">
                          <strong>Pré-visualização:</strong>
                          <pre>{previewResult.text}</pre>
                        </div>
                      )}
                      {isBotStart && (
                        <div className="menu-buttons-preview">
                          {config.telegram_bot_menu_buttons.map((btn) => (
                            <span key={btn.label} className="menu-button-chip">
                              {btn.label}
                            </span>
                          ))}
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

            <div style={{ marginBottom: 32 }}>
              <div className="section-title-row" style={{ marginBottom: 12 }}>
                <h4 style={{ fontFamily: 'Outfit', margin: 0 }}>Menu do bot — botões</h4>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={restoreMenuButtons}
                    style={{ fontSize: '0.8rem', padding: '4px 10px' }}
                  >
                    Restaurar padrão
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={addMenuButton}
                    disabled={config.telegram_bot_menu_buttons.length >= 6}
                    style={{
                      fontSize: '0.8rem',
                      padding: '4px 10px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                    }}
                  >
                    <Plus size={14} /> Adicionar
                  </button>
                </div>
              </div>
              <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: 16 }}>
                Botões exibidos no teclado do Telegram. Ao tocar, o bot executa o comando associado.
                Comandos personalizados também funcionam digitando /nome no chat.
              </p>
              {config.telegram_bot_menu_buttons.map((btn, index) => {
                const custom = !isBuiltinBotMenuCommand(btn.command);
                return (
                <div key={index} className="menu-button-row" style={{ flexDirection: 'column', alignItems: 'stretch', gap: 12 }}>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end' }}>
                  <div className="input-group" style={{ flex: 1, marginBottom: 0 }}>
                    <label className="input-label">Texto do botão</label>
                    <input
                      type="text"
                      className="input-field"
                      maxLength={32}
                      value={btn.label}
                      onChange={(e) => updateMenuButton(index, { label: e.target.value })}
                    />
                  </div>
                  <div className="input-group" style={{ flex: 1, marginBottom: 0 }}>
                    <label className="input-label">Comando</label>
                    <select
                      className="input-field"
                      value={custom ? '__custom__' : btn.command}
                      onChange={(e) => {
                        const value = e.target.value;
                        if (value === '__custom__') {
                          updateMenuButton(index, {
                            command: 'contato',
                            response:
                              'Entendido, {cliente}. Nossa equipe entrará em contato em breve.',
                          });
                          return;
                        }
                        updateMenuButton(index, { command: value, response: null });
                      }}
                    >
                      {BOT_MENU_BUILTIN_COMMANDS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                      <option value="__custom__">Personalizado…</option>
                    </select>
                  </div>
                  <button
                    type="button"
                    className="btn-icon-danger"
                    onClick={() => removeMenuButton(index)}
                    disabled={config.telegram_bot_menu_buttons.length <= 1}
                    title="Remover botão"
                  >
                    <Trash2 size={16} />
                  </button>
                  </div>
                  {custom && (
                    <>
                      <div className="input-group" style={{ marginBottom: 0 }}>
                        <label className="input-label">Nome do comando (sem /)</label>
                        <input
                          type="text"
                          className="input-field"
                          maxLength={31}
                          value={btn.command}
                          placeholder="ex.: horario, contato"
                          onChange={(e) =>
                            updateMenuButton(index, {
                              command: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''),
                            })
                          }
                        />
                      </div>
                      <div className="input-group" style={{ marginBottom: 0 }}>
                        <label className="input-label">Resposta do comando</label>
                        <textarea
                          className="input-field"
                          rows={3}
                          maxLength={2000}
                          value={btn.response ?? ''}
                          placeholder="Use {cliente}, {placa}, {proximo_vencimento}…"
                          onChange={(e) => updateMenuButton(index, { response: e.target.value })}
                        />
                      </div>
                    </>
                  )}
                </div>
              )})}
            </div>

            <div className="settings-card" style={{ marginTop: 24 }}>
              <h4 style={{ fontFamily: 'Outfit', margin: '0 0 8px' }}>Notificar dono no Telegram</h4>
              <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: 16 }}>
                Receba uma cópia no seu Telegram quando um locatário pedir contato ou tocar em um botão
                como &quot;Quero falar com alguém&quot;. Use o @userinfobot para descobrir seu ID.
              </p>
              <label className="checkbox-row" style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                <input
                  type="checkbox"
                  checked={config.telegram_owner_notify_enabled}
                  onChange={(e) =>
                    setConfig((prev) => ({
                      ...prev,
                      telegram_owner_notify_enabled: e.target.checked,
                    }))
                  }
                />
                <span>Ativar notificações de pedido de contato</span>
              </label>
              <div className="input-group" style={{ marginBottom: 0 }}>
                <label className="input-label">Seu Telegram ID</label>
                <input
                  type="text"
                  className="input-field"
                  value={config.telegram_owner_notify_id ?? ''}
                  placeholder="ID numérico (ex.: 987654321)"
                  disabled={!config.telegram_owner_notify_enabled}
                  onChange={(e) =>
                    setConfig((prev) => ({
                      ...prev,
                      telegram_owner_notify_id: e.target.value.trim() || null,
                    }))
                  }
                />
              </div>
            </div>
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
        .menu-buttons-preview {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 10px;
        }
        .menu-button-chip {
          display: inline-block;
          padding: 6px 12px;
          border-radius: 8px;
          background: rgba(99, 102, 241, 0.15);
          border: 1px solid rgba(99, 102, 241, 0.3);
          font-size: 0.85rem;
        }
        .menu-button-row {
          display: flex;
          align-items: flex-end;
          gap: 12px;
          margin-bottom: 12px;
        }
        .btn-icon-danger {
          background: transparent;
          border: 1px solid var(--glass-border);
          color: var(--danger, #ef4444);
          padding: 10px;
          border-radius: 8px;
          cursor: pointer;
          margin-bottom: 2px;
        }
        .btn-icon-danger:disabled {
          opacity: 0.4;
          cursor: not-allowed;
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
