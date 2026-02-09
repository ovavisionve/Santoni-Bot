"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { User } from "@/types";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    const token = api.getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const me = await api.getMe();
      setUser(me);
    } catch {
      api.logout();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (username: string, password: string) => {
    await api.login(username, password);
    const me = await api.getMe();
    setUser(me);
    return me;
  };

  const logout = () => {
    api.logout();
    setUser(null);
  };

  return { user, loading, login, logout, checkAuth };
}
