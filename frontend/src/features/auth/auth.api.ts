import { apiClient } from "../../services/api/client";
import type { LoginRequest, RegisterRequest, TokenResponse } from "../../types/auth.types";
import type { User } from "../../types/user.types";

export const login = (payload: LoginRequest): Promise<TokenResponse> =>
  apiClient.post<TokenResponse>("/auth/login", payload);

export const register = (payload: RegisterRequest): Promise<TokenResponse> =>
  apiClient.post<TokenResponse>("/auth/register", payload);

export const getCurrentUser = (): Promise<User> =>
  apiClient.get<User>("/auth/me");

export const logout = (): Promise<void> =>
  apiClient.post<void>("/auth/logout");
