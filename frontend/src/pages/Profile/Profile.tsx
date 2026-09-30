import {
  BriefcaseBusiness,
  Mail,
  ShieldCheck,
  UserRound,
} from "lucide-react";

import "./profile-settings.css";

export default function Profile() {
  return (
    <div className="profile-page">
      <div className="profile-card glass-card">
        <div className="profile-cover" />

        <div className="profile-avatar">
          LW
        </div>

        <div className="profile-main">
          <span className="eyebrow">
            ACCOUNT
          </span>

          <h1>Local Workspace</h1>

          <p>
            User authentication is not configured for this project.
          </p>

          <div className="profile-info">
            <div>
              <UserRound size={16} />

              <span>Account identity</span>

              <strong>
                Not configured
              </strong>
            </div>

            <div>
              <Mail size={16} />

              <span>Email</span>

              <strong>
                Not configured
              </strong>
            </div>

            <div>
              <BriefcaseBusiness size={16} />

              <span>Workspace</span>

              <strong>
                Local development workspace
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
                Authentication and session controls
                are not implemented by the backend.
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
