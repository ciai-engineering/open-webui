import logging
import json
import time

from .graph import Graph
from .fill_form import FillLeaveForm
from apps.web.models.services import LeaveForm
from apps.web.models.users import Users
from utils.security import safe_log

class Mail:
    graph: Graph

    def __init__(self, client_id: str, tenant_id: str, authorization: str, refresh_token: str = None, client_secret: str = None, user_id: str = None, graph_user_scopes: list[str] = ["Mail.Send"]):
        azure_settings={}
        azure_settings["client_id"] = client_id
        azure_settings["tenant_id"] = tenant_id
        azure_settings["graph_user_scopes"] = graph_user_scopes
        azure_settings["authorization"] = authorization
        azure_settings["refresh_token"] = refresh_token
        azure_settings["client_secret"] = client_secret
        self.graph: Graph = Graph(azure_settings)
        self.user_id = user_id

    async def ensure_valid_token(self):
        """确保令牌有效，必要时刷新
        
        Returns:
            bool: 是否有有效令牌
        """
        # 尝试验证当前令牌
        is_valid = await self.graph.validate_token()
        if is_valid:
            safe_log(logging.info, "当前令牌有效，无需刷新")
            return True
            
        # 令牌无效，尝试刷新
        if self.graph.refresh_token and self.user_id:
            safe_log(logging.info, "当前令牌无效，尝试刷新")
            access_token, refresh_token = await self.graph.refresh_access_token()
            
            if access_token:
                safe_log(logging.info, "令牌刷新成功，更新授权信息")
                # 更新当前实例的令牌
                self.graph.authorization = f"Bearer {access_token}"
                self.graph.refresh_token = refresh_token
                
                # 更新数据库中存储的令牌
                if self.user_id:
                    user = Users.get_user_by_id(self.user_id)
                    if user and user.extra_sso:
                        try:
                            extra_sso_data = json.loads(user.extra_sso)
                            extra_sso_data["access_token"] = access_token
                            extra_sso_data["refresh_token"] = refresh_token
                            extra_sso_data["expires_at"] = time.time() + 3600  # 假设令牌有效期为1小时
                            
                            Users.update_user_by_id(
                                self.user_id, 
                                {"extra_sso": json.dumps(extra_sso_data)}
                            )
                            safe_log(logging.info, "用户令牌已更新", {"user_id": self.user_id})
                        except Exception as e:
                            safe_log(logging.error, "更新用户令牌时出错", exception=e)
                
                return True
                
        safe_log(logging.error, "无法获取有效令牌")
        return False

    async def send_mail(self, subject, body, recipient, form_data: LeaveForm):
        """
        Send an email with a filled leave form as an attachment.

        Args:
            subject (str): The subject of the email.
            body (str): The body content of the email.
            recipient (str): The recipient's email address.
            form_data (LeaveForm): The data to fill in the leave form.
        """
        # 确保令牌有效
        token_valid = await self.ensure_valid_token()
        if not token_valid:
            raise PermissionError("令牌已过期，无法发送邮件。请重新登录。")
            
        # fill the leave form
        template_path = 'utils/mail/leave_template.pdf'
        output_path = 'utils/mail/'

        data = {
                    '{NAME}': form_data.name,
                    '{ID}': form_data.employee_id,
                    '{JOBTITLE}': form_data.job_title,
                    '{DEPT}': form_data.dept,
                    '{LEAVETYPE}': form_data.type_of_leave,
                    '{REMARKS}': form_data.remarks,
                    '{LEAVEFROM}': form_data.leavefrom,
                    '{LEAVETO}': form_data.leaveto,
                    '{DAYS}': form_data.days,
                    '{ADDRESS}': form_data.address,
                    '{TELE}': form_data.tele,
                    '{EMAIL}': form_data.email,
                    '{DATE}': form_data.date,
                }
        # get the form file path
        file_path = FillLeaveForm(template_path, output_path, data).fill_template()
        # make the mail content and send the mail can customize the subject and body
        attachment_path = file_path
        attachment_name = 'Leave_Application_Form.pdf'

        safe_log(logging.info, "发送带附件的邮件", {"recipient": recipient, "attachment": attachment_name})
        await self.graph.send_leave_mail(subject, body, recipient, attachment_path, attachment_name)
        safe_log(logging.info, "邮件发送成功")

    async def send_simple_mail(self, subject, content, recipient):
        """
        Send a simple email without any attachments.

        Args:
            subject (str): The subject of the email.
            content (str): The body content of the email.
            recipient (str): The recipient's email address.
        """
        # 确保令牌有效
        token_valid = await self.ensure_valid_token()
        if not token_valid:
            raise PermissionError("令牌已过期，无法发送邮件。请重新登录。")
            
        safe_log(logging.info, "发送简单邮件", {"recipient": recipient, "subject": subject})
        await self.graph.send_leave_mail(subject, content, recipient, None, None)
        safe_log(logging.info, "邮件发送成功")