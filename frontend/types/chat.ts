export type ThemeMode = "light" | "dark" | "system";
export type SettingsSection =
  | "contacts"
  | "profile"
  | "appearance"
  | "notifications"
  | "privacy"
  | "storage"
  | "linked-devices"
  | "stories"
  | "about";

export interface Contact {
  id: string;
  name: string;
  phone: string;
  avatar: string;
  status: "online" | "offline" | "away";
  about: string;
}

export interface Reaction {
  emoji: string;
  count: number;
  reacted: boolean;
}

export interface AttachmentDraft {
  id: string;
  name: string;
  type: "image" | "video" | "document";
  sizeLabel: string;
  preview?: string;
  progress: number;
}

export interface ChatMessage {
  id: string;
  senderId: string;
  content: string;
  timestamp: string;
  status: "sending" | "sent" | "delivered" | "read" | "failed";
  isOutgoing: boolean;
  isEdited?: boolean;
  quotedMessageId?: string;
  forwardedFrom?: string;
  pinned?: boolean;
  scheduledFor?: string;
  disappearingLabel?: string;
  reactions?: Reaction[];
  rawAttachments?: any[];
  attachments?: AttachmentDraft[];
}

export interface Conversation {
  id: string;
  kind: "direct" | "group";
  title: string;
  avatar: string;
  members: Contact[];
  unreadCount: number;
  isMuted: boolean;
  lastMessage: string;
  lastMessageAt: string;
  typingText?: string;
  draft?: string;
  messages: ChatMessage[];
}

export interface SearchResult {
  id: string;
  type: "contact" | "conversation" | "message";
  title: string;
  subtitle: string;
  conversationId?: string;
  highlight: string;
}
