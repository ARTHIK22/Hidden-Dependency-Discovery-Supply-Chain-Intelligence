import type { ButtonHTMLAttributes, ReactNode } from "react";
import "./button.css";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> { children: ReactNode; variant?: "primary" | "secondary" | "ghost"; size?: "sm" | "md" | "lg"; fullWidth?: boolean; }
function Button({ children, variant = "primary", size = "md", fullWidth = false, className = "", ...props }: ButtonProps) { return <button className={["liquid-button", `liquid-button-${variant}`, `liquid-button-${size}`, fullWidth ? "liquid-button-full" : "", className].join(" ")} {...props}>{children}</button>; }
export default Button;
