import type { ApiConversation, ApiMessage } from "@/services/chat";
import type { AttachmentDraft, ChatMessage, Conversation, SearchResult } from "@/types/chat";

function initials(value: string) {
  return value
    .split(" ")
    .map((part) => part[0] || "")
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function mapApiMessage(message: ApiMessage, currentUserId: string): ChatMessage {
  const receiverReceipts = message.receipts.filter((receipt) => receipt.user_id !== message.sender_id);
  
  return {
    id: message.id,
    senderId: message.sender_id,
    content: message.content || "",
    timestamp: message.created_at,
    status:
      (message as any).status === "failed"
        ? "failed"
        : (message as any).status === "sending"
          ? "sending"
          : receiverReceipts.length > 0 && receiverReceipts.every((receipt) => receipt.status === "READ")
          ? "read"
          : receiverReceipts.some((receipt) => receipt.status === "DELIVERED" || receipt.status === "READ")
            ? "delivered"
            : "sent",
    isOutgoing: message.sender_id === currentUserId,
    isEdited: Boolean(message.edited_at),
    quotedMessageId: message.reply_to_id || undefined,
    forwardedFrom: message.forwarded_from_id || undefined,
    pinned: message.is_pinned,
    scheduledFor: message.scheduled_at || undefined,
    disappearingLabel: message.expires_at ? "custom timer" : undefined,
    reactions: message.reactions.map((reaction) => ({
      emoji: reaction.reaction,
      count: 1,
      reacted: reaction.user_id === currentUserId,
    })),
    rawAttachments: (message as any).rawAttachments,
    attachments: message.attachments.map<AttachmentDraft>((attachment) => ({
      id: attachment.id,
      name: attachment.original_filename,
      type: attachment.mime_type.startsWith("image")
        ? "image"
        : attachment.mime_type.startsWith("video")
          ? "video"
          : "document",
      sizeLabel: `${Math.max(1, Math.round(attachment.size / 1024 / 1024))} MB`,
      preview: attachment.thumbnail_url || undefined,
      progress: 100,
    })),
  };
}

export function mapApiConversation(conversation: ApiConversation, currentUserId: string): Conversation {
  const otherMembers = conversation.members.filter((member) => member.user_id !== currentUserId);
  const title =
    conversation.name ||
    otherMembers
      .map((member) => member.user?.display_name || member.user?.username || member.user?.phone || "Unknown")
      .join(", ") ||
    "Conversation";

  const myMember = conversation.members.find((member) => member.user_id === currentUserId);
  const unreadCount = myMember?.last_read_message_id !== conversation.last_message_id && conversation.last_message_id && conversation.last_message?.sender_id !== currentUserId ? 1 : 0;

  return {
    id: conversation.id,
    kind: conversation.type === "GROUP" ? "group" : "direct",
    title,
    avatar: initials(title),
    members: otherMembers.map((member) => ({
      id: member.user_id,
      name: member.user?.display_name || member.user?.username || member.user?.phone || "Unknown",
      phone: member.user?.phone || "",
      avatar: initials(member.user?.display_name || member.user?.username || member.user?.phone || "U"),
      status:
        member.user?.presence_status === "ONLINE"
          ? "online"
          : member.user?.presence_status === "AWAY"
            ? "away"
            : "offline",
      about: member.user?.bio || "",
    })),
    unreadCount,
    isMuted: false,
    lastMessage: conversation.last_message?.content || "No messages yet",
    lastMessageAt: conversation.last_activity_at,
    messages: conversation.last_message
      ? [mapApiMessage(conversation.last_message, currentUserId)]
      : [],
  };
}

export function mapSearchResults(
  query: string,
  payload: {
    contacts: Array<{
      id: string;
      nickname: string | null;
      contact_user_id: string;
      contact_user: {
        display_name: string | null;
        username: string | null;
        phone: string;
      } | null;
    }>;
    conversations: ApiConversation[];
    messages: ApiMessage[];
  },
  currentUserId: string
): SearchResult[] {
  const contactResults: SearchResult[] = payload.contacts.map((contact) => ({
    id: `contact-${contact.id}`,
    type: "contact",
    title:
      contact.nickname ||
      contact.contact_user?.display_name ||
      contact.contact_user?.username ||
      contact.contact_user?.phone ||
      "Contact",
    subtitle: contact.contact_user?.phone || "",
    highlight: query,
  }));

  const conversationResults: SearchResult[] = payload.conversations.map((conversation) => {
    const mapped = mapApiConversation(conversation, currentUserId);
    return {
      id: `conversation-${conversation.id}`,
      type: "conversation",
      title: mapped.title,
      subtitle: mapped.lastMessage,
      conversationId: conversation.id,
      highlight: query,
    };
  });

  const messageResults: SearchResult[] = payload.messages.map((message) => ({
    id: `message-${message.id}`,
    type: "message",
    title: "Message result",
    subtitle: message.content || "",
    conversationId: message.conversation_id,
    highlight: query,
  }));

  return [...contactResults, ...conversationResults, ...messageResults];
}
