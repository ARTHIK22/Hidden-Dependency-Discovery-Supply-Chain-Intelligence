import {
	Search,
	Bell,
	Command,
} from "lucide-react";

import "./header.css";

function Header() {
	return (
		<header className="app-header">
			<div className="header-search">
				<Search size={17} aria-hidden="true" />
				<input
					type="text"
					aria-label="Search investigations, entities, and sources"
					placeholder="Search investigations, entities, sources..."
				/>
				<div className="search-shortcut" aria-hidden="true">
					<Command size={11} />
					<span>K</span>
				</div>
			</div>

			<div className="header-actions">
				<button
					className="header-icon-button"
					aria-label="Notifications"
					type="button"
				>
					<Bell size={18} />
					<span className="notification-dot" />
				</button>

				<div className="profile-button">
					<div className="profile-avatar">A</div>
					<div className="profile-info">
						<strong>Arthik</strong>
						<span>Analyst</span>
					</div>
				</div>
			</div>
		</header>
	);
}

export default Header;
