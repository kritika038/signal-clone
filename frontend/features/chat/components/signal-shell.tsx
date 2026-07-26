"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import {
  Bell,
  Image as ImageIcon,
  LogOut,
  Menu,
  MessageSquarePlus,
  MoonStar,
  Search,
  Settings,
  Smile,
  UsersRound,
  Video,
} from "lucide-react";
import { useDeferredValue, useEffect, useMemo, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { fetchMe, logoutUser } from "@/services/auth";
import {
  createGroup,
  deleteMessage,
  editMessage,
  fetchConversation,
  fetchConversations,
  fetchMessages,
  searchGlobal,
  sendMessage,
  uploadMedia,
} from "@/services/chat";
import { socketService } from "@/services/socket";
import { useSessionStore } from "@/store/use-session-store";
import { useSignalStore } from "@/store/use-signal-store";
import type { Conversation } from "@/types/chat";
import { mapApiConversation, mapApiMessage, mapSearchResults } from "@/utils/chat-mappers";
import { formatMessageTime, formatPresenceText, formatSidebarTime } from "@/utils/chat";

import { SettingsPanel } from "@/features/chat/components/settings-panel";

export function SignalShell() {
  const queryClient = useQueryClient();
  const { accessToken, user, updateUser, clearSession } = useSessionStore();
  const {
    composerText,
    queuedAttachments,
    replyToMessageId,
    searchQuery,
    theme,
    setTheme,
    setComposerText,
    queueAttachment,
    clearQueuedAttachments,
    setReplyTarget,
    setSearchQuery,
    selectConversation,
    toggleSidebar,
    isSidebarOpen,
    openSettings,
    isOffline,
    markOffline,
    setSocketState,
    socketBanner,
    featureNotice,
    setFeatureNotice,
    activeConversationId,
  } = useSignalStore();
  const [groupName, setGroupName] = useState("");
  const [showNewGroup, setShowNewGroup] = useState(false);
  const [typingUsers, setTypingUsers] = useState<Set<string>>(new Set());
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const deferredSearch = useDeferredValue(searchQuery);

  const meQuery = useQuery({
    queryKey: ["me", accessToken],
    queryFn: () => fetchMe(accessToken!),
    enabled: Boolean(accessToken),
  });

  useEffect(() => {
    if (meQuery.data) {
      updateUser(meQuery.data);
    }
  }, [meQuery.data, updateUser]);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("light", "dark");
    if (theme === "system") {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      root.classList.add(prefersDark ? "dark" : "light");
    } else {
      root.classList.add(theme);
    }
  }, [theme]);

  useEffect(() => {
    const syncOnline = () => markOffline(!navigator.onLine);
    syncOnline();
    window.addEventListener("online", syncOnline);
    window.addEventListener("offline", syncOnline);
    return () => {
      window.removeEventListener("online", syncOnline);
      window.removeEventListener("offline", syncOnline);
    };
  }, [markOffline]);

  const conversationsQuery = useQuery({
    queryKey: ["conversations", accessToken],
    queryFn: () => fetchConversations(accessToken!),
    enabled: Boolean(accessToken),
  });

  const currentUserId = user?.id || meQuery.data?.id || "";
  const conversations = useMemo<Conversation[]>(
    () =>
      (conversationsQuery.data || []).map((conversation) =>
        mapApiConversation(conversation, currentUserId)
      ),
    [conversationsQuery.data, currentUserId]
  );

  useEffect(() => {
    if (!conversations[0]?.id) return;
    const notificationConversationId = new URLSearchParams(window.location.search).get("conversation_id");
    const requestedConversation = conversations.find((conversation) => conversation.id === notificationConversationId);
    if (requestedConversation) {
      selectConversation(requestedConversation.id);
      window.history.replaceState({}, "", window.location.pathname);
    } else if (!activeConversationId) {
      selectConversation(conversations[0].id);
    }
  }, [activeConversationId, conversations, selectConversation]);

  const activeConversation = conversations.find((conversation) => conversation.id === activeConversationId) || null;

  const conversationDetailQuery = useQuery({
    queryKey: ["conversation", activeConversationId, accessToken],
    queryFn: () => fetchConversation(accessToken!, activeConversationId!),
    enabled: Boolean(accessToken && activeConversationId),
  });

  const messagesQuery = useQuery({
    queryKey: ["messages", activeConversationId, accessToken],
    queryFn: () => fetchMessages(accessToken!, activeConversationId!),
    enabled: Boolean(accessToken && activeConversationId),
  });

  const searchQueryResult = useQuery({
    queryKey: ["search", deferredSearch, accessToken],
    queryFn: () => searchGlobal(accessToken!, deferredSearch),
    enabled: Boolean(accessToken && deferredSearch.trim().length > 0),
  });

  const mappedMessages = useMemo(
    () => (messagesQuery.data || []).map((message) => mapApiMessage(message, currentUserId)),
    [messagesQuery.data, currentUserId]
  );

  const replyMessage = mappedMessages.find((message) => message.id === replyToMessageId) || null;
  const searchResults = useMemo(() => {
    if (!searchQueryResult.data) {
      return [];
    }
    return mapSearchResults(deferredSearch, searchQueryResult.data, currentUserId);
  }, [currentUserId, deferredSearch, searchQueryResult.data]);

  const sendMessageMutation = useMutation({
    mutationFn: async () => {
      if (!accessToken || !activeConversationId) {
        throw new Error("No active conversation selected");
      }
      const uploadedAttachments =
        queuedAttachments.length > 0
          ? await Promise.all(
              queuedAttachments
                .filter((attachment): attachment is typeof attachment & { file: File } => "file" in attachment)
                .map((attachment) => uploadMedia(accessToken, attachment.file))
            )
          : [];
      return sendMessage(accessToken, activeConversationId, {
        content: composerText || null,
        reply_to_id: replyToMessageId,
        attachments: uploadedAttachments,
      });
    },
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ["messages", activeConversationId] });
      const previousMessages = queryClient.getQueryData(["messages", activeConversationId]);
      
      const optimisticMessage = {
        id: crypto.randomUUID(),
        conversation_id: activeConversationId,
        sender_id: currentUserId,
        content: composerText || null,
        message_type: "text",
        reply_to_id: replyToMessageId,
        is_outgoing: true,
        is_system: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        deleted_at: null,
        attachments: [],
        reactions: [],
        receipts: [],
      };

      queryClient.setQueryData(["messages", activeConversationId], (old: any) => {
        return old ? [...old, optimisticMessage] : [optimisticMessage];
      });

      setComposerText("");
      clearQueuedAttachments();
      setReplyTarget(null);
      setFeatureNotice(null);

      return { previousMessages };
    },
    onError: (error: Error, _, context) => {
      setFeatureNotice(error.message);
      if (context?.previousMessages) {
        queryClient.setQueryData(["messages", activeConversationId], context.previousMessages);
      }
    },
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: ["conversations"] });
      await queryClient.invalidateQueries({ queryKey: ["messages", activeConversationId] });
    },
  });

  const editMessageMutation = useMutation({
    mutationFn: ({ messageId, content }: { messageId: string; content: string }) =>
      editMessage(accessToken!, messageId, content),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["messages", activeConversationId] });
    },
  });

  const deleteMessageMutation = useMutation({
    mutationFn: ({ messageId, deleteType }: { messageId: string; deleteType: "me" | "everyone" }) =>
      deleteMessage(accessToken!, messageId, deleteType),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["messages", activeConversationId] });
      await queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  const createGroupMutation = useMutation({
    mutationFn: () => createGroup(accessToken!, { name: groupName, description: null, member_ids: [] }),
    onSuccess: async () => {
      setGroupName("");
      setShowNewGroup(false);
      setFeatureNotice("Group created. Member management is live once user IDs are available.");
      await queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
    onError: (error: Error) => setFeatureNotice(error.message),
  });

  useEffect(() => {
    if (!accessToken) {
      return;
    }
    const socket = socketService.connect(accessToken);
    const handleConnect = () => setSocketState(true, null);
    const handleDisconnect = () => setSocketState(false, "Reconnecting to Signal service…");
    const handleIncomingChange = async () => {
      await queryClient.invalidateQueries({ queryKey: ["conversations"] });
      if (activeConversationId) {
        await queryClient.invalidateQueries({ queryKey: ["messages", activeConversationId] });
      }
    };
    const handleTypingStart = (data: { user_id: string; conversation_id: string }) => {
      if (data.conversation_id === activeConversationId && data.user_id !== currentUserId) {
        setTypingUsers((prev) => new Set(prev).add(data.user_id));
      }
    };
    const handleTypingStop = (data: { user_id: string; conversation_id: string }) => {
      if (data.conversation_id === activeConversationId) {
        setTypingUsers((prev) => {
          const next = new Set(prev);
          next.delete(data.user_id);
          return next;
        });
      }
    };

    socket.on("connect", handleConnect);
    socket.on("disconnect", handleDisconnect);
    socket.on("message.received", handleIncomingChange);
    socket.on("message.updated", handleIncomingChange);
    socket.on("message.deleted", handleIncomingChange);
    socket.on("message.delivered", handleIncomingChange);
    socket.on("message.read", handleIncomingChange);
    socket.on("typing.start", handleTypingStart);
    socket.on("typing.stop", handleTypingStop);
    socket.emit("heartbeat");
    
    // Mark messages as read
    if (activeConversationId) {
      socket.emit("message.read", { conversation_id: activeConversationId });
    }

    return () => {
      socket.off("connect", handleConnect);
      socket.off("disconnect", handleDisconnect);
      socket.off("message.received", handleIncomingChange);
      socket.off("message.updated", handleIncomingChange);
      socket.off("message.deleted", handleIncomingChange);
      socket.off("message.delivered", handleIncomingChange);
      socket.off("message.read", handleIncomingChange);
      socket.off("typing.start", handleTypingStart);
      socket.off("typing.stop", handleTypingStop);
    };
  }, [accessToken, activeConversationId, currentUserId, queryClient, setSocketState]);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-neutral-950 text-neutral-200">
      <AnimatePresence>
        {(isOffline || socketBanner || featureNotice) && (
          <motion.div
            initial={{ opacity: 0, y: -40 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -40 }}
            className="absolute left-1/2 top-4 z-50 flex -translate-x-1/2 items-center rounded-full bg-blue-600/90 px-4 py-1.5 text-sm font-medium text-white shadow-lg backdrop-blur-md"
          >
            {isOffline ? "Waiting for network..." : socketBanner || featureNotice}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <aside className={`${isSidebarOpen ? "flex" : "hidden"} w-80 flex-col border-r border-neutral-800 bg-neutral-900/50 md:flex`}>
        {/* Sidebar Header */}
        <div className="flex h-14 shrink-0 items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-xs font-semibold text-white">
              {user?.display_name?.slice(0, 2).toUpperCase() || "SG"}
            </div>
            <span className="font-medium text-neutral-200 truncate max-w-[120px]">{user?.display_name || user?.username || "User"}</span>
          </div>
          <div className="flex items-center gap-1">
            <ToolbarIcon label="Settings" onClick={() => openSettings("profile")}>
              <Settings className="h-4 w-4" />
            </ToolbarIcon>
            <ToolbarIcon label="New Chat" onClick={() => setShowNewGroup(true)}>
              <MessageSquarePlus className="h-4 w-4" />
            </ToolbarIcon>
          </div>
        </div>

        {/* Search */}
        <div className="px-3 pb-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-500" />
            <Input
              className="h-8 w-full rounded-md border-none bg-neutral-800/80 pl-9 text-sm text-neutral-200 placeholder-neutral-500 focus-visible:ring-1 focus-visible:ring-blue-500"
              placeholder="Search"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
            />
          </div>
        </div>

        {/* Chat List */}
        <div className="flex-1 overflow-y-auto px-2">
          {deferredSearch ? (
            <div className="py-2">
              <p className="px-2 text-xs font-medium uppercase text-neutral-500">Global Search</p>
              {searchResults.length === 0 ? (
                <p className="px-2 py-3 text-sm text-neutral-500">No results found.</p>
              ) : (
                searchResults.map((result) => (
                  <button
                    key={result.id}
                    className="mt-1 w-full rounded-md px-2 py-2 text-left hover:bg-neutral-800"
                    onClick={() => result.conversationId && selectConversation(result.conversationId)}
                  >
                    <div className="truncate text-sm font-medium text-neutral-200">{result.title}</div>
                    <div className="truncate text-xs text-neutral-500">{result.subtitle}</div>
                  </button>
                ))
              )}
            </div>
          ) : (
            <div className="space-y-0.5">
              {conversationsQuery.isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-3 rounded-md px-2 py-2">
                    <div className="h-10 w-10 shrink-0 animate-pulse rounded-full bg-neutral-800" />
                    <div className="flex-1 space-y-2">
                      <div className="h-3 w-1/2 animate-pulse rounded bg-neutral-800" />
                      <div className="h-3 w-3/4 animate-pulse rounded bg-neutral-800" />
                    </div>
                  </div>
                ))
              ) : conversations.length ? (
                conversations.map((conversation) => (
                  <button
                    key={conversation.id}
                    className={`flex w-full items-center gap-3 rounded-md px-2 py-2 transition-colors ${
                      activeConversationId === conversation.id ? "bg-blue-600 text-white" : "hover:bg-neutral-800"
                    }`}
                    onClick={() => selectConversation(conversation.id)}
                  >
                    <div
                      className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${
                        activeConversationId === conversation.id ? "bg-white/20 text-white" : "bg-blue-500/20 text-blue-400"
                      }`}
                    >
                      {conversation.avatar}
                    </div>
                    <div className="min-w-0 flex-1 text-left">
                      <div className="flex justify-between">
                        <span className="truncate text-[15px] font-medium">{conversation.title}</span>
                        <span className={`shrink-0 text-xs ${activeConversationId === conversation.id ? "text-blue-100" : "text-neutral-500"}`}>
                          {formatSidebarTime(conversation.lastMessageAt)}
                        </span>
                      </div>
                      <p className={`truncate text-sm ${activeConversationId === conversation.id ? "text-blue-100" : "text-neutral-400"}`}>
                        {conversation.lastMessage || "No messages yet"}
                      </p>
                    </div>
                  </button>
                ))
              ) : (
                <div className="mt-10 px-4 text-center text-sm text-neutral-500">
                  No conversations. Click New Chat to start.
                </div>
              )}
            </div>
          )}
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="flex min-w-0 flex-1 flex-col bg-neutral-950">
        {activeConversationId ? (
          <>
            {/* Chat Header */}
            <header className="flex h-14 shrink-0 items-center justify-between border-b border-neutral-800 bg-neutral-900/50 px-4">
              <div className="flex items-center gap-3">
                <Button className="md:hidden" size="icon" variant="ghost" onClick={toggleSidebar}>
                  <Menu className="h-5 w-5" />
                </Button>
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-500/20 text-sm font-semibold text-blue-400">
                  {activeConversation?.avatar}
                </div>
                <div>
                  <h2 className="text-[15px] font-medium text-neutral-100">{activeConversation?.title}</h2>
                  <p className="text-xs text-neutral-500">
                    {typingUsers.size > 0 ? (
                      <span className="text-blue-400">typing...</span>
                    ) : conversationDetailQuery.data?.type === "GROUP" ? (
                      `${conversationDetailQuery.data.members.length} members`
                    ) : (
                      "Online"
                    )}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <ToolbarIcon label="Voice Call" onClick={() => setFeatureNotice("Voice Calls are coming soon.")}>
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>
                </ToolbarIcon>
                <ToolbarIcon label="Video Call" onClick={() => setFeatureNotice("Video Calls are coming soon.")}>
                  <Video className="h-4 w-4" />
                </ToolbarIcon>
                <ToolbarIcon label="Search">
                  <Search className="h-4 w-4" />
                </ToolbarIcon>
                <ToolbarIcon label="Conversation Info" onClick={() => openSettings("about")}>
                  <Settings className="h-4 w-4" />
                </ToolbarIcon>
              </div>
            </header>

            {/* Chat History */}
            <div className="flex-1 overflow-y-auto p-4">
              <div className="mx-auto max-w-3xl space-y-2">
                {messagesQuery.isLoading ? (
                  Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className={`flex ${i % 2 === 0 ? "justify-start" : "justify-end"}`}>
                      <div className="h-10 w-48 animate-pulse rounded-lg bg-neutral-800" />
                    </div>
                  ))
                ) : mappedMessages.length ? (
                  mappedMessages.map((message, index) => {
                    const quoted = message.quotedMessageId
                      ? mappedMessages.find((c) => c.id === message.quotedMessageId)
                      : null;
                    const showDay =
                      index === 0 ||
                      new Date(mappedMessages[index - 1]!.timestamp).toDateString() !==
                        new Date(message.timestamp).toDateString();

                    return (
                      <div key={message.id}>
                        {showDay && (
                          <div className="my-4 flex justify-center">
                            <span className="rounded-full bg-neutral-800/60 px-3 py-1 text-xs font-medium text-neutral-400 backdrop-blur-sm">
                              {new Date(message.timestamp).toLocaleDateString(undefined, {
                                weekday: "long",
                                month: "short",
                                day: "numeric",
                              })}
                            </span>
                          </div>
                        )}
                        <motion.div
                          initial={{ opacity: 0, y: 4 }}
                          animate={{ opacity: 1, y: 0 }}
                          className={`flex ${message.isOutgoing ? "justify-end" : "justify-start"} mt-1 group`}
                        >
                          <div
                            className={`relative max-w-[70%] rounded-2xl px-3.5 py-2 text-[15px] leading-relaxed shadow-sm ${
                              message.isOutgoing
                                ? "rounded-br-sm bg-blue-600 text-white"
                                : "rounded-bl-sm bg-neutral-800 text-neutral-100"
                            }`}
                          >
                            {quoted && (
                              <button
                                className="mb-2 block w-full rounded-md border-l-2 border-white/20 bg-black/10 px-2 py-1 text-left text-xs text-white/80"
                                onClick={() => setReplyTarget(quoted.id)}
                              >
                                <span className="block font-semibold">{quoted.isOutgoing ? "You" : activeConversation?.title}</span>
                                <span className="truncate block">{quoted.content}</span>
                              </button>
                            )}
                            <p className="whitespace-pre-wrap break-words">{message.content}</p>
                            <div className={`mt-1 flex items-center justify-end gap-1.5 text-[10px] ${message.isOutgoing ? "text-blue-200" : "text-neutral-500"}`}>
                              {message.isEdited && <span>Edited</span>}
                              <span>{formatMessageTime(message.timestamp)}</span>
                              {message.isOutgoing && <span>{message.status === "read" ? "✓✓" : message.status === "delivered" ? "✓✓" : "✓"}</span>}
                            </div>
                            
                            {/* Message Actions (Hover) */}
                            {message.isOutgoing && (
                              <div className="absolute -left-16 top-1/2 hidden -translate-y-1/2 items-center gap-1 group-hover:flex">
                                <button className="rounded-full bg-neutral-800 p-1.5 text-neutral-400 hover:text-white" onClick={() => editMessageMutation.mutate({ messageId: message.id, content: `${message.content} (edited)` })}>
                                  <Settings className="h-3 w-3" />
                                </button>
                                <button className="rounded-full bg-neutral-800 p-1.5 text-neutral-400 hover:text-red-400" onClick={() => deleteMessageMutation.mutate({ messageId: message.id, deleteType: "everyone" })}>
                                  <LogOut className="h-3 w-3" />
                                </button>
                              </div>
                            )}
                          </div>
                        </motion.div>
                      </div>
                    );
                  })
                ) : (
                  <div className="flex flex-col items-center justify-center py-20 text-center text-neutral-500">
                    <MessageSquarePlus className="mb-4 h-12 w-12 opacity-20" />
                    <p className="text-sm">No messages here yet.</p>
                    <p className="text-xs">Send a message to start the conversation.</p>
                  </div>
                )}
              </div>
            </div>

            {/* Chat Input */}
            <div className="shrink-0 bg-neutral-900/50 p-4">
              <div className="mx-auto max-w-3xl">
                {replyMessage && (
                  <div className="mb-2 flex items-center justify-between rounded-t-lg bg-neutral-800 px-3 py-2 text-sm border-l-2 border-blue-500">
                    <div>
                      <span className="font-semibold text-blue-400">Replying to {replyMessage.isOutgoing ? "yourself" : activeConversation?.title}</span>
                      <p className="text-neutral-400 truncate max-w-sm">{replyMessage.content}</p>
                    </div>
                    <Button size="sm" variant="ghost" className="h-6 text-neutral-400" onClick={() => setReplyTarget(null)}>✕</Button>
                  </div>
                )}
                <div className="flex items-end gap-2">
                  <Button size="icon" variant="ghost" className="shrink-0 text-neutral-400 hover:text-neutral-100" onClick={() => fileInputRef.current?.click()}>
                    <ImageIcon className="h-5 w-5" />
                  </Button>
                  <div className="flex min-h-[44px] flex-1 items-end rounded-2xl bg-neutral-800 px-3 py-1 shadow-sm focus-within:ring-1 focus-within:ring-blue-500">
                    <Textarea
                      className="max-h-32 min-h-[36px] w-full resize-none border-0 bg-transparent py-2 text-[15px] placeholder:text-neutral-500 focus-visible:ring-0"
                      placeholder="Write a message..."
                      value={composerText}
                      onChange={(e) => {
                        setComposerText(e.target.value);
                        if (activeConversationId) {
                          socketService.emit("typing.start", { conversation_id: activeConversationId });
                          if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
                          typingTimeoutRef.current = setTimeout(() => {
                            socketService.emit("typing.stop", { conversation_id: activeConversationId });
                          }, 3000);
                        }
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          if (composerText.trim()) sendMessageMutation.mutate();
                        }
                      }}
                    />
                    <Button size="icon" variant="ghost" className="shrink-0 h-9 w-9 text-neutral-400 hover:text-neutral-100" onClick={() => setFeatureNotice("Emoji picker is coming soon.")}>
                      <Smile className="h-5 w-5" />
                    </Button>
                  </div>
                  <Button
                    size="icon"
                    className="shrink-0 rounded-full bg-blue-600 hover:bg-blue-700"
                    onClick={() => sendMessageMutation.mutate()}
                    disabled={!composerText.trim() && !queuedAttachments.length}
                  >
                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-white transform -rotate-90 translate-y-0.5"><path d="M22 12L3 20L6.5 12L3 4L22 12Z" fill="currentColor"/></svg>
                  </Button>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex h-full flex-col items-center justify-center bg-neutral-950 text-neutral-500">
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-neutral-900 mb-6 shadow-inner">
              <MessageSquarePlus className="h-8 w-8 text-neutral-700" />
            </div>
            <p className="text-lg font-medium text-neutral-300">Signal Desktop Clone</p>
            <p className="mt-2 max-w-sm text-center text-sm text-neutral-500">Select a chat to start messaging.</p>
          </div>
        )}
      </main>

      {/* Settings Overlay & Modals */}
      <SettingsPanel />

      <AnimatePresence>
        {showNewGroup && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-sm rounded-xl border border-neutral-800 bg-neutral-900 p-6 shadow-2xl"
            >
              <h3 className="mb-1 text-lg font-semibold text-neutral-100">Create New Group</h3>
              <p className="mb-5 text-sm text-neutral-500">Enter a name for the new group chat.</p>
              <Input
                className="mb-4 bg-neutral-950 border-neutral-800"
                placeholder="Group name"
                value={groupName}
                onChange={(e) => setGroupName(e.target.value)}
                autoFocus
              />
              <div className="flex justify-end gap-2">
                <Button variant="ghost" className="text-neutral-300 hover:text-white" onClick={() => setShowNewGroup(false)}>Cancel</Button>
                <Button className="bg-blue-600 hover:bg-blue-700 text-white" onClick={() => createGroupMutation.mutate()} disabled={!groupName.trim() || createGroupMutation.isPending}>
                  Create
                </Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      <input
        ref={fileInputRef}
        className="hidden"
        type="file"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (!file) return;
          queueAttachment({
            id: crypto.randomUUID(),
            name: file.name,
            type: file.type.startsWith("image") ? "image" : file.type.startsWith("video") ? "video" : "document",
            sizeLabel: `${Math.max(1, Math.round(file.size / 1024 / 1024))} MB`,
            progress: 100,
            file,
          } as typeof queuedAttachments[number] & { file: File });
        }}
      />
    </div>
  );
}

function ToolbarIcon({
  children,
  label,
  onClick,
}: {
  children: React.ReactNode;
  label: string;
  onClick?: () => void;
}) {
  return (
    <button
      aria-label={label}
      className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/5 text-slate-200 transition hover:bg-white/10"
      onClick={onClick}
      type="button"
    >
      {children}
    </button>
  );
}
