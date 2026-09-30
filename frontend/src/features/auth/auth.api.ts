import { ApiError } from "../../services/api/client";
import type { LoginRequest, RegisterRequest, TokenResponse } from "../../types/auth.types";
import type { User } from "../../types/user.types";

function authenticationUnavailable<T>(): Promise<T> {
  return Promise.reject(
    new ApiError("Authentication is unavailable because the current backend does not provide authentication endpoints.", 501, null),
  );
}

// These signatures remain available to the existing auth screens, but the
// current FastAPI backend does not expose the corresponding routes.
export const login = (_payload: LoginRequest): Promise<TokenResponse> => authenticationUnavailable();
export const register = (_payload: RegisterRequest): Promise<TokenResponse> => authenticationUnavailable();
export const getCurrentUser = (): Promise<User> => authenticationUnavailable();
export const updateProfile = (_fullName: string): Promise<User> => authenticationUnavailable();
