from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import jwt, JWTError

from kisan_backend.core.config import settings
from kisan_backend.core.exceptions import AuthException
from kisan_backend.core.messages import ResponseMessages

class TokenService:
    """Handles JWT generation and decoding."""

    def __init__(self, secret_key: str = settings.SECRET_KEY, algorithm: str = settings.ALGORITHM):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def create_access_token(self, subject: str, session_id: str, minutes: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
        """Generates an access token."""
        return self._create_token(
            data={"sub": subject, "sid": session_id, "type": "access"},
            expires_delta=timedelta(minutes=minutes)
        )

    def create_refresh_token(self, subject: str, session_id: str, expires_delta: Optional[timedelta] = None) -> str:
        """Generates a refresh token."""
        if not expires_delta:
            expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            
        return self._create_token(
            data={"sub": subject, "sid": session_id, "type": "refresh"},
            expires_delta=expires_delta
        )

    def _create_token(self, data: dict, expires_delta: timedelta) -> str:
        """Internal helper for JWT encoding."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str, verify_exp: bool = True) -> Dict[str, Any]:
        """Decodes a JWT and returns the payload."""
        try:
            return jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_exp": verify_exp}
            )
        except JWTError:
            raise AuthException(ResponseMessages.INVALID_REFRESH_TOKEN)
