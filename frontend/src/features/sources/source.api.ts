import { ApiError } from "../../services/api/client";
import type { Source, SourceCreate } from "../../types/source.types";

function sourcesUnavailable<T>(): Promise<T> {
  return Promise.reject(
    new ApiError("Source catalog endpoints are not available in the current backend.", 501, null),
  );
}

export const listSources = (_params: { limit?: number; offset?: number } = {}): Promise<Source[]> =>
  sourcesUnavailable();
export const createSource = (_payload: SourceCreate): Promise<Source> => sourcesUnavailable();
