import { useState, useEffect, type Dispatch, type SetStateAction } from 'react';
import { Plus, Trash2, Pencil, Eye } from 'lucide-react';
import type { AxiosInstance } from 'axios';
import type {
  CustomMessageTriggerMeta,
  OperacaoConfig,
  TelegramCustomMessage,
  TelegramTemplatePreviewOut,
} from '../apiTypes';
import { parseApiError } from '../utils/apiError';

type Props = {
  api: AxiosInstance;
  config: OperacaoConfig;
  setConfig: Dispatch<SetStateAction<OperacaoConfig>>;
  onError: (message: string) => void;
};

const emptyCustomForm = (): TelegramCustomMessage => ({
  id: crypto.randomUUID(),
  label: '',
  trigger: '',
  body: '',
  enabled: true,
  replace_default: false,
});

const AdminCustomMessagesPanel = ({ api, config, setConfig, onError }: Props) => {
  const [customTriggers, setCustomTriggers] = useState<CustomMessageTriggerMeta[]>([]);
  const [previewing, setPreviewing] = useState<string | null>(null);
  const [previewResult, setPreviewResult] = useState<{ id: string; text: string } | null>(null);
  const [showCustomForm, setShowCustomForm] = useState(false);
  const [customForm, setCustomForm] = useState<TelegramCustomMessage>(emptyCustomForm);
  const [editingCustomId, setEditingCustomId] = useState<string | null>(null);

  useEffect(() => {
    void api
      .get<CustomMessageTriggerMeta[]>('/api/v1/operacoes/custom-message-triggers')
      .then((r) => setCustomTriggers(r.data))
      .catch((e) => onError(parseApiError(e, 'Erro ao carregar gatilhos')));
  }, [api, onError]);

  const triggerLabel = (trigger: string) =>
    customTriggers.find((t) => t.trigger === trigger)?.label ?? trigger;

  const selectedTriggerMeta = customTriggers.find((t) => t.trigger === customForm.trigger);

  const handlePreviewCustom = async (msg: TelegramCustomMessage) => {
    setPreviewing(msg.id);
    onError('');
    try {
      const r = await api.post<TelegramTemplatePreviewOut>('/api/v1/operacoes/telegram-template-preview', {
        trigger: msg.trigger,
        template: msg.body,
      });
      setPreviewResult({ id: msg.id, text: r.data.text });
    } catch (e) {
      onError(parseApiError(e, 'Erro ao pré-visualizar mensagem'));
    } finally {
      setPreviewing(null);
    }
  };

  const startNewCustomMessage = () => {
    setCustomForm({ ...emptyCustomForm(), trigger: customTriggers[0]?.trigger ?? '' });
    setEditingCustomId(null);
    setShowCustomForm(true);
  };

  const startEditCustomMessage = (msg: TelegramCustomMessage) => {
    setCustomForm({ ...msg });
    setEditingCustomId(msg.id);
    setShowCustomForm(true);
  };

  const saveCustomForm = () => {
    if (!customForm.label.trim() || !customForm.trigger || !customForm.body.trim()) {
      onError('Preencha nome, gatilho e texto da mensagem personalizada.');
      return;
    }
    onError('');
    setConfig((prev) => {
      const list = [...prev.telegram_custom_messages];
      const idx = list.findIndex((m) => m.id === customForm.id);
      if (idx >= 0) {
        list[idx] = { ...customForm };
      } else {
        list.push({ ...customForm });
      }
      return { ...prev, telegram_custom_messages: list };
    });
    setShowCustomForm(false);
    setEditingCustomId(null);
  };

  const removeCustomMessage = (id: string) => {
    setConfig((prev) => ({
      ...prev,
      telegram_custom_messages: prev.telegram_custom_messages.filter((m) => m.id !== id),
    }));
    if (editingCustomId === id) {
      setShowCustomForm(false);
      setEditingCustomId(null);
    }
  };

  const toggleCustomEnabled = (id: string, enabled: boolean) => {
    setConfig((prev) => ({
      ...prev,
      telegram_custom_messages: prev.telegram_custom_messages.map((m) =>
        m.id === id ? { ...m, enabled } : m
      ),
    }));
  };

  return (
    <div className="settings-section" style={{ marginTop: 40 }}>
      <div className="section-title-row">
        <h3 style={{ display: 'flex', alignItems: 'center', gap: 10, margin: 0 }}>
          <Plus size={20} color="var(--primary)" /> Mensagens personalizadas
        </h3>
        {!showCustomForm && (
          <button
            type="button"
            className="btn-secondary"
            onClick={startNewCustomMessage}
            style={{ display: 'flex', alignItems: 'center', gap: 8 }}
          >
            <Plus size={16} /> Nova mensagem
          </button>
        )}
      </div>
      <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: 20 }}>
        Crie mensagens extras enviadas automaticamente no gatilho escolhido. Marque
        &quot;Substituir padrão&quot; para enviar só a personalizada.
      </p>

      {config.telegram_custom_messages.length === 0 && !showCustomForm && (
        <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: 16 }}>
          Nenhuma mensagem personalizada cadastrada.
        </p>
      )}

      {config.telegram_custom_messages.map((msg) => (
        <div key={msg.id} className="custom-msg-card">
          <div className="custom-msg-header">
            <div>
              <strong>{msg.label}</strong>
              <p className="text-muted custom-msg-trigger">{triggerLabel(msg.trigger)}</p>
            </div>
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={msg.enabled}
                onChange={(e) => toggleCustomEnabled(msg.id, e.target.checked)}
              />
              Ativa
            </label>
          </div>
          {msg.replace_default && (
            <span className="custom-msg-badge">Substitui mensagem padrão</span>
          )}
          <p className="custom-msg-body-preview">{msg.body}</p>
          <div className="custom-msg-actions">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => startEditCustomMessage(msg)}
              style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <Pencil size={14} /> Editar
            </button>
            <button
              type="button"
              className="btn-secondary"
              disabled={previewing === msg.id}
              onClick={() => void handlePreviewCustom(msg)}
              style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <Eye size={14} />
              {previewing === msg.id ? '...' : 'Pré-visualizar'}
            </button>
            <button
              type="button"
              className="btn-danger"
              onClick={() => removeCustomMessage(msg.id)}
              style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <Trash2 size={14} /> Remover
            </button>
          </div>
          {previewResult?.id === msg.id && (
            <div className="preview-box">
              <strong>Pré-visualização:</strong>
              <pre>{previewResult.text}</pre>
            </div>
          )}
        </div>
      ))}

      {showCustomForm && (
        <div className="custom-msg-form">
          <h4 style={{ fontFamily: 'Outfit', marginBottom: 16 }}>
            {editingCustomId ? 'Editar mensagem' : 'Nova mensagem'}
          </h4>
          <div className="input-group">
            <label className="input-label">Nome da mensagem</label>
            <input
              type="text"
              className="input-field"
              value={customForm.label}
              onChange={(e) => setCustomForm({ ...customForm, label: e.target.value })}
              placeholder="Ex.: Lembrete amigável"
            />
          </div>
          <div className="input-group">
            <label className="input-label">Quando enviar</label>
            <select
              className="input-field"
              value={customForm.trigger}
              onChange={(e) => setCustomForm({ ...customForm, trigger: e.target.value })}
            >
              {customTriggers.map((t) => (
                <option key={t.trigger} value={t.trigger}>
                  {t.label}
                </option>
              ))}
            </select>
            {selectedTriggerMeta && (
              <small className="text-muted">{selectedTriggerMeta.description}</small>
            )}
          </div>
          <div className="input-group">
            <label className="input-label">Texto</label>
            <textarea
              className="input-field"
              rows={4}
              value={customForm.body}
              onChange={(e) => setCustomForm({ ...customForm, body: e.target.value })}
            />
            {selectedTriggerMeta && selectedTriggerMeta.placeholders.length > 0 && (
              <small className="text-muted">
                Placeholders: {selectedTriggerMeta.placeholders.map((p) => `{${p}}`).join(', ')}
              </small>
            )}
          </div>
          <label className="toggle-label" style={{ marginBottom: 16 }}>
            <input
              type="checkbox"
              checked={customForm.replace_default}
              onChange={(e) => setCustomForm({ ...customForm, replace_default: e.target.checked })}
            />
            Substituir mensagem padrão deste gatilho
          </label>
          <div className="custom-msg-actions">
            <button type="button" className="btn-primary" onClick={saveCustomForm}>
              {editingCustomId ? 'Atualizar na lista' : 'Adicionar à lista'}
            </button>
            <button
              type="button"
              className="btn-secondary"
              disabled={!customForm.trigger || !customForm.body.trim()}
              onClick={() => void handlePreviewCustom(customForm)}
            >
              Pré-visualizar
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                setShowCustomForm(false);
                setEditingCustomId(null);
              }}
            >
              Cancelar
            </button>
          </div>
          {previewResult?.id === customForm.id && (
            <div className="preview-box">
              <strong>Pré-visualização:</strong>
              <pre>{previewResult.text}</pre>
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        .section-title-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 20px;
          flex-wrap: wrap;
        }
        .input-group {
          margin-bottom: 15px;
        }
        .btn-secondary {
          background: var(--secondary);
          color: white;
          border: none;
          padding: 8px 14px;
          border-radius: 8px;
          cursor: pointer;
        }
        .btn-danger {
          background: rgba(239, 68, 68, 0.15);
          color: var(--danger);
          border: 1px solid rgba(239, 68, 68, 0.3);
          padding: 8px 14px;
          border-radius: 8px;
          cursor: pointer;
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
        .custom-msg-card,
        .custom-msg-form {
          border: 1px solid var(--glass-border);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          background: rgba(0, 0, 0, 0.15);
        }
        .custom-msg-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 12px;
          margin-bottom: 8px;
        }
        .custom-msg-trigger {
          font-size: 0.8rem;
          margin-top: 4px;
        }
        .custom-msg-badge {
          display: inline-block;
          font-size: 0.72rem;
          color: var(--warning);
          margin-bottom: 8px;
        }
        .custom-msg-body-preview {
          font-size: 0.85rem;
          color: var(--text-muted);
          white-space: pre-wrap;
          margin-bottom: 12px;
        }
        .custom-msg-actions {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }
        .toggle-label {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 0.85rem;
          color: var(--text-muted);
          cursor: pointer;
        }
      `}</style>
    </div>
  );
};

export default AdminCustomMessagesPanel;
