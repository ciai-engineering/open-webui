import unittest
import logging
import json
import sys
import os
import asyncio
import aiohttp
from unittest.mock import patch, MagicMock, AsyncMock
from configparser import ConfigParser

# 添加项目根目录到sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.mail.graph import Graph
from utils.security import safe_log

class TestGraphTokenEdgeCases(unittest.TestCase):
    """测试Graph类令牌处理的边界情况"""

    async def asyncSetUp(self):
        """异步设置测试环境"""
        # 创建自定义记录器进行测试
        self.log_records = []
        self.test_logger = logging.getLogger("test_graph_token_logger")
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
        self.graph.logger = self.test_logger

    async def asyncTearDown(self):
        """异步清理测试环境"""
        # 清理日志记录
        self.log_records.clear()
        
        # 移除日志处理器
        self.test_logger.removeHandler(self.log_handler)

    @patch('utils.mail.graph.safe_log')
    @patch('utils.mail.graph.aiohttp.ClientSession')
    async def test_token_refresh_with_invalid_response(self, mock_client_session, mock_safe_log):
        """测试令牌刷新时收到无效响应的情况"""
        # 模拟无效的响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'access_token': None,  # 无效的访问令牌
            'refresh_token': None,  # 无效的刷新令牌
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
        self.assertIsNone(access_token)
        self.assertIsNone(refresh_token)

        # 验证日志记录
        mock_safe_log.assert_called_with(logging.error, "令牌刷新失败：响应中缺少必要的令牌信息")

    @patch('utils.mail.graph.safe_log')
    @patch('utils.mail.graph.aiohttp.ClientSession')
    async def test_token_refresh_with_timeout(self, mock_client_session, mock_safe_log):
        """测试令牌刷新时发生超时的情况"""
        # 模拟超时异常
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.post = AsyncMock(side_effect=asyncio.TimeoutError("Request timed out"))

        mock_client_session.return_value = mock_session

        # 调用refresh_access_token方法
        access_token, refresh_token = await self.graph.refresh_access_token()

        # 验证结果
        self.assertIsNone(access_token)
        self.assertIsNone(refresh_token)

        # 验证日志记录
        mock_safe_log.assert_called_with(logging.error, "令牌刷新失败：请求超时")

    @patch('utils.mail.graph.safe_log')
    @patch('utils.mail.graph.aiohttp.ClientSession')
    async def test_concurrent_token_refresh(self, mock_client_session, mock_safe_log):
        """测试并发令牌刷新的情况"""
        # 模拟成功的响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'access_token': 'new_token_1',
            'refresh_token': 'new_refresh_1',
            'expires_in': 3600,
            'token_type': 'Bearer'
        })

        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.post = AsyncMock(return_value=mock_response)

        mock_client_session.return_value = mock_session

        # 创建多个并发任务
        tasks = [
            self.graph.refresh_access_token(),
            self.graph.refresh_access_token(),
            self.graph.refresh_access_token()
        ]

        # 执行并发任务
        results = await asyncio.gather(*tasks)

        # 验证所有任务都成功完成
        for access_token, refresh_token in results:
            self.assertEqual(access_token, 'new_token_1')
            self.assertEqual(refresh_token, 'new_refresh_1')

        # 验证只发送了一次请求
        self.assertEqual(mock_session.post.call_count, 1)

    @patch('utils.mail.graph.safe_log')
    @patch('utils.mail.graph.aiohttp.ClientSession')
    async def test_token_refresh_with_network_error(self, mock_client_session, mock_safe_log):
        """测试令牌刷新时发生网络错误的情况"""
        # 模拟网络错误
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.post = AsyncMock(side_effect=aiohttp.ClientError("Network error"))

        mock_client_session.return_value = mock_session

        # 调用refresh_access_token方法
        access_token, refresh_token = await self.graph.refresh_access_token()

        # 验证结果
        self.assertIsNone(access_token)
        self.assertIsNone(refresh_token)

        # 验证日志记录
        mock_safe_log.assert_called_with(logging.error, "令牌刷新失败：网络错误")

    @patch('utils.mail.graph.safe_log')
    @patch('utils.mail.graph.aiohttp.ClientSession')
    async def test_token_refresh_with_invalid_token_format(self, mock_client_session, mock_safe_log):
        """测试令牌刷新时收到格式无效的令牌的情况"""
        # 模拟格式无效的响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'access_token': 'invalid_token_format',  # 格式无效的令牌
            'refresh_token': 'invalid_refresh_format',  # 格式无效的刷新令牌
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
        self.assertIsNone(access_token)
        self.assertIsNone(refresh_token)

        # 验证日志记录
        mock_safe_log.assert_called_with(logging.error, "令牌刷新失败：令牌格式无效")

    @patch('utils.mail.graph.safe_log')
    @patch('utils.mail.graph.aiohttp.ClientSession')
    async def test_token_refresh_with_rate_limit(self, mock_client_session, mock_safe_log):
        """测试令牌刷新时遇到速率限制的情况"""
        # 模拟速率限制响应
        mock_response = AsyncMock()
        mock_response.status = 429  # Too Many Requests
        mock_response.text = AsyncMock(return_value="Rate limit exceeded")

        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.post = AsyncMock(return_value=mock_response)

        mock_client_session.return_value = mock_session

        # 调用refresh_access_token方法
        access_token, refresh_token = await self.graph.refresh_access_token()

        # 验证结果
        self.assertIsNone(access_token)
        self.assertIsNone(refresh_token)

        # 验证日志记录
        mock_safe_log.assert_called_with(logging.error, "令牌刷新失败：请求过于频繁")

    @patch('utils.mail.graph.safe_log')
    @patch('utils.mail.graph.aiohttp.ClientSession')
    async def test_token_refresh_with_expired_token(self, mock_client_session, mock_safe_log):
        """测试令牌过期后成功获取新令牌的情况"""
        # 模拟令牌过期响应
        mock_expired_response = AsyncMock()
        mock_expired_response.status = 401
        mock_expired_response.text = AsyncMock(return_value="Token expired")

        # 模拟成功获取新令牌的响应
        mock_refresh_response = AsyncMock()
        mock_refresh_response.status = 200
        mock_refresh_response.json = AsyncMock(return_value={
            'access_token': 'new_access_token_123',
            'refresh_token': 'new_refresh_token_123',
            'expires_in': 3600,
            'token_type': 'Bearer'
        })

        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        
        # 设置请求序列：第一次请求失败（过期），第二次请求成功（刷新）
        mock_session.post = AsyncMock(side_effect=[
            mock_expired_response,  # 第一次请求返回过期
            mock_refresh_response   # 第二次请求返回新令牌
        ])

        mock_client_session.return_value = mock_session

        # 调用refresh_access_token方法
        access_token, refresh_token = await self.graph.refresh_access_token()

        # 验证结果
        self.assertEqual(access_token, 'new_access_token_123')
        self.assertEqual(refresh_token, 'new_refresh_token_123')

        # 验证日志记录
        mock_safe_log.assert_any_call(logging.info, "令牌刷新成功")

        # 验证请求参数
        self.assertEqual(mock_session.post.call_count, 2)
        
        # 验证第一次请求（令牌过期）
        first_call = mock_session.post.call_args_list[0]
        self.assertEqual(first_call[1]['url'], f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token")
        self.assertEqual(first_call[1]['data']['client_id'], self.client_id)
        self.assertEqual(first_call[1]['data']['refresh_token'], self.refresh_token)
        self.assertEqual(first_call[1]['data']['client_secret'], self.client_secret)
        self.assertEqual(first_call[1]['data']['grant_type'], 'refresh_token')
        
        # 验证第二次请求（获取新令牌）
        second_call = mock_session.post.call_args_list[1]
        self.assertEqual(second_call[1]['url'], f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token")
        self.assertEqual(second_call[1]['data']['client_id'], self.client_id)
        self.assertEqual(second_call[1]['data']['refresh_token'], self.refresh_token)
        self.assertEqual(second_call[1]['data']['client_secret'], self.client_secret)
        self.assertEqual(second_call[1]['data']['grant_type'], 'refresh_token')

        # 验证Graph实例的令牌被更新
        self.assertEqual(self.graph.authorization, "Bearer new_access_token_123")
        self.assertEqual(self.graph.refresh_token, "new_refresh_token_123")

if __name__ == '__main__':
    unittest.main() 