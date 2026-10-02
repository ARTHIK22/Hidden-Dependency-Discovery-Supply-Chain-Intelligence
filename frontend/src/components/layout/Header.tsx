import { Menu, Plus } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import GlobalSearch from "../search/GlobalSearch";
import Notifications from "../notifications/Notifications";
import ProfileMenu from "../profile/ProfileMenu";

import "./header.css";

const routeLabels: Record<string, string> = {
	"/": "Dashboard",
	"/dashboard": "Dashboard",
	"/investigations": "Investigations",
	"/investigations/new": "New investigation",
	"/graph": "Dependency graph",
	"/entities": "Entities",
	"/relationships": "Relationships",
	"/evidence": "Evidence",
	"/risks": "Risk intelligence",
	"/alerts": "Alerts",
	"/watchlist": "Watchlist",
	"/reports": "Reports",
	"/profile": "Profile",
	"/settings": "Settings",
};

interface HeaderProps {
	mobileNavOpen: boolean;
	onToggleNavigation: () => void;
}

function Header({ mobileNavOpen, onToggleNavigation }: HeaderProps) {
	const { pathname } = useLocation();
	const pageLabel = routeLabels[pathname] ?? (pathname.startsWith("/investigations/") ? "Investigation" : "Workspace");
	const showCreateAction = pathname !== "/investigations/new";

	return (
		<header className="app-header">
			<div className="header-context">
				<button className="mobile-menu-button" type="button" aria-label={mobileNavOpen ? "Close navigation" : "Open navigation"} aria-expanded={mobileNavOpen} onClick={onToggleNavigation}><Menu size={18} /></button>
				<div className="header-breadcrumb"><span>Workspace</span><span className="breadcrumb-divider">/</span><strong>{pageLabel}</strong></div>
			</div>
			<div className="header-search"><GlobalSearch /></div>
			<div className="header-actions">
				{showCreateAction && <Link className="header-create-action" to="/investigations/new" aria-label="New investigation"><Plus size={15} /><span>New investigation</span></Link>}
				<Notifications />
				<ProfileMenu />
			</div>
		</header>
	);
}

export default Header;
