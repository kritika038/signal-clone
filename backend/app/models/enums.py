from enum import Enum

class ConversationType(str, Enum):
    DIRECT = "DIRECT"
    GROUP = "GROUP"

class MessageType(str, Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    FILE = "FILE"
    SYSTEM = "SYSTEM"

class PresenceStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    AWAY = "AWAY"
    DO_NOT_DISTURB = "DO_NOT_DISTURB"

class ConversationRole(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"

class ReceiptStatus(str, Enum):
    SENDING = "SENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    READ = "READ"
