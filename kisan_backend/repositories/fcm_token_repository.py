"""
fcm_token_repository.py — Data access for UserFCMToken.

Responsibility: DB queries only. No business logic.
Upsert semantics: same (user_id, device_id) pair overwrites the token.
"""

import uuid
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from kisan_backend.models.user_fcm_token import UserFCMToken


class FCMTokenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, user_id: uuid.UUID, device_id: str, fcm_token: str) -> None:
        """
        Insert or overwrite the FCM token for a (user_id, device_id) pair.

        Uses PostgreSQL's ON CONFLICT DO UPDATE so the operation is atomic
        and idempotent — safe to call on every app open without side-effects
        when the token hasn't changed.
        """
        stmt = (
            pg_insert(UserFCMToken)
            .values(
                id=uuid.uuid4(),
                user_id=user_id,
                device_id=device_id,
                fcm_token=fcm_token,
                updated_at=datetime.utcnow(),
            )
            .on_conflict_do_update(
                constraint="uq_user_fcm_token_device",
                set_={
                    "fcm_token": fcm_token,
                    "updated_at": datetime.utcnow(),
                },
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()
