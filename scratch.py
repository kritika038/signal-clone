import re

with open("frontend/features/chat/components/signal-shell.tsx", "r") as f:
    content = f.read()

# 1. Update imports
content = content.replace(
    'import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";',
    'import { useMutation, useQuery, useInfiniteQuery, useQueryClient } from "@tanstack/react-query";'
)

# 2. Add refs
content = content.replace(
    'const fileInputRef = useRef<HTMLInputElement>(null);',
    'const fileInputRef = useRef<HTMLInputElement>(null);\n  const messagesEndRef = useRef<HTMLDivElement>(null);\n  const loadMoreRef = useRef<HTMLDivElement>(null);'
)

# 3. Replace messagesQuery
old_query = """  const messagesQuery = useQuery({
    queryKey: ["messages", activeConversationId, accessToken],
    queryFn: () => fetchMessages(accessToken!, activeConversationId!),
    enabled: Boolean(accessToken && activeConversationId),
  });"""

new_query = """  const messagesQuery = useInfiniteQuery({
    queryKey: ["messages", activeConversationId, accessToken],
    queryFn: ({ pageParam }) => fetchMessages(accessToken!, activeConversationId!, 50, pageParam as number),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      if (lastPage.length < 50) return undefined;
      return allPages.length * 50;
    },
    enabled: Boolean(accessToken && activeConversationId),
  });

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && messagesQuery.hasNextPage && !messagesQuery.isFetchingNextPage) {
          messagesQuery.fetchNextPage();
        }
      },
      { threshold: 0.1 }
    );
    if (loadMoreRef.current) observer.observe(loadMoreRef.current);
    return () => observer.disconnect();
  }, [messagesQuery.hasNextPage, messagesQuery.isFetchingNextPage, messagesQuery.fetchNextPage]);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messagesQuery.data?.pages[0]]);"""

content = content.replace(old_query, new_query)

# 4. Replace mappedMessages
old_mapped = """  const mappedMessages = useMemo(
    () => (messagesQuery.data || []).map((message) => mapApiMessage(message, currentUserId)),
    [messagesQuery.data, currentUserId]
  );"""

new_mapped = """  const mappedMessages = useMemo(() => {
    const allMessages = messagesQuery.data?.pages.flat() || [];
    return [...allMessages].reverse().map((message) => mapApiMessage(message, currentUserId));
  }, [messagesQuery.data, currentUserId]);"""

content = content.replace(old_mapped, new_mapped)

# 5. Fix optimistic update in sendMessageMutation
old_onMutate = """      queryClient.setQueryData(["messages", activeConversationId], (old: any) => {
        return old ? [...old, optimisticMessage] : [optimisticMessage];
      });"""

new_onMutate = """      queryClient.setQueryData(["messages", activeConversationId], (old: any) => {
        if (!old) return { pages: [[optimisticMessage]], pageParams: [0] };
        const newPages = [...old.pages];
        newPages[0] = [optimisticMessage, ...newPages[0]];
        return { ...old, pages: newPages };
      });"""

content = content.replace(old_onMutate, new_onMutate)

# 6. Fix onError in sendMessageMutation
old_onError = """    onError: (error: Error, _, context) => {
      setFeatureNotice(error.message);
      if (context?.previousMessages) {
        queryClient.setQueryData(["messages", activeConversationId], context.previousMessages);
      }
    },"""

new_onError = """    onError: (error: Error, _, context: any) => {
      setFeatureNotice(error.message);
      if (context?.optimisticMessage) {
        queryClient.setQueryData(["messages", activeConversationId], (old: any) => {
          if (!old) return old;
          const newPages = [...old.pages];
          newPages[0] = newPages[0].map((m: any) => 
            m.id === context.optimisticMessage.id ? { ...m, status: "failed" } : m
          );
          return { ...old, pages: newPages };
        });
      }
    },"""

content = content.replace(old_onError, new_onError)

# We need to pass optimisticMessage in context
old_return_ctx = """      return { previousMessages };"""
new_return_ctx = """      return { previousMessages, optimisticMessage };"""
content = content.replace(old_return_ctx, new_return_ctx)

# 7. Add loadMoreRef div in Chat History and messagesEndRef at bottom
old_chat_history_start = """            {/* Chat History */}
            <div className="flex-1 overflow-y-auto p-4">
              <div className="mx-auto max-w-3xl space-y-2">
                {messagesQuery.isLoading ? ("""

new_chat_history_start = """            {/* Chat History */}
            <div className="flex-1 overflow-y-auto p-4">
              <div className="mx-auto max-w-3xl space-y-2">
                <div ref={loadMoreRef} className="h-4 w-full" />
                {messagesQuery.isFetchingNextPage && <div className="text-center text-xs text-neutral-500 py-2">Loading older messages...</div>}
                {messagesQuery.isLoading ? ("""

content = content.replace(old_chat_history_start, new_chat_history_start)

old_chat_history_end = """                  <div className="flex flex-col items-center justify-center py-20 text-center text-neutral-500">
                    <MessageSquarePlus className="mb-4 h-12 w-12 opacity-20" />
                    <p className="text-sm">No messages here yet.</p>
                    <p className="text-xs">Send a message to start the conversation.</p>
                  </div>
                )}
              </div>
            </div>"""

new_chat_history_end = """                  <div className="flex flex-col items-center justify-center py-20 text-center text-neutral-500">
                    <MessageSquarePlus className="mb-4 h-12 w-12 opacity-20" />
                    <p className="text-sm">No messages here yet.</p>
                    <p className="text-xs">Send a message to start the conversation.</p>
                  </div>
                )}
                <div ref={messagesEndRef} className="h-1" />
              </div>
            </div>"""

content = content.replace(old_chat_history_end, new_chat_history_end)

# 8. Render Failed status and retry button
old_status = """                              {message.isOutgoing && (
                                <span className={message.status === "read" ? "text-blue-900 font-bold" : ""}>
                                  {message.status === "read" ? "✓✓" : message.status === "delivered" ? "✓✓" : "✓"}
                                </span>
                              )}"""

new_status = """                              {message.isOutgoing && (
                                <span className={message.status === "read" ? "text-blue-900 font-bold" : message.status === "failed" ? "text-red-400" : ""}>
                                  {message.status === "failed" ? "Failed" : message.status === "read" ? "✓✓" : message.status === "delivered" ? "✓✓" : "✓"}
                                </span>
                              )}
                              {message.status === "failed" && (
                                <button className="ml-2 text-blue-500 hover:underline" onClick={() => {
                                  setComposerText(message.content || "");
                                  sendMessageMutation.mutate();
                                  // Optionally, delete the failed message optimistic update
                                  queryClient.setQueryData(["messages", activeConversationId], (old: any) => {
                                    if (!old) return old;
                                    const newPages = [...old.pages];
                                    newPages[0] = newPages[0].filter((m: any) => m.id !== message.id);
                                    return { ...old, pages: newPages };
                                  });
                                }}>
                                  Retry
                                </button>
                              )}"""

content = content.replace(old_status, new_status)

with open("frontend/features/chat/components/signal-shell.tsx", "w") as f:
    f.write(content)

print("Patched signal-shell.tsx")
