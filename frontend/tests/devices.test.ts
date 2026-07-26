import test from "node:test";
import assert from "node:assert/strict";
import { DeviceTokenData } from "@/services/devices";

test("device token payload validation and structure", () => {
  const sampleDevice: DeviceTokenData = {
    id: "dev-123",
    user_id: "user-456",
    device_id: "web-browser-safari",
    platform: "web",
    fcm_token: "fcm-token-web-789",
    created_at: "2026-07-26T12:00:00Z",
    updated_at: "2026-07-26T12:00:00Z",
    last_seen: "2026-07-26T12:00:00Z",
  };

  assert.equal(sampleDevice.platform, "web");
  assert.equal(sampleDevice.device_id, "web-browser-safari");
  assert.ok(sampleDevice.fcm_token.startsWith("fcm-token"));
});
