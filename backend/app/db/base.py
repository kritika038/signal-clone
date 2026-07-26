# Import all models here so that Base has them registered before
# Alembic imports database metadata.
from app.db.base_class import Base  # noqa
from app.models.enums import ConversationType, MessageType, PresenceStatus, ConversationRole, ReceiptStatus  # noqa
from app.models.user import User  # noqa
from app.models.user_session import UserSession  # noqa
from app.models.user_settings import UserSettings  # noqa
from app.models.contact import Contact  # noqa
from app.models.blocked_user import BlockedUser  # noqa
from app.models.conversation import Conversation  # noqa
from app.models.conversation_member import ConversationMember  # noqa
from app.models.conversation_preference import ConversationPreference  # noqa
from app.models.otp import OTPRequest  # noqa
from app.models.message import Message  # noqa
from app.models.message_receipt import MessageReceipt  # noqa
from app.models.message_reaction import MessageReaction  # noqa
from app.models.attachment import Attachment  # noqa
from app.models.typing_status import TypingStatus  # noqa
from app.models.notification import Notification  # noqa
from app.models.starred_message import StarredMessage  # noqa
from app.models.message_deleted_for_me import MessageDeletedForMe  # noqa
from app.models.conversation_draft import ConversationDraft  # noqa
from app.models.device_token import DeviceToken  # noqa

