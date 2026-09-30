const TOKEN_KEY = "hdi.access_token";

export const tokenStorage = {
  get(): string | null {
    try { return window.localStorage.getItem(TOKEN_KEY); } catch { return null; }
  },
  set(token: string): void {
    try { window.localStorage.setItem(TOKEN_KEY, token); } catch { /* Storage may be disabled. */ }
  },
  clear(): void {
    try { window.localStorage.removeItem(TOKEN_KEY); } catch { /* Storage may be disabled. */ }
  },
};
