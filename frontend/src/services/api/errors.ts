import { ApiError } from "./client";

export { ApiError };

export function userMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "Your session has expired. Please sign in again.";
    if (error.status === 403) return "You do not have permission to do that.";
    if (error.status === 404) return "The requested item could not be found.";
    if (error.status === 409) return error.message || "This change conflicts with existing data.";
    if (error.status === 422) return error.message || "Please check the submitted information.";
    if (error.status === 501) return error.message;
    if (error.status >= 500) return "The server could not complete the request. Please try again.";
    return error.message;
  }
  return error instanceof Error ? error.message : "The backend could not be reached. Check that it is running and try again.";
}
