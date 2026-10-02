import { useEffect, useState, type ReactNode } from "react";

import Sidebar from "./Sidebar";
import Header from "./Header";

import "./app-layout.css";

interface AppLayoutProps {
	children: ReactNode;
}

function AppLayout({
	children,
}: AppLayoutProps) {
	const [mobileNavOpen, setMobileNavOpen] = useState(false);
	const closeMobileNav = () => setMobileNavOpen(false);
	useEffect(() => {
		if (!mobileNavOpen) return;
		const closeOnEscape = (event: KeyboardEvent) => {
			if (event.key === "Escape") closeMobileNav();
		};
		window.addEventListener("keydown", closeOnEscape);
		return () => window.removeEventListener("keydown", closeOnEscape);
	}, [mobileNavOpen]);

	return (
		<div className="app-shell">
			<div className="app-background" />
			{mobileNavOpen && <button className="mobile-nav-backdrop" aria-label="Close navigation" onClick={closeMobileNav} />}
			<Sidebar mobileOpen={mobileNavOpen} onNavigate={closeMobileNav} />
			<section className="app-main">
				<Header mobileNavOpen={mobileNavOpen} onToggleNavigation={() => setMobileNavOpen((open) => !open)} />
				{children}
			</section>
		</div>
	);
}

export default AppLayout;
