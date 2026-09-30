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
import "./profile-menu.css";

export default function ProfileMenu() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

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
        <div className="profile-avatar">L</div>

        <div className="profile-info">
          <strong>Local Workspace</strong>
          <span>No user session</span>
        </div>

        <ChevronDown
          size={15}
          className={`profile-chevron ${open ? "rotate" : ""}`}
        />
      </button>

      {open && (
        <div className="profile-menu">
          <div className="profile-menu-header">
            <div className="profile-large-avatar">L</div>

            <div>
              <strong>Local Workspace</strong>
              <span>Authentication is not configured</span>
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
            <span className="signout-button" aria-disabled="true">Sign-in and sign-out are not implemented</span>
          </div>
        </div>
      )}
    </div>
  );
}
