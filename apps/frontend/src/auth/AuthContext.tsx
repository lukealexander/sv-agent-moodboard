import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { logoutUrl, refreshAccessToken, type TokenSet } from "./cognito";

const REFRESH_TOKEN_KEY = "cognito_refresh_token";
const LOCAL_DEV = import.meta.env.VITE_LOCAL_DEV === "true";

interface AuthState {
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  setTokens: (tokens: TokenSet) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(
    LOCAL_DEV
      ? { accessToken: "local-dev-token", isAuthenticated: true, isLoading: false }
      : { accessToken: null, isAuthenticated: false, isLoading: true },
  );

  const refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const scheduleRefresh = useCallback((tokens: TokenSet) => {
    if (refreshTimer.current) clearTimeout(refreshTimer.current);
    // Refresh 60 s before expiry
    const delay = Math.max((tokens.expires_in - 60) * 1000, 0);
    refreshTimer.current = setTimeout(async () => {
      try {
        const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
        if (!refreshToken) return;
        const next = await refreshAccessToken(refreshToken);
        setTokens(next);
      } catch {
        logout();
      }
    }, delay);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const setTokens = useCallback(
    (tokens: TokenSet) => {
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
      setState({ accessToken: tokens.access_token, isAuthenticated: true, isLoading: false });
      scheduleRefresh(tokens);
    },
    [scheduleRefresh],
  );

  const logout = useCallback(() => {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    if (refreshTimer.current) clearTimeout(refreshTimer.current);
    setState({ accessToken: null, isAuthenticated: false, isLoading: false });
    if (!LOCAL_DEV) window.location.replace(logoutUrl());
  }, []);

  // On mount, try to restore session via refresh token
  useEffect(() => {
    if (LOCAL_DEV) return;
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!refreshToken) {
      setState((s) => ({ ...s, isLoading: false }));
      return;
    }
    refreshAccessToken(refreshToken)
      .then(setTokens)
      .catch(() => {
        localStorage.removeItem(REFRESH_TOKEN_KEY);
        setState({ accessToken: null, isAuthenticated: false, isLoading: false });
      });
  }, [setTokens]);

  return (
    <AuthContext.Provider value={{ ...state, setTokens, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
