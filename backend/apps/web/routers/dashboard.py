import math
from itertools import chain
import json
from fastapi import Response, Request
from fastapi import Depends, FastAPI, HTTPException, status
from datetime import datetime, timedelta
from typing import List, Union, Optional
from peewee import fn
from playhouse.shortcuts import model_to_dict

from fastapi import APIRouter
import logging

from apps.web.models.dashboard import ChatResponse, ChatsTableResponse
from apps.web.models.users import Users
from apps.web.models.chats import Chats, Chat, ChatModel

from utils.utils import get_current_user, get_password_hash, get_admin_user
from constants import ERROR_MESSAGES

from config import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()

############################
# GetChats
############################


@router.post("/chats", response_model=ChatsTableResponse)
async def get_chats(chat_filter: Optional[ChatResponse] = None):
    log.info(f"chat_filter: {chat_filter}")
    conditions = Chat.select()
    page_number = 1
    page_size = 10
    total_pages = 1
    total_chats = 0
    if chat_filter:
        if chat_filter.id and chat_filter.id != "":
            conditions = conditions.where(Chat.id.contains(chat_filter.id))
        if chat_filter.title and chat_filter.title != "":
            conditions = conditions.where(Chat.title.contains(chat_filter.title))
        # if chat_filter.user.name and chat_filter.user.name != "":
        #     conditions = conditions.where(Chat.user_id.contains(chat_filter.user.id))
        if chat_filter.message and chat_filter.message != "":
            # conditions = conditions.where(fn.json_extract(Chat.chat, '$.messages[0].content').contains(chat_filter.message))
            conditions = conditions.where(Chat.chat.contains(chat_filter.message))
        if chat_filter.response and chat_filter.response != "":
            conditions = conditions.where(Chat.chat.contains(chat_filter.response))
        if chat_filter.rating and chat_filter.rating != 0:
            conditions = conditions.where(Chat.chat.contains(f'"rating": {chat_filter.rating}'))
        if chat_filter.rating_reason and chat_filter.rating_reason != "":
            conditions = conditions.where(Chat.chat.contains(chat_filter.rating_reason))
        if chat_filter.rating_comment and chat_filter.rating_comment != "":
            conditions = conditions.where(Chat.chat.contains(chat_filter.rating_comment))
        conditions = conditions.order_by(Chat.updated_at.desc())
        conditions = conditions.limit(chat_filter.page_size)
        conditions = conditions.offset((chat_filter.page_number - 1) * chat_filter.page_size)

    chats = [ChatModel(**model_to_dict(chat)) for chat in conditions]
    print(f"chats: {len(chats)}")

    page_number=chat_filter.page_number
    page_size=chat_filter.page_size
    total_pages=math.ceil(len(chats)/chat_filter.page_size)
    total_chats=len(chats)

    chatTableResponse = ChatsTableResponse(
        chats=list(chain.from_iterable(convert(chat) for chat in chats)),
        page_number=page_number,
        page_size=page_size,
        total_pages=total_pages,
        total_chats=total_chats
    )

    return remove_none_values(chatTableResponse)


from apps.web.models.users import Users, UserModel
from apps.web.models.auths import UserResponse


def split_chat_message(chat_model: ChatModel) -> List[dict]:
    chat_json = json.loads(chat_model.chat)
    chat_history = chat_json.get("history", {}).get("messages", {})
    qa_pairs = []
    for message_id, message in chat_history.items():
        if message["role"] == "user":
            question: str = message["content"]
            answer_id = message["childrenIds"][0] if message["childrenIds"] else None
            answer: str = chat_history[answer_id]["content"] if answer_id and answer_id in chat_history else ""
            annotation = chat_history[answer_id].get("annotation", {}) if answer_id and answer_id in chat_history else None
            rating: int = annotation.get("rating", 0) if annotation else 0
            rating_reason: str = annotation.get("rating_reason", "") if annotation else ""
            rating_comment: str = annotation.get("rating_comment", "") if annotation else ""
            qa_pairs.append({"question": question, "answer": answer, "rating": rating, "rating_reason": rating_reason, "rating_comment": rating_comment})
    return qa_pairs


def convert(chat_model: ChatModel) -> List[ChatResponse]:
    id: str = chat_model.id
    userModel: UserModel = Users.get_user_by_id(id=chat_model.user_id)
    user: UserResponse = UserResponse(id=userModel.id, email=userModel.email, name=userModel.name, role=userModel.role, profile_image_url=userModel.profile_image_url, extra_sso="")
    title: str = chat_model.title.replace("\"", "")
    view_chat: bool = True
    created_at: int = chat_model.created_at
    updated_at: int = chat_model.updated_at
    page_number: int = 0
    page_size: int = 0
    total_pages: int = 0
    total_chats: int = 0
    qa_pairs = split_chat_message(chat_model)

    chat_responses = []
    for qa_pair in qa_pairs:
        message = qa_pair["question"]
        response = qa_pair["answer"]
        rating: int = qa_pair.get("rating", 0)
        rating_reason: str = qa_pair.get("rating_reason", "")
        rating_comment: str = qa_pair.get("rating_comment", "")
        chat_response: ChatResponse = ChatResponse(id=id, user=user, title=title, message=message, response=response, rating=rating, view_chat=view_chat, rating_reason=rating_reason, rating_comment=rating_comment, created_at=created_at, updated_at=updated_at, page_number=page_number, page_size=page_size, total_pages=total_pages, total_chats=total_chats)
        chat_responses.append(chat_response)
    return chat_responses


def remove_none_values(data):
    if isinstance(data, dict):
        return {k: remove_none_values(v) for k, v in data.items() if v is not None}
    elif isinstance(data, list):
        return [remove_none_values(item) for item in data]
    else:
        return data
