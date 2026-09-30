import { get } from "./client";
import type { DashboardSummary } from "../../types/api.types";

export const getDashboardSummary = (signal?: AbortSignal) =>
  get<DashboardSummary>("/dashboard/summary", signal);
