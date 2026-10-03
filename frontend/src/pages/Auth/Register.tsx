import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../../features/auth/auth.api";
import { authErrorMessage } from "../../features/auth/auth.utils";
import { authStore } from "../../stores/auth.store";

export default function Register() {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(""); setBusy(true);
    try {
      const session = await register({ full_name: fullName, email, password });
      authStore.setToken(session.access_token); authStore.setUser(session.user); navigate("/", { replace: true });
    } catch (reason) { setError(authErrorMessage(reason, "register")); } finally { setBusy(false); }
  }
  return <main className="auth-screen"><form className="auth-card" onSubmit={submit}>
    <span className="eyebrow">SUPPLY INTELLIGENCE</span><h1>Create account</h1><p>Register to join the shared development workspace.</p>
    {error && <div role="alert" className="auth-error">{error}</div>}
    <label>Full name<input autoComplete="name" required maxLength={255} value={fullName} onChange={(event) => setFullName(event.target.value)} /></label>
    <label>Email<input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
    <label>Password<input type="password" autoComplete="new-password" required minLength={8} maxLength={72} value={password} onChange={(event) => setPassword(event.target.value)} /><small>At least 8 characters (maximum 72 UTF-8 bytes).</small></label>
    <button type="submit" disabled={busy}>{busy ? "Creating account…" : "Create account"}</button>
    <p>Already registered? <Link to="/login">Sign in</Link></p>
  </form></main>;
}
