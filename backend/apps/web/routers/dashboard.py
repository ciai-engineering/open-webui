import math
import json
from itertools import chain
from fastapi import APIRouter, Depends
from typing import List, Optional
from utils.utils import get_admin_user
from playhouse.shortcuts import model_to_dict
import logging

from apps.web.models.dashboard import UserInfo, ChatResponse, ChatsTableResponse
from apps.web.models.users import Users
from apps.web.models.chats import Chat, ChatModel

from config import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()

############################
# GetChats
############################

@router.post("/chats", response_model=ChatsTableResponse)
async def get_chats(chat_filter: Optional[ChatResponse] = None, user=Depends(get_admin_user)):
    """
    Get the chats based on the chat_filter
    """
    log.info(f"chat_filter: {chat_filter}. user: {user}")
    conds = Chat.select()

    page_from = 1
    page_to = 10
    # Apply filters if chat_filter is provided
    if chat_filter:
        if chat_filter.id:
            conds = conds.where(Chat.id == chat_filter.id)
        if chat_filter.user and chat_filter.user.id:
            conds = conds.where(Chat.user_id == chat_filter.user.id)
        if chat_filter.title:
            conds = conds.where(Chat.title.contains(chat_filter.title))
        if chat_filter.message:
            conds = conds.where(Chat.chat.contains(chat_filter.message))
        if chat_filter.response:
            conds = conds.where(Chat.chat.contains(chat_filter.response))
        if chat_filter.rating:
            conds = conds.where(Chat.chat.contains(f'"rating": {chat_filter.rating}'))
        if chat_filter.rating_reason:
            conds = conds.where(Chat.chat.contains(chat_filter.rating_reason))
        if chat_filter.rating_comment:
            conds = conds.where(Chat.chat.contains(chat_filter.rating_comment))
        
        # Order and paginate results
        conds = conds.order_by(Chat.updated_at.desc())

        # conditions = conditions.limit(chat_filter.page_size)
        # conditions = conditions.offset((chat_filter.page_number - 1) * chat_filter.page_size)

        page_from = (chat_filter.page_number - 1) * chat_filter.page_size
        page_to = chat_filter.page_number * chat_filter.page_size

    # Convert database models to ChatModel instances
    chats = [ChatModel(**model_to_dict(chat)) for chat in conds]
    chats = list(chain.from_iterable(convert(chat, chat_filter) for chat in chats))

    # Calculate pagination details
    total_chats = len(chats)
    total_pages = math.ceil(total_chats / chat_filter.page_size) if chat_filter else 1

    # Create response object
    chatTableResponse = ChatsTableResponse(
        chats=chats[page_from:page_to],
        page_number=chat_filter.page_number if chat_filter else 1,
        page_size=chat_filter.page_size if chat_filter else 10,
        total_pages=total_pages,
        total_chats=total_chats
    )

    return remove_none_values(chatTableResponse)

def split_chat_message(chat_model: ChatModel) -> List[dict]:
    """
    Split the chat message into question and answer pairs
    """
    chat_json = json.loads(chat_model.chat)
    chat_history = chat_json.get("history", {}).get("messages", {})
    qa_pairs = []
    for message_id, message in chat_history.items():
        if message["role"] == "user":
            question = message["content"]
            answer_id = message["childrenIds"][0] if message["childrenIds"] else None
            answer = chat_history[answer_id]["content"] if answer_id and answer_id in chat_history else ""
            annotation = chat_history[answer_id].get("annotation", {}) if answer_id and answer_id in chat_history else None
            rating = annotation.get("rating", 0) if annotation else 0
            rating_reason = annotation.get("reason", "") if annotation else ""
            rating_comment = annotation.get("comment", "") if annotation else ""
            qa_pairs.append({
                "question": question,
                "answer": answer,
                "rating": rating,
                "rating_reason": rating_reason,
                "rating_comment": rating_comment
            })
    return qa_pairs

def filter_chat_message(chat_response: ChatResponse, chat_filter: Optional[ChatResponse] = None) -> bool:
    """
    Filter the chat message based on the chat_filter
    """
    is_match = True
    if chat_filter.message:
        if chat_filter.message not in chat_response.message:
            is_match = False
    if chat_filter.response:
        if chat_filter.response not in chat_response.response:
            is_match = False
    if chat_filter.rating:
        if chat_filter.rating != chat_response.rating:
            is_match = False
    if chat_filter.rating_reason:
        if chat_filter.rating_reason not in chat_response.rating_reason:
            is_match = False
    if chat_filter.rating_comment:
        if chat_filter.rating_comment not in chat_response.rating_comment:
            is_match = False
    return is_match

def convert(chat_model: ChatModel, chat_filter: Optional[ChatResponse] = None) -> List[ChatResponse]:
    """
    Convert the chat model to chat response
    """
    userModel = Users.get_user_by_id(id=chat_model.user_id)
    user = UserInfo(
        id=userModel.id, 
        email=userModel.email, 
        name=userModel.name, 
        role=userModel.role
    )
    title = chat_model.title.replace("\"", "")
    qa_pairs = split_chat_message(chat_model)

    chat_responses = []
    for qa_pair in qa_pairs:
        chat_response = ChatResponse(
            id=chat_model.id, 
            user=user, 
            title=title, 
            message=qa_pair["question"], 
            response=qa_pair["answer"], 
            rating=qa_pair.get("rating", 0), 
            view_chat=True, 
            rating_reason=qa_pair.get("rating_reason", ""), 
            rating_comment=qa_pair.get("rating_comment", ""), 
            created_at=chat_model.created_at, 
            updated_at=chat_model.updated_at, 
            page_number=0, 
            page_size=0
        )
        if filter_chat_message(chat_response, chat_filter):
            chat_responses.append(chat_response)
    return chat_responses

def remove_none_values(data):
    """
    Remove none values from the data
    """
    if isinstance(data, dict):
        return {k: remove_none_values(v) for k, v in data.items() if v is not None}
    elif isinstance(data, list):
        return [remove_none_values(item) for item in data]
    return data
