from typing import Dict, Any, Optional
from datetime import datetime
import time

class SSOUser:
    """SSO user model that represents a user authenticated through SSO (e.g. Microsoft Azure AD)"""
    
    def __init__(self, user_info: Dict[str, Any]):
        self.id = user_info.get("id")
        self.email = user_info.get("userPrincipalName", "")
        self.first_name = user_info.get("givenName", "")
        self.last_name = user_info.get("surname", "")
        self.display_name = user_info.get("displayName", "")
        self.picture = user_info.get("avatar", "")
        self.provider = "microsoft"
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[float] = None

    def set_tokens(self, access_token: str, refresh_token: Optional[str] = None, expires_in: Optional[int] = None) -> None:
        """Set the access token and related information for this SSO user"""
        self.access_token = access_token
        if refresh_token:
            self.refresh_token = refresh_token
        if expires_in:
            self.token_expires_at = time.time() + expires_in

    def is_token_expired(self) -> bool:
        """Check if the current access token is expired"""
        if not self.token_expires_at:
            return True
        return time.time() >= self.token_expires_at

    @property
    def full_name(self) -> str:
        """Get the full name of the user"""
        if self.display_name:
            return self.display_name
        parts = [self.first_name, self.last_name]
        return " ".join(filter(None, parts))

    def to_dict(self) -> Dict[str, Any]:
        """Convert the SSO user to a dictionary"""
        return {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "display_name": self.display_name,
            "picture": self.picture,
            "provider": self.provider,
            "full_name": self.full_name,
            "token_expires_at": self.token_expires_at
        } 