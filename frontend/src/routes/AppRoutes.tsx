import { AnimatePresence, motion } from "framer-motion";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import Dashboard from "../pages/Dashboard/Dashboard";

import CreateInvestigation from "../pages/Investigations/CreateInvestigation";
import InvestigationDetails from "../pages/Investigations/InvestigationDetails";
import InvestigationHistory from "../pages/Investigations/InvestigationHistory";

import DependencyGraph from "../pages/Graph/DependencyGraph";

import Evidence from "../pages/Evidence/Evidence";

import EntityExplorer from "../pages/Entities/EntityExplorer";

import RiskIntelligence from "../pages/Risks/RiskIntelligence";

import Alerts from "../pages/Alerts/Alerts";

import Watchlist from "../pages/Watchlist/Watchlist";

import Reports from "../pages/Reports/Reports";

import Profile from "../pages/Profile/Profile";

import Settings from "../pages/Settings/Settings";

function PageTransition({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <motion.div
      initial={{
        opacity: 0,
        y: 8,
        filter: "blur(4px)",
      }}
      animate={{
        opacity: 1,
        y: 0,
        filter: "blur(0px)",
      }}
      transition={{
        duration: 0.22,
        ease: [0.22, 1, 0.36, 1],
      }}
      style={{
        width: "100%",
      }}
    >
      {children}
    </motion.div>
  );
}

export default function AppRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes
        location={location}
        key={location.pathname}
      >
        {/* Dashboard */}
        <Route
          path="/"
          element={
            <PageTransition>
              <Dashboard />
            </PageTransition>
          }
        />

        {/* Investigations */}
        <Route
          path="/investigations"
          element={
            <PageTransition>
              <InvestigationHistory />
            </PageTransition>
          }
        />

        <Route
          path="/investigations/new"
          element={
            <PageTransition>
              <CreateInvestigation />
            </PageTransition>
          }
        />

        <Route
          path="/investigations/:investigationId"
          element={
            <PageTransition>
              <InvestigationDetails />
            </PageTransition>
          }
        />

        {/* Graph */}
        <Route
          path="/graph"
          element={
            <PageTransition>
              <DependencyGraph />
            </PageTransition>
          }
        />

        {/* Evidence */}
        <Route
          path="/evidence"
          element={
            <PageTransition>
              <Evidence />
            </PageTransition>
          }
        />

        {/* Entities */}
        <Route
          path="/entities"
          element={
            <PageTransition>
              <EntityExplorer />
            </PageTransition>
          }
        />

        {/* Risk */}
        <Route
          path="/risks"
          element={
            <PageTransition>
              <RiskIntelligence />
            </PageTransition>
          }
        />

        {/* Alerts */}
        <Route
          path="/alerts"
          element={
            <PageTransition>
              <Alerts />
            </PageTransition>
          }
        />

        {/* Watchlist */}
        <Route
          path="/watchlist"
          element={
            <PageTransition>
              <Watchlist />
            </PageTransition>
          }
        />

        {/* Reports */}
        <Route
          path="/reports"
          element={
            <PageTransition>
              <Reports />
            </PageTransition>
          }
        />

        {/* Profile */}
        <Route
          path="/profile"
          element={
            <PageTransition>
              <Profile />
            </PageTransition>
          }
        />

        {/* Settings */}
        <Route
          path="/settings"
          element={
            <PageTransition>
              <Settings />
            </PageTransition>
          }
        />

        <Route
          path="*"
          element={<Navigate to="/" replace />}
        />
      </Routes>
    </AnimatePresence>
  );
}
