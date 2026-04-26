import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field, Column, String, UniqueConstraint


class UserFCMToken(SQLModel, table=True):
    """
    Stores FCM push tokens keyed by (user_id, device_id).

    Design:
    - One row per physical device per user.
    - Upsert on (user_id, device_id) → same device always overwrites its token.
    - Multiple devices per user are supported (e.g., farmer with two phones).
    """

    __tablename__ = "user_fcm_tokens"
    __table_args__ = (
        UniqueConstraint("user_id", "device_id", name="uq_user_fcm_token_device"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, nullable=False)
    device_id: str = Field(sa_column=Column(String, nullable=False))
    fcm_token: str = Field(sa_column=Column(String, nullable=False))
    updated_at: datetime = Field(default_factory=datetime.utcnow)
