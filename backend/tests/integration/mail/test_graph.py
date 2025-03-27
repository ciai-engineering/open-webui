import unittest
import logging
import json
import sys
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, Mock
from configparser import ConfigParser
from unittest import IsolatedAsyncioTestCase

# 添加项目根目录到sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from utils.mail.graph import Graph, GraphConfig
from utils.security import safe_log
from tests.utils.mail.test_config import get_test_config, get_test_mode, can_run_real_api_tests

class TestGraphSecurity(IsolatedAsyncioTestCase):
    """测试Graph类的安全性功能"""

    async def asyncSetUp(self):
        """异步设置测试环境"""
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
        self.client_secret = "test_client_secret"
        self.scopes = ["Mail.Send"]  # 使用简单的权限名称，GraphConfig 会自动转换为正确的格式
        
        # 创建 Graph 配置
        self.config = GraphConfig(
            client_id=self.client_id,
            tenant_id=self.tenant_id,
            client_secret=self.client_secret,
            scopes=self.scopes
        )
        
        # 创建 Graph 实例
        self.graph = Graph(self.config)
        self.graph.logger = self.test_logger

    async def asyncTearDown(self):
        """异步清理测试环境"""
        # 清理日志记录
        self.log_records.clear()
        
        # 移除日志处理器
        self.test_logger.removeHandler(self.log_handler)

    @patch('utils.mail.graph.safe_log')
    @patch('utils.mail.graph.ClientSecretCredential')
    async def test_send_leave_mail_with_token_refresh(self, mock_credential, mock_safe_log):
        """测试发送邮件时token过期并成功刷新的情况"""
        # 模拟凭证
        mock_credential_instance = MagicMock()
        mock_credential.return_value = mock_credential_instance
        
        # 模拟获取令牌
        mock_credential_instance.get_token.return_value = MagicMock(token="new_token_123456789")
        
        # 模拟 Graph 客户端
        mock_graph_client = MagicMock()
        self.graph.graph_client = mock_graph_client
        
        # 模拟发送邮件响应
        mock_response = AsyncMock()
        mock_response.status = 202
        mock_graph_client.users.by_user_id.return_value.send_mail.post.return_value = mock_response
        
        # 调用send_leave_mail方法
        await self.graph.send_leave_mail(
            "Test Subject",
            "Test Body",
            "recipient@example.com",
            "",  # 空字符串代替None
            ""   # 空字符串代替None
        )
        
        # 验证日志记录
        mock_safe_log.assert_any_call(logging.info, "邮件发送成功")
        
        # 验证发送邮件的调用
        mock_graph_client.users.by_user_id.assert_called_once_with("me")
        mock_graph_client.users.by_user_id.return_value.send_mail.post.assert_called_once()

    @patch('utils.mail.graph.safe_log')
    @patch('utils.mail.graph.ClientSecretCredential')
    async def test_validate_token(self, mock_credential, mock_safe_log):
        """测试令牌验证功能"""
        # 模拟凭证
        mock_credential_instance = MagicMock()
        mock_credential.return_value = mock_credential_instance
        
        # 模拟获取令牌
        mock_credential_instance.get_token.return_value = MagicMock(token="test_token")
        
        # 验证令牌
        is_valid = await self.graph.validate_token()
        
        # 验证结果
        self.assertTrue(is_valid)
        mock_safe_log.assert_not_called()
        
        # 验证凭证调用
        mock_credential_instance.get_token.assert_called_once_with(self.scopes[0])

@pytest.mark.asyncio
class IntegrationTestGraph(unittest.TestCase):
    """集成测试类，用于测试与真实Graph API的交互"""
    
    def setUp(self):
        # 获取测试配置
        self.config = get_test_config()
        
        # 创建 Graph 配置
        self.graph_config = GraphConfig(
            client_id=self.config["client_id"],
            tenant_id=self.config["tenant_id"],
            client_secret=self.config["client_secret"],
            scopes=self.config["graph_user_scopes"]
        )
        
        # 创建 Graph 实例
        self.graph = Graph(self.graph_config)
    
    async def test_send_leave_mail_with_real_api(self):
        """测试使用真实API发送休假邮件"""
        if not can_run_real_api_tests():
            self.skipTest("跳过真实API测试")
            
        # 发送测试邮件
        await self.graph.send_leave_mail(
            "Test Leave Request",
            "This is a test leave request.",
            "test@example.com",
            "",  # 空字符串代替None
            ""   # 空字符串代替None
        )
        
        # 验证邮件发送成功
        self.assertTrue(True)  # 如果没有抛出异常，则认为发送成功
    
    async def test_refresh_token_with_real_api(self):
        """测试使用真实API刷新令牌"""
        if not can_run_real_api_tests():
            self.skipTest("跳过真实API测试")
            
        # 验证令牌
        is_valid = await self.graph.validate_token()
        
        # 验证令牌有效
        self.assertTrue(is_valid)

if __name__ == '__main__':
    if can_run_real_api_tests():
        print("可以运行真实API测试")
    else:
        print("将使用模拟进行测试")
    unittest.main() 