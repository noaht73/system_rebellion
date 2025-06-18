from fastapi import Depends, Query, WebSocket
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, AsyncGenerator

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.user import User

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get an async database session.
    """
    async with AsyncSessionLocal() as db_session:
        yield db_session

async def get_user_from_token(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_async_db),
    token: str | None = Query(None),
) -> User | None:
    if token is None:
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            return None
    except JWTError:
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        return None
    return user
