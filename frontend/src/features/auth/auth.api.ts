import { apiClient } from "../../services/api/client";
import type { LoginRequest, RegisterRequest, TokenResponse } from "../../types/auth.types";
import type { User } from "../../types/user.types";
export const login = (payload: LoginRequest) => apiClient.post<TokenResponse>("/auth/login", payload);
export const register = (payload: RegisterRequest) => apiClient.post<TokenResponse>("/auth/register", payload);
export const getCurrentUser = () => apiClient.get<User>("/auth/me");
export const updateProfile = (full_name: string) => apiClient.patch<User>("/users/me", { full_name });
