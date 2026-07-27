import sys

def patch_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # 1. Update mutation definition
    old_mutation = """  const sendMessageMutation = useMutation({
    mutationFn: async (overrideContent: string | void) => {
      if (!accessToken || !activeConversationId) {
        throw new Error("No active conversation selected");
      }
      const textToSend = overrideContent !== undefined && overrideContent !== null ? overrideContent : composerText;
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
    },
    onMutate: async (overrideContent: string | void) => {
      const textToSend = overrideContent !== undefined && overrideContent !== null ? overrideContent : composerText;
      await queryClient.cancelQueries({ queryKey: ["messages", activeConversationId] });"""

    new_mutation = """  const sendMessageMutation = useMutation({
    mutationFn: async (payload: { content: string; attachments: typeof queuedAttachments; replyToId: string | null }) => {
      if (!accessToken || !activeConversationId) {
        throw new Error("No active conversation selected");
      }
      const uploadedAttachments =
        payload.attachments.length > 0
          ? await Promise.all(
              payload.attachments
                .filter((attachment): attachment is typeof attachment & { file: File } => "file" in attachment)
                .map((attachment) => uploadMedia(accessToken, attachment.file))
            )
          : [];
      return sendMessage(accessToken, activeConversationId, {
        content: payload.content || null,
        reply_to_id: payload.replyToId,
        attachments: uploadedAttachments,
      });
    },
    onMutate: async (payload) => {
      await queryClient.cancelQueries({ queryKey: ["messages", activeConversationId] });"""

    if old_mutation not in content:
        print("Could not find old_mutation block")
        # Try matching the original one before void changes
        old_mutation_2 = """  const sendMessageMutation = useMutation({
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
    },
    onMutate: async (overrideContent?: string) => {
      const textToSend = overrideContent !== undefined ? overrideContent : composerText;
      await queryClient.cancelQueries({ queryKey: ["messages", activeConversationId] });"""
        
        if old_mutation_2 in content:
             content = content.replace(old_mutation_2, new_mutation)
        else:
             print("Could not find old_mutation_2 either!")
             sys.exit(1)
    else:
        content = content.replace(old_mutation, new_mutation)

    # 2. Update optimisticMessage content
    content = content.replace("content: textToSend || null,", "content: payload.content || null,")

    # 3. Update mutate calls
    old_call_1 = """                                  // Retry with the original content
                                  sendMessageMutation.mutate(message.content || "");
                                }}>
                                  Retry"""
    new_call_1 = """                                  // Retry with the original content
                                  sendMessageMutation.mutate({ content: message.content || "", attachments: [], replyToId: message.replyToMessageId || null });
                                }}>
                                  Retry"""
    if old_call_1 in content:
        content = content.replace(old_call_1, new_call_1)
    else:
        # Check if it was message.reply_to_id
        old_call_1_alt = """                                  // Retry with the original content
                                  sendMessageMutation.mutate(message.content || "");
                                }}>
                                  Retry"""
        if old_call_1_alt in content:
             content = content.replace(old_call_1_alt, new_call_1)
        else:
            print("Could not find old_call_1")
            
    old_call_2 = """                          if (composerText.trim()) sendMessageMutation.mutate();"""
    new_call_2 = """                          if (composerText.trim()) sendMessageMutation.mutate({ content: composerText, attachments: queuedAttachments, replyToId: replyToMessageId });"""
    if old_call_2 in content:
        content = content.replace(old_call_2, new_call_2)
    else:
        print("Could not find old_call_2")

    old_call_3 = """                    onClick={() => sendMessageMutation.mutate()}"""
    new_call_3 = """                    onClick={() => sendMessageMutation.mutate({ content: composerText, attachments: queuedAttachments, replyToId: replyToMessageId })}"""
    if old_call_3 in content:
        content = content.replace(old_call_3, new_call_3)
    else:
        print("Could not find old_call_3")

    with open(filepath, 'w') as f:
        f.write(content)

patch_file("frontend/features/chat/components/signal-shell.tsx")
print("Done")
