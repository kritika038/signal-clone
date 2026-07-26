import type { AuthSessionPayload, AuthUser, DeviceSession } from "@/types/auth";

import { apiRequest } from "@/services/api";

export interface RegisterPayload {
  phone: string;
  username: string;
  password: string;
  display_name: string;
}

export interface LoginPayload {
  login_id: string;
  password: string;
}

export interface VerifyOtpPayload {
  phone: string;
  otp: string;
}

export interface RefreshPayload {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RegistrationResult {
  message: string;
  otp_mock: string;
}

export async function registerUser(payload: RegisterPayload) {
  return apiRequest<RegistrationResult>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function verifyOtp(payload: VerifyOtpPayload) {
  return apiRequest<AuthSessionPayload>("/api/v1/auth/verify-otp", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function loginUser(payload: LoginPayload) {
  return apiRequest<AuthSessionPayload>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function refreshSession(token: string) {
  return apiRequest<RefreshPayload>("/api/v1/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: token }),
  });
}

export async function logoutUser(token: string) {
  return apiRequest<{ message: string }>("/api/v1/auth/logout", {
    method: "POST",
    token,
  });
}

export async function fetchMe(token: string) {
  return apiRequest<AuthUser>("/api/v1/auth/me", { token });
}

export async function fetchSession(token: string) {
  return apiRequest<DeviceSession>("/api/v1/auth/session", { token });
}

export async function updateProfile(
  token: string,
  payload: {
    display_name?: string;
    bio?: string;
    theme?: string;
    privacy_read_receipts?: boolean;
    privacy_typing_indicator?: boolean;
    notifications_enabled?: boolean;
  }
) {
  return apiRequest<AuthUser>("/api/v1/auth/me", {
    method: "PATCH",
    token,
    body: JSON.stringify(payload),
  });
}
