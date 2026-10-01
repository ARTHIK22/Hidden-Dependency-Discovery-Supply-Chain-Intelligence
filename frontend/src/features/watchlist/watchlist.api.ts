import { apiClient } from "../../services/api/client";
import type { ApiList, WatchlistEntry } from "../../types/api.types";

export const listWatchlist = (q?: string, signal?: AbortSignal) =>
  apiClient.get<ApiList<WatchlistEntry>>("/watchlist", {
    params: { q },
    signal,
  });

export const addToWatchlist = (entityId: string) =>
  apiClient.post<WatchlistEntry>("/watchlist", { entity_id: entityId });

export type WatchTargetType = "entity" | "relationship" | "investigation" | "risk_condition";

export const addWatchTarget = (input: {
  target_type: WatchTargetType;
  target_id: string;
  risk_threshold?: number;
  condition_json?: Record<string, unknown>;
}) => apiClient.post<WatchlistEntry>("/watchlist", input);

export const removeWatchEntry = (entryId: string) =>
  apiClient.delete<void>(`/watchlist/items/${encodeURIComponent(entryId)}`);

export const removeFromWatchlist = (entityId: string) =>
  apiClient.delete<void>(`/watchlist/${encodeURIComponent(entityId)}`);
