from pydantic import BaseModel
from typing import List, Optional

from apps.web.models.auths import UserResponse

####################
# Forms
####################

class UserInfo(BaseModel):
    id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None

class ChatResponse(BaseModel):
    """
    Chat response model
    """
    id: Optional[str] = None
    user: Optional[UserInfo] = None
    title: Optional[str] = None
    message: Optional[str] = None
    response: Optional[str] = None
    rating: Optional[int] = None
    rating_reason: Optional[str] = None
    rating_comment: Optional[str] = None
    view_chat: Optional[bool] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    page_number: int
    page_size: int

class ChatsTableResponse(BaseModel):
    """
    Chats table response model
    """
    chats: List[ChatResponse]
    page_number: int
    page_size: int
    total_pages: int
    total_chats: int