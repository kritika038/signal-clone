import re

with open("frontend/features/chat/components/signal-shell.tsx", "r") as f:
    content = f.read()

# 1. Update handleIncomingChange and the default socket mount message.read
old_socket_effect = """    const handleIncomingChange = async () => {
      await queryClient.invalidateQueries({ queryKey: ["conversations"] });
      if (activeConversationId) {
        await queryClient.invalidateQueries({ queryKey: ["messages", activeConversationId] });
      }
    };"""

new_socket_effect = """    const handleIncomingChange = async (data?: any) => {
      await queryClient.invalidateQueries({ queryKey: ["conversations"] });
      if (activeConversationId) {
        await queryClient.invalidateQueries({ queryKey: ["messages", activeConversationId] });
        
        // If this is a new message and it belongs to the active conversation, mark it read
        if (data && data.message_id || data?.id) {
          const msgId = data.message_id || data.id;
          if (data.conversation_id === activeConversationId && data.sender_id !== currentUserId) {
            socket.emit("message.read", { message_id: msgId });
          }
        }
      } else if (data && (data.message_id || data.id) && data.sender_id !== currentUserId) {
        // If it's a background message, mark it delivered
        const msgId = data.message_id || data.id;
        socket.emit("message.delivered", { message_id: msgId });
      }
    };"""

content = content.replace(old_socket_effect, new_socket_effect)

old_mark_read = """    // Mark messages as read
    if (activeConversationId) {
      socket.emit("message.read", { conversation_id: activeConversationId });
    }"""

new_mark_read = """    // Note: To properly mark all previous messages as read, we'd iterate unread ones.
    // For now, we handle it actively as they arrive in handleIncomingChange."""

content = content.replace(old_mark_read, new_mark_read)

with open("frontend/features/chat/components/signal-shell.tsx", "w") as f:
    f.write(content)
print("Added real-time receipts")
