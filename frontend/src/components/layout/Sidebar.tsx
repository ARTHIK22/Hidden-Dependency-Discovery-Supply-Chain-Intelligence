import {
	LayoutDashboard,
	Search,
	Building2,
	GitBranch,
	Globe2,
	Network,
	FileSearch,
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
	{ label: "Overview", icon: LayoutDashboard, path: "/" },
	{ label: "Investigations", icon: Search, path: "/investigations" },
	{ label: "Entities", icon: Building2, path: "/entities" },
	{ label: "Relationships", icon: GitBranch, path: "/relationships" },
	{ label: "Sources", icon: Globe2, path: "/sources" },
	{ label: "Dependency Graph", icon: Network, path: "/graph" },
	{ label: "Evidence", icon: FileSearch, path: "/evidence" },
	{ label: "Risks", icon: ShieldAlert, path: "/risks" },
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
				<button className="sidebar-item" type="button">
					<Settings size={18} strokeWidth={1.8} />
					<span>Settings</span>
				</button>

				<div className="sidebar-status">
					<span className="status-dot" />
					<div>
						<strong>Backend connection</strong>
						<small>Stored-data analysis available</small>
					</div>
				</div>
			</div>
		</aside>
	);
}

export default Sidebar;
