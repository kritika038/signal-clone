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
    onSuccess: async () => {
      setComposerText("");
      clearQueuedAttachments();
      setReplyTarget(null);
      setFeatureNotice(null);
      await queryClient.invalidateQueries({ queryKey: ["conversations"] });
      await queryClient.invalidateQueries({ queryKey: ["messages", activeConversationId] });
    },
    onError: (error: Error) => setFeatureNotice(error.message),
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
    socket.on("connect", handleConnect);
    socket.on("disconnect", handleDisconnect);
    socket.on("message.received", handleIncomingChange);
    socket.on("message.updated", handleIncomingChange);
    socket.on("message.deleted", handleIncomingChange);
    socket.on("message.delivered", handleIncomingChange);
    socket.on("message.read", handleIncomingChange);
    socket.on("typing.start", () => setFeatureNotice("Typing indicator event received from Socket.IO."));
    socket.emit("heartbeat");
    return () => {
      socket.off("connect", handleConnect);
      socket.off("disconnect", handleDisconnect);
      socket.off("message.received", handleIncomingChange);
      socket.off("message.updated", handleIncomingChange);
      socket.off("message.deleted", handleIncomingChange);
      socket.off("message.delivered", handleIncomingChange);
      socket.off("message.read", handleIncomingChange);
    };
  }, [accessToken, activeConversationId, queryClient, setFeatureNotice, setSocketState]);

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,_#0b1118_0%,_#111f2c_100%)] text-slate-100">
      <div className="mx-auto flex min-h-screen max-w-[1600px] flex-col">
        <AnimatePresence>
          {(isOffline || socketBanner) && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="border-b border-amber-300/20 bg-amber-400/8 px-4 py-3 text-sm text-amber-50"
            >
              {isOffline ? "You are offline. Requests will resume when the connection returns." : socketBanner}
            </motion.div>
          )}
        </AnimatePresence>

        <div className="flex min-h-[calc(100vh-1px)] flex-1">
          <aside className={`${isSidebarOpen ? "flex" : "hidden"} w-full max-w-[356px] flex-col border-r border-white/8 bg-[#0d1724]/92 backdrop-blur-2xl md:flex`}>
            <div className="border-b border-white/8 px-5 pb-4 pt-5">
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-signal-500/15 text-sm font-semibold text-signal-100">
                    {user?.display_name?.slice(0, 2).toUpperCase() || "SG"}
                  </div>
                  <div>
                    <p className="font-medium text-white">{user?.display_name || user?.username || "Signal User"}</p>
                    <p className="text-sm text-slate-400">{formatPresenceText(user?.last_seen || null)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <ToolbarIcon label="Settings" onClick={() => openSettings("profile")}>
                    <Settings className="h-4 w-4" />
                  </ToolbarIcon>
                  <ToolbarIcon label="New group" onClick={() => setShowNewGroup(true)}>
                    <UsersRound className="h-4 w-4" />
                  </ToolbarIcon>
                  <ToolbarIcon label="Theme" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
                    <MoonStar className="h-4 w-4" />
                  </ToolbarIcon>
                </div>
              </div>
              <div className="relative">
                <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                <Input
                  className="pl-11"
                  placeholder="Search Signal"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  aria-label="Search conversations and messages"
                />
              </div>
            </div>

            {deferredSearch ? (
              <div className="border-b border-white/8 px-3 py-3">
                <p className="px-2 pb-2 text-[11px] uppercase tracking-[0.22em] text-slate-500">Global search</p>
                <div className="space-y-1">
                  {searchResults.map((result) => (
                    <button
                      key={result.id}
                      className="w-full rounded-2xl px-3 py-2 text-left hover:bg-white/6"
                      onClick={() => result.conversationId && selectConversation(result.conversationId)}
                      type="button"
                    >
                      <div className="text-sm font-medium text-white">{result.title}</div>
                      <div className="text-xs text-slate-400">{result.subtitle}</div>
                    </button>
                  ))}
                  {!searchResults.length && (
                    <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 px-3 py-3 text-sm text-slate-400">
                      No search results for “{deferredSearch}”.
                    </div>
                  )}
                </div>
              </div>
            ) : null}

            <div className="flex-1 overflow-y-auto px-3 py-3">
              {conversationsQuery.isLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 5 }).map((_, index) => (
                    <div key={index} className="h-20 animate-pulse rounded-[22px] bg-white/5" />
                  ))}
                </div>
              ) : conversations.length ? (
                conversations.map((conversation) => (
                  <button
                    key={conversation.id}
                    className={`mb-1 flex w-full items-start gap-3 rounded-[22px] px-3 py-3 text-left transition ${
                      activeConversationId === conversation.id ? "bg-white text-slate-950" : "hover:bg-white/6"
                    }`}
                    onClick={() => selectConversation(conversation.id)}
                    type="button"
                  >
                    <div
                      className={`mt-0.5 flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl text-sm font-semibold ${
                        activeConversationId === conversation.id ? "bg-slate-950 text-white" : "bg-signal-500/14 text-signal-100"
                      }`}
                    >
                      {conversation.avatar}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <p
                          className={`truncate text-sm font-medium ${
                            activeConversationId === conversation.id ? "text-slate-950" : "text-white"
                          }`}
                        >
                          {conversation.title}
                        </p>
                        <span
                          className={`shrink-0 text-[11px] ${
                            activeConversationId === conversation.id ? "text-slate-600" : "text-slate-500"
                          }`}
                        >
                          {formatSidebarTime(conversation.lastMessageAt)}
                        </span>
                      </div>
                      <p
                        className={`mt-1 truncate text-sm ${
                          activeConversationId === conversation.id ? "text-slate-700" : "text-slate-400"
                        }`}
                      >
                        {conversation.lastMessage}
                      </p>
                    </div>
                  </button>
                ))
              ) : (
                <div className="flex h-full min-h-[280px] flex-col items-center justify-center rounded-[28px] border border-dashed border-white/10 bg-white/4 p-6 text-center">
                  <Badge>Inbox empty</Badge>
                  <h3 className="mt-4 text-xl font-semibold text-white">No conversations yet</h3>
                  <p className="mt-3 max-w-xs text-sm leading-6 text-slate-400">
                    Start a secure chat by adding a contact and creating a conversation.
                  </p>
                </div>
              )}
            </div>

            <div className="border-t border-white/8 p-3">
              <Button
                className="w-full justify-start rounded-[22px]"
                variant="secondary"
                onClick={() => openSettings("contacts")}
              >
                <MessageSquarePlus className="h-4 w-4" />
                New chat
              </Button>
            </div>
          </aside>

          <main className="flex min-w-0 flex-1 flex-col bg-[#111c28]/88 backdrop-blur-2xl">
            <header className="flex items-center justify-between border-b border-white/8 px-4 py-4 md:px-6">
              <div className="flex items-center gap-3">
                <Button className="md:hidden" size="icon" variant="ghost" onClick={toggleSidebar}>
                  <Menu className="h-5 w-5" />
                </Button>
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/8 text-sm font-semibold text-white">
                  {activeConversation?.avatar || "SG"}
                </div>
                <div>
                  <p className="font-medium text-white">{activeConversation?.title || "Select a conversation"}</p>
                  <p className="text-sm text-slate-400">
                    {conversationDetailQuery.data
                      ? conversationDetailQuery.data.type === "GROUP"
                        ? `${conversationDetailQuery.data.members.length} members`
                        : activeConversation?.members[0]?.about || "Private conversation"
                      : "Signal conversation view"}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <ToolbarIcon label="Media">
                  <ImageIcon className="h-4 w-4" />
                </ToolbarIcon>
                <ToolbarIcon label="Call placeholder">
                  <Video className="h-4 w-4" />
                </ToolbarIcon>
                <ToolbarIcon label="Notifications">
                  <Bell className="h-4 w-4" />
                </ToolbarIcon>
                <ToolbarIcon label="Conversation settings" onClick={() => openSettings("about")}>
                  <Settings className="h-4 w-4" />
                </ToolbarIcon>
              </div>
            </header>

            <div className="flex-1 overflow-y-auto px-4 py-5 md:px-8">
              <div className="mx-auto flex max-w-3xl flex-col gap-4">
                {!activeConversationId ? (
                  <div className="flex min-h-[320px] flex-col items-center justify-center rounded-[36px] border border-dashed border-white/10 bg-white/4 px-8 py-16 text-center">
                    <Badge>Inbox</Badge>
                    <h3 className="mt-5 text-3xl font-semibold text-white">Choose a conversation</h3>
                    <p className="mt-3 max-w-xl text-sm leading-7 text-slate-400">
                      Your conversations and messages are synchronized with the Signal backend.
                    </p>
                  </div>
                ) : messagesQuery.isLoading ? (
                  Array.from({ length: 6 }).map((_, index) => (
                    <div
                      key={index}
                      className={`h-20 animate-pulse rounded-[28px] ${index % 2 === 0 ? "bg-white/5" : "bg-signal-500/10"}`}
                    />
                  ))
                ) : mappedMessages.length ? (
                  mappedMessages.map((message, index) => {
                    const quoted = message.quotedMessageId
                      ? mappedMessages.find((candidate) => candidate.id === message.quotedMessageId)
                      : null;
                    const showDay =
                      index === 0 ||
                      new Date(mappedMessages[index - 1]!.timestamp).toDateString() !==
                        new Date(message.timestamp).toDateString();

                    return (
                      <div key={message.id}>
                        {showDay ? (
                          <div className="mb-4 flex justify-center">
                            <Badge>{new Date(message.timestamp).toDateString()}</Badge>
                          </div>
                        ) : null}
                        <motion.div
                          initial={{ opacity: 0, y: 12 }}
                          animate={{ opacity: 1, y: 0 }}
                          className={`flex ${message.isOutgoing ? "justify-end" : "justify-start"}`}
                        >
                          <div
                            className={`max-w-[78%] rounded-[28px] px-4 py-3 ${
                              message.isOutgoing
                                ? "bg-signal-500 text-white shadow-lg shadow-signal-900/20"
                                : "bg-white/7 text-slate-100"
                            }`}
                          >
                            {quoted ? (
                              <button
                                className="mb-3 block w-full rounded-2xl border border-white/12 bg-black/10 px-3 py-2 text-left text-xs text-white/80"
                                onClick={() => setReplyTarget(quoted.id)}
                                type="button"
                              >
                                <span className="mb-1 block font-medium">{quoted.isOutgoing ? "You" : activeConversation?.title}</span>
                                {quoted.content}
                              </button>
                            ) : null}
                            <p className="whitespace-pre-wrap text-[15px] leading-6">{message.content}</p>
                            <div className="mt-3 flex items-center justify-between gap-4 text-[11px] text-white/70">
                              <span>{message.isEdited ? "Edited" : "Message"}</span>
                              <span>
                                {formatMessageTime(message.timestamp)} • {message.status}
                              </span>
                            </div>
                            {message.isOutgoing ? (
                              <div className="mt-3 flex flex-wrap gap-2">
                                <button
                                  className="rounded-full bg-black/10 px-2 py-1 text-xs"
                                  onClick={() => setReplyTarget(message.id)}
                                  type="button"
                                >
                                  Reply
                                </button>
                                <button
                                  className="rounded-full bg-black/10 px-2 py-1 text-xs"
                                  onClick={() =>
                                    editMessageMutation.mutate({
                                      messageId: message.id,
                                      content: `${message.content} (edited ${new Date().toLocaleTimeString()})`,
                                    })
                                  }
                                  type="button"
                                >
                                  Edit
                                </button>
                                <button
                                  className="rounded-full bg-black/10 px-2 py-1 text-xs"
                                  onClick={() =>
                                    deleteMessageMutation.mutate({
                                      messageId: message.id,
                                      deleteType: "everyone",
                                    })
                                  }
                                  type="button"
                                >
                                  Delete
                                </button>
                              </div>
                            ) : null}
                          </div>
                        </motion.div>
                      </div>
                    );
                  })
                ) : (
                  <div className="flex min-h-[320px] flex-col items-center justify-center rounded-[36px] border border-dashed border-white/10 bg-white/4 px-8 py-16 text-center">
                    <Badge>No messages</Badge>
                    <h3 className="mt-5 text-3xl font-semibold text-white">Start the conversation</h3>
                    <p className="mt-3 max-w-xl text-sm leading-7 text-slate-400">
                    Send a message to begin this conversation.
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="border-t border-white/8 px-4 py-4 md:px-6">
              <div className="mx-auto max-w-3xl">
                {replyMessage ? (
                  <div className="mb-3 flex items-center justify-between rounded-[24px] border border-white/10 bg-white/5 px-4 py-3 text-sm">
                    <div>
                      <p className="font-medium text-white">Replying to {replyMessage.isOutgoing ? "yourself" : activeConversation?.title}</p>
                      <p className="text-slate-400">{replyMessage.content}</p>
                    </div>
                    <Button size="sm" variant="ghost" onClick={() => setReplyTarget(null)}>
                      Clear
                    </Button>
                  </div>
                ) : null}

                {queuedAttachments.length ? (
                  <div className="mb-3 grid gap-2 rounded-[28px] border border-white/10 bg-white/5 p-3">
                    {queuedAttachments.map((attachment) => (
                      <div
                        key={attachment.id}
                        className="flex items-center justify-between rounded-2xl bg-black/10 px-3 py-2 text-sm text-slate-200"
                      >
                        <span>{attachment.name}</span>
                        <span>{attachment.progress}%</span>
                      </div>
                    ))}
                  </div>
                ) : null}

                <div className="flex items-end gap-3 rounded-[32px] border border-white/10 bg-[#0d1724]/95 p-3 shadow-2xl shadow-black/20">
                  <div className="flex gap-2">
                    <Button size="icon" variant="ghost" onClick={() => fileInputRef.current?.click()}>
                      <ImageIcon className="h-4 w-4" />
                    </Button>
                  </div>
                  <Textarea
                    className="min-h-[72px] flex-1 border-none bg-transparent px-0 py-1"
                    placeholder={activeConversationId ? "Message" : "Select a conversation to start messaging"}
                    value={composerText}
                    onChange={(event) => setComposerText(event.target.value)}
                    disabled={!activeConversationId}
                  />
                  <Button
                    size="icon"
                    onClick={() => sendMessageMutation.mutate()}
                    disabled={!activeConversationId || sendMessageMutation.isPending}
                  >
                    <MessageSquarePlus className="h-4 w-4" />
                  </Button>
                </div>
                {featureNotice ? <p className="mt-3 text-sm text-amber-200">{featureNotice}</p> : null}
              </div>
            </div>
          </main>

          <SettingsPanel />
        </div>

        <AnimatePresence>
          {showNewGroup ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 flex items-center justify-center bg-[#04070c]/72 p-4"
            >
              <motion.div
                initial={{ opacity: 0, y: 18, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 18, scale: 0.98 }}
                className="w-full max-w-md rounded-[32px] border border-white/10 bg-[#0d1724] p-6 shadow-2xl shadow-black/35"
              >
                <div className="mb-5">
                  <Badge>Create Group</Badge>
                  <h3 className="mt-3 text-2xl font-semibold text-white">New group chat</h3>
                  <p className="mt-2 text-sm text-slate-400">
                    Create the group, then add members from the group management controls.
                  </p>
                </div>
                <div className="space-y-4">
                  <Input placeholder="Group name" value={groupName} onChange={(event) => setGroupName(event.target.value)} />
                  <div className="flex justify-end gap-3">
                    <Button variant="ghost" onClick={() => setShowNewGroup(false)}>
                      Cancel
                    </Button>
                    <Button onClick={() => createGroupMutation.mutate()} disabled={!groupName.trim() || createGroupMutation.isPending}>
                      Create
                    </Button>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          ) : null}
        </AnimatePresence>

        <input
          ref={fileInputRef}
          className="hidden"
          type="file"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (!file) {
              return;
            }
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

        <div className="fixed bottom-4 right-4 flex gap-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={async () => {
              if (accessToken) {
                await logoutUser(accessToken).catch(() => undefined);
              }
              socketService.disconnect();
              clearQueuedAttachments();
              clearSession();
            }}
          >
            <LogOut className="h-4 w-4" />
            Logout
          </Button>
        </div>
      </div>
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
