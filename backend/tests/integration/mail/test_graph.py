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

from utils.mail.graph import Graph
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
        self.tenant_id = "c93272d3-1b07-4b3d-a3b6-19b34a973915"
        self.access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
        self.refresh_token = "refresh_123456789"
        self.client_secret = "client_secret_123"
        
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
        self.graph = Graph(self.settings)
        
        # 设置日志记录器
        self.graph.logger = self.test_logger
        
        # 模拟GraphServiceClient
        self.mock_graph_client = MagicMock()
        self.graph.user_client = self.mock_graph_client

    async def asyncTearDown(self):
        """异步清理测试环境"""
        # 清理日志记录
        self.log_records.clear()
        
        # 移除日志处理器
        self.test_logger.removeHandler(self.log_handler)

    @patch('utils.mail.graph.safe_log')
    @patch('utils.mail.graph.aiohttp.ClientSession')
    async def test_send_leave_mail_logs_securely_on_success(self, mock_client_session, mock_safe_log):
        """测试发送邮件成功时安全记录日志"""
        # 设置authorization
        self.graph.authorization = f"Bearer {self.access_token}"

        # 模拟验证token成功
        mock_validate_response = AsyncMock()
        mock_validate_response.status = 200
        mock_validate_response.json = AsyncMock(return_value={
            'id': 'test_user_id',
            'displayName': 'Test User'
        })

        # 模拟发送邮件成功
        mock_send_response = AsyncMock()
        mock_send_response.status = 202
        mock_send_response.text = AsyncMock(return_value="")

        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.get = AsyncMock(return_value=mock_validate_response)
        mock_session.post = AsyncMock(return_value=mock_send_response)

        mock_client_session.return_value = mock_session

        # 调用send_leave_mail方法
        await self.graph.send_leave_mail(
            "Test Subject",
            "Test Body",
            "recipient@example.com",
            "",  # 空字符串代替None
            ""   # 空字符串代替None
        )

        # 验证日志记录
        mock_safe_log.assert_any_call(logging.info, "令牌验证成功")
        mock_safe_log.assert_any_call(logging.info, "邮件发送成功")

        # 验证敏感信息未被记录
        for call_args in mock_safe_log.call_args_list:
            args, _ = call_args
            log_message = args[1] if len(args) > 1 else ""
            self.assertNotIn(self.access_token, log_message)
            self.assertNotIn(self.refresh_token, log_message)
            self.assertNotIn(self.client_secret, log_message)

    @patch('utils.mail.graph.safe_log')
    @patch('utils.mail.graph.aiohttp.ClientSession')
    async def test_send_leave_mail_logs_securely_on_value_error(self, mock_client_session, mock_safe_log):
        """测试发送邮件出现ValueError时安全记录日志"""
        # 设置authorization
        self.graph.authorization = f"Bearer {self.access_token}"

        # 模拟验证token成功
        mock_validate_response = AsyncMock()
        mock_validate_response.status = 200
        mock_validate_response.json = AsyncMock(return_value={
            'id': 'test_user_id',
            'displayName': 'Test User'
        })

        # 模拟发送邮件失败
        mock_send_response = AsyncMock()
        mock_send_response.status = 400
        mock_send_response.text = AsyncMock(return_value="Error with token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")

        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.get = AsyncMock(return_value=mock_validate_response)
        mock_session.post = AsyncMock(return_value=mock_send_response)

        mock_client_session.return_value = mock_session

        # 调用send_leave_mail方法并捕获异常
        with self.assertRaises(ValueError):
            await self.graph.send_leave_mail(
                "Test Subject",
                "Test Body",
                "recipient@example.com",
                "",  # 空字符串代替None
                ""   # 空字符串代替None
            )

        # 验证日志记录
        mock_safe_log.assert_any_call(logging.info, "令牌验证成功")
        mock_safe_log.assert_any_call(logging.error, "发送邮件失败，HTTP状态: 400", {"error": "Error with token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"})

        # 验证敏感信息未被记录
        for call_args in mock_safe_log.call_args_list:
            args, _ = call_args
            log_message = args[1] if len(args) > 1 else ""
            self.assertNotIn(self.access_token, log_message)
            self.assertNotIn(self.refresh_token, log_message)
            self.assertNotIn(self.client_secret, log_message)

    @patch('utils.mail.graph.safe_log')
    @patch('utils.mail.graph.aiohttp.ClientSession')
    async def test_send_leave_mail_logs_securely_on_general_error(self, mock_client_session, mock_safe_log):
        """测试发送邮件出现一般错误时安全记录日志"""
        # 模拟验证token成功
        mock_validate_response = AsyncMock()
        mock_validate_response.status = 200
        
        # 模拟发送邮件失败
        mock_send_response = AsyncMock()
        mock_send_response.status = 500
        mock_send_response.text = AsyncMock(return_value="Error with token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
        
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.get = AsyncMock()
        mock_session.get.return_value = mock_validate_response
        mock_session.post = AsyncMock()
        mock_session.post.return_value = mock_send_response
        
        mock_client_session.return_value = mock_session
        
        # 调用send_leave_mail方法并捕获异常
        with self.assertRaises(Exception):
            await self.graph.send_leave_mail(
                "Test Subject",
                "Test Body",
                "recipient@example.com",
                "",  # 空字符串代替None
                ""   # 空字符串代替None
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
        """测试刷新token时安全记录日志"""
        # 设置必要的属性
        self.graph.refresh_token = self.refresh_token
        self.graph.client_secret = self.client_secret
        self.graph.settings["client_id"] = self.client_id
        self.graph.settings["tenant_id"] = self.tenant_id

        # 模拟aiohttp.ClientSession
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'access_token': 'new_token_123456789',
            'refresh_token': 'new_refresh_123456789',
            'expires_in': 3600,
            'token_type': 'Bearer'
        })

        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.post = AsyncMock(return_value=mock_response)

        mock_client_session.return_value = mock_session

        # 调用refresh_access_token方法
        access_token, refresh_token = await self.graph.refresh_access_token()

        # 验证结果
        self.assertEqual(access_token, 'new_token_123456789')
        self.assertEqual(refresh_token, 'new_refresh_123456789')

        # 验证日志记录
        mock_safe_log.assert_called_with(logging.info, "令牌刷新成功")

        # 验证敏感信息未被记录
        for call in mock_safe_log.call_args_list:
            args = call[0]
            message = args[1]
            self.assertNotIn('access_token', message)
            self.assertNotIn('refresh_token', message)
            self.assertNotIn('client_secret', message)

    @patch('utils.mail.graph.safe_log')
    @patch('utils.mail.graph.aiohttp.ClientSession')
    async def test_refresh_access_token_logs_securely_on_error(self, mock_client_session, mock_safe_log):
        """测试刷新token出错时安全记录日志"""
        # 模拟aiohttp.ClientSession
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="Error with token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")

        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.post = AsyncMock()
        mock_session.post.return_value = mock_response

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
    @patch('utils.mail.graph.aiohttp.ClientSession')
    async def test_validate_token_logs_securely_when_valid(self, mock_client_session, mock_safe_log):
        """测试验证有效token时安全记录日志"""
        # 设置authorization
        self.graph.authorization = f"Bearer {self.access_token}"

        # 模拟Graph API请求成功
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'id': 'test_user_id',
            'displayName': 'Test User'
        })

        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.get = AsyncMock(return_value=mock_response)

        mock_client_session.return_value = mock_session

        # 调用validate_token方法
        result = await self.graph.validate_token()

        # 验证结果
        self.assertTrue(result)

        # 验证日志记录
        mock_safe_log.assert_called_with(logging.info, "令牌验证成功")

        # 验证敏感信息未被记录
        for call in mock_safe_log.call_args_list:
            args = call[0]
            message = args[1]
            self.assertNotIn('access_token', message)
            self.assertNotIn('refresh_token', message)
            self.assertNotIn('client_secret', message)

    @patch('utils.mail.graph.safe_log')
    @patch('utils.mail.graph.aiohttp.ClientSession')
    async def test_validate_token_logs_securely_when_invalid(self, mock_client_session, mock_safe_log):
        """测试验证无效token时安全记录日志"""
        # 模拟Graph API请求失败
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Token expired")
        
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.get = AsyncMock()
        mock_session.get.return_value = mock_response
        
        mock_client_session.return_value = mock_session
        
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

    @patch('utils.mail.graph.safe_log')
    @patch('utils.mail.graph.aiohttp.ClientSession')
    async def test_send_leave_mail_with_token_refresh(self, mock_client_session, mock_safe_log):
        """测试发送邮件时token过期并成功刷新的情况"""
        # 设置必要的属性
        self.graph.refresh_token = self.refresh_token
        self.graph.client_secret = self.client_secret
        self.graph.settings["client_id"] = self.client_id
        self.graph.settings["tenant_id"] = self.tenant_id

        # 模拟验证token失败
        mock_validate_response = AsyncMock()
        mock_validate_response.status = 401
        mock_validate_response.text = AsyncMock(return_value="Token expired")

        # 模拟token刷新成功
        mock_refresh_response = AsyncMock()
        mock_refresh_response.status = 200
        mock_refresh_response.json = AsyncMock(return_value={
            'access_token': 'new_token_123456789',
            'refresh_token': 'new_refresh_123456789',
            'expires_in': 3600,
            'token_type': 'Bearer'
        })

        # 模拟使用新token发送邮件成功
        mock_send_response = AsyncMock()
        mock_send_response.status = 202
        mock_send_response.text = AsyncMock(return_value="")

        # 配置mock session
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session

        # 设置get和post方法的返回值
        mock_session.get = AsyncMock()
        mock_session.get.side_effect = [
            mock_validate_response,  # 第一次验证token失败
            AsyncMock(status=200, json=AsyncMock(return_value={'id': 'test_user_id'}))  # 第二次验证token成功
        ]

        mock_session.post = AsyncMock()
        mock_session.post.side_effect = [
            mock_refresh_response,  # token刷新成功
            mock_send_response  # 使用新token发送邮件成功
        ]

        mock_client_session.return_value = mock_session

        # 调用send_leave_mail方法
        await self.graph.send_leave_mail(
            "Test Subject",
            "Test Body",
            "recipient@example.com",
            "",  # 空字符串代替None
            ""   # 空字符串代替None
        )

        # 验证日志记录
        mock_safe_log.assert_any_call(logging.info, "令牌验证成功")
        mock_safe_log.assert_any_call(logging.info, "令牌刷新成功")
        mock_safe_log.assert_any_call(logging.info, "邮件发送成功")

        # 验证敏感信息未被记录
        for call in mock_safe_log.call_args_list:
            args = call[0]
            message = args[1]
            self.assertNotIn('access_token', message)
            self.assertNotIn('refresh_token', message)
            self.assertNotIn('client_secret', message)

        # 验证token被更新
        self.assertEqual(self.graph.authorization, "Bearer new_token_123456789")
        self.assertEqual(self.graph.refresh_token, "new_refresh_123456789")

        # 验证发送邮件的调用
        self.assertEqual(mock_session.post.call_count, 2)

        # 验证第一次调用（刷新token）
        first_call = mock_session.post.call_args_list[0]
        self.assertEqual(first_call[1]['url'], f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token")
        self.assertEqual(first_call[1]['data']['client_id'], self.client_id)
        self.assertEqual(first_call[1]['data']['refresh_token'], self.refresh_token)
        self.assertEqual(first_call[1]['data']['client_secret'], self.client_secret)
        self.assertEqual(first_call[1]['data']['grant_type'], 'refresh_token')
        self.assertEqual(first_call[1]['data']['scope'], 'https://graph.microsoft.com/.default offline_access Mail.Send')

        # 验证第二次调用（发送邮件）
        second_call = mock_session.post.call_args_list[1]
        self.assertEqual(second_call[1]['url'], "https://graph.microsoft.com/v1.0/me/sendMail")
        self.assertEqual(second_call[1]['headers']['Authorization'], "Bearer new_token_123456789")
        self.assertEqual(second_call[1]['json']['message']['subject'], "Test Subject")
        self.assertEqual(second_call[1]['json']['message']['body']['content'], "Test Body")
        self.assertEqual(second_call[1]['json']['message']['toRecipients'][0]['emailAddress']['address'], "recipient@example.com")
    
    @patch('utils.mail.graph.safe_log')
    @patch('utils.mail.graph.aiohttp.ClientSession')
    async def test_send_leave_mail_with_multiple_token_refresh(self, mock_client_session, mock_safe_log):
        """测试发送邮件时多次token过期并成功刷新的情况"""
        # 设置必要的属性
        self.graph.refresh_token = self.refresh_token
        self.graph.client_secret = self.client_secret
        self.graph.settings["client_id"] = self.client_id
        self.graph.settings["tenant_id"] = self.tenant_id

        # 模拟验证token失败
        mock_validate_response = AsyncMock()
        mock_validate_response.status = 401
        mock_validate_response.text = AsyncMock(return_value="Token expired")

        # 模拟第一次token刷新成功
        mock_refresh_response1 = AsyncMock()
        mock_refresh_response1.status = 200
        mock_refresh_response1.json = AsyncMock(return_value={
            'access_token': 'new_token_1',
            'refresh_token': 'new_refresh_1',
            'expires_in': 3600,
            'token_type': 'Bearer'
        })

        # 模拟第二次token刷新成功
        mock_refresh_response2 = AsyncMock()
        mock_refresh_response2.status = 200
        mock_refresh_response2.json = AsyncMock(return_value={
            'access_token': 'new_token_2',
            'refresh_token': 'new_refresh_2',
            'expires_in': 3600,
            'token_type': 'Bearer'
        })

        # 模拟使用新token发送邮件成功
        mock_send_response = AsyncMock()
        mock_send_response.status = 202
        mock_send_response.text = AsyncMock(return_value="")

        # 配置mock session
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session

        # 设置get和post方法的返回值
        mock_session.get = AsyncMock()
        mock_session.get.side_effect = [
            mock_validate_response,  # 第一次验证token失败
            AsyncMock(status=200, json=AsyncMock(return_value={'id': 'test_user_id'})),  # 第二次验证token成功
            AsyncMock(status=401, text=AsyncMock(return_value="Token expired")),  # 第三次验证token失败
            AsyncMock(status=200, json=AsyncMock(return_value={'id': 'test_user_id'}))  # 第四次验证token成功
        ]

        mock_session.post = AsyncMock()
        mock_session.post.side_effect = [
            mock_refresh_response1,  # 第一次token刷新成功
            mock_send_response,  # 第一次发送邮件成功
            mock_refresh_response2,  # 第二次token刷新成功
            mock_send_response  # 第二次发送邮件成功
        ]

        mock_client_session.return_value = mock_session

        # 调用send_leave_mail方法
        await self.graph.send_leave_mail(
            "Test Subject",
            "Test Body",
            "recipient@example.com",
            "",  # 空字符串代替None
            ""   # 空字符串代替None
        )

        # 验证日志记录
        mock_safe_log.assert_any_call(logging.info, "令牌验证成功")
        mock_safe_log.assert_any_call(logging.info, "令牌刷新成功")
        mock_safe_log.assert_any_call(logging.info, "邮件发送成功")

        # 验证敏感信息未被记录
        for call in mock_safe_log.call_args_list:
            args = call[0]
            message = args[1]
            self.assertNotIn('new_token_1', message)
        for call_args in mock_safe_log.call_args_list:
            args, _ = call_args
            log_message = args[1] if len(args) > 1 else ""
            self.assertNotIn('new_token_1', log_message)
            self.assertNotIn('new_refresh_1', log_message)
            self.assertNotIn('new_token_2', log_message)
            self.assertNotIn('new_refresh_2', log_message)
            self.assertNotIn(self.client_secret, log_message)

@pytest.mark.asyncio
class IntegrationTestGraph(unittest.TestCase):
    """集成测试类，用于测试与真实Graph API的交互"""
    
    def setUp(self):
        # 获取测试配置
        self.config = get_test_config()
        
        # 创建配置解析器
        config_parser = ConfigParser()
        config_parser.add_section('graph')
        for key, value in self.config.items():
            config_parser['graph'][key] = str(value)
        
        # 获取graph部分的SectionProxy
        self.settings = config_parser['graph']
        
        # 创建Graph实例
        self.graph = Graph(self.settings)
    
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
            
        # 刷新令牌
        new_access_token, new_refresh_token = await self.graph.refresh_access_token()
        
        # 验证令牌刷新成功
        self.assertIsNotNone(new_access_token)
        self.assertIsNotNone(new_refresh_token)
        
        # 验证令牌被更新
        self.assertEqual(self.graph.authorization, f"Bearer {new_access_token}")
        self.assertEqual(self.graph.refresh_token, new_refresh_token)
    
    async def test_validate_token_with_real_api(self):
        """测试使用真实API验证令牌"""
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