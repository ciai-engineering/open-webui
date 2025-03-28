import logging
import base64
from pathlib import Path
from typing import List, Optional, Union
from msgraph.graph_service_client import GraphServiceClient
from msgraph.generated.users.item.send_mail.send_mail_post_request_body import SendMailPostRequestBody
from msgraph.generated.models.message import Message
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.recipient import Recipient
from msgraph.generated.models.email_address import EmailAddress
from msgraph.generated.models.file_attachment import FileAttachment
from azure.core.credentials import AccessToken, TokenCredential as AzureTokenCredential

from utils.security import safe_log

logger = logging.getLogger(__name__)

class TokenCredential(AzureTokenCredential):
    def __init__(self, access_token):
        self.access_token = access_token

    def get_token(self, *scopes, **kwargs):
        return AccessToken(self.access_token, 3600)  # 1 hour expiry

def create_file_attachment(file_path: Union[str, Path], name: Optional[str] = None) -> FileAttachment:
    """
    Create a FileAttachment object from a file path
    
    Args:
        file_path: Path to the file to attach
        name: Optional name for the attachment (defaults to file name)
    
    Returns:
        FileAttachment object
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'rb') as f:
        file_content = f.read()
        file_content_base64 = base64.b64encode(file_content).decode("utf-8")
    
    # Use provided name or file name
    attachment_name = name or file_path.name
    
    # Get file extension and determine content type
    file_extension = file_path.suffix.lower()
    safe_log(logger.debug, f"File extension: {file_extension}")
    content_type_map = {
        '.txt': 'text/plain',
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.zip': 'application/zip',
        '.rar': 'application/x-rar-compressed',
    }
    content_type = content_type_map.get(file_extension, 'application/octet-stream')
    safe_log(logger.debug, f"Content type: {content_type}")

    # Create FileAttachment object
    attachment = FileAttachment()
    attachment.name = attachment_name
    attachment.content_type = content_type
    attachment.content_bytes = base64.b64decode(file_content_base64)  # Convert to bytes
    attachment.o_data_type = "#microsoft.graph.fileAttachment"
    safe_log(logger.debug, f"Attachment: {attachment}")
    return attachment

async def send_email_with_attachments(
    access_token: str,
    to_email: str,
    subject: str,
    body: str,
    attachment_paths: Optional[List[str]] = None,
    cc_emails: Optional[List[str]] = None,
    bcc_emails: Optional[List[str]] = None
) -> bool:
    """
    Send email with attachments using Microsoft Graph SDK
    
    Args:
        access_token: Microsoft Graph API access token
        to_email: Recipient email address
        subject: Email subject
        body: Email body content
        attachment_paths: List of file paths to attach
        cc_emails: List of CC email addresses
        bcc_emails: List of BCC email addresses
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    # Create a custom credential that uses the access token
    credential = TokenCredential(access_token)
    
    # Create Graph client with the credential
    graph_client = GraphServiceClient(credentials=credential)
    
    # Create recipients list
    to_recipients = [
        Recipient(
            email_address=EmailAddress(
                address=to_email,
            ),
        ),
    ]
    
    # Add CC recipients if provided
    if cc_emails:
        to_recipients.extend([
            Recipient(
                email_address=EmailAddress(
                    address=cc_email,
                ),
            )
            for cc_email in cc_emails
        ])
    
    # Create BCC recipients if provided
    bcc_recipients = [
        Recipient(
            email_address=EmailAddress(
                address=bcc_email,
            ),
        )
        for bcc_email in (bcc_emails or [])
    ]
    
    # Create the email message
    message = Message(
        subject=subject,
        body=ItemBody(
            content_type=BodyType.Text,
            content=body,
        ),
        to_recipients=to_recipients,
        bcc_recipients=bcc_recipients,
    )
    
    # Add attachments if provided
    if attachment_paths:
        attachments = []
        for file_path in attachment_paths:
            try:
                attachment = create_file_attachment(file_path)
                attachments.append(attachment)
            except Exception as e:
                safe_log(logger.error, f"Error creating attachment from {file_path}: {str(e)}")
                continue
        
        if attachments:
            message.attachments = attachments
    
    # Create the request body
    request_body = SendMailPostRequestBody(
        message=message,
    )
    
    # Send the email
    await graph_client.me.send_mail.post(request_body)
    safe_log(logger.info, f"Email sent successfully to {to_email}")
    return True