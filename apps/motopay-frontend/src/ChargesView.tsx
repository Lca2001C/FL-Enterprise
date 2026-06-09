import { useState, useEffect, useCallback, type FormEvent } from 'react';
import { Plus, Copy, CheckCircle, Clock, AlertTriangle, Check, Filter } from 'lucide-react';
import { useAuth } from './AuthContext';
import type {
  ClienteMpCardOut,
  ClienteOut,
  CobrancaOut,
  ContratoOut,
  Paginated,
  PortalLinkOut,
} from './apiTypes';
import PayCobrancaModal from './components/PayCobrancaModal';
import { PAGE_SIZE } from './apiTypes';
import { formatBrl, formatDate } from './utils/format';
import { parseApiError } from './utils/apiError';
import { getMercadoPagoDeviceId } from './integrations/mercadopago/deviceId';
import { fetchAllPaginated } from './utils/fetchPaginated';
import EmptyState from './components/EmptyState';
import ErrorBanner from './components/ErrorBanner';
import AdminScopeBanner from './components/AdminScopeBanner';

type StatusFilter = 'todos' | 'pendente' | 'atrasado' | 'recebido';

const ChargesView = () => {
  const { api } = useAuth();
  const [cobrancas, setCobrancas] = useState<CobrancaOut[]>([]);
  const [contratos, setContratos] = useState<ContratoOut[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [contratoId, setContratoId] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('todos');
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [copiedPortalId, setCopiedPortalId] = useState<number | null>(null);
  const [refundCob, setRefundCob] = useState<CobrancaOut | null>(null);
  const [refundAmount, setRefundAmount] = useState('');
  const [refundLoading, setRefundLoading] = useState(false);
  const [payCob, setPayCob] = useState<CobrancaOut | null>(null);
  const [payCliente, setPayCliente] = useState<ClienteOut | null>(null);
  const [payCards, setPayCards] = useState<ClienteMpCardOut[]>([]);
  const [payError, setPayError] = useState('');

  const contratosAtivos = contratos.filter((c) => c.status === 'ativo');

  const fetchData = useCallback(
    async (pageOffset = 0) => {
      setLoading(true);
      setError('');
      try {
        const cobParams: Record<string, unknown> = { limit: PAGE_SIZE, offset: pageOffset };
        if (statusFilter !== 'todos') cobParams.status = statusFilter;
        const [cobRes, ctItems] = await Promise.all([
          api.get<Paginated<CobrancaOut>>('/api/v1/cobrancas', { params: cobParams }),
          fetchAllPaginated<ContratoOut>(api, '/api/v1/contratos', { status: 'ativo' }),
        ]);
        setCobrancas(cobRes.data.items);
        setTotal(cobRes.data.total);
        setOffset(pageOffset);
        setContratos(ctItems);
      } catch (e) {
        setError(parseApiError(e, 'Erro ao carregar cobranças'));
      } finally {
        setLoading(false);
      }
    },
    [api, statusFilter]
  );

  useEffect(() => {
    void fetchData(0);
  }, [fetchData]);

  const handleCreateCharge = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const device_id = getMercadoPagoDeviceId();
      await api.post('/api/v1/cobrancas/pix', { contrato_id: parseInt(contratoId, 10), device_id });
      setShowModal(false);
      setContratoId('');
      await fetchData(offset);
    } catch (err) {
      setError(parseApiError(err, 'Erro ao gerar cobrança'));
    }
  };

  const copyPix = async (id: number, text: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const displayValor = (cob: CobrancaOut) =>
    cob.dias_atraso > 0 ? cob.valor_total : cob.valor;

  const canCopyPix = (cob: CobrancaOut) =>
    cob.pix_copia_cola && (cob.status === 'pendente' || cob.status === 'atrasado');

  const canPay = (cob: CobrancaOut) =>
    cob.status === 'pendente' || cob.status === 'atrasado';

  const revokePortalLink = async (cobrancaId: number) => {
    if (!confirm('Revogar o link público desta cobrança?')) return;
    setError('');
    try {
      await api.delete(`/api/v1/cobrancas/${cobrancaId}/portal-link`);
    } catch (e) {
      setError(parseApiError(e, 'Erro ao revogar link'));
    }
  };

  const copyPortalLink = async (cobrancaId: number) => {
    setError('');
    try {
      const r = await api.post<PortalLinkOut>(`/api/v1/cobrancas/${cobrancaId}/portal-link`);
      await navigator.clipboard.writeText(r.data.url);
      setCopiedPortalId(cobrancaId);
      setTimeout(() => setCopiedPortalId(null), 2000);
    } catch (e) {
      setError(parseApiError(e, 'Erro ao gerar link de pagamento'));
    }
  };

  const refundableAmount = (cob: CobrancaOut) =>
    Math.max(0, cob.valor - (cob.valor_estornado ?? 0));

  const handleRefund = async () => {
    if (!refundCob) return;
    setRefundLoading(true);
    setError('');
    try {
      const remaining = refundableAmount(refundCob);
      const body =
        refundAmount.trim() === ''
          ? {}
          : { amount: parseFloat(refundAmount.replace(',', '.')) };
      if (body.amount != null && (body.amount <= 0 || body.amount > remaining)) {
        setError(`Valor deve ser entre 0,01 e ${remaining.toFixed(2)}`);
        return;
      }
      await api.post(`/api/v1/cobrancas/${refundCob.id}/refund`, body);
      setRefundCob(null);
      setRefundAmount('');
      await fetchData(offset);
    } catch (e) {
      setError(parseApiError(e, 'Erro ao estornar cobrança'));
    } finally {
      setRefundLoading(false);
    }
  };

  const openPay = async (cob: CobrancaOut) => {
    setPayError('');
    const ct = contratos.find((c) => c.id === cob.contrato_id);
    if (!ct) {
      setError('Contrato não encontrado para esta cobrança');
      return;
    }
    try {
      const [clRes, cardsRes] = await Promise.all([
        api.get<ClienteOut>(`/api/v1/clientes/${ct.cliente_id}`),
        api.get<ClienteMpCardOut[]>(`/api/v1/clientes/${ct.cliente_id}/mp-cards`),
      ]);
      setPayCliente(clRes.data);
      setPayCards(cardsRes.data);
      setPayCob(cob);
    } catch (e) {
      setError(parseApiError(e, 'Erro ao abrir pagamento'));
    }
  };

  return (
    <div className="view-container animate-fade">
      <div className="view-header">
        <div>
          <h2>Gestão de Cobranças</h2>
          <p className="text-muted">Acompanhamento de pagamentos e faturamento</p>
        </div>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={20} /> Gerar Cobrança
        </button>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}
      <AdminScopeBanner />

      <div className="filter-tabs glass">
        <Filter size={16} />
        {(['todos', 'pendente', 'atrasado', 'recebido'] as StatusFilter[]).map((s) => (
          <button
            key={s}
            type="button"
            className={`tab ${statusFilter === s ? 'active' : ''}`}
            onClick={() => setStatusFilter(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      <div className="glass table-container" data-tour="charges-list">
        {loading ? (
          <p style={{ padding: 40, textAlign: 'center' }}>Carregando cobranças...</p>
        ) : cobrancas.length === 0 ? (
          <EmptyState
            title="Nenhuma cobrança encontrada"
            description="Gere uma cobrança Pix para um contrato ativo."
            action={
              <button className="btn-primary" onClick={() => setShowModal(true)}>
                <Plus size={18} /> Gerar Cobrança
              </button>
            }
          />
        ) : (
          <table className="custom-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Vencimento</th>
                <th>Valor</th>
                <th>Gateway</th>
                <th>Status</th>
                <th>Contrato</th>
                <th>Atraso / Multa</th>
                <th style={{ textAlign: 'right' }}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {cobrancas.map((cob) => (
                <tr key={cob.id}>
                  <td>
                    <span className="text-muted">#{cob.id}</span>
                  </td>
                  <td>{formatDate(cob.vencimento)}</td>
                  <td style={{ fontWeight: 700 }}>{formatBrl(displayValor(cob))}</td>
                  <td>
                    <span className="gateway-badge mercadopago">Mercado Pago</span>
                  </td>
                  <td>
                    <span className={`status-badge ${cob.status}`}>
                      {cob.status === 'recebido' ? (
                        <CheckCircle size={12} />
                      ) : cob.status === 'pendente' ? (
                        <Clock size={12} />
                      ) : (
                        <AlertTriangle size={12} />
                      )}
                      {cob.status.toUpperCase()}
                    </span>
                    {cob.mercadopago_dispute_status && (
                      <a
                        className="dispute-badge"
                        title="Ver no Mercado Pago"
                        href="https://www.mercadopago.com.br/activities/chargebacks"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Disputa: {cob.mercadopago_dispute_status}
                      </a>
                    )}
                    {(cob.valor_estornado ?? 0) > 0 && (
                      <div className="text-muted" style={{ fontSize: '0.75rem', marginTop: 4 }}>
                        Estornado {formatBrl(cob.valor_estornado ?? 0)}
                      </div>
                    )}
                  </td>
                  <td>
                    <div className="contrato-tag">Contrato #{cob.contrato_id}</div>
                  </td>
                  <td>
                    {cob.dias_atraso > 0 ? (
                      <div style={{ fontSize: '0.8rem', color: 'var(--danger)' }}>
                        <div style={{ fontWeight: 700 }}>{cob.dias_atraso} dias</div>
                        <div>
                          Multa {formatBrl(cob.multa)} · Juros {formatBrl(cob.juros)}
                        </div>
                        <div>Total {formatBrl(cob.valor_total)}</div>
                      </div>
                    ) : (
                      <span className="text-muted">—</span>
                    )}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    {canPay(cob) && (
                      <>
                        <button
                          type="button"
                          className="btn-secondary"
                          style={{ marginRight: 8 }}
                          onClick={() => void openPay(cob)}
                        >
                          Pagar
                        </button>
                        <button
                          type="button"
                          className="action-btn-pix"
                          style={{ marginRight: 8 }}
                          title="Copiar link público de pagamento"
                          onClick={() => void copyPortalLink(cob.id)}
                        >
                          {copiedPortalId === cob.id ? <Check size={14} /> : <Copy size={14} />}
                          {copiedPortalId === cob.id ? 'Link copiado' : 'Link'}
                        </button>
                        <button
                          type="button"
                          className="icon-btn"
                          style={{ marginRight: 8 }}
                          title="Revogar link público"
                          onClick={() => void revokePortalLink(cob.id)}
                        >
                          Revogar
                        </button>
                      </>
                    )}
                    {canCopyPix(cob) && (
                      <button
                        type="button"
                        className="action-btn-pix"
                        onClick={() => void copyPix(cob.id, cob.pix_copia_cola!)}
                      >
                        {copiedId === cob.id ? <Check size={14} /> : <Copy size={14} />}
                        {copiedId === cob.id ? 'Copiado' : 'PIX'}
                      </button>
                    )}
                    {cob.status === 'recebido' && refundableAmount(cob) > 0 && (
                      <button
                        type="button"
                        className="icon-btn danger"
                        style={{ marginLeft: 8 }}
                        title="Estornar no Mercado Pago"
                        onClick={() => {
                          setRefundCob(cob);
                          setRefundAmount('');
                        }}
                      >
                        Estornar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {total > PAGE_SIZE && (
        <div className="pagination glass">
          <button
            type="button"
            className="btn-secondary"
            disabled={offset === 0 || loading}
            onClick={() => void fetchData(Math.max(0, offset - PAGE_SIZE))}
          >
            Anterior
          </button>
          <span className="text-muted">
            {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} de {total}
          </span>
          <button
            type="button"
            className="btn-secondary"
            disabled={offset + PAGE_SIZE >= total || loading}
            onClick={() => void fetchData(offset + PAGE_SIZE)}
          >
            Próxima
          </button>
        </div>
      )}

      {payCob && payCliente && (
        <PayCobrancaModal
          cob={payCob}
          cliente={payCliente}
          savedCards={payCards}
          api={api}
          displayValor={displayValor(payCob)}
          onClose={() => {
            setPayCob(null);
            setPayCliente(null);
            setPayCards([]);
          }}
          onPaid={() => {
            setPayCob(null);
            setPayCliente(null);
            void fetchData(offset);
          }}
          onError={setPayError}
        />
      )}
      {payError && <ErrorBanner message={payError} onDismiss={() => setPayError('')} />}

      {refundCob && (
        <div className="modal-overlay">
          <div className="glass modal-content animate-fade">
            <h3>Estornar cobrança #{refundCob.id}</h3>
            <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: 16 }}>
              Valor máximo estornável: {formatBrl(refundableAmount(refundCob))}. Deixe em branco para
              estorno total do saldo restante.
            </p>
            <div className="input-group">
              <label className="input-label">Valor parcial (opcional)</label>
              <input
                type="text"
                className="input-field"
                value={refundAmount}
                onChange={(e) => setRefundAmount(e.target.value)}
                placeholder={refundableAmount(refundCob).toFixed(2)}
              />
            </div>
            <div className="modal-actions">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => {
                  setRefundCob(null);
                  setRefundAmount('');
                }}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="btn-primary danger"
                disabled={refundLoading}
                onClick={() => void handleRefund()}
              >
                {refundLoading ? 'Estornando…' : 'Confirmar estorno'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showModal && (
        <div className="modal-overlay">
          <div className="glass modal-content animate-fade">
            <h3>Gerar Cobrança Pix</h3>
            <p className="text-muted" style={{ fontSize: '0.8rem', marginBottom: '20px' }}>
              Cria uma cobrança Pix no Mercado Pago para o contrato selecionado.
            </p>
            <form onSubmit={(e) => void handleCreateCharge(e)}>
              <div className="input-group">
                <label className="input-label">Contrato</label>
                <select
                  className="input-field"
                  value={contratoId}
                  onChange={(e) => setContratoId(e.target.value)}
                  required
                >
                  <option value="">Selecione...</option>
                  {contratosAtivos.map((ct) => (
                    <option key={ct.id} value={ct.id}>
                      #{ct.id} — {formatBrl(ct.valor_recorrente)} / {ct.ciclo}
                    </option>
                  ))}
                </select>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary">
                  Gerar Pix
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <style jsx>{`
        .view-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
          flex-wrap: wrap;
          gap: 16px;
        }
        .filter-tabs {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 16px;
          margin-bottom: 20px;
          border-radius: 12px;
          flex-wrap: wrap;
        }
        .tab {
          background: none;
          border: 1px solid var(--glass-border);
          color: var(--text-muted);
          padding: 6px 14px;
          border-radius: 8px;
          cursor: pointer;
          font-size: 0.85rem;
        }
        .tab.active {
          background: var(--primary-glow);
          color: var(--primary);
          border-color: var(--primary);
        }
        .table-container {
          overflow-x: auto;
        }
        .custom-table {
          width: 100%;
          border-collapse: collapse;
          min-width: 720px;
        }
        .custom-table th {
          text-align: left;
          padding: 15px 20px;
          color: var(--text-muted);
          font-size: 0.85rem;
          border-bottom: 1px solid var(--glass-border);
        }
        .custom-table td {
          padding: 15px 20px;
          border-bottom: 1px solid var(--glass-border);
          font-size: 0.9rem;
        }
        .status-badge {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 4px 10px;
          border-radius: 6px;
          font-size: 0.7rem;
          font-weight: 700;
          width: fit-content;
        }
        .status-badge.recebido {
          background: rgba(16, 185, 129, 0.1);
          color: var(--accent);
        }
        .status-badge.pendente {
          background: rgba(245, 158, 11, 0.1);
          color: var(--warning);
        }
        .status-badge.atrasado {
          background: rgba(239, 68, 68, 0.1);
          color: var(--danger);
        }
        .contrato-tag {
          background: rgba(255, 255, 255, 0.05);
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 0.8rem;
          border: 1px solid var(--glass-border);
        }
        .gateway-badge {
          padding: 4px 10px;
          border-radius: 6px;
          font-size: 0.7rem;
          font-weight: 600;
        }
        .gateway-badge.mercadopago {
          background: rgba(245, 158, 11, 0.1);
          color: var(--warning);
        }
        .pagination {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px 16px;
          margin-top: 16px;
          border-radius: 12px;
        }
        .action-btn-pix {
          background: var(--primary-glow);
          color: var(--primary);
          border: 1px solid var(--primary);
          padding: 4px 10px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 0.75rem;
          font-weight: 600;
          display: inline-flex;
          align-items: center;
          gap: 5px;
        }
        .btn-secondary {
          background: var(--secondary);
          color: white;
          border: none;
          padding: 10px 20px;
          border-radius: 8px;
          cursor: pointer;
        }
        .dispute-badge {
          display: inline-block;
          margin-top: 6px;
          font-size: 0.65rem;
          font-weight: 700;
          color: var(--danger);
          background: rgba(239, 68, 68, 0.1);
          padding: 2px 6px;
          border-radius: 4px;
          width: fit-content;
          text-decoration: none;
        }
        .dispute-badge:hover {
          text-decoration: underline;
        }
        .btn-primary.danger {
          background: var(--danger);
        }
      `}</style>
    </div>
  );
};

export default ChargesView;
