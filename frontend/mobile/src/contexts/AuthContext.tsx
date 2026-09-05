import React, { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from 'react';

import * as authApi from '../api/auth';
import { registerUnauthorizedHandler, setAuthToken } from '../api/client';
import { clearSession, loadSession, saveSession } from '../api/tokenStorage';
import type { Role } from '../types/api';

interface Session {
  username: string;
  role: Role;
}

interface AuthContextValue {
  session: Session | null;
  /** True while restoring a persisted session on app launch. */
  isRestoring: boolean;
  loginError: string | null;
  isLoggingIn: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<Session | null>(null);
  const [isRestoring, setIsRestoring] = useState(true);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  useEffect(() => {
    registerUnauthorizedHandler(() => {
      setAuthToken(null);
      setSession(null);
      void clearSession();
    });
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const stored = await loadSession();
        if (!stored) return;
        setAuthToken(stored.token);
        // Validate the restored token against the server and pick up the
        // authoritative, current role rather than trusting the cached one.
        const me = await authApi.fetchCurrentUser();
        setSession({ username: me.username, role: me.role as Role });
      } catch {
        setAuthToken(null);
        await clearSession();
      } finally {
        setIsRestoring(false);
      }
    })();
  }, []);

  const login = async (username: string, password: string) => {
    setIsLoggingIn(true);
    setLoginError(null);
    try {
      const token = await authApi.login(username, password);
      setAuthToken(token.access_token);
      await saveSession({ token: token.access_token, username: token.username, role: token.role });
      setSession({ username: token.username, role: token.role });
    } catch (err) {
      const message =
        err && typeof err === 'object' && 'status' in err && (err as { status: number }).status === 401
          ? 'Incorrect username or password.'
          : 'Could not sign in. Check your connection and try again.';
      setLoginError(message);
      throw err;
    } finally {
      setIsLoggingIn(false);
    }
  };

  const logout = async () => {
    setAuthToken(null);
    setSession(null);
    await clearSession();
  };

  const value = useMemo(
    () => ({ session, isRestoring, loginError, isLoggingIn, login, logout }),
    [session, isRestoring, loginError, isLoggingIn]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
