with open("frontend/services/chat.ts", "a") as f:
    f.write("""
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
""")
print("Added APIs to chat.ts")
