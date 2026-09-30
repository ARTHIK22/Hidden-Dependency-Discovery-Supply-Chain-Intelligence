import { apiClient } from "../../services/api/client";
import type { RiskAnalysis } from "../../types/risk.types";
export const getRiskAnalysis = () => apiClient.get<RiskAnalysis>("/risks/analysis");
