import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import SessionLocal
from app.core.security import get_password_hash
from app.models.enums import ConversationRole, ConversationType, MessageType, PresenceStatus, ReceiptStatus
from app.models.user import User
from app.models.user_session import UserSession
from app.models.user_settings import UserSettings
from app.models.contact import Contact
from app.models.blocked_user import BlockedUser
from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.models.conversation_preference import ConversationPreference
from app.models.message import Message
from app.models.message_receipt import MessageReceipt
from app.models.message_reaction import MessageReaction
from app.models.attachment import Attachment
from app.models.notification import Notification

# Setup standard seed values
USER_PROFILES = [
    ("+12025550101", "alice", "Alice Smith", "Security advocate & code lover"),
    ("+12025550102", "bob", "Bob Jones", "Always coding, always caffeinated"),
    ("+12025550103", "charlie", "Charlie Brown", "Just a regular designer"),
    ("+12025550104", "dana", "Dana Scully", "The truth is out there"),
    ("+12025550105", "evan", "Evan Wright", "Systems architect & devops"),
    ("+12025550106", "fiona", "Fiona Gallagher", "Family first, chaos second"),
    ("+12025550107", "george", "George Costanza", "I'm unemployed & loving it"),
    ("+12025550108", "hannah", "Hannah Baker", "Listening to cassette tapes"),
    ("+12025550109", "ian", "Ian Malcolm", "Life finds a way"),
    ("+12025550110", "julia", "Julia Roberts", "Living life one smile at a time"),
    ("+12025550111", "kevin", "Kevin Mitnick", "Free Kevin! Security expert"),
    ("+12025550112", "laura", "Laura Palmer", "Fire walk with me"),
]

CHAT_CONTENT_TEMPLATES = [
    "Hey! How's the project going?",
    "Did you check the new security policy updates?",
    "We need to review the pull request today.",
    "Sure, let's schedule a call at 3 PM.",
    "That makes sense. Let's do it.",
    "I'm working on the SQLite database layer.",
    "Signal's encryption protocol is absolutely amazing.",
    "Can you share the file you mentioned yesterday?",
    "Check out this cool picture!",
    "No problem, happy to help.",
    "Let me know when you're free to pair program.",
    "What's the status of the Docker container build?",
    "Don't forget to push your code changes.",
    "Yes, I completely agree with your proposal.",
    "Haha, that was hilarious! 😂",
    "I'll upload the logs right now.",
    "Let's meet in the main conference room.",
    "Is the dev server up?",
    "Please check the environment settings.",
    "Got it, thanks for the heads up!",
]

EMOJIS = [
    ("👍", "U+1F44D"),
    ("❤️", "U+2764"),
    ("😂", "U+1F602"),
    ("😮", "U+1F62E"),
    ("😢", "U+1F622"),
    ("🙏", "U+1F64F"),
    ("🔥", "U+1F525"),
    ("🎉", "U+1F389"),
]

async def seed_data(db: Optional[AsyncSession] = None):
    is_local = False
    if db is None:
        db = SessionLocal()
        is_local = True
    try:
        print("[Seed] Starting comprehensive data seeding...")
        
        # 1. Create 12 Users
        users: List[User] = []
        pass_hash = get_password_hash("SignalSecretPass123!")
        now = datetime.now(timezone.utc)
        
        for idx, (phone, username, display_name, bio) in enumerate(USER_PROFILES):
            user = User(
                id=uuid.uuid4(),
                phone=phone,
                username=username,
                display_name=display_name,
                bio=bio,
                hashed_password=pass_hash,
                is_verified=True,
                presence_status=random.choice(list(PresenceStatus)),
                last_seen=now - timedelta(minutes=random.randint(5, 1440)),
                created_at=now - timedelta(days=120)
            )
            db.add(user)
            users.append(user)
        await db.flush()
        print(f"[Seed] Created {len(users)} users.")

        # 2. Generate UserSettings & UserSessions for each User
        for user in users:
            settings = UserSettings(
                id=uuid.uuid4(),
                user_id=user.id,
                theme="dark" if random.choice([True, False]) else "light",
                language="en",
                privacy_last_seen=random.choice(["EVERYBODY", "CONTACTS", "NOBODY"]),
                privacy_profile_photo=random.choice(["EVERYBODY", "CONTACTS"]),
                privacy_read_receipts=True,
                privacy_typing_indicator=True,
                notifications_enabled=True,
                auto_download_media=random.choice([True, False]),
                default_disappearing_timer=random.choice([0, 30, 300, 3600]),
                font_size="medium"
            )
            db.add(settings)

            session = UserSession(
                id=uuid.uuid4(),
                user_id=user.id,
                refresh_token_hash=get_password_hash(str(uuid.uuid4())),
                device_name=f"Device-{random.choice(['iPhone', 'Pixel', 'Macbook', 'Thinkpad'])}",
                device_type=random.choice(["MOBILE", "DESKTOP"]),
                ip_address=f"192.168.1.{random.randint(10, 250)}",
                last_activity=now - timedelta(minutes=random.randint(1, 120)),
                expires_at=now + timedelta(days=30)
            )
            db.add(session)
        print("[Seed] Created user settings & sessions.")

        # 3. Create 60 Contacts (each user has 5 unique contacts on average)
        contacts_count = 0
        added_contacts = set()
        while contacts_count < 60:
            u1 = random.choice(users)
            u2 = random.choice(users)
            if u1.id != u2.id and (u1.id, u2.id) not in added_contacts:
                contact = Contact(
                    id=uuid.uuid4(),
                    owner_id=u1.id,
                    contact_user_id=u2.id,
                    nickname=f"{u2.display_name} (Work)" if random.choice([True, False]) else None,
                    created_at=now - timedelta(days=90)
                )
                db.add(contact)
                added_contacts.add((u1.id, u2.id))
                contacts_count += 1
        print(f"[Seed] Created {contacts_count} contacts.")

        # 4. Create 3 Blocked Users links
        blocked_pairs = set()
        while len(blocked_pairs) < 3:
            u1 = random.choice(users)
            u2 = random.choice(users)
            if u1.id != u2.id and (u1.id, u2.id) not in blocked_pairs:
                block = BlockedUser(
                    id=uuid.uuid4(),
                    user_id=u1.id,
                    blocked_user_id=u2.id,
                    created_at=now - timedelta(days=30)
                )
                db.add(block)
                blocked_pairs.add((u1.id, u2.id))
        print("[Seed] Created blocked relationships.")

        # 5. Create Conversations
        # 20 Direct conversations
        direct_convs: List[Conversation] = []
        added_directs = set()
        
        while len(direct_convs) < 20:
            u1 = random.choice(users)
            u2 = random.choice(users)
            pair = tuple(sorted([str(u1.id), str(u2.id)]))
            if u1.id != u2.id and pair not in added_directs:
                conv = Conversation(
                    id=uuid.uuid4(),
                    type=ConversationType.DIRECT,
                    last_activity_at=now - timedelta(days=90),
                    created_at=now - timedelta(days=90)
                )
                db.add(conv)
                added_directs.add(pair)
                direct_convs.append(conv)
                
                # Add members
                m1 = ConversationMember(conversation_id=conv.id, user_id=u1.id, role=ConversationRole.MEMBER)
                m2 = ConversationMember(conversation_id=conv.id, user_id=u2.id, role=ConversationRole.MEMBER)
                db.add_all([m1, m2])
                
                # Add preferences
                p1 = ConversationPreference(conversation_id=conv.id, user_id=u1.id)
                p2 = ConversationPreference(conversation_id=conv.id, user_id=u2.id)
                db.add_all([p1, p2])
        await db.flush()
        print("[Seed] Created 20 direct conversations.")

        # 8 Group conversations
        group_convs: List[Conversation] = []
        group_names = [
            "Project Alpha Devs", "Security & Encryption Talk", "Design Feedback",
            "Random Chit-Chat", "Weekend Outing Planning", "Core Engineering Team",
            "Product Roadmap Q3", "Signal Community Hub"
        ]
        
        for idx, gname in enumerate(group_names):
            creator = random.choice(users)
            conv = Conversation(
                id=uuid.uuid4(),
                type=ConversationType.GROUP,
                name=gname,
                description=f"Official group for {gname.lower()}",
                created_by=creator.id,
                last_activity_at=now - timedelta(days=60),
                created_at=now - timedelta(days=60)
            )
            db.add(conv)
            group_convs.append(conv)

            # Add creator as OWNER
            owner_m = ConversationMember(
                conversation_id=conv.id,
                user_id=creator.id,
                role=ConversationRole.OWNER
            )
            db.add(owner_m)
            db.add(ConversationPreference(conversation_id=conv.id, user_id=creator.id))

            # Select 4-6 random users as group members
            m_count = random.randint(4, 7)
            g_members = random.sample(users, m_count)
            for gm in g_members:
                if gm.id != creator.id:
                    role = ConversationRole.ADMIN if random.choice([True, False, False]) else ConversationRole.MEMBER
                    m = ConversationMember(
                        conversation_id=conv.id,
                        user_id=gm.id,
                        role=role
                    )
                    db.add(m)
                    db.add(ConversationPreference(conversation_id=conv.id, user_id=gm.id))
        await db.flush()
        print("[Seed] Created 8 group conversations.")

        # 6. Generate 2500+ Messages spread over several months
        all_convs = direct_convs + group_convs
        messages: List[Message] = []
        
        # Load conversation members in memory to quickly assign sender ID
        conv_members_map = {}
        for c in all_convs:
            res_m = await db.execute(select(ConversationMember.user_id).where(ConversationMember.conversation_id == c.id))
            conv_members_map[c.id] = list(res_m.scalars().all())

        total_messages_target = 2550
        base_time = now - timedelta(days=90)
        
        print(f"[Seed] Generating {total_messages_target} messages...")
        for i in range(total_messages_target):
            conv = random.choice(all_convs)
            sender_id = random.choice(conv_members_map[conv.id])
            
            # Progressively increase timestamps to simulate real conversations
            msg_time = base_time + timedelta(seconds=i * random.randint(15, 3000))
            if msg_time > now:
                msg_time = now - timedelta(minutes=random.randint(1, 10))

            m_type = random.choice([MessageType.TEXT, MessageType.TEXT, MessageType.TEXT, MessageType.IMAGE, MessageType.FILE])
            content = random.choice(CHAT_CONTENT_TEMPLATES)
            
            msg = Message(
                id=uuid.uuid4(),
                conversation_id=conv.id,
                sender_id=sender_id,
                content=content if m_type == MessageType.TEXT else f"Shared attachment: {content.split()[-1]}",
                message_type=m_type,
                is_system=False,
                created_at=msg_time,
                updated_at=msg_time
            )
            db.add(msg)
            messages.append(msg)
            
            # Flush periodically to prevent memory exhaustion
            if i % 500 == 0:
                await db.flush()
        
        await db.flush()
        print(f"[Seed] Generated {len(messages)} messages successfully.")

        # 7. Create 40 Reply chains (nested reply mappings)
        reply_count = 0
        for _ in range(100):
            if reply_count >= 40:
                break
            parent = random.choice(messages)
            conv_members = conv_members_map[parent.conversation_id]
            replier_id = random.choice(conv_members)
            
            reply_msg = Message(
                id=uuid.uuid4(),
                conversation_id=parent.conversation_id,
                sender_id=replier_id,
                content=f"Replying to: '{parent.content[:20]}...' -> I agree with that point.",
                message_type=MessageType.TEXT,
                reply_to_id=parent.id,
                created_at=parent.created_at + timedelta(seconds=random.randint(30, 300)),
                updated_at=parent.created_at + timedelta(seconds=random.randint(30, 300))
            )
            db.add(reply_msg)
            reply_count += 1
        await db.flush()
        print(f"[Seed] Created {reply_count} reply chains.")

        # 8. Create 200 Attachments
        media_count = 0
        attachment_msg_types = [MessageType.IMAGE, MessageType.VIDEO, MessageType.FILE]
        
        for msg in messages:
            if media_count >= 200:
                break
            if msg.message_type in attachment_msg_types or random.choice([True, False, False, False]):
                m_type = "image/png" if msg.message_type == MessageType.IMAGE else "application/pdf"
                fname = "photo.png" if msg.message_type == MessageType.IMAGE else "document.pdf"
                
                attach = Attachment(
                    id=uuid.uuid4(),
                    message_id=msg.id,
                    storage_key=f"uploads/{uuid.uuid4()}-{fname}",
                    original_filename=fname,
                    mime_type=m_type,
                    size=random.randint(1024, 1024 * 1024 * 15), # 1KB to 15MB
                    width=1920 if msg.message_type == MessageType.IMAGE else None,
                    height=1080 if msg.message_type == MessageType.IMAGE else None,
                    checksum=str(uuid.uuid4()).replace("-", ""),
                    created_at=msg.created_at
                )
                db.add(attach)
                media_count += 1
        await db.flush()
        print(f"[Seed] Attached {media_count} media/file attachments.")

        # 9. Create 300 Reactions
        reactions_count = 0
        added_reactions = set()
        for _ in range(1000): # Loop more times to get enough unique reactions
            if reactions_count >= 300:
                break
            msg = random.choice(messages)
            conv_members = conv_members_map[msg.conversation_id]
            reactor_id = random.choice(conv_members)
            emoji, unicode_val = random.choice(EMOJIS)
            
            # Track in-memory to prevent duplicate key error during transaction
            pair = (msg.id, reactor_id, emoji)
            if pair not in added_reactions:
                reaction = MessageReaction(
                    id=uuid.uuid4(),
                    message_id=msg.id,
                    user_id=reactor_id,
                    reaction=emoji,
                    unicode=unicode_val,
                    created_at=msg.created_at + timedelta(seconds=random.randint(10, 600))
                )
                db.add(reaction)
                added_reactions.add(pair)
                reactions_count += 1
        await db.flush()
        print(f"[Seed] Created {reactions_count} message emoji reactions.")

        # 10. Create 500+ receipts
        receipts_count = 0
        added_receipts = set()
        for msg in random.sample(messages, len(messages)):
            if receipts_count >= 520:
                break
            conv_members = conv_members_map[msg.conversation_id]
            for user_id in conv_members:
                if user_id != msg.sender_id:
                    pair = (msg.id, user_id)
                    if pair not in added_receipts:
                        status = random.choice([ReceiptStatus.DELIVERED, ReceiptStatus.READ])
                        receipt = MessageReceipt(
                            id=uuid.uuid4(),
                            message_id=msg.id,
                            user_id=user_id,
                            status=status,
                            created_at=msg.created_at + timedelta(seconds=random.randint(5, 60)),
                            updated_at=msg.created_at + timedelta(seconds=random.randint(5, 3600))
                        )
                        db.add(receipt)
                        added_receipts.add(pair)
                        receipts_count += 1
            if receipts_count >= 520:
                break
        await db.flush()
        print(f"[Seed] Logged {receipts_count} message receipts.")

        # 11. Create 50 Notification alerts
        notif_count = 0
        for msg in random.sample(messages, min(len(messages), 100)):
            if notif_count >= 50:
                break
            conv_members = conv_members_map[msg.conversation_id]
            recipients = [u for u in conv_members if u != msg.sender_id]
            if recipients:
                target_user = random.choice(recipients)
                notif = Notification(
                    id=uuid.uuid4(),
                    user_id=target_user,
                    message_id=msg.id,
                    type="MESSAGE",
                    is_read=random.choice([True, False]),
                    created_at=msg.created_at
                )
                db.add(notif)
                notif_count += 1
        await db.flush()
        print(f"[Seed] Seeded {notif_count} notification records.")

        # 12. Finalize conversations metadata (last_message_id, last_activity_at)
        for conv in all_convs:
            # Find the newest message in this conversation
            newest_msg_query = (
                select(Message)
                .where(Message.conversation_id == conv.id)
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            newest_res = await db.execute(newest_msg_query)
            newest_msg = newest_res.scalar_one_or_none()
            if newest_msg:
                conv.last_message_id = newest_msg.id
                conv.last_activity_at = newest_msg.created_at
                
        await db.commit()
        print("[Seed] Successfully completed database seeding! 🎉")

    except Exception as e:
        await db.rollback()
        print(f"[Seed] Seeding failed with exception: {e}")
        raise e
    finally:
        if is_local:
            await db.close()

if __name__ == "__main__":
    asyncio.run(seed_data())
