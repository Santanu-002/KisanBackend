class ResponseMessages:
    # Auth Success
    OTP_SENT = "OTP sent successfully via {channel}."
    OTP_VERIFIED = "OTP verified successfully."
    TOKEN_REFRESHED = "Tokens refreshed successfully."
    LOGOUT_SUCCESS = "Logged out successfully from this session."
    
    # Auth Errors
    INVALID_OTP = "The OTP provided is invalid."
    OTP_EXPIRED = "The OTP has expired. Please request a new one."
    TOO_MANY_ATTEMPTS = "Too many failed attempts. Please try again later."
    MAX_RETRIES_REACHED = "Maximum attempts reached. Please try again after 24 hours."
    USER_NOT_FOUND = "User account not found."
    INVALID_REFRESH_TOKEN = "Invalid or expired refresh token. Please login again."
    
    # User/Profile Success
    PROFILE_FETCHED = "Profile fetched successfully."
    PROFILE_UPDATED = "Profile updated successfully."
    UPLOAD_URL_GENERATED = "Upload URL generated successfully."
    KYC_SUBMITTED = "KYC documents submitted successfully."

    # General Errors
    VALIDATION_ERROR = "One or more fields are invalid."
    INTERNAL_SERVER_ERROR = "An unexpected error occurred on our end."
    RATE_LIMIT_EXCEEDED = "Rate limit exceeded. Please slow down."
    NOT_FOUND = "The requested resource was not found."
