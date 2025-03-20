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

import base64, os, time, aiohttp
from msgraph.generated.models.attachment import Attachment
from msgraph.generated.models.file_attachment import FileAttachment

from kiota_abstractions.base_request_configuration import BaseRequestConfiguration
from kiota_abstractions.headers_collection import HeadersCollection

from constants import ERROR_MESSAGES
from utils.security import safe_log


class Graph:
    settings: SectionProxy
    device_code_credential: DeviceCodeCredential
    user_client: GraphServiceClient

    def __init__(self, config: SectionProxy):
        safe_log(logging.info, "初始化Graph客户端")
        self.settings = config
        client_id = self.settings["client_id"]
        tenant_id = self.settings["tenant_id"]
        graph_scopes = self.settings["graph_user_scopes"]
        self.authorization = self.settings["authorization"]
        self.refresh_token = self.settings.get("refresh_token", None)
        self.client_secret = self.settings.get("client_secret", None)

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
            safe_log(logging.error, "发送邮件时发生值错误", exception=e)
            raise PermissionError(message=ERROR_MESSAGES.EMAIL_ERROR)
        except Exception as e:
            safe_log(logging.error, "发送邮件时发生错误", exception=e)
            raise e
            
    async def refresh_access_token(self):
        """刷新访问令牌
        
        Returns:
            tuple: (access_token, refresh_token) - 新的访问令牌和刷新令牌
        """
        if not self.refresh_token or not self.settings["client_id"] or not self.client_secret:
            safe_log(logging.error, "无法刷新令牌，缺少必要的参数")
            return None, None
            
        token_endpoint = f"https://login.microsoftonline.com/{self.settings['tenant_id']}/oauth2/v2.0/token"
        
        data = {
            'client_id': self.settings["client_id"],
            'scope': 'https://graph.microsoft.com/.default offline_access Mail.Send',
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token',
            'client_secret': self.client_secret
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(token_endpoint, data=data) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        safe_log(logging.info, "令牌刷新成功")
                        return token_data['access_token'], token_data.get('refresh_token', self.refresh_token)
                    else:
                        safe_log(logging.error, "令牌刷新失败", {"status": response.status})
                        return None, None
        except Exception as e:
            safe_log(logging.error, "令牌刷新过程中发生错误", exception=e)
            return None, None
            
    async def validate_token(self):
        """验证当前令牌是否有效
        
        Returns:
            bool: 令牌是否有效
        """
        try:
            # 尝试执行一个简单的Graph API请求来验证令牌
            requestConfiguration = BaseRequestConfiguration()
            requestConfiguration.headers = HeadersCollection()
            requestConfiguration.headers.add("Authorization", self.authorization)
            
            # 使用一个轻量级请求检查令牌
            await self.user_client.me.get(request_configuration=requestConfiguration)
            return True
        except Exception as e:
            safe_log(logging.warning, "令牌验证失败", exception=e)
            return False