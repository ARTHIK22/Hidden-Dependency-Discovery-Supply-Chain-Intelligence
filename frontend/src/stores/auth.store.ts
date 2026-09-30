import type { User } from "../types/user.types";
import { tokenStorage } from "../services/storage/localStorage";

let currentUser: User | null = null;
let loading = Boolean(tokenStorage.get());
const listeners = new Set<() => void>();
let snapshot: { user: User | null; loading: boolean } = { user: currentUser, loading };
const notify = () => { snapshot = { user: currentUser, loading }; listeners.forEach((listener) => listener()); };
export const authStore = {
  getSnapshot: () => snapshot,
  subscribe(listener: () => void) { listeners.add(listener); return () => listeners.delete(listener); },
  setUser(user: User | null) { currentUser = user; loading = false; notify(); },
  setLoading(value: boolean) { loading = value; notify(); },
  clear() { currentUser = null; loading = false; tokenStorage.clear(); notify(); },
  hasToken: () => Boolean(tokenStorage.get()),
  setToken: (token: string) => tokenStorage.set(token),
};
