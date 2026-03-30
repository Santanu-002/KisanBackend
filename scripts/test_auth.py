import asyncio
import httpx
import sys

BASE_URL = "http://localhost:8000/api/v1"

async def test_auth_flow(phone_number: str):
    async with httpx.AsyncClient() as client:
        # 1. Send OTP
        print(f"\n[1] Requesting OTP for {phone_number}...")
        try:
            response = await client.post(
                f"{BASE_URL}/auth/send-otp",
                json={"phone_number": phone_number}
            )
            response.raise_for_status()
            print("Response:", response.json())
        except Exception as e:
            print(f"Error sending OTP: {e}")
            return

        # 2. Verify OTP
        otp = input("\nEnter the OTP received (check console if using mock provider): ")
        print(f"\n[2] Verifying OTP {otp} for {phone_number}...")
        try:
            response = await client.post(
                f"{BASE_URL}/auth/verify-otp",
                json={"phone_number": phone_number, "otp": otp}
            )
            response.raise_for_status()
            data = response.json()["data"]
            print("Success! Tokens received:")
            print(f"Access Token: {data['access_token'][:20]}...")
            print(f"Refresh Token: {data['refresh_token'][:20]}...")
            
            access_token = data['access_token']
            refresh_token = data['refresh_token']
        except Exception as e:
            print(f"Error verifying OTP: {e}")
            return

        # 3. Refresh Token
        print("\n[3] Testing Refresh Token...")
        try:
            response = await client.post(
                f"{BASE_URL}/auth/refresh-token",
                json={"refresh_token": refresh_token}
            )
            response.raise_for_status()
            data = response.json()["data"]
            print("Refresh Success! New Access Token received.")
        except Exception as e:
            print(f"Error refreshing token: {e}")
            return

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_auth.py <phone_number>")
        sys.exit(1)
        
    phone = sys.argv[1]
    asyncio.run(test_auth_flow(phone))
