from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "Kisan Backend"
    API_V1_STR: str = "/api/v1"
    
    # Database
    # Standard format: postgresql+asyncpg://user:pass@host:port/db
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/kisan_db")
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Security
    SECRET_KEY: str = Field(default="dev_secret_key_please_change_in_production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # OTP Configuration
    OTP_EXPIRY_SECONDS: int = 600
    OTP_MAX_ATTEMPTS: int = 5
    OTP_RATE_LIMIT_REQUESTS: int = 3
    OTP_RATE_LIMIT_WINDOW_SECONDS: int = 600
    
    # SMS Providers
    SMS_PROVIDER: str = "mock"  # Options: mock, fast2sms, twilio, msg91
    FAST2SMS_API_KEY: Optional[str] = None
    
    # Twilio (Required if SMS_PROVIDER=twilio)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None
    TWILIO_MESSAGING_SERVICE_SID: Optional[str] = None
    
    # Client Config
    ANDROID_APP_HASH: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        case_sensitive=True,
        extra='ignore' # Ignore extra env variables
    )

settings = Settings()
