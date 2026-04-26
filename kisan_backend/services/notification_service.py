import os
import firebase_admin
from firebase_admin import credentials, messaging
from loguru import logger
from typing import Optional, Dict, Any
from kisan_backend.core.config import settings
from kisan_backend.models.user import User

class NotificationService:
    def __init__(self):
        self._initialized = False
        self._initialize_firebase()

    def _initialize_firebase(self):
        try:
            if not firebase_admin._apps:
                cred_path = settings.FIREBASE_SERVICE_ACCOUNT_PATH
                if cred_path and os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                    self._initialized = True
                    logger.info("✅ [FIREBASE] Initialized with service account.")
                else:
                    # Initialize with default credentials (if running on GCP) or skip
                    try:
                        firebase_admin.initialize_app()
                        self._initialized = True
                        logger.info("✅ [FIREBASE] Initialized with default credentials.")
                    except Exception:
                        logger.warning("⚠️ [FIREBASE] Not initialized. Push notifications will be disabled.")
            else:
                self._initialized = True
        except Exception as e:
            logger.error(f"❌ [FIREBASE] Initialization failed: {e}")

    async def send_push_notification(
        self, 
        token: str, 
        title: str, 
        body: str, 
        data: Optional[Dict[str, str]] = None
    ) -> bool:
        if not self._initialized or not token:
            logger.warning(f"🚫 [NOTIFICATION] Skip sending. Initialized: {self._initialized}, Token present: {bool(token)}")
            return False

        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                token=token,
            )
            response = messaging.send(message)
            logger.info(f"📤 [NOTIFICATION] Sent successfully: {response}")
            return True
        except Exception as e:
            logger.error(f"❌ [NOTIFICATION] Failed to send: {e}")
            return False

    async def send_kyc_status_notification(
        self, 
        user: User, 
        approved: bool, 
        remarks: Optional[str] = None
    ):
        if not user.fcm_token:
            return

        if approved:
            title = "KYC Approved! 🎉"
            body = "Congratulations! Your KYC has been verified. You can now access all features of the Kisan app."
        else:
            title = "KYC Action Required ⚠️"
            body = f"Your KYC submission was rejected. Reason: {remarks or 'Documents unclear'}. Please resubmit."

        data = {
            "type": "kyc_status",
            "approved": str(approved).lower(),
            "click_action": "FLUTTER_NOTIFICATION_CLICK"
        }

        await self.send_push_notification(
            token=user.fcm_token,
            title=title,
            body=body,
            data=data
        )

# Singleton instance
notification_service = NotificationService()
