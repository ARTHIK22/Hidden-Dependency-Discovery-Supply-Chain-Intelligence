import { FormEvent, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { login } from "../../features/auth/auth.api";
import { authStore } from "../../stores/auth.store";
import { userMessage } from "../../services/api/errors";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(""); setBusy(true);
    try {
      const session = await login({ email, password });
      authStore.setToken(session.access_token); authStore.setUser(session.user);
      navigate((location.state as { from?: string } | null)?.from || "/", { replace: true });
    } catch (reason) { setError(userMessage(reason)); } finally { setBusy(false); }
  }
  return <main className="auth-screen"><form className="auth-card" onSubmit={submit}>
    <span className="eyebrow">SUPPLY INTELLIGENCE</span><h1>Sign in</h1><p>Access your investigations and dependency data.</p>
    {error && <div role="alert" className="auth-error">{error}</div>}
    <label>Email<input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
    <label>Password<input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
    <button type="submit" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
    <p>New here? <Link to="/register">Create an account</Link></p>
  </form></main>;
}
