import { Navigate, Route, Routes } from "react-router-dom";
import Dashboard from "../pages/Dashboard/Dashboard";
import CreateInvestigation from "../pages/Investigations/CreateInvestigation";
import InvestigationDetails from "../pages/Investigations/InvestigationDetails";
import DependencyGraph from "../pages/Graph/DependencyGraph";
import Evidence from "../pages/Evidence/Evidence";
import RiskIntelligence from "../pages/Risks/RiskIntelligence";

function AppRoutes() {
	return <Routes>
		<Route path="/" element={<Dashboard />} />
		<Route path="/investigations/new" element={<CreateInvestigation />} />
		<Route path="/investigations/demo" element={<InvestigationDetails />} />
		<Route path="/graph" element={<DependencyGraph />} />
		<Route path="/evidence" element={<Evidence />} />
		<Route path="/risks" element={<RiskIntelligence />} />
		<Route path="*" element={<Navigate to="/" replace />} />
	</Routes>;
}

export default AppRoutes;
