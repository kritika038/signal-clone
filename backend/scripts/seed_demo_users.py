import asyncio
import uuid
import logging
from typing import List, Tuple
from sqlalchemy import select
from datetime import datetime

from app.db.session import SessionLocal
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.conversation import Conversation, ConversationType
from app.models.conversation_member import ConversationMember, ConversationRole
from app.models.message import Message, MessageType

logger = logging.getLogger(__name__)

DEMO_USERS = [
    ("+919999990001", "demo1", "Demo User 1"),
    ("+919999990002", "demo2", "Demo User 2"),
    ("+919999990003", "demo3", "Demo User 3"),
    ("+919999990004", "demo4", "Demo User 4"),
    ("+919999990005", "demo5", "Demo User 5"),
    ("+919999990006", "demo6", "Demo User 6"),
    ("+919999990007", "demo7", "Demo User 7"),
    ("+919999990008", "demo8", "Demo User 8"),
    ("+919999990009", "demo9", "Demo User 9"),
    ("+919999990010", "demo10", "Demo User 10"),
]

async def seed_demo_data():
    logger.info("Starting demo data seed process...")
    async with SessionLocal() as session:
        created_users: List[User] = []
        for phone, username, display_name in DEMO_USERS:
            # Check if user exists
            stmt = select(User).where(User.phone == phone)
            result = await session.execute(stmt)
            user = result.scalars().first()

            if not user:
                user = User(
                    id=uuid.uuid4(),
                    phone=phone,
                    username=username,
                    display_name=display_name,
                    is_verified=True,
                    avatar_url=f"https://ui-avatars.com/api/?name={username}&background=random",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(user)
                await session.flush()
                
                settings = UserSettings(
                    user_id=user.id,
                    theme="dark"
                )
                session.add(settings)
                logger.info(f"Created demo user: {username}")
            else:
                # Ensure they are fully initialized in case of partial seed
                user.is_verified = True
                
                stmt = select(UserSettings).where(UserSettings.user_id == user.id)
                res = await session.execute(stmt)
                settings = res.scalars().first()
                if not settings:
                    settings = UserSettings(
                        user_id=user.id,
                        theme="dark"
                    )
                    session.add(settings)
            
            created_users.append(user)

        await session.commit()
        
        # Create a few demo conversations
        if len(created_users) >= 3:
            u1, u2, u3 = created_users[0], created_users[1], created_users[2]
            pairs = [(u1, u2), (u1, u3)]
            
            for p1, p2 in pairs:
                stmt = select(Conversation).join(ConversationMember).where(
                    Conversation.type == ConversationType.DIRECT,
                    ConversationMember.user_id == p1.id
                ).intersect(
                    select(Conversation).join(ConversationMember).where(
                        Conversation.type == ConversationType.DIRECT,
                        ConversationMember.user_id == p2.id
                    )
                )
                res = await session.execute(stmt)
                conv = res.scalars().first()
                
                if not conv:
                    conv_id = uuid.uuid4()
                    conv = Conversation(
                        id=conv_id,
                        type=ConversationType.DIRECT,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    session.add(conv)
                    
                    m1 = ConversationMember(
                        id=uuid.uuid4(),
                        conversation_id=conv_id,
                        user_id=p1.id,
                        role=ConversationRole.MEMBER,
                        joined_at=datetime.utcnow()
                    )
                    m2 = ConversationMember(
                        id=uuid.uuid4(),
                        conversation_id=conv_id,
                        user_id=p2.id,
                        role=ConversationRole.MEMBER,
                        joined_at=datetime.utcnow()
                    )
                    session.add_all([m1, m2])
                    await session.flush()
                    
                    # Add a welcome message
                    msg = Message(
                        id=uuid.uuid4(),
                        conversation_id=conv_id,
                        sender_id=p1.id,
                        message_type=MessageType.TEXT,
                        content=f"Hello {p2.display_name}! This is a demo conversation.",
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    session.add(msg)
                    logger.info(f"Created demo conversation between {p1.username} and {p2.username}")
                    
            await session.commit()
    logger.info("Demo data seed process completed.")

if __name__ == "__main__":
    asyncio.run(seed_demo_data())
