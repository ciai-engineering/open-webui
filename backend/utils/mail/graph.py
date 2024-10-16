# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

# <UserAuthConfigSnippet>
import logging
from configparser import SectionProxy
from azure.identity import DeviceCodeCredential
from msgraph import GraphServiceClient
from msgraph.generated.users.item.send_mail.send_mail_post_request_body import (
    SendMailPostRequestBody,
)
from msgraph.generated.models.message import Message
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.recipient import Recipient
from msgraph.generated.models.email_address import EmailAddress

import base64, os
from msgraph.generated.models.attachment import Attachment
from msgraph.generated.models.file_attachment import FileAttachment

from kiota_abstractions.base_request_configuration import BaseRequestConfiguration
from kiota_abstractions.headers_collection import HeadersCollection

from constants import ERROR_MESSAGES


class Graph:
    settings: SectionProxy
    device_code_credential: DeviceCodeCredential
    user_client: GraphServiceClient

    def __init__(self, config: SectionProxy):
        logging.info(f"Initializing Graph client with settings")
        self.settings = config
        client_id = self.settings["client_id"]
        tenant_id = self.settings["tenant_id"]
        graph_scopes = self.settings["graph_user_scopes"]
        self.authorization = self.settings["authorization"]

        # Initialize DeviceCodeCredential with client_id and tenant_id
        self.device_code_credential = DeviceCodeCredential(
            client_id=client_id, tenant_id=tenant_id
        )
        # Initialize GraphServiceClient with DeviceCodeCredential and graph_scopes
        self.user_client = GraphServiceClient(self.device_code_credential, graph_scopes)

    # <sendMailSnippet>
    async def send_leave_mail(
        self, subject: str, leave_body: str, recipient: str, attachment_path: str, attachment_name: str
    ):
        # Create a new message object
        message = Message()
        message.subject = subject

        # Set the body of the message
        message.body = ItemBody()
        message.body.content_type = BodyType.Text
        message.body.content = leave_body

        # Set the recipient of the message
        to_recipient = Recipient()
        to_recipient.email_address = EmailAddress()
        to_recipient.email_address.address = recipient
        message.to_recipients = []
        message.to_recipients.append(to_recipient)

        # Add attachment if the attachment path is valid
        if attachment_path and os.path.isfile(attachment_path):
            with open(attachment_path, "rb") as attachment_file:
                attachment_content = attachment_file.read()
                attachment_base64 = base64.urlsafe_b64encode(attachment_content).decode(
                    "utf-8"
                )
                attachment = FileAttachment(
                    odata_type="#microsoft.graph.fileAttachment",
                    name=attachment_name,
                    content_bytes=base64.urlsafe_b64decode(attachment_base64),
                    content_type="text/plain",
                )
            message.attachments = []
            message.attachments.append(attachment)

        # Create the request body for sending the email
        request_body = SendMailPostRequestBody()
        request_body.message = message
        request_body.save_to_sent_items = True
        requestConfiguration: BaseRequestConfiguration = BaseRequestConfiguration()
        requestConfiguration.headers = HeadersCollection()
        requestConfiguration.headers.add("Authorization", self.authorization)
        try:
            # Send the email using the Graph API
            await self.user_client.me.send_mail.post(
                body=request_body, request_configuration=requestConfiguration
            )
        except ValueError as e:
            logging.error(f"Error sending email: {e}")
            raise PermissionError(message=ERROR_MESSAGES.EMAIL_ERROR)
        except Exception as e:
            logging.error(f"Error sending email: {e}")
            raise e