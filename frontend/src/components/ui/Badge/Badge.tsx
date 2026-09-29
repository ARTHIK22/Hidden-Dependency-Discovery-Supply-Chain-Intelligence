import type { ReactNode } from "react";
import "./badge.css";
interface BadgeProps { children: ReactNode; variant?: "default" | "success" | "warning" | "danger"; }
function Badge({ children, variant = "default" }: BadgeProps) { return <span className={`badge badge-${variant}`}>{children}</span>; }
export default Badge;
