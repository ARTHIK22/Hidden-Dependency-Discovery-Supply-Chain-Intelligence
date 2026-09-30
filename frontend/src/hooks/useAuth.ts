import { useEffect, useSyncExternalStore } from "react";
import { authStore } from "../stores/auth.store";
import { getCurrentUser } from "../features/auth/auth.api";

export function useAuth() {
  const state = useSyncExternalStore(authStore.subscribe, authStore.getSnapshot, authStore.getSnapshot);
  useEffect(() => {
    const handleUnauthorized = () => authStore.clear();
    window.addEventListener("hdi:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("hdi:unauthorized", handleUnauthorized);
  }, []);
  useEffect(() => {
    if (!authStore.hasToken() || state.user || !state.loading) return;
    let active = true;
    getCurrentUser().then((user) => { if (active) authStore.setUser(user); }).catch(() => { if (active) authStore.clear(); });
    return () => { active = false; };
  }, [state.loading, state.user]);
  return { ...state, logout: authStore.clear };
}
