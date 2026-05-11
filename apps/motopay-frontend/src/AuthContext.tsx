import {
  createContext,
  useContext,
  useState,
  useEffect,
  useMemo,
  type ReactNode,
} from 'react';
import type { AxiosInstance } from 'axios';
import { createApiClient } from './apiClient';

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
  /** Escopo opcional para admin (query operacao_id). Dono usa sempre operacao_id do token. */
  operacaoScopeId: number | null;
  setOperacaoScopeId: (id: number | null) => void;
  api: AxiosInstance;
  login: (email: string, password: string) => Promise<unknown>;
  logout: () => void;
  fetchMe: () => Promise<void>;
};

const LS_TOKEN = 'token';
const LS_API_BASE = 'apiBase';
const LS_SCOPE = 'operacao_scope_id';

const AuthContext = createContext<AuthContextValue | null>(null);

function defaultApiBase(): string {
  const fromEnv = import.meta.env.VITE_API_BASE_URL as string | undefined;
  if (fromEnv && fromEnv.trim()) return fromEnv.replace(/\/$/, '');
  const stored = localStorage.getItem(LS_API_BASE);
  if (stored && stored.trim()) return stored.replace(/\/$/, '');
  return 'http://localhost:8000';
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

  const api = useMemo(
    () =>
      createApiClient(
        apiBase,
        () => token,
        () => effectiveOperacaoId(user, operacaoScopeId)
      ),
    [apiBase, token, user, operacaoScopeId]
  );

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
      });
    } else {
      localStorage.removeItem(LS_TOKEN);
      setUser(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- apenas token; evita loop com api/user
  }, [token]);

  useEffect(() => {
    localStorage.setItem(LS_API_BASE, apiBase);
  }, [apiBase]);

  const login = async (email: string, password: string) => {
    const response = await api.post<{ access_token: string }>('/api/v1/auth/login', {
      email,
      password,
    });
    setToken(response.data.access_token);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setOperacaoScopeId(null);
  };

  const value = useMemo(
    (): AuthContextValue => ({
      user,
      token,
      apiBase,
      setApiBase,
      operacaoScopeId,
      setOperacaoScopeId,
      api,
      login,
      logout,
      fetchMe,
    }),
    [user, token, apiBase, operacaoScopeId, api]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
