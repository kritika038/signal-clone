import { apiRequest } from "@/services/api";
import type { ApiUserSummary } from "@/services/chat";

export interface ApiContact {
  id: string;
  owner_id: string;
  contact_user_id: string;
  nickname: string | null;
  contact_user: ApiUserSummary | null;
}

export function fetchContacts(token: string) {
  return apiRequest<ApiContact[]>("/api/v1/contacts", { token });
}

export function createContact(token: string, contactUserId: string, nickname?: string) {
  return apiRequest<ApiContact>("/api/v1/contacts", {
    method: "POST",
    token,
    body: JSON.stringify({ contact_user_id: contactUserId, nickname: nickname || null }),
  });
}

export function deleteContact(token: string, contactId: string) {
  return apiRequest<{ deleted: boolean; id: string }>(`/api/v1/contacts/${contactId}`, { method: "DELETE", token });
}
