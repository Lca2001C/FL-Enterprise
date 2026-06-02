import React from 'react';
import { AuthProvider, useAuth } from './AuthContext';
import { MercadoPagoProvider } from './integrations/mercadopago/MercadoPagoProvider';
import Login from './Login';
import FleetView from './FleetView';
import ClientsView from './ClientsView';
import ContractsView from './ContractsView';
import FinanceView from './FinanceView';
import MetricsView from './MetricsView';
import ChargesView from './ChargesView';
import SettingsView from './SettingsView';
import AccountView from './AccountView';
import AdminOperacoesView from './AdminOperacoesView';
import AdminUsuariosView from './AdminUsuariosView';
import OpsDashboardView from './OpsDashboardView';
import AlertsPanel from './components/AlertsPanel';
import HealthStatus from './components/HealthStatus';
import { AlertProvider } from './stores/AlertContext';
import { useRealtime } from './realtime/useRealtime';
import { useAlertsPolling } from './hooks/useAlerts';
import {
  LayoutDashboard,
  Users,
  Bike,
  Receipt,
  Banknote,
  BarChart3,
  LogOut,
  Shield,
  Settings,
  FileText,
  Menu,
  X,
  AlertTriangle,
  Copy,
  Check,
  Building2,
  UserCog,
  UserCircle,
  HelpCircle,
  Activity,
} from 'lucide-react';
import type {
  AnalyticsSummary,
  AppTab,
  ClienteOut,
  CobrancaOut,
  ContratoOut,
  MotoOut,
  Paginated,
  RecentActivityItem,
} from './apiTypes';
import { fetchAllPaginated } from './utils/fetchPaginated';
import { formatBrl, formatDate, roleLabel } from './utils/format';
import { parseApiError } from './utils/apiError';
import ErrorBanner from './components/ErrorBanner';
import ReloadPrompt from './components/ReloadPrompt';
import InstallPrompt from './components/InstallPrompt';
import TourWelcomeBanner from './components/TourWelcomeBanner';
import { dismissOwnerTourBanner, shouldShowOwnerTourBanner, isOwnerTourEligible } from './guide/ownerTourSteps';
import { useOwnerTour } from './guide/useOwnerTour';

const TAB_LABELS: Partial<Record<AppTab, string>> = {
  dashboard: 'Visão Geral',
  motos: 'Gestão de Frota',
  clientes: 'Clientes',
  contratos: 'Contratos',
  financeiro: 'Financeiro',
  metricas: 'Métricas',
  cobrancas: 'Cobranças',
  ajustes: 'Ajustes',
  'admin-operacoes': 'Operações',
  'admin-usuarios': 'Usuários',
  'admin-ops': 'Filas & Ops',
  conta: 'Minha Conta',
};

const Dashboard = () => {
  const {
    user,
    logout,
    api,
    operacaoScopeId,
    setOperacaoScopeId,
    operacaoNome,
    operacoes,
    activeTab,
    setActiveTab,
    navigateToContracts,
    registerOwnerTour,
  } = useAuth();
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
  const [isMobileNav, setIsMobileNav] = React.useState(false);
  const [stats, setStats] = React.useState<AnalyticsSummary | null>(null);

  React.useEffect(() => {
    const mq = window.matchMedia('(max-width: 768px)');
    const update = () => {
      setIsMobileNav(mq.matches);
      if (!mq.matches) setSidebarOpen(false);
    };
    update();
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);

  React.useEffect(() => {
    if (!sidebarOpen) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setSidebarOpen(false);
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = prevOverflow;
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [sidebarOpen]);
  const [recentActivity, setRecentActivity] = React.useState<RecentActivityItem[]>([]);
  const [inadimplentes, setInadimplentes] = React.useState<ContratoOut[]>([]);
  const [clientes, setClientes] = React.useState<ClienteOut[]>([]);
  const [cobrancas, setCobrancas] = React.useState<CobrancaOut[]>([]);
  const [totalMotos, setTotalMotos] = React.useState(0);
  const [totalClientes, setTotalClientes] = React.useState(0);
  const [totalContratos, setTotalContratos] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState('');
  const [copiedContratoId, setCopiedContratoId] = React.useState<number | null>(null);
  const [showTourBanner, setShowTourBanner] = React.useState(false);
  const activeTabRef = React.useRef(activeTab);
  activeTabRef.current = activeTab;

  const { startTour, resetTour } = useOwnerTour({
    role: user?.tipo,
    setActiveTab,
    getActiveTab: () => activeTabRef.current,
  });

  const showOwnerTour = isOwnerTourEligible(user?.tipo);

  React.useEffect(() => {
    if (!showOwnerTour) return;
    registerOwnerTour({ start: () => void startTour(), reset: () => resetTour() });
  }, [registerOwnerTour, resetTour, showOwnerTour, startTour]);

  React.useEffect(() => {
    setShowTourBanner(
      shouldShowOwnerTourBanner(activeTab, loading, showOwnerTour)
    );
  }, [showOwnerTour, activeTab, loading]);

  const isAdmin = user?.tipo === 'admin';
  const showAjustes = true;
  useRealtime({ enabled: isAdmin });
  useAlertsPolling({ pollInterval: 30000, enabled: isAdmin });
  const brandTitle = isAdmin ? 'MotoPay Admin' : operacaoNome ? `MotoPay · ${operacaoNome}` : 'MotoPay Painel';
  const roleDisplay =
    user?.tipo === 'dono' && operacaoNome
      ? `${roleLabel(user.tipo)} — ${operacaoNome}`
      : roleLabel(user?.tipo);

  const cobrancaByContrato = React.useMemo(() => {
    const map: Record<number, CobrancaOut> = {};
    for (const c of cobrancas) {
      if (c.status === 'pendente' || c.status === 'atrasado') {
        map[c.contrato_id] = c;
      }
    }
    return map;
  }, [cobrancas]);

  const clienteMap = React.useMemo(
    () => Object.fromEntries(clientes.map((c) => [c.id, c])),
    [clientes]
  );

  const fleetPct =
    totalMotos > 0 ? Math.round(((stats?.motos_ativas ?? 0) / totalMotos) * 100) : 0;

  const showSetupChecklist =
    !loading && (totalMotos === 0 || totalClientes === 0 || totalContratos === 0);

  const fetchStats = async () => {
    setLoading(true);
    setError('');
    try {
      const [sRes, aRes, ctTotalRes, ctInadRes, clTotalRes, clItems, cobItems, motoRes] =
        await Promise.all([
        api.get<AnalyticsSummary>('/api/v1/analytics/summary'),
        api.get<RecentActivityItem[]>('/api/v1/analytics/recent-activity'),
        api.get<Paginated<ContratoOut>>('/api/v1/contratos', { params: { limit: 1, offset: 0 } }),
        api.get<Paginated<ContratoOut>>('/api/v1/contratos', {
          params: { limit: 50, offset: 0, inadimplente: true },
        }),
        api.get<Paginated<ClienteOut>>('/api/v1/clientes', { params: { limit: 1, offset: 0 } }),
        fetchAllPaginated<ClienteOut>(api, '/api/v1/clientes'),
        fetchAllPaginated<CobrancaOut>(api, '/api/v1/cobrancas'),
        api.get<Paginated<MotoOut>>('/api/v1/motos', { params: { limit: 1, offset: 0 } }),
      ]);
      setStats(sRes.data);
      setRecentActivity(aRes.data);
      setInadimplentes(ctInadRes.data.items);
      setClientes(clItems);
      setCobrancas(cobItems);
      setTotalMotos(motoRes.data.total);
      setTotalClientes(clTotalRes.data.total);
      setTotalContratos(ctTotalRes.data.total);
    } catch (e) {
      setError(parseApiError(e, 'Erro ao buscar dados do dashboard'));
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    if (activeTab === 'dashboard') void fetchStats();
  }, [activeTab, api]);

  const goToTab = (tab: AppTab) => {
    setActiveTab(tab);
    setSidebarOpen(false);
  };

  const copyPix = async (contratoId: number, pix: string) => {
    await navigator.clipboard.writeText(pix);
    setCopiedContratoId(contratoId);
    setTimeout(() => setCopiedContratoId(null), 2000);
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return (
          <>
            {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

            {showTourBanner && showOwnerTour && (
              <TourWelcomeBanner
                onStart={() => {
                  setShowTourBanner(false);
                  void startTour();
                }}
                onDismiss={() => {
                  dismissOwnerTourBanner();
                  setShowTourBanner(false);
                }}
              />
            )}

            {showSetupChecklist && (
              <div
                className="glass card setup-checklist animate-fade"
                style={{ marginBottom: 24 }}
                data-tour="dashboard-alerts"
              >
                <h3>Primeiros passos</h3>
                <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: 16 }}>
                  Configure sua operação para começar a gerenciar locações.
                </p>
                <ul className="checklist">
                  <li className={totalMotos > 0 ? 'done' : ''}>
                    <Check size={14} /> Cadastrar motos na frota
                  </li>
                  <li className={totalClientes > 0 ? 'done' : ''}>
                    <Check size={14} /> Cadastrar clientes
                  </li>
                  <li className={totalContratos > 0 ? 'done' : ''}>
                    <Check size={14} /> Criar um contrato de locação
                  </li>
                </ul>
                <div className="checklist-actions">
                  <button type="button" className="btn-primary" onClick={() => goToTab('motos')}>
                    Ir para Frota
                  </button>
                  <button type="button" className="btn-secondary" onClick={() => goToTab('clientes')}>
                    Ir para Clientes
                  </button>
                  <button type="button" className="btn-secondary" onClick={() => goToTab('contratos')}>
                    Ir para Contratos
                  </button>
                </div>
              </div>
            )}

            <div className="stats-grid" data-tour="stats-grid">
              <StatCard
                title="Receita Bruta"
                value={
                  loading
                    ? '...'
                    : formatBrl(stats?.receita_total ?? 0)
                }
                trend="Total recebido"
              />
              <StatCard
                title="Lucro Líquido"
                value={loading ? '...' : formatBrl(stats?.lucro_liquido ?? 0)}
                trend="Receitas − despesas"
              />
              <StatCard
                title="Cobranças em Atraso"
                value={loading ? '...' : String(stats?.cobrancas_atrasadas ?? 0)}
                trend="Requer atenção"
                negative={(stats?.cobrancas_atrasadas ?? 0) > 0}
              />
              <StatCard
                title="Inadimplentes"
                value={loading ? '...' : String(stats?.clientes_inadimplentes ?? 0)}
                trend="Contratos em atraso"
                negative={(stats?.clientes_inadimplentes ?? 0) > 0}
              />
            </div>

            <div className="main-grid">
              <div className="glass card animate-fade" style={{ animationDelay: '0.1s' }}>
                <h3>Atividade Recente</h3>
                <div className="placeholder-list">
                  {loading ? (
                    <p>Carregando dados...</p>
                  ) : recentActivity.length === 0 ? (
                    <p className="text-muted">Nenhuma atividade.</p>
                  ) : (
                    recentActivity.map((act) => (
                      <div key={act.id} className="list-item">
                        <div className={`dot ${act.tipo === 'receita' ? 'success' : 'danger'}`} />
                        <div className="item-text">
                          <p>{act.descricao}</p>
                          <span>
                            {formatDate(act.data)} — {formatBrl(act.valor)}
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="side-stack">
                <div className="glass card animate-fade" style={{ animationDelay: '0.2s' }}>
                  <h3>Status da Frota</h3>
                  <div className="progress-box">
                    <p>
                      Alugadas: {stats?.motos_ativas ?? 0} de {totalMotos} motos ({fleetPct}%)
                    </p>
                    <div className="progress-bar">
                      <div className="fill" style={{ width: `${fleetPct}%` }} />
                    </div>
                  </div>
                  <p className="text-muted" style={{ fontSize: '0.8rem', marginTop: 12 }}>
                    Pendentes: {stats?.cobrancas_pendentes ?? 0} · Despesas:{' '}
                    {loading ? '...' : formatBrl(stats?.despesa_total ?? 0)}
                  </p>
                </div>

                <div
                  className="glass card animate-fade"
                  style={{ animationDelay: '0.25s' }}
                  data-tour={showSetupChecklist ? undefined : 'dashboard-alerts'}
                >
                  <div className="card-title-row">
                    <h3>
                      <AlertTriangle size={18} color="var(--danger)" /> Inadimplência
                    </h3>
                    {inadimplentes.length > 0 && (
                      <button
                        type="button"
                        className="link-btn"
                        onClick={() => navigateToContracts('inadimplentes')}
                      >
                        Ver todos
                      </button>
                    )}
                  </div>
                  {loading ? (
                    <p className="text-muted">Carregando...</p>
                  ) : inadimplentes.length === 0 ? (
                    <p className="text-muted">Nenhum contrato inadimplente.</p>
                  ) : (
                    <div className="inad-list">
                      {inadimplentes.slice(0, 5).map((ct) => {
                        const cl = clienteMap[ct.cliente_id];
                        const cob = cobrancaByContrato[ct.id];
                        return (
                          <div key={ct.id} className="inad-item">
                            <div>
                              <strong>{cl?.nome ?? `Cliente #${ct.cliente_id}`}</strong>
                              <span className="text-muted">
                                {ct.dias_atraso_acumulado} dia(s) · venc.{' '}
                                {formatDate(ct.proximo_vencimento)}
                              </span>
                            </div>
                            {cob?.pix_copia_cola && (
                              <button
                                type="button"
                                className="mini-pix-btn"
                                onClick={() => void copyPix(ct.id, cob.pix_copia_cola!)}
                              >
                                {copiedContratoId === ct.id ? (
                                  <Check size={12} />
                                ) : (
                                  <Copy size={12} />
                                )}
                              </button>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </>
        );
      case 'motos':
        return <FleetView />;
      case 'clientes':
        return <ClientsView />;
      case 'contratos':
        return <ContractsView />;
      case 'financeiro':
        return <FinanceView />;
      case 'metricas':
        return <MetricsView />;
      case 'cobrancas':
        return <ChargesView />;
      case 'ajustes':
        return showAjustes ? <SettingsView /> : null;
      case 'admin-operacoes':
        return isAdmin ? <AdminOperacoesView /> : null;
      case 'admin-usuarios':
        return isAdmin ? <AdminUsuariosView /> : null;
      case 'admin-ops':
        return isAdmin ? <OpsDashboardView /> : null;
      case 'conta':
        return <AccountView />;
      default:
        return null;
    }
  };

  return (
    <div className="dashboard-layout">
      {sidebarOpen && (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="Fechar menu"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <aside
        id="app-sidebar"
        className={`sidebar ${isMobileNav ? 'sidebar-solid' : 'glass'} ${sidebarOpen ? 'open' : ''}`}
        aria-hidden={isMobileNav && !sidebarOpen}
      >
        <div className="sidebar-header">
          <Shield size={24} color="#6366f1" />
          <span className="brand-font sidebar-brand">{brandTitle}</span>
          <button
            type="button"
            className="sidebar-close mobile-only"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={20} />
          </button>
        </div>

        <nav className="nav-menu" data-tour="nav-menu">
          <NavItem
            icon={<LayoutDashboard size={20} />}
            label="Visão Geral"
            active={activeTab === 'dashboard'}
            onClick={() => goToTab('dashboard')}
            tourId="nav-dashboard"
          />
          <NavItem
            icon={<Bike size={20} />}
            label="Gestão de Frota"
            active={activeTab === 'motos'}
            onClick={() => goToTab('motos')}
            tourId="nav-motos"
          />
          <NavItem
            icon={<Users size={20} />}
            label="Clientes"
            active={activeTab === 'clientes'}
            onClick={() => goToTab('clientes')}
            tourId="nav-clientes"
          />
          <NavItem
            icon={<FileText size={20} />}
            label="Contratos"
            active={activeTab === 'contratos'}
            onClick={() => goToTab('contratos')}
            tourId="nav-contratos"
          />
          <NavItem
            icon={<Receipt size={20} />}
            label="Financeiro"
            active={activeTab === 'financeiro'}
            onClick={() => goToTab('financeiro')}
            tourId="nav-financeiro"
          />
          <NavItem
            icon={<BarChart3 size={20} />}
            label="Métricas"
            active={activeTab === 'metricas'}
            onClick={() => goToTab('metricas')}
            tourId="nav-metricas"
          />
          <NavItem
            icon={<Banknote size={20} />}
            label="Cobranças"
            active={activeTab === 'cobrancas'}
            onClick={() => goToTab('cobrancas')}
            tourId="nav-cobrancas"
          />
          {showAjustes && (
            <NavItem
              icon={<Settings size={20} />}
              label="Ajustes"
              active={activeTab === 'ajustes'}
              onClick={() => goToTab('ajustes')}
              tourId="nav-ajustes"
            />
          )}
          {isAdmin && (
            <>
              <NavItem
                icon={<Building2 size={20} />}
                label="Operações"
                active={activeTab === 'admin-operacoes'}
                onClick={() => goToTab('admin-operacoes')}
              />
              <NavItem
                icon={<UserCog size={20} />}
                label="Usuários"
                active={activeTab === 'admin-usuarios'}
                onClick={() => goToTab('admin-usuarios')}
              />
              <NavItem
                icon={<Activity size={20} />}
                label="Filas & Ops"
                active={activeTab === 'admin-ops'}
                onClick={() => goToTab('admin-ops')}
              />
            </>
          )}
        </nav>

        <div className="sidebar-footer">
          {showOwnerTour && (
            <button
              type="button"
              className="conta-link tour-link"
              data-tour="tour-sidebar-btn"
              onClick={() => void startTour()}
            >
              <HelpCircle size={18} /> Tour guiado
            </button>
          )}
          <button type="button" className="conta-link" onClick={() => goToTab('conta')}>
            <UserCircle size={18} /> Minha conta
          </button>
          <div className="user-info">
            <div className="avatar">{user?.email?.[0].toUpperCase()}</div>
            <div className="details">
              <p className="email">{user?.email}</p>
              <p className="role">{roleDisplay}</p>
            </div>
          </div>
          <button type="button" className="logout-btn" onClick={logout}>
            <LogOut size={18} /> Sair
          </button>
        </div>
      </aside>

      <main className="content">
        <header className="content-header animate-fade">
          <div className="header-row">
            <div className="header-left">
              <button
                type="button"
                className="menu-btn mobile-only"
                onClick={() => setSidebarOpen(true)}
                aria-label="Abrir menu"
                aria-expanded={isMobileNav ? sidebarOpen : undefined}
                aria-controls="app-sidebar"
              >
                <Menu size={22} />
              </button>
              <div>
                <h1>{TAB_LABELS[activeTab] ?? 'Painel'}</h1>
                <p className="text-muted">
                  Bem-vindo, {user?.email.split('@')[0]}
                </p>
              </div>
            </div>
            <div className="header-actions">
              {isAdmin && (
                <>
                  <HealthStatus />
                  <AlertsPanel />
                </>
              )}
              {isAdmin && (
                <div className="scope-select" data-tour="scope-select">
                  <label className="input-label scope-label">Operação (escopo)</label>
                  <select
                    className="input-field"
                    value={operacaoScopeId ?? ''}
                    onChange={(e) => {
                      const v = e.target.value;
                      setOperacaoScopeId(v === '' ? null : parseInt(v, 10));
                    }}
                  >
                    <option value="">Todas</option>
                    {operacoes.map((op) => (
                      <option key={op.id} value={op.id}>
                        {op.nome}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              {activeTab === 'dashboard' && (
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => void fetchStats()}
                  disabled={loading}
                >
                  {loading ? '...' : 'Atualizar'}
                </button>
              )}
            </div>
          </div>
        </header>

        {renderContent()}
      </main>

      <style jsx>{`
        .dashboard-layout {
          display: flex;
          min-height: 100vh;
        }
        .sidebar-backdrop {
          display: none;
        }
        .sidebar {
          width: var(--sidebar-width);
          height: 100vh;
          height: 100dvh;
          max-height: 100dvh;
          position: fixed;
          left: 0;
          top: 0;
          padding-bottom: env(safe-area-inset-bottom, 0px);
          border-radius: 0 24px 24px 0;
          display: flex;
          flex-direction: column;
          z-index: 200;
        }
        .sidebar-solid {
          background: var(--bg-sidebar);
          backdrop-filter: none;
          -webkit-backdrop-filter: none;
          border: none;
          border-right: 1px solid var(--glass-border);
          box-shadow: none;
        }
        .sidebar-header {
          padding: 18px 20px;
          padding-top: calc(12px + env(safe-area-inset-top, 0px));
          display: flex;
          align-items: center;
          gap: 12px;
          font-size: 1rem;
          font-weight: 700;
          flex-shrink: 0;
        }
        .sidebar-brand {
          flex: 1;
          line-height: 1.2;
          font-size: 0.95rem;
        }
        .sidebar-close,
        .menu-btn {
          display: inline-flex;
          background: none;
          border: none;
          color: var(--text-muted);
          cursor: pointer;
          padding: 10px;
          min-width: 44px;
          min-height: 44px;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          -webkit-tap-highlight-color: transparent;
          touch-action: manipulation;
          border-radius: 10px;
        }
        .sidebar-close:hover,
        .menu-btn:hover {
          color: white;
          background: rgba(255, 255, 255, 0.06);
        }
        .mobile-only {
          display: none;
        }
        .nav-menu {
          padding: 12px 16px;
          flex: 1;
          min-height: 0;
          overflow-y: auto;
          overscroll-behavior: contain;
          -webkit-overflow-scrolling: touch;
        }
        .content {
          margin-left: var(--sidebar-width);
          flex: 1;
          padding: 24px 32px calc(40px + env(safe-area-inset-bottom, 0px));
          padding-left: max(32px, env(safe-area-inset-left, 0px));
          padding-right: max(32px, env(safe-area-inset-right, 0px));
          width: calc(100% - var(--sidebar-width));
          min-height: 0;
        }
        .content-header {
          margin-bottom: 32px;
        }
        .header-row {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          flex-wrap: wrap;
          gap: 16px;
        }
        .header-left {
          display: flex;
          align-items: flex-start;
          gap: 12px;
        }
        .header-actions {
          display: flex;
          align-items: flex-end;
          gap: 12px;
          flex-wrap: wrap;
        }
        .scope-select {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .scope-label {
          margin-bottom: 0;
          font-size: 0.75rem;
        }
        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 20px;
          margin-bottom: 32px;
        }
        .stat-card {
          padding: 24px;
        }
        .stat-value {
          font-size: 1.6rem;
          font-weight: 700;
          margin: 8px 0;
          font-family: 'Outfit', sans-serif;
        }
        .trend {
          font-size: 0.8rem;
          font-weight: 600;
          padding: 4px 8px;
          border-radius: 6px;
          background: rgba(16, 185, 129, 0.1);
          color: var(--accent);
        }
        .trend.negative {
          background: rgba(239, 68, 68, 0.1);
          color: var(--danger);
        }
        .main-grid {
          display: grid;
          grid-template-columns: 2fr 1fr;
          gap: 24px;
        }
        .side-stack {
          display: flex;
          flex-direction: column;
          gap: 24px;
        }
        .card {
          padding: 24px;
        }
        .card-title-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }
        .card-title-row h3 {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 1rem;
        }
        .link-btn {
          background: none;
          border: none;
          color: var(--primary);
          cursor: pointer;
          font-size: 0.8rem;
        }
        .inad-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .inad-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 8px;
          padding-bottom: 10px;
          border-bottom: 1px solid var(--glass-border);
          font-size: 0.85rem;
        }
        .inad-item span {
          display: block;
          font-size: 0.75rem;
        }
        .mini-pix-btn {
          background: var(--primary-glow);
          border: 1px solid var(--primary);
          color: var(--primary);
          border-radius: 6px;
          padding: 6px;
          cursor: pointer;
          flex-shrink: 0;
        }
        .sidebar-footer {
          padding: 16px;
          padding-bottom: calc(16px + env(safe-area-inset-bottom, 0px));
          border-top: 1px solid var(--glass-border);
          flex-shrink: 0;
        }
        .conta-link {
          width: 100%;
          background: rgba(255, 255, 255, 0.04);
          border: 1px solid var(--glass-border);
          color: var(--text-muted);
          padding: 10px 12px;
          border-radius: 8px;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 0.85rem;
          margin-bottom: 12px;
        }
        .conta-link:hover {
          color: white;
          background: rgba(255, 255, 255, 0.08);
        }
        .tour-link {
          border: 1px solid rgba(99, 102, 241, 0.35);
          color: #c7d2fe;
          background: linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(79, 70, 229, 0.08));
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
        }
        .tour-link:hover {
          color: white;
          border-color: rgba(129, 140, 248, 0.55);
          background: linear-gradient(135deg, rgba(99, 102, 241, 0.28), rgba(79, 70, 229, 0.18));
        }
        .setup-checklist h3 {
          margin-bottom: 8px;
        }
        .checklist {
          list-style: none;
          padding: 0;
          margin: 0 0 16px;
        }
        .checklist li {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 0;
          font-size: 0.9rem;
          color: var(--text-muted);
        }
        .checklist li.done {
          color: var(--accent);
        }
        .checklist-actions {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
        }
        .btn-secondary {
          background: var(--secondary);
          color: white;
          border: none;
          padding: 10px 16px;
          border-radius: 8px;
          cursor: pointer;
        }
        .user-info {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 16px;
        }
        .avatar {
          width: 40px;
          height: 40px;
          background: var(--primary);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          flex-shrink: 0;
        }
        .details .email {
          font-size: 0.85rem;
          font-weight: 600;
          word-break: break-all;
        }
        .details .role {
          font-size: 0.75rem;
          color: var(--text-muted);
        }
        .logout-btn {
          width: 100%;
          background: rgba(239, 68, 68, 0.1);
          color: var(--danger);
          border: none;
          padding: 10px;
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          cursor: pointer;
          -webkit-tap-highlight-color: transparent;
          touch-action: manipulation;
          min-height: 44px;
        }
        .logout-btn:hover {
          background: var(--danger);
          color: white;
        }
        .list-item {
          display: flex;
          gap: 12px;
          margin-top: 16px;
          padding-bottom: 16px;
          border-bottom: 1px solid var(--glass-border);
        }
        .dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: var(--primary);
          margin-top: 6px;
          flex-shrink: 0;
        }
        .dot.success {
          background: var(--accent);
        }
        .dot.danger {
          background: var(--danger);
        }
        .item-text p {
          font-size: 0.9rem;
        }
        .item-text span {
          font-size: 0.75rem;
          color: var(--text-muted);
        }
        .progress-box {
          margin-top: 12px;
        }
        .progress-box p {
          font-size: 0.85rem;
          margin-bottom: 8px;
          color: var(--text-muted);
        }
        .progress-bar {
          height: 8px;
          background: var(--secondary);
          border-radius: 4px;
          overflow: hidden;
        }
        .fill {
          height: 100%;
          background: var(--primary);
        }
        @media (max-width: 1024px) {
          .main-grid {
            grid-template-columns: 1fr;
          }
        }
        @media (max-width: 768px) {
          .mobile-only {
            display: inline-flex;
          }
          .sidebar {
            width: min(var(--sidebar-width), calc(100vw - 48px));
            max-width: 100%;
            transform: translateX(-100%);
            transition: transform 0.25s ease;
            pointer-events: none;
            background: var(--bg-sidebar);
            backdrop-filter: none;
            -webkit-backdrop-filter: none;
            box-shadow: none;
          }
          .sidebar.open {
            transform: translateX(0);
            pointer-events: auto;
            box-shadow: 8px 0 32px rgba(0, 0, 0, 0.45);
          }
          .sidebar-backdrop {
            display: block;
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.55);
            z-index: 150;
            border: none;
            cursor: pointer;
            -webkit-tap-highlight-color: transparent;
          }
          .content {
            margin-left: 0;
            width: 100%;
            padding: 16px;
            padding-top: calc(12px + env(safe-area-inset-top, 0px));
            padding-bottom: calc(28px + env(safe-area-inset-bottom, 0px));
            padding-left: max(16px, env(safe-area-inset-left, 0px));
            padding-right: max(16px, env(safe-area-inset-right, 0px));
          }
          .content-header {
            margin-bottom: 20px;
          }
          .header-left {
            align-items: center;
            min-width: 0;
            flex: 1;
          }
          .header-left h1 {
            font-size: 1.25rem;
            line-height: 1.2;
          }
          .header-left .text-muted {
            font-size: 0.8rem;
          }
          .header-row {
            gap: 12px;
          }
          .header-actions {
            width: 100%;
            flex-wrap: wrap;
          }
          .scope-select {
            flex: 1;
            min-width: min(100%, 200px);
          }
          .scope-select .input-field {
            width: 100%;
          }
        }
        @media (max-width: 640px) {
          .header-row {
            flex-direction: column;
            align-items: stretch;
          }
          .header-actions .btn-primary {
            width: 100%;
          }
        }
        @media (max-width: 480px) {
          .stats-grid {
            grid-template-columns: 1fr;
          }
          .sidebar-header .sidebar-brand {
            font-size: 0.88rem;
          }
        }
      `}</style>
    </div>
  );
};

const NavItem = ({
  icon,
  label,
  active,
  onClick,
  tourId,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
  tourId?: string;
}) => (
  <div
    className={`nav-item ${active ? 'active' : ''}`}
    onClick={onClick}
    role="button"
    tabIndex={0}
    data-tour={tourId}
  >
    {icon}
    <span>{label}</span>
    <style jsx>{`
      .nav-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 14px 16px;
        min-height: 48px;
        border-radius: 12px;
        color: var(--text-muted);
        cursor: pointer;
        transition: var(--transition);
        margin-bottom: 4px;
        -webkit-tap-highlight-color: transparent;
        touch-action: manipulation;
      }
      .nav-item:hover {
        background: rgba(255, 255, 255, 0.05);
        color: white;
      }
      .nav-item.active {
        background: var(--primary-glow);
        color: var(--primary);
        border-left: 4px solid var(--primary);
        border-radius: 4px 12px 12px 4px;
      }
    `}</style>
  </div>
);

const StatCard = ({
  title,
  value,
  trend,
  negative = false,
}: {
  title: string;
  value: string;
  trend: string;
  negative?: boolean;
}) => (
  <div className="glass stat-card animate-fade">
    <p className="text-muted" style={{ fontSize: '0.9rem' }}>
      {title}
    </p>
    <div className="stat-value">{value}</div>
    <span className={`trend ${negative ? 'negative' : ''}`}>{trend}</span>
    <style jsx>{`
      .stat-value {
        font-size: 1.6rem;
        font-weight: 700;
        margin: 8px 0;
        font-family: 'Outfit', sans-serif;
      }
      .trend {
        font-size: 0.8rem;
        font-weight: 600;
        padding: 4px 8px;
        border-radius: 6px;
        background: rgba(16, 185, 129, 0.1);
        color: var(--accent);
      }
      .trend.negative {
        background: rgba(239, 68, 68, 0.1);
        color: var(--danger);
      }
    `}</style>
  </div>
);

const MainApp = () => {
  const { token, user } = useAuth();
  if (!token) return <Login />;
  if (!user) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }} className="text-muted">
        Carregando...
      </div>
    );
  }
  return <Dashboard />;
};

function App() {
  return (
    <AuthProvider>
      <AlertProvider>
        <>
          <ReloadPrompt />
          <InstallPrompt />
          <MercadoPagoProvider>
            <MainApp />
          </MercadoPagoProvider>
        </>
      </AlertProvider>
    </AuthProvider>
  );
}

export default App;
