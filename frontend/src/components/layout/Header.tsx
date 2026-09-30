import {
	Search,
	Bell,
	Command,
	LogOut,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Link } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";

import "./header.css";

function Header() {
	const navigate = useNavigate();
	const { user, logout } = useAuth();
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
				<Link
					to="/alerts"
					className="header-icon-button"
					aria-label="Notifications"
				>
					<Bell size={18} />
				</Link>

				<button className="profile-button" type="button" onClick={() => { logout(); navigate("/login", { replace: true }); }} aria-label="Sign out">
					<div className="profile-avatar">{user?.full_name?.charAt(0)?.toUpperCase() ?? "U"}</div>
					<div className="profile-info">
						<strong>{user?.full_name ?? "User"}</strong>
						<span>{user?.role ?? "Analyst"}</span>
					</div>
					<LogOut size={15} aria-hidden="true" />
				</button>
			</div>
		</header>
	);
}

export default Header;
