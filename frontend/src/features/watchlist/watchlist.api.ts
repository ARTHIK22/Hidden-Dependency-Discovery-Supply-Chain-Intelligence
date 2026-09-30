import { apiClient } from "../../services/api/client";
import type { WatchlistItem } from "../../types/graph.types";
export const listWatchlist = () => apiClient.get<WatchlistItem[]>("/watchlists");
export const addToWatchlist = (entityId: string, name?: string) => apiClient.post<WatchlistItem>(`/watchlists/${encodeURIComponent(entityId)}${name ? `?name=${encodeURIComponent(name)}` : ""}`);
export const removeFromWatchlist = (entityId: string) => apiClient.delete<void>(`/watchlists/${encodeURIComponent(entityId)}`);
