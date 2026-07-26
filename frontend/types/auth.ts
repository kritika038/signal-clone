export interface UserSettings {
  theme: string;
  language: string;
  privacy_last_seen: boolean;
  privacy_profile_photo: boolean;
  privacy_read_receipts: boolean;
  privacy_typing_indicator: boolean;
  notifications_enabled: boolean;
  auto_download_media: boolean;
  default_disappearing_timer: number;
  font_size: string;
}

export interface AuthUser {
  id: string;
  phone: string;
  username: string;
  display_name: string | null;
  bio: string | null;
  avatar_url: string | null;
  presence_status: string | null;
  last_seen: string | null;
  is_verified: boolean;
  settings: UserSettings | null;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AuthSessionPayload {
  user: AuthUser;
  session_id: string;
  tokens: AuthTokens;
}

export interface DeviceSession {
  session_id: string;
  device_name: string;
  device_type: string;
  ip_address: string;
  last_activity: string | null;
  expires_at: string;
}
