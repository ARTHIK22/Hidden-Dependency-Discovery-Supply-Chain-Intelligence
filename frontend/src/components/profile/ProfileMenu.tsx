import { useEffect, useRef, useState } from "react";
import {
  User,
  Building2,
  Settings,
  SlidersHorizontal,
  ChevronDown,
  Check,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import "./profile-menu.css";

export default function ProfileMenu() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const displayName = user?.full_name || user?.email || "Account";
  const initials = displayName.split(/[\s@._-]+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join("") || "U";

  useEffect(() => {
    const handleOutside = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    document.addEventListener("mousedown", handleOutside);

    return () => {
      document.removeEventListener("mousedown", handleOutside);
    };
  }, []);

  const close = () => setOpen(false);

  return (
    <div className="profile-wrapper" ref={ref}>
      <button
        className={`profile-trigger ${open ? "active" : ""}`}
        onClick={() => setOpen((value) => !value)}
        aria-label="Open profile menu"
        aria-expanded={open}
        type="button"
      >
        <span className="profile-trigger-avatar" aria-hidden="true">{initials}</span>

        <span className="profile-user-info">
          <span className="profile-user-name">{displayName}</span>
          <span className="profile-user-email">{user?.email}</span>
        </span>

        <ChevronDown
          size={15}
          className={`profile-chevron ${open ? "rotate" : ""}`}
        />
      </button>

      {open && (
        <div className="profile-menu">
          <div className="profile-menu-header">
            <div className="profile-large-avatar">{initials}</div>

            <div>
              <strong>{displayName}</strong>
              <span>{user?.email}</span>
            </div>
          </div>

          <div className="workspace-card">
            <div className="workspace-icon">
              <Building2 size={16} />
            </div>

            <div>
              <span>Workspace</span>
              <strong>Development Workspace</strong>
            </div>

            <Check size={15} />
          </div>

          <div className="profile-menu-section">
            <button
              onClick={() => {
                close();
                navigate("/profile");
              }}
              type="button"
            >
              <User size={17} />
              <span>My Profile</span>
            </button>

            <button
              onClick={() => {
                close();
                navigate("/settings");
              }}
              type="button"
            >
              <Settings size={17} />
              <span>Settings</span>
            </button>

            <button
              onClick={() => {
                close();
                navigate("/settings");
              }}
              type="button"
            >
              <SlidersHorizontal size={17} />
              <span>Preferences</span>
            </button>
          </div>

          <div className="profile-menu-footer">
            <button
              className="signout-button"
              type="button"
              onClick={async () => {
                close();
                try { await logout(); } catch { /* The local session is cleared even if the server cannot be reached. */ }
                navigate("/login", { replace: true });
              }}
            >Sign out</button>
          </div>
        </div>
      )}
    </div>
  );
}
