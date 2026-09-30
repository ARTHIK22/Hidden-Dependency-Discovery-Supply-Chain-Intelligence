import {
  AlertTriangle,
  Inbox,
  LoaderCircle,
  RefreshCcw,
} from "lucide-react";

import "./async-states.css";

type Props = {
  title?: string;
  description?: string;
  action?: () => void;
};

export function LoadingState({
  label = "Loading intelligence...",
}: {
  label?: string;
}) {
  return (
    <div className="async-state glass-card">
      <LoaderCircle
        className="spin"
        size={26}
      />

      <strong>{label}</strong>

      <span>
        Preparing the latest investigation data.
      </span>
    </div>
  );
}

export function EmptyState({
  title = "Nothing here yet",
  description = "There is no data to display.",
  action,
}: Props) {
  return (
    <div className="async-state glass-card">
      <Inbox size={26} />

      <strong>{title}</strong>

      <span>{description}</span>

      {action && (
        <button onClick={action}>
          <RefreshCcw size={14} />
          Try again
        </button>
      )}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  description = "Check the connection and retry the operation.",
  action,
}: Props) {
  return (
    <div className="async-state glass-card">
      <AlertTriangle size={26} />

      <strong>{title}</strong>

      <span>{description}</span>

      {action && (
        <button onClick={action}>
          <RefreshCcw size={14} />
          Retry
        </button>
      )}
    </div>
  );
}
