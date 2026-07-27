import type { AuthSessionPayload, AuthUser, DeviceSession } from "@/types/auth";

import { apiRequest } from "@/services/api";

export interface SendOtpPayload {
  phone: string;
}

export interface VerifyOtpPayload {
  phone: string;
  otp: string;
}

export interface RegisterPayload {
  registration_token: string;
  phone: string;
  username: string;
  display_name: string;
  avatar_url?: string;
}

export interface LoginSendOtpPayload {
  login_id: string;
}

export interface LoginVerifyOtpPayload {
  login_id: string;
  otp: string;
}


export interface RefreshPayload {
  access_token: string;
  refresh_token: string;
  token_type: string;
}


export async function sendOtp(payload: SendOtpPayload) {
  return apiRequest<{ message: string }>("/api/v1/auth/register/send-otp", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function verifyOtp(payload: VerifyOtpPayload) {
  return apiRequest<{ registration_token: string; message: string }>("/api/v1/auth/register/verify", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function registerUser(payload: RegisterPayload) {
  return apiRequest<AuthSessionPayload>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function sendLoginOtp(payload: LoginSendOtpPayload) {
  return apiRequest<{ message: string }>("/api/v1/auth/login/send-otp", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function verifyLoginOtp(payload: LoginVerifyOtpPayload) {
  return apiRequest<AuthSessionPayload>("/api/v1/auth/login/verify", {
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

export async function checkUsername(username: string) {
  return apiRequest<{ available: boolean }>(`/api/v1/auth/check-username?username=${encodeURIComponent(username)}`);
}

export async function updateProfile(
  token: string,
  payload: {
    display_name?: string;
    username?: string;
    avatar_url?: string;
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
