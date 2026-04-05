import asyncio
import sys
import os

# Add the root directory to path to allow importing kisan_backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kisan_backend.services.sms_service import get_sms_provider
from kisan_backend.core.config import settings
from kisan_backend.schemas.auth import ChannelType

async def test_sms_channels():
    print(f"--- Multi-Channel OTP Test ---")
    print(f"Provider: {settings.SMS_PROVIDER}")
    print(f"Phone Loaded: {settings.TWILIO_PHONE_NUMBER}")
    print(f"WhatsApp Loaded: {settings.TWILIO_WHATSAPP_NUMBER}")
    print(f"Messaging Service SID: {settings.TWILIO_MESSAGING_SERVICE_SID if settings.TWILIO_MESSAGING_SERVICE_SID else 'None'}")
    print(f"-------------------------------")
    
    provider = get_sms_provider()
    
    # Update this to your real phone number for testing
    test_number = "+910000000000" 
    test_message = "Kisan Backend: Multi-Channel Setup Success!"
    
    print("Select Channel:")
    print("1. SMS")
    print("2. WhatsApp")
    choice = input("Choice (1/2): ")
    
    channel = ChannelType.SMS if choice == '1' else ChannelType.WHATSAPP
    
    confirm = input(f"Send test {channel.value} to {test_number}? (y/n): ")
    if confirm.lower() == 'y':
        success = await provider.send_sms(test_number, test_message, channel=channel)
        if success:
            print(f"SUCCESS: {channel.value} triggered successfully.")
        else:
            print(f"FAILED: Check backend logs for details.")
    else:
        print("Cancelled.")

if __name__ == "__main__":
    asyncio.run(test_sms_channels())
