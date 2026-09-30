import { apiClient } from "../../services/api/client";
import type { ApiList, WatchlistEntry } from "../../types/api.types";

export const listWatchlist = (q?: string, signal?: AbortSignal) =>
  apiClient.get<ApiList<WatchlistEntry>>("/watchlist", {
    params: { q },
    signal,
  });

export const addToWatchlist = (entityId: string) =>
  apiClient.post<WatchlistEntry>("/watchlist", { entity_id: entityId });

export const removeFromWatchlist = (entityId: string) =>
  apiClient.delete<void>(`/watchlist/${encodeURIComponent(entityId)}`);
