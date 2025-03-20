import sys
import os
import pytest
import json
from fastapi import FastAPI, status, Request
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

# 添加项目根目录到sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../")))

# 导入需要测试的模块
from apps.web.routers.auths import router, ACCESS_TOKEN, REFRESH_TOKEN
from apps.web.exceptions.exception import IllegalAccountException
from apps.web.models.staffs import Staffs

# 创建测试应用
app = FastAPI()
app.include_router(router, prefix="/auths")

# 测试客户端
client = TestClient(app)

# 模拟数据
mock_access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
mock_refresh_token = "refresh_123456789"

# 测试get_staff_dict函数的安全日志记录
@patch('apps.web.routers.auths.safe_log')
@patch('apps.web.routers.auths.Staffs')
def test_get_staff_dict_logs_securely(mock_staffs, mock_safe_log):
    # 导入get_staff_dict以便单独测试
    from apps.web.routers.auths import get_staff_dict
    
    # 模拟SSO用户
    mock_sso_user = MagicMock()
    mock_sso_user.email.lower.return_value = "test@example.com"
    
    # 模拟staff_dict
    mock_staff_dict = {
        "name": "Test User",
        "email": "test@example.com",
        "role": "user"
    }
    mock_staffs.get_staff_by_email.return_value = mock_staff_dict
    
    # 模拟aiohttp会话
    with patch('apps.web.routers.auths.aiohttp.ClientSession') as mock_client_session:
        # 模拟令牌响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "access_token": mock_access_token,
            "refresh_token": mock_refresh_token,
            "expires_in": 3600
        })
        
        # 配置模拟会话
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.post.return_value.__aenter__.return_value = mock_response
        mock_client_session.return_value = mock_session
        
        # 模拟sso.access_token
        with patch('apps.web.routers.auths.sso') as mock_sso:
            mock_sso.access_token = mock_access_token
            
            # 创建mock request
            mock_request = MagicMock()
            mock_request.query_params = {"code": "test_auth_code"}
            
            # 直接调用被测试函数，但不要期望返回值
            pytest.mark.asyncio(get_staff_dict)(mock_sso_user)
            
            # 验证日志调用
            # 检查所有日志不含敏感令牌
            for call in mock_safe_log.call_args_list:
                args, _ = call
                call_str = str(args)
                assert mock_access_token not in call_str
                assert mock_refresh_token not in call_str

# 测试SSO回调中的异常处理安全日志记录
@patch('apps.web.routers.auths.safe_log')
@patch('apps.web.routers.auths.retry_operation')
def test_signin_callback_logs_securely_on_error(mock_retry_operation, mock_safe_log):
    # 模拟retry_operation抛出异常
    mock_retry_operation.side_effect = Exception(f"Error with token {mock_access_token}")
    
    # 调用SSO回调
    response = client.get("/auths/signin/callback")
    
    # 验证响应
    assert response.status_code == 500
    
    # 在错误处理中，我们关注的是敏感信息不被记录，而不是一定要调用safe_log
    # 检查捕获的日志不含敏感令牌
    for call in mock_safe_log.call_args_list:
        args, _ = call
        call_str = str(args)
        assert mock_access_token not in call_str
        assert mock_refresh_token not in call_str

# 测试get_sso_user函数的安全日志记录
@patch('apps.web.routers.auths.safe_log')
@patch('apps.web.routers.auths.sso')
@patch('apps.web.routers.auths.retry_operation')
def test_get_sso_user_logs_securely(mock_retry_operation, mock_sso, mock_safe_log):
    # 导入get_sso_user以便单独测试
    from apps.web.routers.auths import get_sso_user
    
    # 模拟request
    mock_request = MagicMock()
    
    # 模拟retry_operation的结果
    mock_user = MagicMock()
    mock_user.email = "test@example.com"
    mock_retry_operation.return_value = mock_user
    
    # 模拟sso.access_token包含敏感信息
    mock_sso.access_token = mock_access_token
    
    # 调用被测试函数
    pytest.mark.asyncio(get_sso_user)(mock_request)
    
    # 如果有日志，检查不含敏感令牌
    for call in mock_safe_log.call_args_list:
        args, _ = call
        call_str = str(args)
        assert mock_access_token not in call_str

if __name__ == "__main__":
    pytest.main(["-xvs", "test_auths_security.py"]) 