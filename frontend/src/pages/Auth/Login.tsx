import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ArrowRight, Eye, EyeOff, LockKeyhole, LoaderCircle, Mail } from "lucide-react";
import { login } from "../../features/auth/auth.api";
import { authErrorMessage } from "../../features/auth/auth.utils";
import { authStore } from "../../stores/auth.store";
import "./login.css";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    setBusy(true);
    try {
      const session = await login({ email, password });
      authStore.setToken(session.access_token);
      authStore.setUser(session.user);
      navigate((location.state as { from?: string } | null)?.from || "/", { replace: true });
    } catch (reason) {
      setError(authErrorMessage(reason, "login"));
    } finally {
      setBusy(false);
    }
  }

  return <main className="auth-screen auth-login-screen">
    <div className="auth-ambience" aria-hidden="true">
      <svg className="auth-network" viewBox="0 0 720 620" fill="none" focusable="false">
        <g className="auth-network-lines">
          <path d="M68 92 178 142 282 82 354 176 472 112 570 192" />
          <path d="M178 142 132 278 264 294 354 176" />
          <path d="M354 176 420 314 570 192 572 326" />
          <path d="M132 278 78 410 236 474 264 294" />
          <path d="M264 294 420 314 402 492 236 474" />
          <path d="M420 314 572 326 610 478 402 492" />
          <path d="M282 82 472 112" />
        </g>
        <g className="auth-network-nodes">
          <circle cx="68" cy="92" r="6" /><circle cx="178" cy="142" r="8" />
          <circle cx="282" cy="82" r="5" /><circle cx="354" cy="176" r="10" />
          <circle cx="472" cy="112" r="6" /><circle cx="570" cy="192" r="7" />
          <circle cx="132" cy="278" r="5" /><circle cx="264" cy="294" r="7" />
          <circle cx="420" cy="314" r="6" /><circle cx="572" cy="326" r="9" />
          <circle cx="78" cy="410" r="5" /><circle cx="236" cy="474" r="8" />
          <circle cx="402" cy="492" r="6" /><circle cx="610" cy="478" r="5" />
        </g>
      </svg>
      <div className="auth-insight-chip">
        <span className="auth-insight-mark" aria-hidden="true"><i /><i /><i /></span>
        <span><strong>Dependency intelligence</strong><small>Evidence-backed workspace</small></span>
      </div>
    </div>

    <div className="auth-composition">
      <form className="login-card" onSubmit={submit} aria-busy={busy}>
        <div className="login-brand" aria-label="Hidden Dependency Supply Intelligence">
          <span className="login-brand-mark" aria-hidden="true">HD</span>
          <span className="login-brand-copy"><strong>HIDDEN DEPENDENCY</strong><small>Supply Intelligence</small></span>
        </div>

        <header className="login-heading">
          <h1>Welcome back</h1>
          <p>Sign in to continue your intelligence workspace.</p>
        </header>

        <div className="login-field">
          <label htmlFor="login-email">Email</label>
          <div className="login-input-shell">
            <Mail size={17} aria-hidden="true" />
            <input id="login-email" type="email" autoComplete="email" inputMode="email" placeholder="you@example.com" required value={email} onChange={(event) => { setEmail(event.target.value); setError(""); setNotice(""); }} />
          </div>
        </div>

        <div className="login-field">
          <label htmlFor="login-password">Password</label>
          <div className="login-input-shell login-password-shell">
            <LockKeyhole size={17} aria-hidden="true" />
            <input id="login-password" type={showPassword ? "text" : "password"} autoComplete="current-password" aria-describedby={error ? "login-auth-error" : undefined} placeholder="Enter your password" required value={password} onChange={(event) => { setPassword(event.target.value); setError(""); setNotice(""); }} />
            <button className="login-password-toggle" type="button" aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword} onClick={() => setShowPassword((visible) => !visible)}>
              {showPassword ? <EyeOff size={17} aria-hidden="true" /> : <Eye size={17} aria-hidden="true" />}
            </button>
          </div>
          {error && <p id="login-auth-error" role="alert" className="login-message login-error login-inline-error">{error}</p>}
          <div className="login-forgot-row"><button className="login-text-action" type="button" onClick={() => setNotice("For password reset help, contact your workspace administrator.")}>Forgot password?</button></div>
          {notice && <p className="login-message login-notice" role="status">{notice}</p>}
        </div>

        <button className="login-submit" type="submit" disabled={busy}>
          <span>{busy ? "Signing in..." : "Sign in"}</span>
          {busy ? <LoaderCircle className="login-spinner" size={17} aria-hidden="true" /> : <ArrowRight className="login-submit-arrow" size={17} aria-hidden="true" />}
        </button>

        <p className="login-create-account">New to Hidden Dependency? <Link to="/register">Create an account <ArrowRight size={14} aria-hidden="true" /></Link></p>
      </form>

      <footer className="auth-trust-footer"><strong>Evidence-backed dependency intelligence</strong><span>Your workspace <i>•</i> Your investigations <i>•</i> Your evidence</span></footer>
    </div>
  </main>;
}
