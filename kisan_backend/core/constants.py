"""
Centralized configuration constants for the Kisan Backend.

All magic numbers and fixed configuration values live here.
Import from this module instead of hardcoding values in service files.
"""


class OTPConfig:
    """OTP generation, storage, and rate-limiting parameters."""

    LENGTH = 6
    MOCK_CODE = "000000"
    MAX_ATTEMPTS_DEFAULT = 5  # Overridden by settings.OTP_MAX_ATTEMPTS if set

    # Backoff wait times (in seconds) between resend attempts
    # Key = attempt number, Value = seconds to wait before next resend is allowed
    BACKOFF_MAP: dict[int, int] = {
        1: 30,
        2: 60,
        3: 120,
        4: 240,
    }

    # Default block duration (in seconds) when max attempts is exceeded (24 hours)
    BLOCK_DURATION_SECONDS = 86_400

    # Redis key prefixes
    REDIS_KEY_OTP = "otp"
    REDIS_KEY_ATTEMPTS = "otp_attempts"


class SessionConfig:
    """Session management and handover parameters."""

    # How long (seconds) to wait for the old device to disconnect during a force-login handover
    HANDOVER_TIMEOUT_SECONDS = 5.0

    # Redis key prefix for active session metadata
    REDIS_KEY_SESSION = "session"

    # Admin refresh token TTL (24 hours in seconds)
    ADMIN_REFRESH_TTL_SECONDS = 86_400

    # Admin refresh token duration as timedelta-compatible hours
    ADMIN_REFRESH_HOURS = 24


class TokenConfig:
    """Token lifecycle thresholds used by the API client and socket manager."""

    # How many seconds before expiry the proactive HTTP refresh kicks in
    PROACTIVE_REFRESH_THRESHOLD_SECONDS = 10

    # How many seconds before expiry the socket pre-connection refresh kicks in
    SOCKET_PRECONNECT_REFRESH_THRESHOLD_SECONDS = 30

    # Minimum remaining TTL (seconds) to skip a refresh inside the mutex lock
    REFRESH_REUSE_THRESHOLD_SECONDS = 30


class DeviceHeaders:
    """HTTP request header names for device identification."""

    DEVICE_ID = "X-Device-Id"
    BRAND = "X-Device-Brand"
    MODEL = "X-Device-Model"
    OS_NAME = "X-Device-OS"
    OS_VERSION = "X-Device-OS-Version"
    APP_VERSION = "X-App-Version"
    BROWSER = "X-Device-Browser"
