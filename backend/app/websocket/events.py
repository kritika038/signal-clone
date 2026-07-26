# Outgoing & Incoming WebSocket Event Names

# Connection Events
CONNECT = "connect"
DISCONNECT = "disconnect"
ERROR = "ws.error"

# Message Events
MESSAGE_SEND = "message.send"
MESSAGE_SENT = "message.sent"
MESSAGE_RECEIVED = "message.received"
MESSAGE_EDIT = "message.edit"
MESSAGE_EDITED = "message.updated"
MESSAGE_DELETE = "message.delete"
MESSAGE_DELETED = "message.deleted"

# Receipt Events
MESSAGE_DELIVERED = "message.delivered"
MESSAGE_READ = "message.read"

# Typing Events
TYPING_START = "typing.start"
TYPING_STOP = "typing.stop"

# Presence Events
PRESENCE_UPDATE = "presence.update"

# Group Events
GROUP_JOIN = "group.join"
GROUP_LEAVE = "group.leave"
GROUP_MEMBER_ADDED = "group.member_added"
GROUP_MEMBER_REMOVED = "group.member_removed"

# Notification Events
NOTIFICATION_CREATED = "notification.created"
