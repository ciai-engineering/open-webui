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
    """Graph API 客户端类"""
    settings: SectionProxy
    authorization: str
    refresh_token: str
    client_secret: str
    logger: logging.Logger
    device_code_credential: DeviceCodeCredential
    user_client: GraphServiceClient

    def __init__(self, settings: SectionProxy):
        """
        初始化Graph客户端

        Args:
            settings (SectionProxy): 配置对象，包含client_id、tenant_id等
        """
        self.settings = settings
        self.authorization = settings.get('authorization', '')
        self.refresh_token = settings.get('refresh_token', '')
        self.client_secret = settings.get('client_secret', '')
        self.logger = logging.getLogger(__name__)
        client_id = self.settings["client_id"]
        tenant_id = self.settings["tenant_id"]
        graph_scopes = self.settings["graph_user_scopes"].split(',')  # 将逗号分隔的字符串转换为列表

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
        # 首先验证当前令牌
        is_valid = await self.validate_token()
        
        # 如果令牌无效，尝试刷新
        if not is_valid:
            safe_log(logging.info, "当前令牌无效，尝试刷新...")
            new_access_token, new_refresh_token = await self.refresh_access_token()
            
            if not new_access_token:
                safe_log(logging.error, "无法获取有效令牌")
                raise PermissionError("Failed to refresh token: Unable to obtain valid token")
                
            # 更新令牌
            self.authorization = f"Bearer {new_access_token}"
            if new_refresh_token:
                self.refresh_token = new_refresh_token
            
            # 再次验证令牌
            is_valid = await self.validate_token()
            if not is_valid:
                safe_log(logging.error, "刷新后的令牌验证失败")
                raise PermissionError("Failed to validate token after refresh")
                
            safe_log(logging.info, "令牌刷新成功，继续发送邮件")

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
                attachment_base64 = base64.b64encode(attachment_content).decode("utf-8")
                attachment = FileAttachment(
                    odata_type="#microsoft.graph.fileAttachment",
                    name=attachment_name,
                    content_bytes=base64.urlsafe_b64decode(attachment_base64),
                    content_type="application/pdf",
                )
            message.attachments = []
            message.attachments.append(attachment)

        # Create the request body for sending the email
        request_body = SendMailPostRequestBody()
        request_body.message = message
        request_body.save_to_sent_items = True
        
        try:
            # 使用aiohttp直接发送请求到Graph API
            graph_endpoint = 'https://graph.microsoft.com/v1.0/me/sendMail'
            
            # 提取令牌值
            token = self.authorization
            if token.startswith("Bearer "):
                token = token[7:]  # 移除"Bearer "前缀
            
            # 将Message对象转换为JSON
            email_data = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "Text",
                        "content": leave_body
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": recipient
                            }
                        }
                    ]
                },
                "saveToSentItems": "true"
            }
            
            # 如果有附件，添加到请求中
            if attachment_path and os.path.isfile(attachment_path):
                with open(attachment_path, "rb") as attachment_file:
                    attachment_content = attachment_file.read()
                    attachment_base64 = base64.b64encode(attachment_content).decode("utf-8")
                
                email_data["message"]["attachments"] = [
                    {
                        "@odata.type": "#microsoft.graph.fileAttachment",
                        "name": attachment_name,
                        "contentBytes": attachment_base64,
                        "contentType": "application/pdf"
                    }
                ]
            
            # 调试日志
            if attachment_path and os.path.isfile(attachment_path):
                safe_log(logging.debug, f"附件大小: {os.path.getsize(attachment_path)} 字节")
                
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
                
                async with session.post(graph_endpoint, headers=headers, json=email_data) as response:
                    if response.status == 202 or response.status == 200:
                        # 邮件发送成功
                        safe_log(logging.info, "邮件发送成功")
                        return
                    else:
                        # 邮件发送失败
                        error_msg = await response.text()
                        safe_log(logging.error, f"邮件发送失败，HTTP状态: {response.status}", {"error": error_msg})
                        
                        if response.status == 401:
                            # 授权问题，尝试刷新令牌
                            safe_log(logging.info, "发送邮件时令牌过期，尝试刷新...")
                            new_access_token, new_refresh_token = await self.refresh_access_token()
                            
                            if not new_access_token:
                                raise PermissionError("Failed to refresh token: Unable to obtain valid token after expiration")
                                
                            # 更新令牌并重试
                            self.authorization = f"Bearer {new_access_token}"
                            if new_refresh_token:
                                self.refresh_token = new_refresh_token
                                
                            # 重试发送邮件
                            headers["Authorization"] = f"Bearer {new_access_token}"
                            async with session.post(graph_endpoint, headers=headers, json=email_data) as retry_response:
                                if retry_response.status == 202 or retry_response.status == 200:
                                    safe_log(logging.info, "使用新令牌重试发送邮件成功")
                                    return
                                else:
                                    retry_error = await retry_response.text()
                                    safe_log(logging.error, f"重试发送邮件失败，HTTP状态: {retry_response.status}", {"error": retry_error})
                                    raise PermissionError(f"Failed to send email after token refresh: {retry_error}")
                        elif response.status == 400:
                            # 参数问题
                            raise ValueError(f"邮件参数错误: {error_msg}")
                        else:
                            # 其他错误
                            raise Exception(f"邮件发送错误 (HTTP {response.status}): {error_msg}")
                            
        except ValueError as e:
            safe_log(logging.error, "发送邮件时发生值错误", exception=e)
            raise
        except Exception as e:
            safe_log(logging.error, "发送邮件时发生未知错误", exception=e)
            raise
            
    async def validate_token(self):
        """验证当前令牌是否有效
        
        Returns:
            bool: 令牌是否有效
        """
        if not self.authorization:
            safe_log(logging.error, "无法验证令牌，authorization为空")
            return False
            
        graph_endpoint = 'https://graph.microsoft.com/v1.0/me'
        
        # 确保 authorization 头格式正确
        if not self.authorization.startswith("Bearer "):
            self.authorization = f"Bearer {self.authorization}"
            
        headers = {
            "Authorization": self.authorization
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(graph_endpoint, headers=headers) as response:
                    if response.status == 200:
                        try:
                            response_data = await response.json()
                            if response_data and 'id' in response_data:
                                safe_log(logging.info, "令牌验证成功")
                                return True
                            else:
                                safe_log(logging.error, "令牌验证失败，响应数据格式不正确")
                                return False
                        except ValueError as e:
                            safe_log(logging.error, "令牌验证失败，无法解析JSON响应", exception=e)
                            return False
                    else:
                        error_msg = await response.text()
                        safe_log(logging.error, f"令牌验证失败，HTTP状态: {response.status}", {"error": error_msg})
                        return False
        except Exception as e:
            safe_log(logging.error, "令牌验证过程中发生错误", exception=e)
            return False
            
    async def refresh_access_token(self):
        """刷新访问令牌
        
        Returns:
            tuple: (access_token, refresh_token) 如果刷新成功，否则返回 (None, None)
        """
        if not self.refresh_token or not self.settings.get("client_id") or not self.client_secret:
            safe_log(logging.error, "缺少刷新令牌所需的参数")
            return None, None
            
        try:
            # 构建刷新令牌请求
            token_url = f"https://login.microsoftonline.com/{self.settings['tenant_id']}/oauth2/v2.0/token"
            data = {
                'client_id': self.settings["client_id"],
                'client_secret': self.client_secret,
                'refresh_token': self.refresh_token,
                'grant_type': 'refresh_token',
                'scope': 'https://graph.microsoft.com/.default offline_access'  # 修改 scope 格式
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        new_access_token = result.get('access_token')
                        new_refresh_token = result.get('refresh_token')
                        
                        if new_access_token:
                            safe_log(logging.info, "令牌刷新成功")
                            # 更新当前实例的令牌
                            self.authorization = f"Bearer {new_access_token}"
                            if new_refresh_token:
                                self.refresh_token = new_refresh_token
                            return new_access_token, new_refresh_token
                        else:
                            safe_log(logging.error, "令牌刷新响应中缺少access_token")
                    else:
                        error_text = await response.text()
                        safe_log(logging.error, f"令牌刷新失败，HTTP状态: {response.status}: {{'error': {error_text}}}")
                        
        except Exception as e:
            safe_log(logging.error, "刷新令牌时发生错误", exception=e)
            
        return None, None