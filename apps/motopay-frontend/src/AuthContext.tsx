import {
  createContext,
  useContext,
  useState,
  useEffect,
  useMemo,
  useCallback,
  useRef,
  type ReactNode,
} from 'react';
import type { AxiosInstance } from 'axios';
import { createApiClient } from './apiClient';
import { resolveApiBase } from './utils/apiBase';
import type { AppTab, ContractsFilter, OperacaoOut } from './apiTypes';

export type AuthUser = {
  id: number;
  email: string;
  tipo: string;
  operacao_id: number | null;
};

type AuthContextValue = {
  user: AuthUser | null;
  token: string | null;
  apiBase: string;
  setApiBase: (v: string) => void;
  operacaoScopeId: number | null;
  setOperacaoScopeId: (id: number | null) => void;
  operacaoNome: string | null;
  operacoes: OperacaoOut[];
  operacoesLoading: boolean;
  refreshOperacoes: () => Promise<void>;
  api: AxiosInstance;
  login: (email: string, password: string) => Promise<unknown>;
  logout: () => void;
  fetchMe: () => Promise<void>;
  activeTab: AppTab;
  setActiveTab: (tab: AppTab) => void;
  contractsFilter: ContractsFilter;
  setContractsFilter: (f: ContractsFilter) => void;
  contractsClienteId: number | null;
  navigateToContracts: (filter?: ContractsFilter, clienteId?: number) => void;
  clearContractsClienteFilter: () => void;
  startOwnerTour: () => void;
  resetOwnerTour: () => void;
  registerOwnerTour: (handlers: { start: () => void; reset: () => void }) => void;
};

const LS_TOKEN = 'token';
const LS_REFRESH = 'refresh_token';
const LS_API_BASE = 'apiBase';
const LS_SCOPE = 'operacao_scope_id';

const AuthContext = createContext<AuthContextValue | null>(null);

function defaultApiBase(): string {
  const fromEnv = import.meta.env.VITE_API_BASE_URL as string | undefined;
  const stored = localStorage.getItem(LS_API_BASE);
  return resolveApiBase(fromEnv, stored);
}

function readScopeFromStorage(): number | null {
  const raw = localStorage.getItem(LS_SCOPE);
  if (raw == null || raw === '') return null;
  const n = parseInt(raw, 10);
  return Number.isFinite(n) && n > 0 ? n : null;
}

function effectiveOperacaoId(user: AuthUser | null, scope: number | null): number | null {
  if (!user) return null;
  if (user.tipo === 'admin') {
    return scope != null && scope > 0 ? scope : null;
  }
  return user.operacao_id != null && user.operacao_id > 0 ? user.operacao_id : null;
}

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(LS_TOKEN));
  const [apiBase, setApiBaseState] = useState<string>(() => defaultApiBase());
  const [operacaoScopeId, setOperacaoScopeIdState] = useState<number | null>(() =>
    readScopeFromStorage()
  );
  const [operacaoNome, setOperacaoNome] = useState<string | null>(null);
  const [operacoes, setOperacoes] = useState<OperacaoOut[]>([]);
  const [operacoesLoading, setOperacoesLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<AppTab>('dashboard');
  const [contractsFilter, setContractsFilter] = useState<ContractsFilter>('todos');
  const [contractsClienteId, setContractsClienteId] = useState<number | null>(null);
  const tokenRef = useRef(token);
  tokenRef.current = token;
  const ownerTourRef = useRef<{ start: () => void; reset: () => void }>({
    start: () => undefined,
    reset: () => undefined,
  });

  const registerOwnerTour = useCallback((handlers: { start: () => void; reset: () => void }) => {
    ownerTourRef.current = handlers;
  }, []);

  const startOwnerTour = useCallback(() => {
    ownerTourRef.current.start();
  }, []);

  const resetOwnerTour = useCallback(() => {
    ownerTourRef.current.reset();
  }, []);

  const setApiBase = (v: string) => {
    const n = v.replace(/\/$/, '');
    setApiBaseState(n);
    localStorage.setItem(LS_API_BASE, n);
  };

  const setOperacaoScopeId = (id: number | null) => {
    setOperacaoScopeIdState(id);
    if (id != null && id > 0) localStorage.setItem(LS_SCOPE, String(id));
    else localStorage.removeItem(LS_SCOPE);
  };

  const logout = useCallback(() => {
    const refreshToken = localStorage.getItem(LS_REFRESH);
    const currentToken = tokenRef.current;
    if (refreshToken && currentToken) {
      void axiosLogout(apiBase, currentToken, refreshToken);
    }
    localStorage.removeItem(LS_REFRESH);
    setToken(null);
    setUser(null);
    setOperacaoNome(null);
    setOperacoes([]);
    setOperacaoScopeId(null);
  }, [apiBase]);

  const api = useMemo(
    () =>
      createApiClient(
        apiBase,
        () => tokenRef.current,
        () => effectiveOperacaoId(user, operacaoScopeId),
        {
          getRefreshToken: () => localStorage.getItem(LS_REFRESH),
          onTokenRefreshed: (accessToken, refreshToken) => {
            localStorage.setItem(LS_TOKEN, accessToken);
            localStorage.setItem(LS_REFRESH, refreshToken);
            setToken(accessToken);
          },
          onAuthFailed: () => logout(),
        }
      ),
    [apiBase, user, operacaoScopeId, logout]
  );

  const fetchOperacaoNome = useCallback(async () => {
    if (!user) {
      setOperacaoNome(null);
      return;
    }
    try {
      if (user.tipo === 'dono') {
        const r = await api.get<{ nome: string }>('/api/v1/operacoes/me');
        setOperacaoNome(r.data.nome);
      } else if (user.tipo === 'admin' && operacaoScopeId) {
        const r = await api.get<{ nome: string }>(`/api/v1/operacoes/${operacaoScopeId}`);
        setOperacaoNome(r.data.nome);
      } else {
        setOperacaoNome(null);
      }
    } catch {
      setOperacaoNome(null);
    }
  }, [api, user, operacaoScopeId]);

  const refreshOperacoes = useCallback(async () => {
    if (!user || user.tipo !== 'admin') {
      setOperacoes([]);
      return;
    }
    setOperacoesLoading(true);
    try {
      const r = await api.get<OperacaoOut[]>('/api/v1/operacoes');
      setOperacoes(r.data);
    } catch {
      setOperacoes([]);
    } finally {
      setOperacoesLoading(false);
    }
  }, [api, user]);

  const fetchMe = async () => {
    if (!token) return;
    const response = await api.get<AuthUser>('/api/v1/auth/me');
    const u = response.data;
    setUser(u);
    if (u.tipo === 'admin' && u.operacao_id != null && u.operacao_id > 0 && readScopeFromStorage() == null) {
      setOperacaoScopeId(u.operacao_id);
    }
  };

  useEffect(() => {
    if (token) {
      localStorage.setItem(LS_TOKEN, token);
      void fetchMe().catch(() => {
        setToken(null);
        setUser(null);
        localStorage.removeItem(LS_TOKEN);
        localStorage.removeItem(LS_REFRESH);
      });
    } else {
      localStorage.removeItem(LS_TOKEN);
      setUser(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (user) void fetchOperacaoNome();
  }, [user, operacaoScopeId, fetchOperacaoNome]);

  useEffect(() => {
    void refreshOperacoes();
  }, [refreshOperacoes]);

  useEffect(() => {
    const resolved = defaultApiBase();
    setApiBaseState(resolved);
    localStorage.setItem(LS_API_BASE, resolved);
  }, []);

  useEffect(() => {
    localStorage.setItem(LS_API_BASE, apiBase);
  }, [apiBase]);

  const login = async (email: string, password: string) => {
    const response = await api.post<{ access_token: string; refresh_token: string }>(
      '/api/v1/auth/login',
      { email, password }
    );
    localStorage.setItem(LS_REFRESH, response.data.refresh_token);
    setToken(response.data.access_token);
  };

  const navigateToContracts = (filter: ContractsFilter = 'inadimplentes', clienteId?: number) => {
    setContractsFilter(filter);
    setContractsClienteId(clienteId ?? null);
    setActiveTab('contratos');
  };

  const clearContractsClienteFilter = useCallback(() => {
    setContractsClienteId(null);
  }, []);

  const value = useMemo(
    (): AuthContextValue => ({
      user,
      token,
      apiBase,
      setApiBase,
      operacaoScopeId,
      setOperacaoScopeId,
      operacaoNome,
      operacoes,
      operacoesLoading,
      refreshOperacoes,
      api,
      login,
      logout,
      fetchMe,
      activeTab,
      setActiveTab,
      contractsFilter,
      setContractsFilter,
      contractsClienteId,
      navigateToContracts,
      clearContractsClienteFilter,
      startOwnerTour,
      resetOwnerTour,
      registerOwnerTour,
    }),
    [
      user,
      token,
      apiBase,
      operacaoScopeId,
      operacaoNome,
      operacoes,
      operacoesLoading,
      refreshOperacoes,
      api,
      activeTab,
      contractsFilter,
      contractsClienteId,
      clearContractsClienteFilter,
      startOwnerTour,
      resetOwnerTour,
      registerOwnerTour,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

async function axiosLogout(base: string, accessToken: string, refreshToken: string) {
  const { default: axios } = await import('axios');
  await axios
    .post(
      `${base.replace(/\/$/, '')}/api/v1/auth/logout`,
      { refresh_token: refreshToken },
      { headers: { Authorization: `Bearer ${accessToken}` } }
    )
    .catch(() => undefined);
}

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
