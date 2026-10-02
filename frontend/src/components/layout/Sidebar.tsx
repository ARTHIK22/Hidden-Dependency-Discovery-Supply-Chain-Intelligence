import {
	LayoutDashboard,
	Search,
	Network,
	FolderSearch,
	ShieldAlert,
	Bell,
	Star,
	FileText,
	Settings,
	UserRound,
	GitBranch,
	Database,
	ChevronRight,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";

import "./sidebar.css";

const navigation = [
	{ label: "Dashboard", icon: LayoutDashboard, path: "/" },
	{ label: "Investigations", icon: FolderSearch, path: "/investigations" },
	{ label: "Dependency Graph", icon: Network, path: "/graph" },
	{ label: "Entities", icon: Search, path: "/entities" },
	{ label: "Relationships", icon: GitBranch, path: "/relationships" },
	{ label: "Evidence", icon: FileText, path: "/evidence" },
	{ label: "Risk Intelligence", icon: ShieldAlert, path: "/risks" },
	{ label: "Alerts", icon: Bell, path: "/alerts" },
	{ label: "Watchlist", icon: Star, path: "/watchlist" },
	{ label: "Reports", icon: FileText, path: "/reports" },
];

interface SidebarProps {
	mobileOpen: boolean;
	onNavigate: () => void;
}

function Sidebar({ mobileOpen, onNavigate }: SidebarProps) {
	const { user } = useAuth();
	const displayName = user?.full_name || user?.email || "Account";
	const initials = displayName.split(/[\s@._-]+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join("") || "U";

	return (
		<aside className={`sidebar glass ${mobileOpen ? "mobile-open" : ""}`} aria-label="Main navigation">
			<div className="sidebar-brand">
				<div className="brand-mark">HD</div>

				<div className="brand-text">
					<h1>Hidden Dependency</h1>
					<span>Supply Intelligence</span>
				</div>
			</div>

			<div className="sidebar-section">
				<span className="sidebar-section-title">WORKSPACE</span>

				<nav className="sidebar-nav">
					{navigation.map((item) => {
						const Icon = item.icon;

						return (
							<NavLink
								key={item.label}
								to={item.path}
								onClick={onNavigate}
								aria-label={item.label}
								className={({ isActive }) =>
									`sidebar-item ${isActive ? "active" : ""}`
								}
							>
								{({ isActive }) => (
									<>
										<Icon size={18} strokeWidth={1.8} />
										<span>{item.label}</span>
										{isActive && (
											<ChevronRight
												size={15}
												className="sidebar-active-arrow"
											/>
										)}
									</>
								)}
							</NavLink>
						);
					})}
				</nav>
			</div>

			<div className="sidebar-bottom">
				<NavLink
					to="/settings"
					onClick={onNavigate}
					aria-label="Settings"
					className={({ isActive }) =>
						`sidebar-item ${isActive ? "active" : ""}`
					}
				>
					<Settings size={18} strokeWidth={1.8} />
					<span>Settings</span>
				</NavLink>

				<NavLink
					to="/profile"
					onClick={onNavigate}
					aria-label={`${displayName} profile`}
					className={({ isActive }) => `sidebar-profile ${isActive ? "active" : ""}`}
				>
					<span className="sidebar-avatar" aria-hidden="true">{initials}</span>
					<span className="sidebar-profile-copy"><strong>{displayName}</strong><small>Workspace profile</small></span>
					<UserRound size={16} className="sidebar-profile-icon" />
				</NavLink>

				<div className="sidebar-status">
					<span className="sidebar-status-mark"><Database size={14} /></span>
					<div>
						<strong>Data provenance</strong>
						<small>Persisted workspace records</small>
					</div>
				</div>
			</div>
		</aside>
	);
}

export default Sidebar;
