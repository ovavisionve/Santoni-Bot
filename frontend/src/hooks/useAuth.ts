"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import type { User } from "@/types";

const INACTIVITY_LIMIT_MS = 30 * 60 * 1000; // 30 minutes
const WARNING_BEFORE_MS = 5 * 60 * 1000; // Show warning 5 min before
const CHECK_INTERVAL_MS = 30 * 1000; // Check every 30 seconds

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [inactivityWarning, setInactivityWarning] = useState(false);
  const lastActivityRef = useRef<number>(Date.now());

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
    lastActivityRef.current = Date.now();
    setInactivityWarning(false);
    return me;
  };

  const logout = useCallback(() => {
    api.logout();
    setUser(null);
    setInactivityWarning(false);
  }, []);

  // Reset activity timer on user interaction
  const resetActivity = useCallback(() => {
    lastActivityRef.current = Date.now();
    if (inactivityWarning) setInactivityWarning(false);
  }, [inactivityWarning]);

  // Track user activity (mouse, keyboard, clicks, scroll, touch)
  useEffect(() => {
    if (!user) return;

    const events = ["mousedown", "keydown", "scroll", "touchstart", "mousemove"];
    // Throttle mousemove to avoid excessive updates
    let throttleTimer: ReturnType<typeof setTimeout> | null = null;

    const handleActivity = (e: Event) => {
      if (e.type === "mousemove") {
        if (throttleTimer) return;
        throttleTimer = setTimeout(() => { throttleTimer = null; }, 10000);
      }
      lastActivityRef.current = Date.now();
      if (inactivityWarning) setInactivityWarning(false);
    };

    events.forEach((event) => window.addEventListener(event, handleActivity, { passive: true }));
    return () => {
      events.forEach((event) => window.removeEventListener(event, handleActivity));
      if (throttleTimer) clearTimeout(throttleTimer);
    };
  }, [user, inactivityWarning]);

  // Check inactivity periodically
  useEffect(() => {
    if (!user) return;

    const interval = setInterval(() => {
      const elapsed = Date.now() - lastActivityRef.current;

      if (elapsed >= INACTIVITY_LIMIT_MS) {
        // 30 min inactivity → auto logout
        logout();
        // Redirect happens in the page component via the user===null check
      } else if (elapsed >= INACTIVITY_LIMIT_MS - WARNING_BEFORE_MS) {
        // 25 min inactivity → show warning
        setInactivityWarning(true);
      }
    }, CHECK_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [user, logout]);

  return { user, loading, login, logout, checkAuth, inactivityWarning, resetActivity };
}
