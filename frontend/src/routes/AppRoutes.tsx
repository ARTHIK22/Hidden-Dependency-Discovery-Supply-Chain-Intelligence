import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import AppLayout from "../components/layout/AppLayout";
import ProtectedRoute from "./ProtectedRoute";
import { authRoutes } from "./auth.routes";
import Dashboard from "../pages/Dashboard/Dashboard";
import Alerts from "../pages/Alerts/Alerts";
import Watchlist from "../pages/Watchlist/Watchlist";
import CreateInvestigation from "../pages/Investigations/CreateInvestigation";
import InvestigationList from "../pages/Investigations/InvestigationList";
import InvestigationDetails from "../pages/Investigations/InvestigationDetails";
import DependencyGraph from "../pages/Graph/DependencyGraph";
import Evidence from "../pages/Evidence/Evidence";
import RiskIntelligence from "../pages/Risks/RiskIntelligence";
import EntityList from "../pages/Entities/EntityList";
import RelationshipList from "../pages/Relationships/RelationshipList";
import SourceList from "../pages/Sources/SourceList";
import ReportList from "../pages/Reports/ReportList";

function AppRoutes() {
	return <Routes>
		{authRoutes}
		<Route element={<ProtectedRoute><AppLayout><Outlet /></AppLayout></ProtectedRoute>}>
			<Route path="/" element={<Dashboard />} />
			<Route path="/investigations/new" element={<CreateInvestigation />} />
			<Route path="/investigations" element={<InvestigationList />} />
			<Route path="/investigations/:investigationId" element={<InvestigationDetails />} />
			<Route path="/investigations/demo" element={<InvestigationDetails />} />
			<Route path="/graph" element={<DependencyGraph />} />
			<Route path="/evidence" element={<Evidence />} />
			<Route path="/entities" element={<EntityList />} />
			<Route path="/relationships" element={<RelationshipList />} />
			<Route path="/sources" element={<SourceList />} />
			<Route path="/reports" element={<ReportList />} />
			<Route path="/risks" element={<RiskIntelligence />} />
			<Route path="/alerts" element={<Alerts />} />
			<Route path="/watchlist" element={<Watchlist />} />
		</Route>
		<Route path="*" element={<Navigate to="/" replace />} />
	</Routes>;
}

export default AppRoutes;
