import { ApiError, apiClient } from "../../services/api/client";

export interface HealthStatus {
  status: "ok" | "degraded";
  database: "connected" | "unavailable" | "not_configured";
  environment: string;
}

export const getHealth = () => apiClient.get<HealthStatus>("/health");

export const getReadiness = (): Promise<never> => Promise.reject(
  new ApiError("The current backend does not provide a separate readiness endpoint.", 501, null),
);
