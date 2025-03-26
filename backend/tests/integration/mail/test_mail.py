import unittest
import logging
import json
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock
from configparser import ConfigParser

# 添加项目根目录到sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from utils.mail.mail import Mail
from utils.security import safe_log
from utils.mail.graph import Graph

class TestMailSecurity(unittest.TestCase):
    def setUp(self):
        # 创建自定义记录器进行测试
        self.log_records = []
        self.test_logger = logging.getLogger("test_mail_logger")
        self.test_logger.setLevel(logging.INFO)
        
        # 移除所有现有处理器
        for handler in self.test_logger.handlers[:]:
            self.test_logger.removeHandler(handler)
        
        # 创建自定义处理器来捕获日志消息
        class TestLogHandler(logging.Handler):
            def __init__(self, log_records):
                super().__init__()
                self.log_records = log_records
                
            def emit(self, record):
                self.log_records.append(record.getMessage())
                
        self.log_handler = TestLogHandler(self.log_records)
        self.test_logger.addHandler(self.log_handler)
        
        # 模拟数据
        self.client_id = "test_client_id"
        self.tenant_id = "test_tenant_id"
        self.access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
        self.refresh_token = "refresh_123456789"
        self.client_secret = "client_secret_123"
        self.user_id = "test_user_id"
        
        # 创建配置解析器
        config = ConfigParser()
        config.add_section('graph')
        config['graph']['client_id'] = self.client_id
        config['graph']['tenant_id'] = self.tenant_id
        config['graph']['graph_user_scopes'] = 'Mail.Send'
        config['graph']['authorization'] = f"Bearer {self.access_token}"
        config['graph']['refresh_token'] = self.refresh_token
        config['graph']['client_secret'] = self.client_secret
        
        # 获取graph部分的SectionProxy
        self.settings = config['graph']
        
        # 创建Graph实例
        self.mock_graph = MagicMock(spec=Graph)
        self.mock_graph.authorization = f"Bearer {self.access_token}"
        self.mock_graph.refresh_token = self.refresh_token
        
        # 创建Mail实例
        self.mail = Mail(
            client_id=self.client_id,
            tenant_id=self.tenant_id,
            authorization=f"Bearer {self.access_token}",
            refresh_token=self.refresh_token,
            client_secret=self.client_secret,
            user_id=self.user_id
        )
        self.mail.graph = self.mock_graph
    
    def tearDown(self):
        """清理测试环境"""
        # 移除日志处理器
        self.test_logger.removeHandler(self.log_handler)
        # 清空日志记录
        self.log_records.clear()
    
    @patch('utils.mail.mail.safe_log')
    async def test_ensure_valid_token_logs_securely_when_valid(self, mock_safe_log):
        # 模拟Graph.validate_token返回True（令牌有效）
        self.mock_graph.validate_token = AsyncMock(return_value=True)
        
        # 调用确保令牌有效方法
        result = await self.mail.ensure_valid_token()
        
        # 验证结果
        self.assertTrue(result)
        
        # 验证safe_log被正确调用，且不包含令牌
        mock_safe_log.assert_called()
        args, _ = mock_safe_log.call_args
        self.assertEqual(args[1], "当前令牌有效，无需刷新")
        
        # 确保敏感信息不在日志中
        for call in mock_safe_log.call_args_list:
            args, _ = call
            call_str = str(args)
            self.assertNotIn(self.access_token, call_str)
            self.assertNotIn(self.refresh_token, call_str)
    
    @patch('utils.mail.mail.safe_log')
    @patch('utils.mail.mail.Users')
    async def test_ensure_valid_token_logs_securely_when_refresh(self, mock_users, mock_safe_log):
        # 模拟graph.validate_token返回False（令牌无效）
        self.mock_graph.validate_token = AsyncMock(return_value=False)
        
        # 模拟graph.refresh_access_token成功返回新令牌
        new_token = "new_token_123456789"
        new_refresh = "new_refresh_123456789"
        self.mock_graph.refresh_access_token = AsyncMock(return_value=(new_token, new_refresh))
        
        # 模拟Users.get_user_by_id
        mock_user = MagicMock()
        mock_user.extra_sso = json.dumps({"access_token": self.access_token})
        mock_users.get_user_by_id.return_value = mock_user
        
        # 调用确保令牌有效方法
        result = await self.mail.ensure_valid_token()
        
        # 验证结果
        self.assertTrue(result)
        
        # 验证令牌被更新
        self.assertEqual(self.mock_graph.authorization, f"Bearer {new_token}")
        self.assertEqual(self.mock_graph.refresh_token, new_refresh)
        
        # 验证safe_log被正确调用
        self.assertTrue(mock_safe_log.called)
        
        # 验证所有日志调用都不包含令牌
        for call in mock_safe_log.call_args_list:
            args, _ = call
            call_str = str(args)
            self.assertNotIn(self.access_token, call_str)
            self.assertNotIn(self.refresh_token, call_str)
            self.assertNotIn(new_token, call_str)
            self.assertNotIn(new_refresh, call_str)
    
    @patch('utils.mail.mail.safe_log')
    async def test_ensure_valid_token_logs_securely_when_refresh_fails(self, mock_safe_log):
        # 模拟graph.validate_token返回False（令牌无效）
        self.mock_graph.validate_token = AsyncMock(return_value=False)
        
        # 模拟graph.refresh_access_token失败
        self.mock_graph.refresh_access_token = AsyncMock(return_value=(None, None))
        
        # 调用确保令牌有效方法
        result = await self.mail.ensure_valid_token()
        
        # 验证结果
        self.assertFalse(result)
        
        # 验证日志调用
        mock_safe_log.assert_called()
        
        # 验证错误日志被安全记录
        error_logs = [call for call in mock_safe_log.call_args_list if "无法获取有效令牌" in str(call)]
        self.assertTrue(len(error_logs) > 0)
        
        # 确保所有日志调用都不包含令牌
        for call in mock_safe_log.call_args_list:
            args, _ = call
            call_str = str(args)
            self.assertNotIn(self.access_token, call_str)
            self.assertNotIn(self.refresh_token, call_str)
    
    @patch('utils.mail.mail.safe_log')    
    @patch('utils.mail.mail.Mail.ensure_valid_token')
    async def test_send_mail_logs_securely(self, mock_ensure_valid_token, mock_safe_log):
        # 模拟ensure_valid_token返回True
        mock_ensure_valid_token.return_value = True
        
        # 模拟FillLeaveForm
        with patch('utils.mail.mail.FillLeaveForm') as mock_fill_form:
            mock_fill_instance = MagicMock()
            mock_fill_instance.fill_template.return_value = "test_file_path.pdf"
            mock_fill_form.return_value = mock_fill_instance
            
            # 模拟发送邮件
            self.mock_graph.send_leave_mail = AsyncMock()
            
            # 模拟LeaveForm数据
            mock_form_data = MagicMock()
            mock_form_data.name = "Test User"
            mock_form_data.employee_id = "EMP123"
            mock_form_data.job_title = "Engineer"
            mock_form_data.dept = "IT"
            mock_form_data.type_of_leave = "Annual Leave"
            mock_form_data.remarks = "Vacation"
            mock_form_data.leavefrom = "01-05-23"
            mock_form_data.leaveto = "10-05-23"
            mock_form_data.days = "10"
            mock_form_data.address = "123 Street"
            mock_form_data.tele = "123-456-7890"
            mock_form_data.email = "test@example.com"
            mock_form_data.date = "01-05-23"
            
            # 发送邮件
            await self.mail.send_mail(
                "Test Subject", 
                "Test Body", 
                "recipient@example.com", 
                mock_form_data
            )
            
            # 验证日志调用
            mock_safe_log.assert_called()
            
            # 验证日志中不包含敏感信息
            for call in mock_safe_log.call_args_list:
                args, _ = call
                call_str = str(args)
                self.assertNotIn(self.access_token, call_str)
                self.assertNotIn(self.refresh_token, call_str)
                
            # 验证日志内容
            log_msgs = [str(call) for call in mock_safe_log.call_args_list]
            self.assertTrue(any("发送带附件的邮件" in msg for msg in log_msgs))
            self.assertTrue(any("邮件发送成功" in msg for msg in log_msgs))

    @patch('utils.mail.mail.safe_log')    
    @patch('utils.mail.mail.Mail.ensure_valid_token')
    async def test_send_mail_handles_permission_error_correctly(self, mock_ensure_valid_token, mock_safe_log):
        """测试send_mail方法正确处理令牌失效情况"""
        # 模拟ensure_valid_token返回False
        mock_ensure_valid_token.return_value = False
        
        # 模拟LeaveForm数据
        mock_form_data = MagicMock()
        mock_form_data.name = "Test User"
        mock_form_data.employee_id = "EMP123"
        
        # 发送邮件应该引发PermissionError
        with self.assertRaises(PermissionError) as context:
            await self.mail.send_mail(
                "Test Subject", 
                "Test Body", 
                "recipient@example.com", 
                mock_form_data
            )
        
        # 验证异常消息
        self.assertTrue("令牌已过期" in str(context.exception))
        
        # 确保send_leave_mail没有被调用
        self.mock_graph.send_leave_mail.assert_not_called()
    
    @patch('utils.mail.mail.safe_log')    
    @patch('utils.mail.mail.Mail.ensure_valid_token')
    async def test_send_simple_mail_handles_permission_error_correctly(self, mock_ensure_valid_token, mock_safe_log):
        """测试send_simple_mail方法正确处理令牌失效情况"""
        # 模拟ensure_valid_token返回False
        mock_ensure_valid_token.return_value = False
        
        # 发送邮件应该引发PermissionError
        with self.assertRaises(PermissionError) as context:
            await self.mail.send_simple_mail(
                "Test Subject", 
                "Test Content", 
                "recipient@example.com"
            )
        
        # 验证异常消息
        self.assertTrue("令牌已过期" in str(context.exception))
        
        # 确保send_leave_mail没有被调用
        self.mock_graph.send_leave_mail.assert_not_called()

    @patch('utils.mail.mail.safe_log')    
    @patch('utils.mail.mail.Mail.ensure_valid_token')
    async def test_send_mail_propagates_graph_error(self, mock_ensure_valid_token, mock_safe_log):
        """测试send_mail方法正确传播Graph API的错误"""
        # 模拟ensure_valid_token返回True
        mock_ensure_valid_token.return_value = True
        
        # 模拟FillLeaveForm
        with patch('utils.mail.mail.FillLeaveForm') as mock_fill_form:
            mock_fill_instance = MagicMock()
            mock_fill_instance.fill_template.return_value = "test_file_path.pdf"
            mock_fill_form.return_value = mock_fill_instance
            
            # 模拟Graph API抛出异常
            permission_error = PermissionError("邮件发送权限不足")
            self.mock_graph.send_leave_mail = AsyncMock(side_effect=permission_error)
            
            # 模拟LeaveForm数据
            mock_form_data = MagicMock()
            mock_form_data.name = "Test User"
            mock_form_data.employee_id = "EMP123"
            mock_form_data.job_title = "Engineer"
            mock_form_data.dept = "IT"
            mock_form_data.type_of_leave = "Annual Leave"
            mock_form_data.remarks = "Vacation"
            mock_form_data.leavefrom = "01-05-23"
            mock_form_data.leaveto = "10-05-23"
            mock_form_data.days = "10"
            mock_form_data.address = "123 Street"
            mock_form_data.tele = "123-456-7890"
            mock_form_data.email = "test@example.com"
            mock_form_data.date = "01-05-23"
            
            # 发送邮件应该传播异常
            with self.assertRaises(PermissionError) as context:
                await self.mail.send_mail(
                    "Test Subject", 
                    "Test Body", 
                    "recipient@example.com", 
                    mock_form_data
                )
            
            # 验证异常是否原样传播
            self.assertEqual(str(context.exception), "邮件发送权限不足")

    @patch('utils.mail.mail.safe_log')    
    @patch('utils.mail.mail.Mail.ensure_valid_token')
    async def test_send_simple_mail_logs_securely(self, mock_ensure_valid_token, mock_safe_log):
        """测试send_simple_mail方法的日志记录安全性"""
        # 模拟ensure_valid_token返回True
        mock_ensure_valid_token.return_value = True
        
        # 模拟发送邮件
        self.mock_graph.send_leave_mail = AsyncMock()
        
        # 发送简单邮件
        await self.mail.send_simple_mail(
            "Test Subject", 
            "Test Content", 
            "recipient@example.com"
        )
        
        # 验证日志调用
        mock_safe_log.assert_called()
        
        # 验证日志中不包含敏感信息
        for call in mock_safe_log.call_args_list:
            args, _ = call
            log_message = args[0]
            self.assertNotIn(self.access_token, log_message)
            self.assertNotIn(self.refresh_token, log_message)
            self.assertNotIn(self.client_secret, log_message)
        
        # 验证日志内容
        log_msgs = [str(call) for call in mock_safe_log.call_args_list]
        self.assertTrue(any("发送简单邮件" in msg for msg in log_msgs))
        self.assertTrue(any("邮件发送成功" in msg for msg in log_msgs))
        
        # 验证send_leave_mail的调用
        self.mock_graph.send_leave_mail.assert_called_once_with(
            "Test Subject", 
            "Test Content", 
            "recipient@example.com",
            "",  # 空字符串代替None
            ""   # 空字符串代替None
        )

if __name__ == '__main__':
    unittest.main() 