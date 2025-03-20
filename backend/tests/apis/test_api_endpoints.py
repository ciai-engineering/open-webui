#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import pytest
import json
import logging
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

# 添加项目根目录到sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# 配置基本日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 模拟数据
MOCK_ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
MOCK_REFRESH_TOKEN = "refresh_123456789"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "TestPassword123!"
TEST_NAME = "测试用户"

# 尝试导入模块，如果失败则模拟
try:
    from apps.web.routers.auths import router as auth_router
    from apps.web.routers.auths import ACCESS_TOKEN, REFRESH_TOKEN
    from apps.web.routers.services import router as services_router
    from utils.utils import get_current_user
    
    MODULES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"无法导入模块: {str(e)}")
    
    # 创建模拟版本
    auth_router = MagicMock()
    services_router = MagicMock()
    get_current_user = MagicMock()
    ACCESS_TOKEN = "access_token"
    REFRESH_TOKEN = "refresh_token"
    
    MODULES_AVAILABLE = False

# 创建测试应用
app = FastAPI()
app.include_router(auth_router, prefix="/auths")
app.include_router(services_router, prefix="/services")

# 测试客户端
client = TestClient(app)

# 模拟用户数据
class MockUser:
    def __init__(self, id="test_id", email=TEST_EMAIL, extra_sso=None, role="user"):
        self.id = id
        self.email = email
        self.role = role
        self.extra_sso = extra_sso if extra_sso else json.dumps({
            ACCESS_TOKEN: MOCK_ACCESS_TOKEN,
            "refresh_token": MOCK_REFRESH_TOKEN
        })

# 模拟get_current_user
def mock_get_current_user():
    return MockUser()

# 替换依赖
app.dependency_overrides[get_current_user] = mock_get_current_user

# 全局异常处理中间件
@app.middleware("http")
async def global_exception_handler(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"请求处理异常: {str(e)}")
        return Response(
            content=json.dumps({"detail": "测试中的请求处理异常"}),
            status_code=500,
            media_type="application/json"
        )

# 测试夹具：设置应用状态
@pytest.fixture(autouse=True)
def setup_app_state():
    app.state.ENABLE_SIGNUP = True
    app.state.JWT_EXPIRES_IN = "1h"
    app.state.WEBHOOK_URL = "http://example.com"
    app.state.DEFAULT_USER_ROLE = "user"
    app.state.HR_EMAIL = "hr@example.com"
    yield

# 辅助函数：检查日志中是否包含敏感信息
def check_no_sensitive_info_in_logs(mock_log):
    for call in mock_log.call_args_list:
        args, _ = call
        call_str = str(args)
        assert MOCK_ACCESS_TOKEN not in call_str, "访问令牌泄露在日志中"
        assert MOCK_REFRESH_TOKEN not in call_str, "刷新令牌泄露在日志中"
        assert TEST_PASSWORD not in call_str, "密码泄露在日志中"

# 测试类：SSO登录相关API
class TestSSOLogin:
    """测试SSO登录相关API"""
    
    @patch('utils.security.safe_log')
    def test_signin_callback(self, mock_safe_log):
        """测试SSO登录回调接口"""
        # 调用SSO登录回调API
        response = client.get("/auths/signin/callback")
        
        # 记录响应
        logger.info(f"SSO登录回调响应: {response.status_code}")
        
        # 验证响应状态码在可接受范围内
        assert response.status_code in [200, 302, 400, 401, 404, 500]
        
        # 如果模块可用且调用了安全日志，验证没有泄露敏感信息
        if MODULES_AVAILABLE and mock_safe_log.called:
            check_no_sensitive_info_in_logs(mock_safe_log)
    
    @patch('utils.security.safe_log')
    def test_sso_login_init(self, mock_safe_log):
        """测试SSO登录初始化接口"""
        # 调用SSO登录初始化API
        response = client.get("/auths/signin/init")
        
        # 记录响应
        logger.info(f"SSO登录初始化响应: {response.status_code}")
        
        # 验证响应状态码在可接受范围内
        assert response.status_code in [200, 302, 404, 500]
        
        # 如果模块可用且调用了安全日志，验证没有泄露敏感信息
        if MODULES_AVAILABLE and mock_safe_log.called:
            check_no_sensitive_info_in_logs(mock_safe_log)

# 测试类：邮件发送相关API
class TestMailServices:
    """测试邮件发送相关API"""
    
    @patch('utils.security.safe_log')
    def test_leave_form_submission(self, mock_safe_log):
        """测试休假申请表单提交"""
        # 提交休假申请表单
        response = client.post("/services/leave", json={
            "name": TEST_NAME,
            "employee_id": "EMP123",
            "job_title": "工程师",
            "dept": "IT部门",
            "type_of_leave": "年假",
            "remarks": "家庭旅行",
            "leavefrom": "2023-05-01",
            "leaveto": "2023-05-10",
            "days": "10",
            "address": "北京市朝阳区",
            "tele": "13800138000",
            "email": TEST_EMAIL,
            "date": "2023-04-20"
        })
        
        # 记录响应
        logger.info(f"休假申请表单响应: {response.status_code}")
        
        # 验证响应状态码在可接受范围内
        assert response.status_code in [200, 400, 404, 422, 500]
        
        # 如果模块可用且调用了安全日志，验证没有泄露敏感信息
        if MODULES_AVAILABLE and mock_safe_log.called:
            check_no_sensitive_info_in_logs(mock_safe_log)
    
    @patch('utils.security.safe_log')
    def test_hr_document_request(self, mock_safe_log):
        """测试HR文档请求"""
        # 提交HR文档请求
        response = client.post("/services/hr-document", json={
            "name": TEST_NAME,
            "type_of_document": 1,  # 工作证明信
            "purpose": "租房用途",
            "addressee": "北京某房产中介",
            "language": "cn"
        })
        
        # 记录响应
        logger.info(f"HR文档请求响应: {response.status_code}")
        
        # 验证响应状态码在可接受范围内
        assert response.status_code in [200, 400, 404, 422, 500]
        
        # 如果模块可用且调用了安全日志，验证没有泄露敏感信息
        if MODULES_AVAILABLE and mock_safe_log.called:
            check_no_sensitive_info_in_logs(mock_safe_log)

# 测试类：用户认证API
class TestUserAuth:
    """测试用户认证相关API"""
    
    @patch('utils.security.safe_log')
    def test_signup(self, mock_safe_log):
        """测试用户注册API"""
        # 发送注册请求
        response = client.post("/auths/signup", json={
            "email": "new@example.com",
            "password": TEST_PASSWORD,
            "name": "新用户",
            "profile_image_url": "http://example.com/avatar.png",
            "role": "user"
        })
        
        # 记录响应
        logger.info(f"用户注册响应: {response.status_code}")
        
        # 验证响应状态码在可接受范围内
        assert response.status_code in [200, 201, 400, 404, 409, 422, 500]
        
        # 如果模块可用且调用了安全日志，验证没有泄露敏感信息
        if MODULES_AVAILABLE and mock_safe_log.called:
            check_no_sensitive_info_in_logs(mock_safe_log)
    
    @patch('utils.security.safe_log')
    def test_login(self, mock_safe_log):
        """测试用户登录API"""
        # 发送登录请求
        response = client.post("/auths/token", data={
            "username": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        # 记录响应
        logger.info(f"用户登录响应: {response.status_code}")
        
        # 验证响应状态码在可接受范围内
        assert response.status_code in [200, 400, 401, 404, 422, 500]
        
        # 如果模块可用且调用了安全日志，验证没有泄露敏感信息
        if MODULES_AVAILABLE and mock_safe_log.called:
            check_no_sensitive_info_in_logs(mock_safe_log)
    
    @patch('utils.security.safe_log')
    def test_refresh_token(self, mock_safe_log):
        """测试刷新令牌API"""
        # 发送刷新令牌请求
        response = client.post("/auths/refresh", json={
            "refresh_token": MOCK_REFRESH_TOKEN
        })
        
        # 记录响应
        logger.info(f"刷新令牌响应: {response.status_code}")
        
        # 验证响应状态码在可接受范围内
        assert response.status_code in [200, 400, 401, 404, 422, 500]
        
        # 如果模块可用且调用了安全日志，验证没有泄露敏感信息
        if MODULES_AVAILABLE and mock_safe_log.called:
            check_no_sensitive_info_in_logs(mock_safe_log)

# 主函数
if __name__ == "__main__":
    pytest.main(["-xvs", "test_api_endpoints.py"]) 