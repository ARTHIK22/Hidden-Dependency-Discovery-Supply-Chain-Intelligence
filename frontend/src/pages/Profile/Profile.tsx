import {
  BriefcaseBusiness,
  Mail,
  ShieldCheck,
  UserRound,
} from "lucide-react";

import "./profile-settings.css";
import { useAuth } from "../../hooks/useAuth";

export default function Profile() {
  const { user } = useAuth();
  const displayName = user?.full_name || user?.email || "Account";
  const initials = displayName.split(/[\s@._-]+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join("") || "U";
  return (
    <div className="profile-page">
      <div className="profile-card glass-card">
        <div className="profile-cover" />

        <div className="profile-avatar">
          {initials}
        </div>

        <div className="profile-main">
          <span className="eyebrow">
            ACCOUNT
          </span>

          <h1>{displayName}</h1>

          <p>
            Account details for the shared local development workspace.
          </p>

          <div className="profile-info">
            <div>
              <UserRound size={16} />

              <span>Account identity</span>

              <strong>
                {user?.full_name || "Not provided"}
              </strong>
            </div>

            <div>
              <Mail size={16} />

              <span>Email</span>

              <strong>
                {user?.email || "Not provided"}
              </strong>
            </div>

            <div>
              <BriefcaseBusiness size={16} />

              <span>Workspace</span>

              <strong>
                Shared demo workspace
              </strong>
            </div>
          </div>

          <div className="profile-security">
            <ShieldCheck size={17} />

            <div>
              <strong>
                Account security
              </strong>

              <span>
                Your account is authenticated with a revocable local access session.
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
