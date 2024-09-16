from fastapi import Depends, FastAPI, HTTPException, status
from datetime import datetime, timedelta
from typing import List, Union, Optional

from fastapi import APIRouter
from pydantic import BaseModel
import json

from apps.web.models.documents import (
    Documents,
    DocumentForm,
    DocumentUpdateForm,
    DocumentModel,
    DocumentResponse,
)

from apps.web.models.staffs import Staffs
from config import (
    CHROMA_CLIENT,
    SRC_LOG_LEVELS
)

from utils.utils import get_current_user, get_admin_user
from constants import ERROR_MESSAGES

import logging
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()

############################
# GetDocuments
############################

MAP_TAGS = {
    "faculty": ["faculty", "common"],
    "staff": ["staff", "common"]
}

def get_documents_by_user_role(user):
    if user.role == "admin":
        log.info("Admin user. Getting all documents")
        return Documents.get_docs()
    
    staff = Staffs.get_staff_by_email(user.email.lower())
    if not staff:
        log.warning(f"Staff not found for user '{user.email}'. Returning documents created by this user.")
        return Documents.get_doc_by_user_id(user.id)
    
    log.info(f"Staff found for user '{user.email}'. Getting documents by employee type '{staff['emp_type']}'.")
    employee_type = staff['emp_type'].lower().strip()
    tags = MAP_TAGS.get(employee_type, [])
    log.info(f"Employee type: {employee_type}. Tags: {tags}")
    return Documents.get_docs_by_tags(tags)

@router.get("/", response_model=List[DocumentResponse])
async def get_documents(user=Depends(get_current_user)):
    doc_db = get_documents_by_user_role(user)
    log.info(f"The number of documents selected: {len(doc_db)}. doc_db: {doc_db}")

    return [
        DocumentResponse(
            **{
                **doc.model_dump(),
                "content": json.loads(doc.content or "{}"),
            }
        )
        for doc in doc_db
    ]


############################
# CreateNewDoc
############################


@router.post("/create", response_model=Optional[DocumentResponse])
async def create_new_doc(form_data: DocumentForm, user=Depends(get_admin_user)):
    doc = Documents.get_doc_by_name(form_data.name)
    if doc == None:
        doc = Documents.insert_new_doc(user.id, form_data)

        if doc:
            return DocumentResponse(
                **{
                    **doc.model_dump(),
                    "content": json.loads(doc.content if doc.content else "{}"),
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.FILE_EXISTS,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NAME_TAG_TAKEN,
        )


############################
# GetDocByName
############################


@router.get("/name/{name}", response_model=Optional[DocumentResponse])
async def get_doc_by_name(name: str, user=Depends(get_current_user)):
    doc = Documents.get_doc_by_name(name)

    if doc:
        return DocumentResponse(
            **{
                **doc.model_dump(),
                "content": json.loads(doc.content if doc.content else "{}"),
            }
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# TagDocByName
############################


class TagItem(BaseModel):
    name: str


class TagDocumentForm(BaseModel):
    name: str
    tags: List[dict]


@router.post("/name/{name}/tags", response_model=Optional[DocumentResponse])
async def tag_doc_by_name(form_data: TagDocumentForm, user=Depends(get_current_user)):
    doc = Documents.update_doc_content_by_name(form_data.name, {"tags": form_data.tags})

    if doc:
        return DocumentResponse(
            **{
                **doc.model_dump(),
                "content": json.loads(doc.content if doc.content else "{}"),
            }
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

@router.post("/filter/tags", response_model=List[DocumentResponse])
async def filter_docs_by_tags(tags: List[str], user=Depends(get_current_user)):
    log.info(f"tags: {tags}")
    filtered_docs = [
        DocumentResponse(
            **{
                **doc.model_dump(),
                "content": json.loads(doc.content if doc.content else "{}"),
            }
        )
        for doc in Documents.get_docs_by_tags(tags)
    ]
    log.info(f"The number of documents selected: {len(filtered_docs)}")
    return filtered_docs


############################
# UpdateDocByName
############################


@router.post("/name/{name}/update", response_model=Optional[DocumentResponse])
async def update_doc_by_name(
    name: str, form_data: DocumentUpdateForm, user=Depends(get_admin_user)
):
    log.info(f"Updating document {name}")
    doc = Documents.update_doc_by_name(name, form_data)
    if doc:
        return DocumentResponse(
            **{
                **doc.model_dump(),
                "content": json.loads(doc.content if doc.content else "{}"),
            }
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NAME_TAG_TAKEN,
        )


############################
# DeleteDocByName
############################


@router.delete("/name/{name}/delete", response_model=bool)
async def delete_doc_by_name(name: str, user=Depends(get_admin_user)):
    doc = Documents.get_doc_by_name(name)
    if doc:
        collection_name = doc.collection_name
        log.debug(f"Deleting vector data of the collection {collection_name} of the document {name}")
        result = CHROMA_CLIENT.delete_collection(name=collection_name)
    
    log.debug(f"Deleting file and metadata of the document {name}")
    result = Documents.delete_doc_by_name(name)
    if result:
        log.info(f"Deleted source file and metadata of the document {name} successfully")
    return result
