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
	ChevronRight,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import "./sidebar.css";

const navigation = [
	{ label: "Dashboard", icon: LayoutDashboard, path: "/" },
	{ label: "Investigations", icon: FolderSearch, path: "/investigations" },
	{ label: "Dependency Graph", icon: Network, path: "/graph" },
	{ label: "Entities", icon: Search, path: "/entities" },
	{ label: "Evidence", icon: FileText, path: "/evidence" },
	{ label: "Risk Intelligence", icon: ShieldAlert, path: "/risks" },
	{ label: "Alerts", icon: Bell, path: "/alerts" },
	{ label: "Watchlist", icon: Star, path: "/watchlist" },
	{ label: "Reports", icon: FileText, path: "/reports" },
];

function Sidebar() {
	return (
		<aside className="sidebar glass">
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
					className={({ isActive }) =>
						`sidebar-item ${isActive ? "active" : ""}`
					}
				>
					<Settings size={18} strokeWidth={1.8} />
					<span>Settings</span>
				</NavLink>

				<div className="sidebar-status">
					<span className="status-dot" />
					<div>
						<strong>Intelligence Engine</strong>
						<small>Ready for investigation</small>
					</div>
				</div>
			</div>
		</aside>
	);
}

export default Sidebar;
