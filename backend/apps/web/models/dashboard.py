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
    id: str
    user: UserResponse
    title: str
    message: str
    response: str
    rating: int
    rating_reason: str
    rating_comment: str
    view_chat: bool
    created_at: int
    updated_at: int
    page_number: int
    page_size: int
    total_pages: int
    total_chats: int

class ChatsTableResponse(BaseModel):
    chats: List[ChatResponse]
    page_number: int
    page_size: int
    total_pages: int
    total_chats: int