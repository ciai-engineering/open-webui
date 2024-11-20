from pydantic import BaseModel
from typing import List, Union, Optional
from peewee import *
from playhouse.shortcuts import model_to_dict

import json
import uuid
import time

from apps.web.internal.db import DB

from apps.web.models.auths import (
    SigninForm,
    SignupForm,
    AddUserForm,
    UpdateProfileForm,
    UpdatePasswordForm,
    UserResponse,
    SigninResponse,
    Auths,
    ApiKey,
)

####################
# Forms
####################

class ChatResponse(BaseModel):
    """
    Chat response model
    """
    id: Optional[str] = None
    user: Optional[UserResponse] = None
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