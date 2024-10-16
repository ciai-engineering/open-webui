import logging

from .graph import Graph
from .fill_form import FillLeaveForm
from apps.web.models.services import LeaveForm

class Mail:
    graph: Graph

    def __init__(self, client_id: str, tenant_id: str, authorization: str, graph_user_scopes: list[str] = ["Mail.Send"]):
        azure_settings={}
        azure_settings["client_id"] = client_id
        azure_settings["tenant_id"] = tenant_id
        azure_settings["graph_user_scopes"] = graph_user_scopes
        azure_settings["authorization"] = authorization
        self.graph: Graph = Graph(azure_settings)

    async def send_mail(self, subject, body, recipient, form_data: LeaveForm):
        """
        Send an email with a filled leave form as an attachment.

        Args:
            subject (str): The subject of the email.
            body (str): The body content of the email.
            recipient (str): The recipient's email address.
            form_data (LeaveForm): The data to fill in the leave form.
        """
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

        logging.info("Sending email...")
        await self.graph.send_leave_mail(subject, body, recipient, attachment_path, attachment_name)
        logging.info("Success")

    async def send_simple_mail(self, subject, content, recipient):
        """
        Send a simple email without any attachments.

        Args:
            subject (str): The subject of the email.
            content (str): The body content of the email.
            recipient (str): The recipient's email address.
        """
        logging.info("Sending simple email...")
        await self.graph.send_leave_mail(subject, content, recipient, None, None)
        logging.info("Success")