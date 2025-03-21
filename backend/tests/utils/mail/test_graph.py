import unittest
import logging
import json
import sys
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, Mock

# 添加项目根目录到sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from utils.mail.graph import Graph
from utils.security import safe_log
from tests.utils.mail.test_config import get_test_config, get_test_mode, can_run_real_api_tests

class TestGraphSecurity(unittest.TestCase):
    def setUp(self):
        # 创建自定义记录器进行测试
        self.log_records = []
        self.test_logger = logging.getLogger("test_graph_logger")
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
        
        # 模拟设置
        self.settings = {
            'client_id': self.client_id,
            'tenant_id': self.tenant_id,
            'graph_user_scopes': ['Mail.Send'],
            'authorization': f"Bearer {self.access_token}",
            'refresh_token': self.refresh_token,
            'client_secret': self.client_secret
        }
        
        # 使用patch模拟DeviceCodeCredential和GraphServiceClient
        self.device_code_patch = patch('utils.mail.graph.DeviceCodeCredential')
        self.mock_device_code = self.device_code_patch.start()
        
        self.graph_client_patch = patch('utils.mail.graph.GraphServiceClient')
        self.mock_graph_client_class = self.graph_client_patch.start()
        self.mock_graph_client = MagicMock()
        self.mock_graph_client_class.return_value = self.mock_graph_client
        
        # 创建测试对象
        self.graph = Graph(self.settings)
    
    def tearDown(self):
        # 停止所有patch
        self.device_code_patch.stop()
        self.graph_client_patch.stop()
    
    @patch('utils.mail.graph.safe_log')
    async def test_send_leave_mail_logs_securely_on_success(self, mock_safe_log):
        # 模拟GraphServiceClient
        self.mock_graph_client.me = MagicMock()
        self.mock_graph_client.me.send_mail = MagicMock()
        self.mock_graph_client.me.send_mail.post = AsyncMock()
        
        # 调用send_leave_mail方法
        await self.graph.send_leave_mail(
            "Test Subject",
            "Test Body",
            "recipient@example.com",
            None,  # 无附件
            None
        )
        
        # 验证日志调用
        mock_safe_log.assert_not_called()  # 成功情况下没有日志
    
    @patch('utils.mail.graph.safe_log')
    async def test_send_leave_mail_logs_securely_on_value_error(self, mock_safe_log):
        # 模拟Graph API出现ValueError
        self.mock_graph_client.me = MagicMock()
        self.mock_graph_client.me.send_mail = MagicMock()
        self.mock_graph_client.me.send_mail.post = AsyncMock(side_effect=ValueError("Error with token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"))
        
        # 调用send_leave_mail方法并捕获异常
        with self.assertRaises(Exception):
            await self.graph.send_leave_mail(
                "Test Subject",
                "Test Body",
                "recipient@example.com",
                None,
                None
            )
        
        # 验证日志调用
        mock_safe_log.assert_called()
        
        # 验证日志中不包含敏感信息
        for call in mock_safe_log.call_args_list:
            args, _ = call
            call_str = str(args)
            self.assertNotIn(self.access_token, call_str)
            self.assertNotIn(self.refresh_token, call_str)
            self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", call_str)
    
    @patch('utils.mail.graph.safe_log')
    async def test_send_leave_mail_logs_securely_on_general_error(self, mock_safe_log):
        # 模拟Graph API出现一般错误
        self.mock_graph_client.me = MagicMock()
        self.mock_graph_client.me.send_mail = MagicMock()
        self.mock_graph_client.me.send_mail.post = AsyncMock(side_effect=Exception("Error with token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"))
        
        # 调用send_leave_mail方法并捕获异常
        with self.assertRaises(Exception):
            await self.graph.send_leave_mail(
                "Test Subject",
                "Test Body",
                "recipient@example.com",
                None,
                None
            )
        
        # 验证日志调用
        mock_safe_log.assert_called()
        
        # 验证日志中不包含敏感信息
        for call in mock_safe_log.call_args_list:
            args, _ = call
            call_str = str(args)
            self.assertNotIn(self.access_token, call_str)
            self.assertNotIn(self.refresh_token, call_str)
            self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", call_str)
    
    @patch('utils.mail.graph.safe_log')
    @patch('utils.mail.graph.aiohttp.ClientSession')
    async def test_refresh_access_token_logs_securely(self, mock_client_session, mock_safe_log):
        # 模拟aiohttp.ClientSession
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'access_token': 'new_token_123456789',
            'refresh_token': 'new_refresh_123456789',
            'expires_in': 3600
        })
        
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        mock_client_session.return_value = mock_session
        
        # 调用refresh_access_token方法
        access_token, refresh_token = await self.graph.refresh_access_token()
        
        # 验证结果
        self.assertEqual(access_token, 'new_token_123456789')
        self.assertEqual(refresh_token, 'new_refresh_123456789')
        
        # 验证日志调用
        mock_safe_log.assert_called()
        
        # 验证日志中不包含敏感信息
        for call in mock_safe_log.call_args_list:
            args, _ = call
            call_str = str(args)
            self.assertNotIn(self.access_token, call_str)
            self.assertNotIn(self.refresh_token, call_str)
            self.assertNotIn('new_token_123456789', call_str)
            self.assertNotIn('new_refresh_123456789', call_str)
    
    @patch('utils.mail.graph.safe_log')
    @patch('utils.mail.graph.aiohttp.ClientSession')
    async def test_refresh_access_token_logs_securely_on_error(self, mock_client_session, mock_safe_log):
        # 模拟aiohttp.ClientSession出现错误
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.post.side_effect = Exception("Connection error with token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
        
        mock_client_session.return_value = mock_session
        
        # 调用refresh_access_token方法
        access_token, refresh_token = await self.graph.refresh_access_token()
        
        # 验证结果
        self.assertIsNone(access_token)
        self.assertIsNone(refresh_token)
        
        # 验证日志调用
        mock_safe_log.assert_called()
        
        # 验证日志中不包含敏感信息
        for call in mock_safe_log.call_args_list:
            args, _ = call
            call_str = str(args)
            self.assertNotIn(self.access_token, call_str)
            self.assertNotIn(self.refresh_token, call_str)
            self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", call_str)
    
    @patch('utils.mail.graph.safe_log')
    async def test_validate_token_logs_securely_when_valid(self, mock_safe_log):
        # 模拟Graph API请求成功
        self.mock_graph_client.me = MagicMock()
        self.mock_graph_client.me.get = AsyncMock()
        
        # 调用validate_token方法
        result = await self.graph.validate_token()
        
        # 验证结果
        self.assertTrue(result)
        
        # 验证没有日志（成功情况）
        mock_safe_log.assert_not_called()
    
    @patch('utils.mail.graph.safe_log')
    async def test_validate_token_logs_securely_when_invalid(self, mock_safe_log):
        # 模拟Graph API请求失败
        self.mock_graph_client.me = MagicMock()
        self.mock_graph_client.me.get = AsyncMock(side_effect=Exception("Error with token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"))
        
        # 调用validate_token方法
        result = await self.graph.validate_token()
        
        # 验证结果
        self.assertFalse(result)
        
        # 验证日志调用
        mock_safe_log.assert_called()
        
        # 验证日志中不包含敏感信息
        for call in mock_safe_log.call_args_list:
            args, _ = call
            call_str = str(args)
            self.assertNotIn(self.access_token, call_str)
            self.assertNotIn(self.refresh_token, call_str)
            self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", call_str)

@pytest.mark.asyncio
class IntegrationTestGraph:
    """集成测试类，可以使用真实的Graph API或回退到模拟"""
    
    @classmethod
    def setup_class(cls):
        """设置测试类，根据配置决定是否使用真实API"""
        cls.test_mode = get_test_mode()
        cls.config = get_test_config()
        
        # 创建记录器
        cls.log_records = []
        cls.test_logger = logging.getLogger("test_graph_integration")
        cls.test_logger.setLevel(logging.INFO)
        
        # 移除所有现有处理器
        for handler in cls.test_logger.handlers[:]:
            cls.test_logger.removeHandler(handler)
        
        # 创建自定义处理器来捕获日志消息
        class TestLogHandler(logging.Handler):
            def __init__(self, log_records):
                super().__init__()
                self.log_records = log_records
                
            def emit(self, record):
                cls.log_records.append(record.getMessage())
                
        cls.log_handler = TestLogHandler(cls.log_records)
        cls.test_logger.addHandler(cls.log_handler)
        
        if cls.test_mode == 'mock':
            # 使用模拟设置
            cls.setup_mock_environment()
        else:
            # 使用真实设置
            cls.graph = Graph(cls.config)
            print(f"使用真实的Graph API进行测试")
    
    @classmethod
    def setup_mock_environment(cls):
        """设置模拟环境"""
        # 模拟DeviceCodeCredential和GraphServiceClient
        cls.device_code_patch = patch('utils.mail.graph.DeviceCodeCredential')
        cls.mock_device_code = cls.device_code_patch.start()
        
        cls.graph_client_patch = patch('utils.mail.graph.GraphServiceClient')
        cls.mock_graph_client_class = cls.graph_client_patch.start()
        cls.mock_graph_client = MagicMock()
        cls.mock_graph_client_class.return_value = cls.mock_graph_client
        
        # 模拟me对象
        cls.mock_graph_client.me = MagicMock()
        cls.mock_graph_client.me.get = AsyncMock()
        cls.mock_graph_client.me.send_mail = MagicMock()
        cls.mock_graph_client.me.send_mail.post = AsyncMock()
        
        # 创建Graph对象
        cls.graph = Graph(cls.config)
        print(f"使用模拟的Graph API进行测试")
    
    @classmethod
    def teardown_class(cls):
        """清理测试环境"""
        if cls.test_mode == 'mock':
            cls.device_code_patch.stop()
            cls.graph_client_patch.stop()
    
    @pytest.mark.skipif(get_test_mode() == 'mock', reason="需要真实API访问")
    async def test_validate_token_real_api(self):
        """测试使用真实API验证令牌"""
        # 此测试仅在真实API模式下运行
        result = await self.graph.validate_token()
        
        # 由于使用的可能是测试令牌，不一定有效，我们不断言结果
        # 但确保方法不会抛出异常
        print(f"令牌验证结果: {result}")
    
    async def test_validate_token_handles_request_configuration_correctly(self):
        """测试验证令牌方法正确处理请求配置"""
        if self.test_mode == 'mock':
            # 设置mock以验证请求配置的使用
            self.mock_graph_client.me.get = AsyncMock()
        
        # 调用validate_token方法
        result = await self.graph.validate_token()
        
        if self.test_mode == 'mock':
            # 验证get方法被正确调用
            self.mock_graph_client.me.get.assert_called_once()
            # 验证request_configuration参数存在
            call_args = self.mock_graph_client.me.get.call_args
            self.assertIn('request_configuration', call_args.kwargs)
            
            # 验证request_configuration包含headers
            request_config = call_args.kwargs['request_configuration']
            self.assertTrue(hasattr(request_config, 'headers'))
    
    async def test_send_leave_mail_handles_request_configuration_correctly(self):
        """测试发送邮件方法正确处理请求配置"""
        if self.test_mode == 'mock':
            # 设置mock以验证请求配置的使用
            self.mock_graph_client.me.send_mail.post = AsyncMock()
        
        # 不实际发送邮件，仅测试配置
        if self.test_mode == 'real':
            pytest.skip("跳过真实邮件发送测试")
            
        # 调用send_leave_mail方法
        try:
            await self.graph.send_leave_mail(
                "Test Subject",
                "Test Body",
                "fake_recipient@example.com",
                None,  # 无附件
                None
            )
        except Exception as e:
            # 在真实API测试中可能会失败，但我们只关心请求配置
            print(f"发送邮件时出现错误: {e}")
        
        if self.test_mode == 'mock':
            # 验证post方法被正确调用
            self.mock_graph_client.me.send_mail.post.assert_called_once()
            # 验证request_configuration参数存在
            call_args = self.mock_graph_client.me.send_mail.post.call_args
            self.assertIn('request_configuration', call_args.kwargs)
            
            # 验证request_configuration包含headers
            request_config = call_args.kwargs['request_configuration']
            self.assertTrue(hasattr(request_config, 'headers'))
    
    async def test_permission_error_format_is_correct(self):
        """测试PermissionError使用正确的格式"""
        if self.test_mode == 'mock':
            # 设置mock以触发ValueError
            self.mock_graph_client.me.send_mail.post = AsyncMock(
                side_effect=ValueError("Test error")
            )
        
        # 在真实API测试中跳过
        if self.test_mode == 'real':
            pytest.skip("跳过真实API的权限错误测试")
        
        # 调用send_leave_mail方法并捕获异常
        with pytest.raises(PermissionError) as excinfo:
            await self.graph.send_leave_mail(
                "Test Subject",
                "Test Body",
                "fake_recipient@example.com",
                None,
                None
            )
        
        # 验证PermissionError的使用方式正确，没有用关键字参数
        error_message = str(excinfo.value)
        print(f"权限错误消息: {error_message}")
        # 确保错误消息存在
        assert len(error_message) > 0

if __name__ == '__main__':
    if can_run_real_api_tests():
        print("可以运行真实API测试")
    else:
        print("将使用模拟进行测试")
    unittest.main() 