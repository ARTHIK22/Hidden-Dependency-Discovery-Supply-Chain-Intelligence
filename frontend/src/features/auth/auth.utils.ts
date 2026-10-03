import { ApiError } from "../../services/api/errors";

type AuthOperation = "login" | "register";

export function authErrorMessage(error: unknown, operation: AuthOperation): string {
  if (error instanceof ApiError) {
    if (error.status === 0) {
      return "Unable to connect. Please check your connection and try again.";
    }
    if (operation === "login" && error.status === 401) {
      return "Incorrect email or password.";
    }
    if (operation === "register" && error.status === 409) {
      return "An account with this email already exists.";
    }
    if (error.status === 429) {
      return "Too many attempts. Please wait a moment and try again.";
    }
  }

  return "Something went wrong. Please try again.";
}
