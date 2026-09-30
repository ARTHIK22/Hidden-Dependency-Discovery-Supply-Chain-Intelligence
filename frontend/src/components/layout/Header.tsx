import GlobalSearch from "../search/GlobalSearch";
import Notifications from "../notifications/Notifications";
import ProfileMenu from "../profile/ProfileMenu";

import "./header.css";

function Header() {
	return (
		<header className="app-header">
			<div className="header-actions">
				<GlobalSearch />
				<Notifications />
				<ProfileMenu />
			</div>
		</header>
	);
}

export default Header;
