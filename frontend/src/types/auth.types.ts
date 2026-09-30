import type { User } from "./user.types";
export interface LoginRequest { email: string; password: string }
export interface RegisterRequest extends LoginRequest { full_name: string }
export interface TokenResponse { access_token: string; token_type: string; user: User }
