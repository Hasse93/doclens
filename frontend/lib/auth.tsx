"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { api, clearToken, getToken, setToken } from "./api";
import type { AuthResponse, User } from "./types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (fullName: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  // Restore a persisted session on first load.
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    const raw = window.localStorage.getItem("doclens_user");
    if (raw) {
      try {
        setUser(JSON.parse(raw) as User);
      } catch {
        clearToken();
      }
    }
    setLoading(false);
  }, []);

  const persist = useCallback((auth: AuthResponse) => {
    setToken(auth.access_token);
    window.localStorage.setItem("doclens_user", JSON.stringify(auth.user));
    setUser(auth.user);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      persist(await api.login(email, password));
      router.push("/dashboard");
    },
    [persist, router],
  );

  const register = useCallback(
    async (fullName: string, email: string, password: string) => {
      persist(await api.register(fullName, email, password));
      router.push("/dashboard");
    },
    [persist, router],
  );

  const logout = useCallback(() => {
    clearToken();
    window.localStorage.removeItem("doclens_user");
    setUser(null);
    router.push("/login");
  }, [router]);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
