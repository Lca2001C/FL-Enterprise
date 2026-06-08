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
import PublicPayView from './PublicPayView';
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
        className={`sidebar ${isMobileNav ? 'sidebar-solid' : ''} ${sidebarOpen ? 'open' : ''}`}
        aria-hidden={isMobileNav && !sidebarOpen}
      >
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <Shield size={18} color="#d4a574" />
          </div>
          <div className="sidebar-brand-wrap">
            <span className="brand-font sidebar-brand">MotoPay</span>
            <span className="sidebar-brand-sub">{isAdmin ? 'Admin' : (operacaoNome ?? 'Painel')}</span>
          </div>
          <button
            type="button"
            className="sidebar-close mobile-only"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={18} />
          </button>
        </div>

        <nav className="nav-menu" data-tour="nav-menu">
          <p className="nav-section-label">Principal</p>
          <NavItem
            icon={<LayoutDashboard size={18} />}
            label="Visão Geral"
            active={activeTab === 'dashboard'}
            onClick={() => goToTab('dashboard')}
            tourId="nav-dashboard"
          />
          <NavItem
            icon={<Bike size={18} />}
            label="Frota"
            active={activeTab === 'motos'}
            onClick={() => goToTab('motos')}
            tourId="nav-motos"
          />
          <NavItem
            icon={<Users size={18} />}
            label="Clientes"
            active={activeTab === 'clientes'}
            onClick={() => goToTab('clientes')}
            tourId="nav-clientes"
          />
          <NavItem
            icon={<FileText size={18} />}
            label="Contratos"
            active={activeTab === 'contratos'}
            onClick={() => goToTab('contratos')}
            tourId="nav-contratos"
          />
          <p className="nav-section-label">Financeiro</p>
          <NavItem
            icon={<Receipt size={18} />}
            label="Financeiro"
            active={activeTab === 'financeiro'}
            onClick={() => goToTab('financeiro')}
            tourId="nav-financeiro"
          />
          <NavItem
            icon={<Banknote size={18} />}
            label="Cobranças"
            active={activeTab === 'cobrancas'}
            onClick={() => goToTab('cobrancas')}
            tourId="nav-cobrancas"
          />
          <NavItem
            icon={<BarChart3 size={18} />}
            label="Métricas"
            active={activeTab === 'metricas'}
            onClick={() => goToTab('metricas')}
            tourId="nav-metricas"
          />
          {showAjustes && (
            <>
              <p className="nav-section-label">Sistema</p>
              <NavItem
                icon={<Settings size={18} />}
                label="Ajustes"
                active={activeTab === 'ajustes'}
                onClick={() => goToTab('ajustes')}
                tourId="nav-ajustes"
              />
            </>
          )}
          {isAdmin && (
            <>
              <NavItem
                icon={<Building2 size={18} />}
                label="Operações"
                active={activeTab === 'admin-operacoes'}
                onClick={() => goToTab('admin-operacoes')}
              />
              <NavItem
                icon={<UserCog size={18} />}
                label="Usuários"
                active={activeTab === 'admin-usuarios'}
                onClick={() => goToTab('admin-usuarios')}
              />
              <NavItem
                icon={<Activity size={18} />}
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
              <HelpCircle size={16} /> Tour guiado
            </button>
          )}
          <button type="button" className="conta-link" onClick={() => goToTab('conta')}>
            <UserCircle size={16} /> Minha conta
          </button>
          <div className="user-info">
            <div className="avatar">{user?.email?.[0].toUpperCase()}</div>
            <div className="details">
              <p className="email">{user?.email}</p>
              <p className="role">{roleDisplay}</p>
            </div>
          </div>
          <button type="button" className="logout-btn" onClick={logout}>
            <LogOut size={16} /> Sair
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
                <Menu size={20} />
              </button>
              <div>
                <h2 style={{ fontSize: '1.35rem', fontFamily: "'Playfair Display', serif", fontWeight: 700, marginBottom: 2 }}>
                  {TAB_LABELS[activeTab] ?? 'Painel'}
                </h2>
                <p className="text-muted" style={{ fontSize: '0.82rem' }}>
                  Bem-vindo, <strong style={{ color: 'var(--primary)', fontWeight: 600 }}>{user?.email.split('@')[0]}</strong>
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
          min-height: 100dvh;
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
          display: flex;
          flex-direction: column;
          z-index: 200;
          background: var(--bg-sidebar);
          border-right: 1px solid var(--glass-border);
          box-shadow: 4px 0 24px rgba(0,0,0,0.5);
        }
        .sidebar-solid {
          background: var(--bg-sidebar);
          backdrop-filter: none;
          -webkit-backdrop-filter: none;
        }
        .sidebar-header {
          padding: 20px 18px 16px;
          padding-top: calc(14px + env(safe-area-inset-top, 0px));
          display: flex;
          align-items: center;
          gap: 10px;
          flex-shrink: 0;
          border-bottom: 1px solid var(--glass-border);
        }
        .sidebar-logo {
          width: 34px;
          height: 34px;
          background: rgba(212,165,116,0.12);
          border: 1px solid rgba(212,165,116,0.25);
          border-radius: 9px;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .sidebar-brand-wrap {
          flex: 1;
          min-width: 0;
        }
        .sidebar-brand {
          display: block;
          font-size: 1.05rem;
          font-weight: 700;
          line-height: 1.15;
          color: var(--text-main);
          letter-spacing: 0.01em;
        }
        .sidebar-brand-sub {
          display: block;
          font-size: 0.7rem;
          color: var(--primary);
          font-weight: 500;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          margin-top: 1px;
        }
        .sidebar-close,
        .menu-btn {
          display: inline-flex;
          background: none;
          border: none;
          color: var(--text-muted);
          cursor: pointer;
          padding: 8px;
          min-width: 36px;
          min-height: 36px;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          -webkit-tap-highlight-color: transparent;
          touch-action: manipulation;
          border-radius: 8px;
          transition: var(--transition);
        }
        .sidebar-close:hover,
        .menu-btn:hover {
          color: var(--text-main);
          background: rgba(255,255,255,0.06);
        }
        .mobile-only {
          display: none;
        }
        .nav-menu {
          padding: 8px 12px;
          flex: 1;
          min-height: 0;
          overflow-y: auto;
          overscroll-behavior: contain;
          -webkit-overflow-scrolling: touch;
        }
        .content {
          margin-left: var(--sidebar-width);
          flex: 1;
          padding: 28px 36px calc(48px + env(safe-area-inset-bottom, 0px));
          padding-left: max(36px, env(safe-area-inset-left, 0px));
          padding-right: max(36px, env(safe-area-inset-right, 0px));
          width: calc(100% - var(--sidebar-width));
          min-height: 0;
        }
        .content-header {
          margin-bottom: 32px;
          padding-bottom: 24px;
          border-bottom: 1px solid var(--glass-border);
        }
        .header-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          flex-wrap: wrap;
          gap: 16px;
        }
        .header-left {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .header-actions {
          display: flex;
          align-items: center;
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
          font-size: 0.7rem;
        }
        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
          gap: 18px;
          margin-bottom: 28px;
        }
        .stat-card {
          padding: 22px 24px;
          border-left: 3px solid transparent;
          transition: var(--transition);
        }
        .stat-card:hover {
          border-left-color: var(--primary);
        }
        .stat-title {
          font-size: 0.72rem;
          font-weight: 700;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          color: var(--text-muted);
          margin-bottom: 10px;
        }
        .stat-value {
          font-size: 1.75rem;
          font-weight: 700;
          margin: 0 0 8px;
          font-family: 'Outfit', sans-serif;
          color: var(--text-main);
          line-height: 1;
        }
        .trend {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          font-size: 0.75rem;
          font-weight: 600;
          padding: 3px 8px;
          border-radius: 6px;
          background: rgba(92,191,138,0.1);
          color: var(--success);
          border: 1px solid rgba(92,191,138,0.2);
        }
        .trend.negative {
          background: rgba(224,92,92,0.1);
          color: var(--danger);
          border-color: rgba(224,92,92,0.2);
        }
        .main-grid {
          display: grid;
          grid-template-columns: 2fr 1fr;
          gap: 20px;
        }
        .side-stack {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }
        .card {
          padding: 22px 24px;
        }
        .card-title-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
          padding-bottom: 12px;
          border-bottom: 1px solid var(--glass-border);
        }
        .card-title-row h3 {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 0.92rem;
          font-weight: 600;
          color: var(--text-main);
          letter-spacing: 0.01em;
        }
        .link-btn {
          background: none;
          border: none;
          color: var(--primary);
          cursor: pointer;
          font-size: 0.78rem;
          font-weight: 500;
          opacity: 0.8;
          transition: var(--transition);
          white-space: nowrap;
        }
        .link-btn:hover { opacity: 1; }
        .inad-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .inad-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 8px;
          padding: 10px 12px;
          border-radius: var(--radius-sm);
          background: rgba(255,255,255,0.02);
          font-size: 0.84rem;
          transition: var(--transition);
        }
        .inad-item:hover { background: rgba(212,165,116,0.05); }
        .inad-item span {
          display: block;
          font-size: 0.72rem;
          color: var(--text-muted);
          margin-top: 2px;
        }
        .mini-pix-btn {
          background: rgba(212,165,116,0.1);
          border: 1px solid rgba(212,165,116,0.3);
          color: var(--primary);
          border-radius: 6px;
          padding: 6px;
          cursor: pointer;
          flex-shrink: 0;
          transition: var(--transition);
        }
        .mini-pix-btn:hover { background: rgba(212,165,116,0.2); }
        .sidebar-footer {
          padding: 14px;
          padding-bottom: calc(14px + env(safe-area-inset-bottom, 0px));
          border-top: 1px solid var(--glass-border);
          flex-shrink: 0;
        }
        .conta-link {
          width: 100%;
          background: none;
          border: none;
          color: var(--text-muted);
          padding: 9px 12px;
          border-radius: 8px;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 0.83rem;
          margin-bottom: 8px;
          transition: var(--transition);
        }
        .conta-link:hover {
          color: var(--text-main);
          background: rgba(212,165,116,0.07);
        }
        .tour-link {
          color: var(--primary);
          border: 1px solid rgba(212,165,116,0.2);
          background: rgba(212,165,116,0.06);
        }
        .tour-link:hover {
          background: rgba(212,165,116,0.12);
          border-color: rgba(212,165,116,0.4);
        }
        .setup-checklist h3 { margin-bottom: 8px; }
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
        .checklist li.done { color: var(--success); }
        .checklist-actions {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
        }
        .btn-secondary {
          background: rgba(212,165,116,0.1);
          color: var(--primary);
          border: 1px solid rgba(212,165,116,0.25);
          padding: 10px 18px;
          border-radius: var(--radius-sm);
          cursor: pointer;
          font-size: 0.88rem;
          font-weight: 600;
          transition: var(--transition);
        }
        .btn-secondary:hover { background: rgba(212,165,116,0.18); }
        .user-info {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 10px;
          padding: 10px 4px;
        }
        .avatar {
          width: 34px;
          height: 34px;
          background: linear-gradient(135deg, var(--primary), var(--primary-dark));
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          font-size: 0.85rem;
          color: #1a1410;
          flex-shrink: 0;
        }
        .details .email {
          font-size: 0.78rem;
          font-weight: 600;
          word-break: break-all;
          color: var(--text-main);
        }
        .details .role {
          font-size: 0.7rem;
          color: var(--text-muted);
          margin-top: 1px;
        }
        .logout-btn {
          width: 100%;
          background: rgba(224,92,92,0.08);
          color: var(--danger);
          border: 1px solid rgba(224,92,92,0.15);
          padding: 9px;
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
          background: var(--success);
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
          height: 6px;
          background: rgba(255,255,255,0.06);
          border-radius: 4px;
          overflow: hidden;
        }
        .fill {
          height: 100%;
          background: linear-gradient(90deg, var(--primary-dark), var(--primary));
          border-radius: 4px;
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
    <span className="nav-icon">{icon}</span>
    <span>{label}</span>
    <style jsx>{`
      .nav-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 9px 12px;
        min-height: 40px;
        border-radius: var(--radius-sm);
        color: var(--text-muted);
        cursor: pointer;
        transition: var(--transition);
        margin-bottom: 2px;
        font-size: 0.88rem;
        font-weight: 500;
        border: none;
        background: none;
        width: 100%;
        text-align: left;
        -webkit-tap-highlight-color: transparent;
        touch-action: manipulation;
      }
      .nav-item:hover {
        background: rgba(212,165,116,0.07);
        color: var(--text-main);
      }
      .nav-item.active {
        background: rgba(212,165,116,0.12);
        color: var(--primary);
        border-left: 2px solid var(--primary);
        padding-left: 10px;
      }
      .nav-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border-radius: 6px;
        flex-shrink: 0;
        transition: var(--transition);
      }
      .nav-item.active .nav-icon {
        background: rgba(212,165,116,0.15);
        color: var(--primary);
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
  <div className="glass stat-card glass-card animate-fade">
    <p className="stat-title">{title}</p>
    <div className="stat-value">{value}</div>
    <span className={`trend ${negative ? 'negative' : ''}`}>{trend}</span>
    <style jsx>{`
      .stat-title {
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--text-muted);
        margin-bottom: 10px;
      }
      .stat-value {
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0 0 10px;
        font-family: 'Outfit', sans-serif;
        color: var(--text-main);
        line-height: 1;
      }
      .trend {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 5px;
        background: rgba(92,191,138,0.1);
        color: var(--success);
        border: 1px solid rgba(92,191,138,0.2);
      }
      .trend.negative {
        background: rgba(224,92,92,0.1);
        color: var(--danger);
        border-color: rgba(224,92,92,0.2);
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

function isPublicPayRoute(): boolean {
  return /^\/pay\/[^/]+\/?$/.test(window.location.pathname);
}

function App() {
  if (isPublicPayRoute()) {
    return <PublicPayView />;
  }
  return (
    <AuthProvider>
      <MercadoPagoProvider>
        <AlertProvider>
          <>
            <ReloadPrompt />
            <InstallPrompt />
            <MainApp />
          </>
        </AlertProvider>
      </MercadoPagoProvider>
    </AuthProvider>
  );
}

export default App;
