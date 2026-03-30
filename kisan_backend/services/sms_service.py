import abc
import random
import logging
from typing import Optional
from kisan_backend.core.config import settings

logger = logging.getLogger("kisan_backend")

class SMSProvider(abc.ABC):
    @abc.abstractmethod
    async def send_sms(self, phone_number: str, message: str) -> bool:
        pass

class MockSMSProvider(SMSProvider):
    async def send_sms(self, phone_number: str, message: str) -> bool:
        logger.info(f"[MOCK SMS] Sent to {phone_number}: {message}")
        return True

class Fast2SMSProvider(SMSProvider):
    async def send_sms(self, phone_number: str, message: str) -> bool:
        if not settings.FAST2SMS_API_KEY:
            logger.error("Fast2SMS API Key not configured")
            return False
            
        url = "https://www.fast2sms.com/dev/bulkV2"
        payload = {
            "route": "otp",
            "variables_values": message.split()[-1], # Assuming the last word is the OTP
            "numbers": phone_number,
        }
        headers = {
            "authorization": settings.FAST2SMS_API_KEY,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(url, data=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                if result.get("return"):
                    logger.info(f"Fast2SMS: OTP sent to {phone_number}")
                    return True
                logger.error(f"Fast2SMS Error: {result.get('message')}")
                return False
        except Exception as e:
            logger.error(f"Fast2SMS exception: {str(e)}")
            return False

class TwilioSMSProvider(SMSProvider):
    async def send_sms(self, phone_number: str, message: str) -> bool:
        if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_PHONE_NUMBER]):
            logger.error("Twilio configuration missing")
            return False
            
        try:
            from twilio.rest import Client
            import asyncio
            
            # Twilio client is synchronous, running in threadpool
            def _send():
                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                return client.messages.create(
                    body=message,
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=phone_number
                )
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _send)
            logger.info(f"Twilio: SMS sent to {phone_number}")
            return True
        except Exception as e:
            logger.error(f"Twilio exception: {str(e)}")
            return False

def get_sms_provider() -> SMSProvider:
    provider = settings.SMS_PROVIDER.lower()
    if provider == "fast2sms":
        return Fast2SMSProvider()
    elif provider == "twilio":
        return TwilioSMSProvider()
    return MockSMSProvider()
