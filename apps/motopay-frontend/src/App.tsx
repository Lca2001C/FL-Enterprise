import React from 'react';
import { AuthProvider, useAuth } from './AuthContext';
import Login from './Login';
import FleetView from './FleetView';
import ClientsView from './ClientsView';
import FinanceView from './FinanceView';
import MetricsView from './MetricsView';
import ChargesView from './ChargesView';
import SettingsView from './SettingsView';
import { LayoutDashboard, Users, Bike, Receipt, BarChart3, LogOut, Shield, Settings } from 'lucide-react';

type OperacaoOpt = { id: number; nome: string };

type SummaryStats = {
  receita_total?: number;
  lucro_liquido?: number;
  cobrancas_atrasadas?: number;
  cobrancas_pendentes?: number;
  motos_ativas?: number;
};

type RecentActivityItem = {
  id: number;
  tipo: string;
  descricao: string;
  data: string;
  valor: number;
};

const Dashboard = () => {
  const { user, logout, api, operacaoScopeId, setOperacaoScopeId } = useAuth();
  const [activeTab, setActiveTab] = React.useState('dashboard');
  const [stats, setStats] = React.useState<SummaryStats | null>(null);
  const [recentActivity, setRecentActivity] = React.useState<RecentActivityItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [operacoes, setOperacoes] = React.useState<OperacaoOpt[]>([]);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const [sRes, aRes] = await Promise.all([
        api.get('/api/v1/analytics/summary'),
        api.get('/api/v1/analytics/recent-activity'),
      ]);
      setStats(sRes.data as SummaryStats);
      setRecentActivity(aRes.data as RecentActivityItem[]);
    } catch (e) {
      console.error("Erro ao buscar stats", e);
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    if (activeTab === 'dashboard') void fetchStats();
  }, [activeTab, api]);

  React.useEffect(() => {
    if (user?.tipo !== 'admin') {
      setOperacoes([]);
      return;
    }
    void api
      .get<OperacaoOpt[]>('/api/v1/operacoes')
      .then((r) => setOperacoes(r.data))
      .catch(() => setOperacoes([]));
  }, [user?.tipo, api]);
  
  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return (
          <>
            <div className="stats-grid">
              <StatCard 
                title="Receita Bruta" 
                value={loading ? "..." : `R$ ${Number(stats?.receita_total || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`} 
                trend="+80%" 
              />
              <StatCard 
                title="Lucro Líquido" 
                value={loading ? "..." : `R$ ${Number(stats?.lucro_liquido || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`} 
                trend="Saldo Real" 
              />
              <StatCard 
                title="Cobranças em Atraso" 
                value={loading ? "..." : (stats?.cobrancas_atrasadas || 0).toString()} 
                trend="Crítico" 
                negative={(stats?.cobrancas_atrasadas || 0) > 0} 
              />
              <StatCard 
                title="Cobranças Pendentes" 
                value={loading ? "..." : (stats?.cobrancas_pendentes || 0).toString()} 
                trend="A vencer" 
              />
            </div>

            <div className="main-grid">
              <div className="glass card animate-fade" style={{ animationDelay: '0.1s' }}>
                <h3>Atividade Recente</h3>
                <div className="placeholder-list">
                  {loading ? <p>Carregando dados...</p> : recentActivity.length === 0 ? <p>Nenhuma atividade.</p> : recentActivity.map(act => (
                    <div key={act.id} className="list-item">
                      <div className={`dot ${act.tipo === 'receita' ? 'success' : 'danger'}`}></div>
                      <div className="item-text">
                        <p>{act.descricao}</p>
                        <span>{new Date(act.data).toLocaleDateString('pt-BR')} - R$ {Number(act.valor).toLocaleString('pt-BR')}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              
              <div className="glass card animate-fade" style={{ animationDelay: '0.2s' }}>
                <h3>Status da Frota</h3>
                <div className="chart-placeholder">
                  <div className="progress-box">
                    <p>Motos Alugadas ({stats?.motos_ativas || 0})</p>
                    <div className="progress-bar">
                      <div 
                        className="fill" 
                        style={{ width: `${Math.min((stats?.motos_ativas || 0) * 10, 100)}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </>
        );
      case 'motos': return <FleetView />;
      case 'clientes': return <ClientsView />;
      case 'financeiro': return <FinanceView />;
      case 'metricas': return <MetricsView />;
      case 'cobrancas': return <ChargesView />;
      case 'ajustes': return <SettingsView />;
      default:
        return (
          <div className="glass card animate-fade" style={{ padding: '100px', textAlign: 'center' }}>
            <h2 className="brand-font">Módulo em Desenvolvimento</h2>
            <p className="text-muted">A tela de {activeTab} será implementada em breve.</p>
          </div>
        );
    }
  };

  return (
    <div className="dashboard-layout">
      <aside className="sidebar glass">
        <div className="sidebar-header">
          <Shield size={24} color="#6366f1" />
          <span className="brand-font">MotoPay Admin</span>
        </div>
        
        <nav className="nav-menu">
          <NavItem 
            icon={<LayoutDashboard size={20} />} 
            label="Visão Geral" 
            active={activeTab === 'dashboard'} 
            onClick={() => setActiveTab('dashboard')}
          />
          <NavItem 
            icon={<Bike size={20} />} 
            label="Gestão de Frota" 
            active={activeTab === 'motos'} 
            onClick={() => setActiveTab('motos')}
          />
          <NavItem 
            icon={<Users size={20} />} 
            label="Clientes" 
            active={activeTab === 'clientes'} 
            onClick={() => setActiveTab('clientes')}
          />
          <NavItem 
            icon={<Receipt size={20} />} 
            label="Financeiro" 
            active={activeTab === 'financeiro'} 
            onClick={() => setActiveTab('financeiro')}
          />
          <NavItem 
            icon={<BarChart3 size={20} />} 
            label="Métricas" 
            active={activeTab === 'metricas'} 
            onClick={() => setActiveTab('metricas')}
          />
          <NavItem 
            icon={<Receipt size={20} />} 
            label="Cobranças" 
            active={activeTab === 'cobrancas'} 
            onClick={() => setActiveTab('cobrancas')}
          />
          <NavItem 
            icon={<Settings size={20} />} 
            label="Ajustes" 
            active={activeTab === 'ajustes'} 
            onClick={() => setActiveTab('ajustes')}
          />
        </nav>

        <div className="sidebar-footer">
          <div className="user-info">
            <div className="avatar">{user?.email?.[0].toUpperCase()}</div>
            <div className="details">
              <p className="email">{user?.email}</p>
              <p className="role">{user?.tipo}</p>
            </div>
          </div>
          <button className="logout-btn" onClick={logout}>
            <LogOut size={18} /> Sair
          </button>
        </div>
      </aside>

      <main className="content">
        <header className="content-header animate-fade">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
            <div>
              <h1>{activeTab === 'dashboard' ? 'Dashboard Principal' : activeTab.charAt(0).toUpperCase() + activeTab.slice(1)}</h1>
              <p className="text-muted">Bem-vindo de volta, {user?.email.split('@')[0]}</p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              {user?.tipo === 'admin' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <label className="input-label" style={{ marginBottom: 0, fontSize: '0.75rem' }}>
                    Operação (escopo)
                  </label>
                  <select
                    className="input-field"
                    style={{ minWidth: 220, padding: '8px 12px' }}
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
                <button className="btn-primary" onClick={() => void fetchStats()} disabled={loading}>
                  {loading ? '...' : 'Atualizar Dados'}
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
        .sidebar {
          width: var(--sidebar-width);
          height: 100vh;
          position: fixed;
          left: 0;
          top: 0;
          border-radius: 0 24px 24px 0;
          display: flex;
          flex-direction: column;
          z-index: 100;
        }
        .sidebar-header {
          padding: 30px;
          display: flex;
          align-items: center;
          gap: 12px;
          font-size: 1.2rem;
          font-weight: 700;
        }
        .nav-menu {
          padding: 20px;
          flex: 1;
        }
        .content {
          margin-left: var(--sidebar-width);
          flex: 1;
          padding: 40px;
        }
        .content-header {
          margin-bottom: 40px;
        }
        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
          gap: 24px;
          margin-bottom: 40px;
        }
        .stat-card {
          padding: 24px;
        }
        .stat-value {
          font-size: 1.8rem;
          font-weight: 700;
          margin: 8px 0;
          font-family: 'Outfit';
        }
        .trend {
          font-size: 0.85rem;
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
        .card {
          padding: 24px;
        }
        .sidebar-footer {
          padding: 20px;
          border-top: 1px solid var(--glass-border);
        }
        .user-info {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 20px;
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
        }
        .details .email {
          font-size: 0.85rem;
          font-weight: 600;
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
          transition: var(--transition);
        }
        .logout-btn:hover { background: var(--danger); color: white; }
        
        .list-item {
          display: flex;
          gap: 12px;
          margin-top: 16px;
          padding-bottom: 16px;
          border-bottom: 1px solid var(--glass-border);
        }
        .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--primary); margin-top: 6px; }
        .item-text p { font-size: 0.9rem; }
        .item-text span { font-size: 0.75rem; color: var(--text-muted); }
        
        .progress-box { margin-top: 20px; }
        .progress-box p { font-size: 0.85rem; margin-bottom: 8px; color: var(--text-muted); }
        .progress-bar { height: 8px; background: var(--secondary); border-radius: 4px; overflow: hidden; }
        .fill { height: 100%; background: var(--primary); }
        .fill.warning { background: var(--warning); }
      `}</style>
    </div>
  );
};

const NavItem = ({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) => (
  <div className={`nav-item ${active ? 'active' : ''}`} onClick={onClick}>
    {icon}
    <span>{label}</span>
    <style jsx>{`
      .nav-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        border-radius: 12px;
        color: var(--text-muted);
        cursor: pointer;
        transition: var(--transition);
        margin-bottom: 4px;
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
    <p className="text-muted" style={{ fontSize: '0.9rem' }}>{title}</p>
    <div className="stat-value">{value}</div>
    <span className={`trend ${negative ? 'negative' : ''}`}>{trend}</span>
  </div>
);

const MainApp = () => {
  const { token } = useAuth();
  return token ? <Dashboard /> : <Login />;
};

function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}

export default App;
