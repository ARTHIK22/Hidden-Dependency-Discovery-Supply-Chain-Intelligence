import { get, post, queryString, remove } from "../../services/api/client";
import type { ApiList, Entity, EntityDetail, WatchlistEntry } from "../../types/api.types";

export const listEntities = (q?: string, signal?: AbortSignal) =>
  get<ApiList<Entity>>(`/entities${queryString({ q, limit: 250 })}`, signal);

export const getEntity = (id: string, signal?: AbortSignal) =>
  get<EntityDetail>(`/entities/${encodeURIComponent(id)}`, signal);

export const searchWorkspace = (q: string, signal?: AbortSignal) =>
  get<{ items: Array<{ id: string; type: "entity" | "investigation"; label: string; path: string }> }>(
    `/search${queryString({ q, limit: 12 })}`,
    signal,
  );

export const listWatchlist = (q?: string, signal?: AbortSignal) =>
  get<ApiList<WatchlistEntry>>(`/watchlist${queryString({ q })}`, signal);

export const addToWatchlist = (entity_id: string) =>
  post<WatchlistEntry>("/watchlist", { entity_id });

export const removeFromWatchlist = (entityId: string) =>
  remove(`/watchlist/${encodeURIComponent(entityId)}`);
