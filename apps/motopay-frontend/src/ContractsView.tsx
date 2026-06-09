import { useState, useEffect, useMemo, useCallback, type FormEvent } from 'react';
import {
  Plus,
  FileText,
  XCircle,
  Copy,
  QrCode,
  Wallet,
  Check,
  Filter,
  X,
  Download,
  Pencil,
} from 'lucide-react';
import { useAuth } from './AuthContext';
import type {
  ClienteOut,
  CobrancaOut,
  ContratoOut,
  MotoOut,
  MpSubscriptionOut,
  Paginated,
} from './apiTypes';
import type { ContractsFilter } from './apiTypes';
import { PAGE_SIZE } from './apiTypes';
import {
  contractEndFromPreset,
  defaultVencimento,
  formatBrl,
  formatDate,
  paymentDueFromPreset,
  todayIso,
  type VencimentoPreset,
  type VigenciaPreset,
} from './utils/format';
import { parseApiError } from './utils/apiError';
import { fetchAllPaginated, offsetAfterDelete } from './utils/fetchPaginated';
import { getMercadoPagoDeviceId } from './integrations/mercadopago/deviceId';
import EmptyState from './components/EmptyState';
import ErrorBanner from './components/ErrorBanner';
import AdminScopeBanner from './components/AdminScopeBanner';

type FilterTab = ContractsFilter;

const VIGENCIA_OPTIONS: { value: VigenciaPreset; label: string }[] = [
  { value: 'indeterminado', label: 'Indeterminado' },
  { value: '1m', label: '1 mês' },
  { value: '3m', label: '3 meses' },
  { value: '6m', label: '6 meses' },
  { value: '1a', label: '1 ano' },
  { value: 'custom', label: 'Personalizado' },
];

const VENCIMENTO_OPTIONS: { value: VencimentoPreset; label: string }[] = [
  { value: 'ciclo', label: 'Conforme ciclo' },
  { value: '7d', label: 'Em 7 dias' },
  { value: '15d', label: 'Em 15 dias' },
  { value: '30d', label: 'Em 30 dias' },
  { value: 'custom', label: 'Personalizado' },
];

const ContractsView = () => {
  const {
    api,
    contractsFilter,
    setContractsFilter,
    contractsClienteId,
    clearContractsClienteFilter,
  } = useAuth();
  const [contratos, setContratos] = useState<ContratoOut[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [clientes, setClientes] = useState<ClienteOut[]>([]);
  const [motos, setMotos] = useState<MotoOut[]>([]);
  const [cobrancas, setCobrancas] = useState<CobrancaOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<FilterTab>(contractsFilter);
  const [showModal, setShowModal] = useState(false);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [subscriptionLink, setSubscriptionLink] = useState<MpSubscriptionOut | null>(null);
  const [editCt, setEditCt] = useState<ContratoOut | null>(null);
  const [editValor, setEditValor] = useState('');
  const [editCiclo, setEditCiclo] = useState<'semanal' | 'mensal'>('mensal');

  const [form, setForm] = useState({
    cliente_id: '',
    moto_id: '',
    valor_recorrente: '',
    ciclo: 'mensal' as 'semanal' | 'mensal',
    data_inicio: todayIso(),
    data_fim_vigencia: '',
    proximo_vencimento: defaultVencimento('mensal', todayIso()),
    gerar_pix: true,
  });
  const [vigenciaModo, setVigenciaModo] = useState<VigenciaPreset>('indeterminado');
  const [vencimentoModo, setVencimentoModo] = useState<VencimentoPreset>('ciclo');

  const clienteMap = useMemo(
    () => Object.fromEntries(clientes.map((c) => [c.id, c])),
    [clientes]
  );
  const motoMap = useMemo(() => Object.fromEntries(motos.map((m) => [m.id, m])), [motos]);

  const cobrancaByContrato = useMemo(() => {
    const map: Record<number, CobrancaOut> = {};
    for (const c of cobrancas) {
      if (c.status === 'pendente' || c.status === 'atrasado') {
        if (!map[c.contrato_id] || map[c.contrato_id].id < c.id) {
          map[c.contrato_id] = c;
        }
      }
    }
    return map;
  }, [cobrancas]);

  const motosDisponiveis = motos.filter((m) => m.status === 'disponivel');

  const buildContratoParams = useCallback(
    (pageOffset: number): Record<string, unknown> => {
      const params: Record<string, unknown> = { limit: PAGE_SIZE, offset: pageOffset };
      if (filter === 'ativos') params.status = 'ativo';
      else if (filter === 'inadimplentes') params.inadimplente = true;
      else if (filter === 'com_promessa') params.com_promessa = true;
      if (contractsClienteId != null) params.cliente_id = contractsClienteId;
      return params;
    },
    [filter, contractsClienteId]
  );

  const fetchContratos = useCallback(
    async (pageOffset = 0) => {
      setLoading(true);
      setError('');
      try {
        const r = await api.get<Paginated<ContratoOut>>('/api/v1/contratos', {
          params: buildContratoParams(pageOffset),
        });
        setContratos(r.data.items);
        setTotal(r.data.total);
        setOffset(pageOffset);
      } catch (e) {
        setError(parseApiError(e, 'Erro ao carregar contratos'));
      } finally {
        setLoading(false);
      }
    },
    [api, buildContratoParams]
  );

  const fetchMeta = useCallback(async () => {
    try {
      const [clItems, moItems, cobItems] = await Promise.all([
        fetchAllPaginated<ClienteOut>(api, '/api/v1/clientes'),
        fetchAllPaginated<MotoOut>(api, '/api/v1/motos'),
        fetchAllPaginated<CobrancaOut>(api, '/api/v1/cobrancas'),
      ]);
      setClientes(clItems);
      setMotos(moItems);
      setCobrancas(cobItems);
    } catch (e) {
      setError(parseApiError(e, 'Erro ao carregar dados auxiliares'));
    }
  }, [api]);

  useEffect(() => {
    void fetchContratos(0);
  }, [fetchContratos]);

  useEffect(() => {
    void fetchMeta();
  }, [fetchMeta]);

  useEffect(() => {
    setFilter(contractsFilter);
  }, [contractsFilter]);

  const handleFilterChange = (f: FilterTab) => {
    setFilter(f);
    setContractsFilter(f);
  };

  const handleCicloChange = (ciclo: 'semanal' | 'mensal') => {
    setForm((prev) => {
      const next = { ...prev, ciclo };
      if (vencimentoModo !== 'custom') {
        next.proximo_vencimento = paymentDueFromPreset(prev.data_inicio, ciclo, vencimentoModo);
      }
      return next;
    });
  };

  const handleDataInicioChange = (data_inicio: string) => {
    setForm((prev) => {
      const next = { ...prev, data_inicio };
      if (vigenciaModo !== 'custom') {
        next.data_fim_vigencia = contractEndFromPreset(data_inicio, vigenciaModo);
      }
      if (vencimentoModo !== 'custom') {
        next.proximo_vencimento = paymentDueFromPreset(data_inicio, prev.ciclo, vencimentoModo);
      }
      return next;
    });
  };

  const handleVigenciaModoChange = (modo: VigenciaPreset) => {
    setVigenciaModo(modo);
    setForm((prev) => ({
      ...prev,
      data_fim_vigencia:
        modo === 'custom'
          ? prev.data_fim_vigencia || contractEndFromPreset(prev.data_inicio, '3m')
          : contractEndFromPreset(prev.data_inicio, modo),
    }));
  };

  const handleVencimentoModoChange = (modo: VencimentoPreset) => {
    setVencimentoModo(modo);
    setForm((prev) => ({
      ...prev,
      proximo_vencimento:
        modo === 'custom'
          ? prev.proximo_vencimento
          : paymentDueFromPreset(prev.data_inicio, prev.ciclo, modo),
    }));
  };

  const resetForm = () => {
    const inicio = todayIso();
    setVigenciaModo('indeterminado');
    setVencimentoModo('ciclo');
    setForm({
      cliente_id: '',
      moto_id: '',
      valor_recorrente: '',
      ciclo: 'mensal',
      data_inicio: inicio,
      data_fim_vigencia: '',
      proximo_vencimento: defaultVencimento('mensal', inicio),
      gerar_pix: true,
    });
  };

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const body: Record<string, unknown> = {
        cliente_id: parseInt(form.cliente_id, 10),
        moto_id: parseInt(form.moto_id, 10),
        valor_recorrente: parseFloat(form.valor_recorrente),
        ciclo: form.ciclo,
        status: 'ativo',
        data_inicio: form.data_inicio,
        proximo_vencimento: form.proximo_vencimento,
      };
      if (form.data_fim_vigencia) {
        body.data_fim_vigencia = form.data_fim_vigencia;
      }
      const res = await api.post<ContratoOut>('/api/v1/contratos', body);
      if (form.gerar_pix) {
        await api.post('/api/v1/cobrancas/pix', { contrato_id: res.data.id, device_id: getMercadoPagoDeviceId() });
      }
      setShowModal(false);
      resetForm();
      await fetchContratos(offset);
      await fetchMeta();
    } catch (err) {
      setError(parseApiError(err, 'Erro ao criar contrato'));
    }
  };

  const openEditContrato = (ct: ContratoOut) => {
    setEditCt(ct);
    setEditValor(String(ct.valor_recorrente));
    setEditCiclo(ct.ciclo as 'semanal' | 'mensal');
  };

  const handleSaveEditContrato = async () => {
    if (!editCt) return;
    setActionLoading(editCt.id);
    setError('');
    try {
      await api.patch(`/api/v1/contratos/${editCt.id}`, {
        valor_recorrente: parseFloat(editValor),
        ciclo: editCiclo,
      });
      setEditCt(null);
      await fetchContratos(offset);
    } catch (err) {
      setError(parseApiError(err, 'Erro ao atualizar contrato'));
    } finally {
      setActionLoading(null);
    }
  };

  const handleEncerrar = async (id: number) => {
    if (!confirm('Encerrar este contrato? A moto não será liberada automaticamente.')) return;
    setActionLoading(id);
    setError('');
    const wasLast = contratos.length === 1;
    try {
      await api.patch(`/api/v1/contratos/${id}`, { status: 'finalizado' });
      await fetchContratos(offsetAfterDelete(offset, PAGE_SIZE, wasLast));
      await fetchMeta();
    } catch (err) {
      setError(parseApiError(err, 'Erro ao encerrar contrato'));
    } finally {
      setActionLoading(null);
    }
  };

  const handleGerarPix = async (contratoId: number) => {
    setActionLoading(contratoId);
    setError('');
    try {
      await api.post('/api/v1/cobrancas/pix', { contrato_id: contratoId, device_id: getMercadoPagoDeviceId() });
      await fetchContratos(offset);
      await fetchMeta();
    } catch (err) {
      setError(parseApiError(err, 'Erro ao gerar Pix'));
    } finally {
      setActionLoading(null);
    }
  };

  const handleAssinaturaMp = async (contratoId: number) => {
    setActionLoading(contratoId);
    setError('');
    try {
      const r = await api.post<MpSubscriptionOut>('/api/v1/cobrancas/assinatura-mercadopago', {
        contrato_id: contratoId,
      });
      setSubscriptionLink(r.data);
      await fetchContratos(offset);
      await fetchMeta();
    } catch (err) {
      setError(parseApiError(err, 'Erro ao criar assinatura Mercado Pago'));
    } finally {
      setActionLoading(null);
    }
  };

  const openSubscriptionLink = async (contratoId: number) => {
    setActionLoading(contratoId);
    setError('');
    try {
      const r = await api.get<MpSubscriptionOut>(
        `/api/v1/contratos/${contratoId}/assinatura-mercadopago`
      );
      setSubscriptionLink(r.data);
    } catch (err) {
      setError(parseApiError(err, 'Erro ao obter link da assinatura'));
    } finally {
      setActionLoading(null);
    }
  };

  const copyPix = async (contratoId: number, pix: string) => {
    await navigator.clipboard.writeText(pix);
    setCopiedId(contratoId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleDownloadContrato = async (contratoId: number, placa: string) => {
    setActionLoading(contratoId);
    setError('');
    try {
      const res = await api.get(`/api/v1/contratos/${contratoId}/documento`, {
        responseType: 'blob',
      });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `contrato-${contratoId}-${placa.replace(/-/g, '')}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(parseApiError(err, 'Erro ao baixar contrato'));
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="view-container animate-fade">
      <div className="view-header">
        <div>
          <h2>Contratos</h2>
          <p className="text-muted">{total} locações cadastradas</p>
        </div>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={20} /> Nova locação
        </button>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}
      <AdminScopeBanner />

      {contractsClienteId != null && (
        <div className="cliente-filter-chip glass">
          <span>Filtrando cliente #{contractsClienteId}</span>
          <button
            type="button"
            className="icon-btn"
            title="Limpar filtro de cliente"
            onClick={clearContractsClienteFilter}
          >
            <X size={14} />
          </button>
        </div>
      )}

      <div className="filter-tabs glass" data-tour="contracts-filters">
        <Filter size={16} />
        {(['todos', 'ativos', 'inadimplentes', 'com_promessa'] as FilterTab[]).map((f) => (
          <button
            key={f}
            type="button"
            className={`tab ${filter === f ? 'active' : ''}`}
            onClick={() => handleFilterChange(f)}
          >
            {f === 'todos'
              ? 'Todos'
              : f === 'ativos'
                ? 'Ativos'
                : f === 'inadimplentes'
                  ? 'Inadimplentes'
                  : 'Com promessa'}
          </button>
        ))}
      </div>

      <div className="glass table-container">
        {loading ? (
          <p style={{ padding: 40, textAlign: 'center' }}>Carregando contratos...</p>
        ) : contratos.length === 0 ? (
          <EmptyState
            icon={<FileText size={40} />}
            title="Nenhum contrato encontrado"
            description={
              filter === 'inadimplentes'
                ? 'Não há contratos inadimplentes no momento.'
                : 'Cadastre uma nova locação para vincular cliente e moto.'
            }
            action={
              filter !== 'inadimplentes' ? (
                <button className="btn-primary" onClick={() => setShowModal(true)}>
                  <Plus size={18} /> Nova locação
                </button>
              ) : undefined
            }
          />
        ) : (
          <table className="custom-table">
            <thead>
              <tr>
                <th>Nº</th>
                <th>Cliente</th>
                <th>Moto</th>
                <th>Valor</th>
                <th>Ciclo</th>
                <th>Venc. pagamento</th>
                <th>Fim vigência</th>
                <th>Promessa</th>
                <th>Assinatura</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {contratos.map((ct) => {
                const cl = clienteMap[ct.cliente_id];
                const mo = motoMap[ct.moto_id];
                const cob = cobrancaByContrato[ct.id];
                const busy = actionLoading === ct.id;
                return (
                  <tr key={ct.id}>
                    <td style={{ fontWeight: 600, color: 'var(--accent)', whiteSpace: 'nowrap' }}>
                      #{ct.numero ?? ct.id}
                    </td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{cl?.nome ?? `#${ct.cliente_id}`}</div>
                      {ct.inadimplente && (
                        <span className="badge-danger">
                          {ct.dias_atraso_acumulado} dia(s) atraso
                        </span>
                      )}
                    </td>
                    <td>
                      <div>{mo?.placa ?? `#${ct.moto_id}`}</div>
                      <div className="text-muted" style={{ fontSize: '0.8rem' }}>
                        {mo?.modelo ?? '—'}
                      </div>
                    </td>
                    <td>{formatBrl(ct.valor_recorrente)}</td>
                    <td>{ct.ciclo}</td>
                    <td>{formatDate(ct.proximo_vencimento)}</td>
                    <td>
                      {ct.data_fim_vigencia ? (
                        formatDate(ct.data_fim_vigencia)
                      ) : (
                        <span className="text-muted">Indeterminado</span>
                      )}
                    </td>
                    <td>
                      {ct.promessa_pagamento_em ? (
                        <div style={{ fontSize: '0.8rem' }}>
                          <div>{formatDate(ct.promessa_pagamento_em)}</div>
                          {ct.promessa_notas && (
                            <div className="text-muted">{ct.promessa_notas}</div>
                          )}
                        </div>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td>
                      <div className="sub-badges">
                        {ct.mercadopago_subscription_id && (
                          <button
                            type="button"
                            className="sub-badge mp"
                            style={{ border: 'none', cursor: 'pointer' }}
                            title="Abrir link de autorização"
                            onClick={() => void openSubscriptionLink(ct.id)}
                          >
                            MP
                            {ct.mercadopago_subscription_status
                              ? ` (${ct.mercadopago_subscription_status})`
                              : ''}
                          </button>
                        )}
                        {!ct.mercadopago_subscription_id && (
                          <span className="text-muted">—</span>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className={`status-badge ${ct.status}`}>{ct.status.toUpperCase()}</span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div className="actions">
                        <button
                          type="button"
                          className="icon-btn"
                          title="Baixar contrato (PDF)"
                          disabled={busy}
                          onClick={() => void handleDownloadContrato(ct.id, mo?.placa ?? 'moto')}
                        >
                          <Download size={16} />
                        </button>
                        {cob?.pix_copia_cola && (
                          <button
                            type="button"
                            className="action-btn-pix"
                            disabled={busy}
                            onClick={() => void copyPix(ct.id, cob.pix_copia_cola!)}
                          >
                            {copiedId === ct.id ? <Check size={14} /> : <Copy size={14} />}
                            {copiedId === ct.id ? 'Copiado' : 'Pix'}
                          </button>
                        )}
                        {ct.status === 'ativo' && (
                          <>
                            <button
                              type="button"
                              className="icon-btn"
                              title="Editar valor e ciclo"
                              disabled={busy}
                              onClick={() => openEditContrato(ct)}
                            >
                              <Pencil size={16} />
                            </button>
                            <button
                              type="button"
                              className="icon-btn"
                              title="Gerar cobrança Pix para este contrato"
                              disabled={busy}
                              onClick={() => void handleGerarPix(ct.id)}
                            >
                              <QrCode size={16} />
                            </button>
                            <button
                              type="button"
                              className="icon-btn"
                              title="Criar assinatura recorrente no Mercado Pago"
                              disabled={busy}
                              onClick={() => void handleAssinaturaMp(ct.id)}
                            >
                              <Wallet size={16} />
                            </button>
                            <button
                              type="button"
                              className="icon-btn danger"
                              title="Encerrar contrato de locação"
                              disabled={busy}
                              onClick={() => void handleEncerrar(ct.id)}
                            >
                              <XCircle size={16} />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
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
            onClick={() => void fetchContratos(Math.max(0, offset - PAGE_SIZE))}
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
            onClick={() => void fetchContratos(offset + PAGE_SIZE)}
          >
            Próxima
          </button>
        </div>
      )}

      {editCt && (
        <div className="modal-overlay" onClick={() => setEditCt(null)}>
          <div className="modal glass" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 420 }}>
            <h3>Editar contrato #{editCt.numero ?? editCt.id}</h3>
            <div className="input-group">
              <label className="input-label">Valor recorrente</label>
              <input
                type="number"
                step="0.01"
                className="input-field"
                value={editValor}
                onChange={(e) => setEditValor(e.target.value)}
              />
            </div>
            <div className="input-group">
              <label className="input-label">Ciclo</label>
              <select
                className="input-field"
                value={editCiclo}
                onChange={(e) => setEditCiclo(e.target.value as 'semanal' | 'mensal')}
              >
                <option value="mensal">Mensal</option>
                <option value="semanal">Semanal</option>
              </select>
            </div>
            {editCt.mercadopago_subscription_id && (
              <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: 12 }}>
                Assinatura MP ativa: o valor/ciclo será sincronizado automaticamente.
              </p>
            )}
            <div className="modal-actions">
              <button type="button" className="btn-secondary" onClick={() => setEditCt(null)}>
                Cancelar
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={actionLoading === editCt.id}
                onClick={() => void handleSaveEditContrato()}
              >
                Salvar
              </button>
            </div>
          </div>
        </div>
      )}

      {subscriptionLink && (
        <div className="modal-overlay" onClick={() => setSubscriptionLink(null)}>
          <div className="modal glass" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 480 }}>
            <h3>Assinatura Mercado Pago</h3>
            <p className="text-muted">
              Contrato #{subscriptionLink.contrato_id} — status:{' '}
              <strong>{subscriptionLink.status ?? 'pending'}</strong>
            </p>
            {subscriptionLink.init_point ? (
              <>
                <p style={{ fontSize: '0.9rem', marginBottom: 12 }}>
                  Envie o link ao cliente para autorizar a cobrança recorrente:
                </p>
                <a
                  href={subscriptionLink.init_point}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-primary"
                  style={{ display: 'inline-block', marginBottom: 12 }}
                >
                  Abrir autorização no Mercado Pago
                </a>
                <textarea
                  className="input-field"
                  readOnly
                  rows={2}
                  value={subscriptionLink.init_point}
                />
              </>
            ) : (
              <p className="text-muted">Link de autorização indisponível. Tente novamente.</p>
            )}
            <button
              type="button"
              className="btn-secondary"
              style={{ marginTop: 12 }}
              onClick={() => setSubscriptionLink(null)}
            >
              Fechar
            </button>
          </div>
        </div>
      )}

      {showModal && (
        <div className="modal-overlay">
          <div className="glass modal-content modal-content--wide animate-fade">
            <h3>Nova locação</h3>
            <form onSubmit={(e) => void handleCreate(e)}>
              <div className="input-group">
                <label className="input-label">Cliente</label>
                <select
                  className="input-field"
                  value={form.cliente_id}
                  onChange={(e) => setForm({ ...form, cliente_id: e.target.value })}
                  required
                >
                  <option value="">Selecione...</option>
                  {clientes.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nome} — {c.cpf}
                    </option>
                  ))}
                </select>
              </div>
              <div className="input-group">
                <label className="input-label">Moto disponível</label>
                <select
                  className="input-field"
                  value={form.moto_id}
                  onChange={(e) => setForm({ ...form, moto_id: e.target.value })}
                  required
                >
                  <option value="">Selecione...</option>
                  {motosDisponiveis.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.placa} — {m.modelo}
                    </option>
                  ))}
                </select>
              </div>
              <div className="input-group">
                <label className="input-label">Valor recorrente (R$)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  className="input-field"
                  value={form.valor_recorrente}
                  onChange={(e) => setForm({ ...form, valor_recorrente: e.target.value })}
                  required
                />
              </div>
              <div className="input-group">
                <label className="input-label">Ciclo</label>
                <select
                  className="input-field"
                  value={form.ciclo}
                  onChange={(e) =>
                    handleCicloChange(e.target.value as 'semanal' | 'mensal')
                  }
                >
                  <option value="mensal">Mensal</option>
                  <option value="semanal">Semanal</option>
                </select>
              </div>
              <div className="input-group">
                <label className="input-label">Início do contrato</label>
                <input
                  type="date"
                  className="input-field"
                  value={form.data_inicio}
                  onChange={(e) => handleDataInicioChange(e.target.value)}
                  required
                />
              </div>

              <div className="form-cards-row">
                <div className="date-option-card glass">
                  <h4>Tempo do contrato</h4>
                  <p className="text-muted date-card-hint">
                    Até quando a locação permanece ativa (encerramento automático).
                  </p>
                  <div className="date-option-grid">
                    {VIGENCIA_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        type="button"
                        className={`date-chip ${vigenciaModo === opt.value ? 'active' : ''}`}
                        onClick={() => handleVigenciaModoChange(opt.value)}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                  <p className="date-effective">
                    {vigenciaModo === 'indeterminado' ? (
                      <span className="text-muted">Sem data de término</span>
                    ) : vigenciaModo === 'custom' ? (
                      <>
                        <span className="text-muted">Data escolhida: </span>
                        {form.data_fim_vigencia ? formatDate(form.data_fim_vigencia) : '—'}
                      </>
                    ) : (
                      <>
                        <span className="text-muted">Encerra em: </span>
                        {formatDate(form.data_fim_vigencia)}
                      </>
                    )}
                  </p>
                  {vigenciaModo === 'custom' && (
                    <input
                      type="date"
                      className="input-field"
                      value={form.data_fim_vigencia}
                      min={form.data_inicio}
                      onChange={(e) => setForm({ ...form, data_fim_vigencia: e.target.value })}
                      required
                    />
                  )}
                </div>

                <div className="date-option-card glass">
                  <h4>Vencimento do pagamento</h4>
                  <p className="text-muted date-card-hint">
                    Quando o cliente deve pagar (primeiro vencimento).
                  </p>
                  <div className="date-option-grid">
                    {VENCIMENTO_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        type="button"
                        className={`date-chip ${vencimentoModo === opt.value ? 'active' : ''}`}
                        onClick={() => handleVencimentoModoChange(opt.value)}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                  <p className="date-effective">
                    <span className="text-muted">Vence em: </span>
                    {formatDate(form.proximo_vencimento)}
                  </p>
                  {vencimentoModo === 'custom' && (
                    <input
                      type="date"
                      className="input-field"
                      value={form.proximo_vencimento}
                      min={form.data_inicio}
                      onChange={(e) =>
                        setForm({ ...form, proximo_vencimento: e.target.value })
                      }
                      required
                    />
                  )}
                </div>
              </div>
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={form.gerar_pix}
                  onChange={(e) => setForm({ ...form, gerar_pix: e.target.checked })}
                />
                Gerar Pix após criar
              </label>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary">
                  Criar locação
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
        .cliente-filter-chip {
          display: inline-flex;
          align-items: center;
          gap: 10px;
          padding: 8px 14px;
          margin-bottom: 16px;
          border-radius: 999px;
          font-size: 0.85rem;
          color: var(--primary);
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
          min-width: 800px;
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
          padding: 4px 10px;
          border-radius: 6px;
          font-size: 0.7rem;
          font-weight: 700;
        }
        .status-badge.ativo {
          background: rgba(16, 185, 129, 0.1);
          color: var(--accent);
        }
        .status-badge.finalizado,
        .status-badge.cancelado {
          background: rgba(148, 163, 184, 0.1);
          color: var(--text-muted);
        }
        .badge-danger {
          display: inline-block;
          margin-top: 4px;
          font-size: 0.7rem;
          color: var(--danger);
          font-weight: 600;
        }
        .sub-badges {
          display: flex;
          gap: 4px;
          flex-wrap: wrap;
        }
        .sub-badge {
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 0.7rem;
          font-weight: 700;
        }
        .sub-badge.mp {
          background: rgba(245, 158, 11, 0.1);
          color: var(--warning);
        }
        .actions {
          display: flex;
          justify-content: flex-end;
          gap: 4px;
          flex-wrap: wrap;
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
        .icon-btn {
          background: none;
          border: none;
          color: var(--text-muted);
          cursor: pointer;
          padding: 5px;
        }
        .icon-btn:hover {
          color: var(--primary);
        }
        .icon-btn.danger:hover {
          color: var(--danger);
        }
        .form-cards-row {
          display: flex;
          flex-wrap: wrap;
          justify-content: center;
          gap: 16px;
          margin: 20px 0;
        }
        .date-option-card {
          flex: 1 1 260px;
          max-width: 300px;
          width: 100%;
          padding: 18px;
          border-radius: 12px;
          text-align: center;
        }
        .date-option-card h4 {
          font-size: 0.95rem;
          margin-bottom: 6px;
        }
        .date-card-hint {
          font-size: 0.75rem;
          margin-bottom: 12px;
          line-height: 1.35;
        }
        .date-option-grid {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          justify-content: center;
          margin-bottom: 12px;
        }
        .date-chip {
          background: var(--secondary);
          border: 1px solid var(--glass-border);
          color: var(--text-muted);
          padding: 6px 12px;
          border-radius: 8px;
          cursor: pointer;
          font-size: 0.78rem;
          transition: border-color 0.15s, background 0.15s, color 0.15s;
        }
        .date-chip:hover {
          border-color: var(--primary);
          color: var(--primary);
        }
        .date-chip.active {
          border-color: var(--primary);
          background: var(--primary-glow);
          color: var(--primary);
          font-weight: 600;
        }
        .date-effective {
          font-size: 0.85rem;
          margin-bottom: 10px;
          min-height: 1.25rem;
        }
        .checkbox-row {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-top: 12px;
          font-size: 0.9rem;
          cursor: pointer;
        }
        .btn-secondary {
          background: var(--secondary);
          color: white;
          border: none;
          padding: 10px 20px;
          border-radius: 8px;
          cursor: pointer;
        }
        .pagination {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px 16px;
          margin-top: 16px;
          border-radius: 12px;
        }
      `}</style>
    </div>
  );
};

export default ContractsView;
