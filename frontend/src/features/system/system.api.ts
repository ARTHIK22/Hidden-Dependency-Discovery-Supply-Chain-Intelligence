import { apiClient } from "../../services/api/client";
export interface HealthStatus { success: boolean; status: string; service: string; version: string; database: string; redis: string; timestamp: string }
export interface ReadinessStatus { success: boolean; status: string; services: { api: string; database: string; redis: string } }
export const getHealth = () => apiClient.get<HealthStatus>("/health");
export const getReadiness = () => apiClient.get<ReadinessStatus>("/health/ready");
