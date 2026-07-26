import { apiRequest } from "./api";

export interface DeviceTokenData {
  id: string;
  user_id: string;
  device_id: string;
  platform: string;
  fcm_token: string;
  created_at: string;
  updated_at: string;
  last_seen: string;
}

export async function registerDeviceToken(
  params: { device_id: string; platform: string; fcm_token: string },
  token: string
): Promise<DeviceTokenData> {
  return apiRequest<DeviceTokenData>("/api/v1/devices/register", {
    method: "POST",
    body: JSON.stringify(params),
    token,
  });
}

export async function deleteDeviceToken(
  deviceId: string,
  token: string
): Promise<{ removed: boolean; device_id: string }> {
  return apiRequest<{ removed: boolean; device_id: string }>(`/api/v1/devices/${deviceId}`, {
    method: "DELETE",
    token,
  });
}

export async function getDevices(token: string): Promise<DeviceTokenData[]> {
  return apiRequest<DeviceTokenData[]>("/api/v1/devices", {
    method: "GET",
    token,
  });
}
