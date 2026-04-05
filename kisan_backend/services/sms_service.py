import abc
import random
import logging
from typing import Optional
from kisan_backend.core.config import settings
from kisan_backend.schemas.auth import ChannelType

logger = logging.getLogger("kisan_backend")

class SMSProvider(abc.ABC):
    """Base class for SMS delivery providers."""
    
    @abc.abstractmethod
    async def send_sms(self, phone_number: str, message: str, channel: ChannelType = ChannelType.SMS) -> bool:
        """Send an SMS or WhatsApp message to a phone number."""
        pass

class MockSMSProvider(SMSProvider):
    """Mock provider for local development that logs messages to the terminal."""
    
    async def send_sms(self, phone_number: str, message: str, channel: ChannelType = ChannelType.SMS) -> bool:
        logger.info(f"[MOCK {channel.upper()}] Sent to {phone_number}: {message}")
        return True

class Fast2SMSProvider(SMSProvider):
    """Provider for the Fast2SMS gateway (Indian market)."""
    
    async def send_sms(self, phone_number: str, message: str, channel: ChannelType = ChannelType.SMS) -> bool:
        if channel == ChannelType.WHATSAPP:
            logger.warning("Fast2SMS does not support WhatsApp. Falling back to SMS.")
            
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
    """Provider for Twilio (Global market, supports WhatsApp and SMS)."""
    
    async def send_sms(self, phone_number: str, message: str, channel: ChannelType = ChannelType.SMS) -> bool:
        if not self._is_configured(channel):
            return False
            
        try:
            from twilio.rest import Client
            import asyncio
            
            def _send():
                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                params = self._prepare_params(phone_number, message, channel)
                return client.messages.create(**params)
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _send)
            logger.info(f"Twilio: {channel.upper()} sent to {phone_number}")
            return True
        except Exception as e:
            logger.error(f"Twilio exception: {str(e)}")
            return False

    def _is_configured(self, channel: ChannelType) -> bool:
        """Check if required settings for the chosen channel are present."""
        base_config = all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN])
        if not base_config:
            logger.error("Twilio SID or Token missing")
            return False
            
        if channel == ChannelType.WHATSAPP and not settings.TWILIO_WHATSAPP_NUMBER:
            logger.error("Twilio WhatsApp number missing")
            return False
            
        if channel == ChannelType.SMS and not any([settings.TWILIO_PHONE_NUMBER, settings.TWILIO_MESSAGING_SERVICE_SID]):
            logger.error("Twilio SMS configuration missing (Phone Number or Messaging Service SID)")
            return False
            
        return True

    def _prepare_params(self, phone_number: str, message: str, channel: ChannelType) -> dict:
        """Prepare parameters for the Twilio message creation API."""
        params = {"body": message}
        
        if channel == ChannelType.WHATSAPP:
            params["from_"] = f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}"
            params["to"] = f"whatsapp:{phone_number}"
        else:
            params["to"] = phone_number
            if settings.TWILIO_MESSAGING_SERVICE_SID:
                params["messaging_service_sid"] = settings.TWILIO_MESSAGING_SERVICE_SID
            else:
                params["from_"] = settings.TWILIO_PHONE_NUMBER
                
        return params

def get_sms_provider() -> SMSProvider:
    """Factory function to get the configured SMS provider."""
    provider = settings.SMS_PROVIDER.lower()
    if provider == "fast2sms":
        return Fast2SMSProvider()
    elif provider == "twilio":
        return TwilioSMSProvider()
    return MockSMSProvider()
