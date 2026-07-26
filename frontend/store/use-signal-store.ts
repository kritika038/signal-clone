"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type {
  AttachmentDraft,
  SettingsSection,
  ThemeMode,
} from "@/types/chat";

interface SignalState {
  theme: ThemeMode;
  isSidebarOpen: boolean;
  isSettingsOpen: boolean;
  activeSettingsSection: SettingsSection;
  activeConversationId: string | null;
  replyToMessageId: string | null;
  composerText: string;
  queuedAttachments: AttachmentDraft[];
  searchQuery: string;
  isOffline: boolean;
  isSocketConnected: boolean;
  socketBanner: string | null;
  featureNotice: string | null;
  setTheme: (theme: ThemeMode) => void;
  toggleSidebar: () => void;
  openSettings: (section?: SettingsSection) => void;
  closeSettings: () => void;
  selectConversation: (id: string) => void;
  setSearchQuery: (query: string) => void;
  setComposerText: (value: string) => void;
  queueAttachment: (attachment: AttachmentDraft) => void;
  clearQueuedAttachments: () => void;
  sendMessage: () => void;
  setReplyTarget: (messageId: string | null) => void;
  toggleReaction: (conversationId: string, messageId: string, emoji: string) => void;
  editMessage: (conversationId: string, messageId: string, content: string) => void;
  deleteMessage: (conversationId: string, messageId: string) => void;
  markOffline: (offline: boolean) => void;
  setSocketState: (connected: boolean, banner?: string | null) => void;
  createGroup: (name: string, memberIds: string[]) => void;
  setFeatureNotice: (message: string | null) => void;
}

export const useSignalStore = create<SignalState>()(
  persist(
    (set) => ({
      theme: "system",
      isSidebarOpen: true,
      isSettingsOpen: false,
      activeSettingsSection: "profile",
      activeConversationId: null,
      replyToMessageId: null,
      composerText: "",
      queuedAttachments: [],
      searchQuery: "",
      isOffline: false,
      isSocketConnected: false,
      socketBanner: "Connecting to Signal service…",
      featureNotice: null,
      setTheme: (theme) => set({ theme }),
      toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
      openSettings: (section = "profile") =>
        set({ isSettingsOpen: true, activeSettingsSection: section }),
      closeSettings: () => set({ isSettingsOpen: false }),
      selectConversation: (id) => set({ activeConversationId: id, replyToMessageId: null }),
      setSearchQuery: (query) => set({ searchQuery: query }),
      setComposerText: (value) => set({ composerText: value }),
      queueAttachment: (attachment) =>
        set((state) => ({ queuedAttachments: [...state.queuedAttachments, attachment] })),
      clearQueuedAttachments: () => set({ queuedAttachments: [] }),
      sendMessage: () => set({ featureNotice: null }),
      setReplyTarget: (messageId) => set({ replyToMessageId: messageId }),
      toggleReaction: () => set({ featureNotice: null }),
      editMessage: () => set({ featureNotice: null }),
      deleteMessage: () => set({ featureNotice: null }),
      markOffline: (offline) => set({ isOffline: offline }),
      setSocketState: (connected, banner = null) =>
        set({ isSocketConnected: connected, socketBanner: banner }),
      createGroup: () => set({ featureNotice: null }),
      setFeatureNotice: (message) => set({ featureNotice: message }),
    }),
    {
      name: "signal-ui-store",
      partialize: (state) => ({
        theme: state.theme,
        isSidebarOpen: state.isSidebarOpen,
        activeConversationId: state.activeConversationId,
      }),
    }
  )
);
