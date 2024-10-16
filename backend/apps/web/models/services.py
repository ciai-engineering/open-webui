from pydantic import BaseModel
import logging

from config import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# Leave Forms
####################


class LeaveResponse(BaseModel):
    email: str
    subject: str
    recipient: str


class LeaveForm(BaseModel):
    name: str
    employee_id: str
    job_title: str
    dept: str
    type_of_leave: str
    remarks: str
    leavefrom: str
    leaveto: str
    days: str
    address: str
    tele: str
    email: str
    date: str

####################
# Hr Docs Forms
####################

class HrDocsResponse(BaseModel):
    email: str
    subject: str
    recipient: str


class HrDocsForm(BaseModel):
    name: str
    employee_id: str
    job_title: str
    dept: str
    type_of_document: int
    purpose: str
    language: str
    addressee: str
    email: str
    date: str