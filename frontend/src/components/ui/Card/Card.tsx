import type { ReactNode } from "react";
interface CardProps { children: ReactNode; className?: string; hover?: boolean; }
function Card({ children, className = "", hover = false }: CardProps) { return <div className={`liquid-card ${hover ? "liquid-card-hover" : ""} ${className}`}>{children}</div>; }
export default Card;
