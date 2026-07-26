/**
 * Shared Type Definitions for the Signal Clone Monorepo.
 * Allows type safety sharing between Frontend client and Backend schemas/payloads.
 */

export interface UserDTO {
  id: string;
  phoneNumber: string;
  displayName: string | null;
  avatarUrl: string | null;
  isActive: boolean;
  createdAt: string;
}

export interface MessageDTO {
  id: string;
  senderId: string;
  recipientId: string;
  content: string;
  isRead: boolean;
  messageType: "text" | "image" | "file";
  createdAt: string;
  updatedAt: string;
}

export interface SocketEventPayloads {
  "message:send": {
    recipientId: string;
    content: string;
    messageType?: "text" | "image" | "file";
  };
  "message:receive": MessageDTO;
  "message:read": {
    messageId: string;
    readerId: string;
  };
}
