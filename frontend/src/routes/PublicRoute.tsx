import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function PublicRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <main className="auth-screen" aria-live="polite">Checking your session…</main>;
  return user ? <Navigate to="/" replace /> : <>{children}</>;
}
