import { apiRequest, API_URL } from "@/services/api";

export interface ApiUserSummary {
  id: string;
  phone: string;
  username: string | null;
  display_name: string | null;
  bio: string | null;
  avatar_url: string | null;
  presence_status: string | null;
  last_seen: string | null;
  is_verified: boolean;
}

export interface ApiConversationMember {
  id: string;
  conversation_id: string;
  user_id: string;
  role: string;
  nickname: string | null;
  joined_at: string;
  left_at: string | null;
  notifications_enabled: boolean;
  last_read_message_id: string | null;
  user: ApiUserSummary | null;
}

export interface ApiMessageAttachment {
  id: string;
  storage_key: string;
  original_filename: string;
  mime_type: string;
  size: number;
  width: number | null;
  height: number | null;
  duration: number | null;
  thumbnail_url: string | null;
  checksum: string | null;
}

export interface ApiMessageReaction {
  id: string;
  user_id: string;
  reaction: string;
  unicode: string;
}

export interface ApiMessageReceipt {
  id: string;
  user_id: string;
  status: string | null;
  updated_at: string;
}

export interface ApiMessage {
  id: string;
  conversation_id: string;
  sender_id: string;
  content: string | null;
  message_type: string | null;
  reply_to_id: string | null;
  edited_at: string | null;
  expires_at: string | null;
  forwarded_from_id: string | null;
  is_system: boolean;
  client_message_id: string | null;
  scheduled_at: string | null;
  is_draft: boolean;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
  attachments: ApiMessageAttachment[];
  reactions: ApiMessageReaction[];
  receipts: ApiMessageReceipt[];
}

export interface ApiConversation {
  id: string;
  type: string | null;
  name: string | null;
  description: string | null;
  avatar_url: string | null;
  created_by: string | null;
  updated_by: string | null;
  last_message_id: string | null;
  last_activity_at: string;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
  members: ApiConversationMember[];
  last_message: ApiMessage | null;
}

export interface ApiSearchResult {
  users: Array<{
    id: string;
    username: string | null;
    display_name: string | null;
    phone: string;
  }>;
  contacts: Array<{
    id: string;
    owner_id: string;
    contact_user_id: string;
    nickname: string | null;
    contact_user: ApiUserSummary | null;
  }>;
  conversations: ApiConversation[];
  messages: ApiMessage[];
}

export async function fetchConversations(token: string) {
  return apiRequest<ApiConversation[]>("/api/v1/conversations", { token });
}

export async function fetchConversation(token: string, conversationId: string) {
  return apiRequest<ApiConversation>(`/api/v1/conversations/${conversationId}`, { token });
}

export async function createDirectConversation(token: string, participantId: string) {
  return apiRequest<ApiConversation>("/api/v1/conversations", {
    method: "POST",
    token,
    body: JSON.stringify({ participant_id: participantId }),
  });
}

export async function fetchMessages(token: string, conversationId: string, limit: number = 50, skip: number = 0) {
  return apiRequest<ApiMessage[]>(`/api/v1/conversations/${conversationId}/messages?limit=${limit}&skip=${skip}`, { token });
}

export async function sendMessage(
  token: string,
  conversationId: string,
  payload: {
    content?: string | null;
    message_type?: string;
    reply_to_id?: string | null;
    attachments?: Array<Record<string, unknown>>;
    client_message_id?: string;
    scheduled_at?: string | null;
  }
) {
  return apiRequest<ApiMessage>(`/api/v1/conversations/${conversationId}/messages`, {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function editMessage(token: string, messageId: string, content: string) {
  return apiRequest<ApiMessage>(`/api/v1/messages/${messageId}`, {
    method: "PATCH",
    token,
    body: JSON.stringify({ content }),
  });
}

export async function deleteMessage(token: string, messageId: string, deleteType: "me" | "everyone" = "everyone") {
  return apiRequest<{ deleted?: boolean; id?: string } | ApiMessage>(
    `/api/v1/messages/${messageId}?delete_type=${deleteType}`,
    {
      method: "DELETE",
      token,
    }
  );
}

export async function uploadMedia(token: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return apiRequest<Record<string, unknown>>(`/api/v1/media/upload`, {
    method: "POST",
    token,
    body: formData,
  });
}

export async function createGroup(
  token: string,
  payload: { name: string; description: string | null; avatar_url?: string | null; member_ids: string[] }
) {
  return apiRequest<ApiConversation>("/api/v1/groups", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function searchGlobal(token: string, query: string) {
  return apiRequest<ApiSearchResult>(`/api/v1/search?q=${encodeURIComponent(query)}`, { token });
}

export async function searchUserByPhone(token: string, phone: string) {
  return apiRequest<ApiUserSummary | null>(`/api/v1/search/phone?q=${encodeURIComponent(phone)}`, { token });
}

export async function updateGroup(
  token: string,
  groupId: string,
  payload: {
    name?: string | null;
    description?: string | null;
    avatar_url?: string | null;
  }
) {
  return apiRequest<ApiConversation>(`/api/v1/groups/${groupId}`, {
    method: "PATCH",
    token,
    body: JSON.stringify(payload),
  });
}

export async function addGroupMember(token: string, groupId: string, userId: string, role: string = "MEMBER") {
  return apiRequest<{
    success: boolean;
    data: {
      id: string;
      conversation_id: string;
      user_id: string;
      role: string;
      left_at: string | null;
    };
  }>(`/api/v1/groups/${groupId}/members`, {
    method: "POST",
    token,
    body: JSON.stringify({ user_id: userId, role }),
  });
}

export async function removeGroupMember(token: string, groupId: string, memberId: string) {
  return apiRequest<{
    success: boolean;
    data: { removed: boolean; conversation_id: string; member_id: string };
  }>(`/api/v1/groups/${groupId}/members/${memberId}`, {
    method: "DELETE",
    token,
  });
}

export async function updateGroupMemberRole(token: string, groupId: string, memberId: string, role: "ADMIN" | "MEMBER") {
  return apiRequest<Record<string, any>>(`/api/v1/groups/${groupId}/members/${memberId}`, {
    method: "PATCH",
    token,
    body: JSON.stringify({ role }),
  });
}
export async function leaveGroup(token: string, groupId: string) {
  return apiRequest<Record<string, any>>(`/api/v1/groups/${groupId}/leave`, {
    method: "DELETE",
    token,
  });
}
