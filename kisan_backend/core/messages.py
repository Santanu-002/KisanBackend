class ResponseMessages:
    # ── Auth Success ───────────────────────────────────────────────────────────
    OTP_SENT = "OTP sent successfully via {channel}."
    OTP_VERIFIED = "OTP verified successfully."
    TOKEN_REFRESHED = "Tokens refreshed successfully."
    LOGOUT_SUCCESS = "Logged out successfully from this session."

    # ── Auth Errors ────────────────────────────────────────────────────────────
    INVALID_OTP = "The OTP provided is invalid."
    OTP_EXPIRED = "The OTP has expired. Please request a new one."
    TOO_MANY_ATTEMPTS = "Too many failed attempts. Please try again later."
    MAX_RETRIES_REACHED = "Maximum attempts reached. Please try again after 24 hours."
    USER_NOT_FOUND = "User account not found."
    INVALID_REFRESH_TOKEN = "Invalid or expired refresh token. Please login again."
    OTP_SEND_FAILED = "Failed to send OTP. Please try again later."

    # ── Access Control ─────────────────────────────────────────────────────────
    ACCESS_DENIED_ADMIN_ONLY = (
        "Access denied. This portal is restricted to administrators only."
    )
    ACCESS_DENIED_BROWSER_FARMERS = (
        "Access denied. The Kisan app must be used on a mobile device, not a browser."
    )

    # ── Session ────────────────────────────────────────────────────────────────
    SESSION_REVOKED = (
        "This session was terminated because you logged in on another device."
    )
    SESSION_CONFLICT = "Active session detected on another device."

    # ── User / Profile ─────────────────────────────────────────────────────────
    PROFILE_FETCHED = "Profile fetched successfully."
    PROFILE_UPDATED = "Profile updated successfully."
    UPLOAD_URL_GENERATED = "Upload URL generated successfully."
    KYC_SUBMITTED = "KYC documents submitted successfully."

    # ── General Errors ─────────────────────────────────────────────────────────
    VALIDATION_ERROR = "One or more fields are invalid."
    INTERNAL_SERVER_ERROR = "An unexpected error occurred on our end."
    RATE_LIMIT_EXCEEDED = "Rate limit exceeded. Please slow down."
    NOT_FOUND = "The requested resource was not found."
