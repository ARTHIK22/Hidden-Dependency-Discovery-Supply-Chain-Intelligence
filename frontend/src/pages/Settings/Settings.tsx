import {
  Bell,
  Eye,
  Palette,
  ShieldCheck,
  SlidersHorizontal,
} from "lucide-react";

import "../Profile/profile-settings.css";

const settings = [
  {
    Icon: Palette,
    title: "Appearance",
    description: "Liquid Glass interface",
    value: "Light spatial theme",
  },
  {
    Icon: Bell,
    title: "Notifications",
    description: "Investigation alerts",
    value: "Enabled",
  },
  {
    Icon: Eye,
    title: "Graph behavior",
    description: "Relationship focus",
    value: "Enabled",
  },
  {
    Icon: ShieldCheck,
    title: "Privacy",
    description: "Evidence provenance",
    value: "Always visible",
  },
  {
    Icon: SlidersHorizontal,
    title: "Investigation defaults",
    description: "Research depth",
    value: "Deep",
  },
];

export default function Settings() {
  return (
    <div className="settings-page">
      <div className="settings-heading">
        <span className="eyebrow">
          PREFERENCES
        </span>

        <h1>Settings</h1>

        <p>
          Control workspace behavior without changing
          the core visual language.
        </p>
      </div>

      <div className="settings-grid">
        {settings.map(
          ({
            Icon,
            title,
            description,
            value,
          }) => (
            <section
              className="setting-card glass-card"
              key={title}
            >
              <div className="setting-icon">
                <Icon size={18} />
              </div>

              <div>
                <h3>{title}</h3>
                <p>{description}</p>
              </div>

              <span>{value}</span>
            </section>
          )
        )}
      </div>
    </div>
  );
}
