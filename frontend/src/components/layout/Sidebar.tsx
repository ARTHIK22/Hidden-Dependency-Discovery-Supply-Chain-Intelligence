import {
	LayoutDashboard,
	Search,
	Network,
	FileSearch,
	ShieldAlert,
	Bell,
	Star,
	FileText,
	Settings,
	ChevronRight,
} from "lucide-react";

import "./sidebar.css";

const navigation = [
	{ label: "Overview", icon: LayoutDashboard, active: true },
	{ label: "Research", icon: Search },
	{ label: "Dependency Graph", icon: Network },
	{ label: "Evidence", icon: FileSearch },
	{ label: "Risks", icon: ShieldAlert },
	{ label: "Alerts", icon: Bell },
	{ label: "Watchlist", icon: Star },
	{ label: "Reports", icon: FileText },
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
							<button
								key={item.label}
								className={`sidebar-item ${item.active ? "active" : ""}`}
								aria-current={item.active ? "page" : undefined}
								type="button"
							>
								<Icon size={18} strokeWidth={1.8} />
								<span>{item.label}</span>
								{item.active && (
									<ChevronRight
										size={15}
										className="sidebar-active-arrow"
									/>
								)}
							</button>
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
						<strong>Intelligence Engine</strong>
						<small>Ready for investigation</small>
					</div>
				</div>
			</div>
		</aside>
	);
}

export default Sidebar;
