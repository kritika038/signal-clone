import re

with open("frontend/features/chat/components/signal-shell.tsx", "r") as f:
    content = f.read()

# Modify sendMessageMutation to accept content
old_mutation = """  const sendMessageMutation = useMutation({
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
    },"""

new_mutation = """  const sendMessageMutation = useMutation({
    mutationFn: async (overrideContent?: string) => {
      if (!accessToken || !activeConversationId) {
        throw new Error("No active conversation selected");
      }
      const textToSend = overrideContent !== undefined ? overrideContent : composerText;
      const uploadedAttachments =
        queuedAttachments.length > 0
          ? await Promise.all(
              queuedAttachments
                .filter((attachment): attachment is typeof attachment & { file: File } => "file" in attachment)
                .map((attachment) => uploadMedia(accessToken, attachment.file))
            )
          : [];
      return sendMessage(accessToken, activeConversationId, {
        content: textToSend || null,
        reply_to_id: replyToMessageId,
        attachments: uploadedAttachments,
      });
    },"""

content = content.replace(old_mutation, new_mutation)

# We also need to update the optimistic UI creation in onMutate to use overrideContent
old_onMutate = """    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ["messages", activeConversationId] });
      const previousMessages = queryClient.getQueryData(["messages", activeConversationId]);
      
      const optimisticMessage = {
        id: crypto.randomUUID(),
        conversation_id: activeConversationId,
        sender_id: currentUserId,
        content: composerText || null,"""

new_onMutate = """    onMutate: async (overrideContent?: string) => {
      const textToSend = overrideContent !== undefined ? overrideContent : composerText;
      await queryClient.cancelQueries({ queryKey: ["messages", activeConversationId] });
      const previousMessages = queryClient.getQueryData(["messages", activeConversationId]);
      
      const optimisticMessage = {
        id: crypto.randomUUID(),
        conversation_id: activeConversationId,
        sender_id: currentUserId,
        content: textToSend || null,"""

content = content.replace(old_onMutate, new_onMutate)

# Now fix the retry button
old_retry = """                              {message.status === "failed" && (
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

new_retry = """                              {message.status === "failed" && (
                                <button className="ml-2 text-blue-500 hover:underline" onClick={() => {
                                  // Delete the failed message optimistic update
                                  queryClient.setQueryData(["messages", activeConversationId], (old: any) => {
                                    if (!old) return old;
                                    const newPages = [...old.pages];
                                    newPages[0] = newPages[0].filter((m: any) => m.id !== message.id);
                                    return { ...old, pages: newPages };
                                  });
                                  // Retry with the original content
                                  sendMessageMutation.mutate(message.content || "");
                                }}>
                                  Retry
                                </button>
                              )}"""

content = content.replace(old_retry, new_retry)

with open("frontend/features/chat/components/signal-shell.tsx", "w") as f:
    f.write(content)
print("Fixed retry bug")
