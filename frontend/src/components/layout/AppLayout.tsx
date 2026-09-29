import type { ReactNode } from "react";

import Sidebar from "./Sidebar";
import Header from "./Header";

import "./app-layout.css";

interface AppLayoutProps {
	children: ReactNode;
}

function AppLayout({
	children,
}: AppLayoutProps) {
	return (
		<div className="app-shell">
			<div className="app-background" />
			<Sidebar />
			<section className="app-main">
				<Header />
				{children}
			</section>
		</div>
	);
}

export default AppLayout;
