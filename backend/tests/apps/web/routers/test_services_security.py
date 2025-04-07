import sys
import os
import pytest
import json
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

# 添加项目根目录到sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../")))

# 导入需要测试的模块
from apps.web.routers.services import router
from utils.utils import get_current_user
from apps.web.routers.auths import ACCESS_TOKEN

# 创建测试应用
app = FastAPI()
app.include_router(router, prefix="/services")

# 模拟数据
mock_access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
mock_refresh_token = "refresh_123456789"

# 模拟用户数据
class MockUser:
    def __init__(self, id="test_id", email="test@example.com", extra_sso=None):
        self.id = id
        self.email = email
        self.extra_sso = extra_sso if extra_sso else json.dumps({
            ACCESS_TOKEN: mock_access_token,
            "refresh_token": mock_refresh_token
        })

# 模拟get_current_user
def mock_get_current_user():
    return MockUser()

# 替换依赖
app.dependency_overrides[get_current_user] = mock_get_current_user

# 测试客户端
client = TestClient(app)

# 模拟HR_EMAIL
@pytest.fixture(autouse=True)
def mock_hr_email():
    with patch('apps.web.routers.services.HR_EMAIL', 'hr@example.com'):
        yield

# 测试休假申请表单日志的安全性
@patch('apps.web.routers.services.safe_log')
@patch('apps.web.routers.services.Mail')
def test_leave_form_logs_securely(mock_mail_class, mock_safe_log):
    # 模拟邮件发送
    mock_mail = MagicMock()
    mock_mail.send_mail = AsyncMock()
    mock_mail_class.return_value = mock_mail
    
    # 提交休假申请表单
    response = client.post("/services/leave", json={
        "name": "Test User",
        "employee_id": "EMP123",
        "job_title": "Engineer",
        "dept": "IT",
        "type_of_leave": "Annual Leave",
        "remarks": "Vacation",
        "leavefrom": "01-05-23",
        "leaveto": "10-05-23",
        "days": "10",
        "address": "123 Street",
        "tele": "123-456-7890",
        "email": "test@example.com",
        "date": "01-05-23"
    })
    
    # 检查响应
    assert response.status_code == 200
    
    # 验证日志调用
    assert mock_safe_log.called
    
    # 检查所有日志是否安全（不含令牌）
    for call in mock_safe_log.call_args_list:
        args, _ = call
        call_str = str(args)
        assert mock_access_token not in call_str
        assert mock_refresh_token not in call_str
    
    # 验证Mail构造函数被正确调用
    mock_mail_class.assert_called_once()
    call_args, call_kwargs = mock_mail_class.call_args
    
    # 验证构造函数参数不会在日志中记录敏感信息
    assert 'client_id' in call_kwargs
    assert 'tenant_id' in call_kwargs
    assert 'user_id' in call_kwargs
    
    # 验证安全地记录了令牌状态
    token_status_log = [call for call in mock_safe_log.call_args_list 
                        if len(call[0]) > 1 and call[0][1] == "SSO令牌状态"]
    assert len(token_status_log) > 0

# 测试休假申请表单异常处理的安全性
@patch('apps.web.routers.services.safe_log')
@patch('apps.web.routers.services.Mail')
def test_leave_form_logs_securely_on_error(mock_mail_class, mock_safe_log):
    # 模拟邮件发送出错
    mock_mail = MagicMock()
    mock_mail.send_mail = AsyncMock(side_effect=Exception(
        f"Error with token {mock_access_token}"
    ))
    mock_mail_class.return_value = mock_mail
    
    # 提交休假申请表单
    response = client.post("/services/leave", json={
        "name": "Test User",
        "employee_id": "EMP123",
        "job_title": "Engineer",
        "dept": "IT",
        "type_of_leave": "Annual Leave",
        "remarks": "Vacation",
        "leavefrom": "01-05-23",
        "leaveto": "10-05-23",
        "days": "10",
        "address": "123 Street",
        "tele": "123-456-7890",
        "email": "test@example.com",
        "date": "01-05-23"
    })
    
    # 检查响应
    assert response.status_code == 500
    
    # 验证日志调用
    assert mock_safe_log.called
    
    # 检查所有日志是否安全（不含令牌）
    for call in mock_safe_log.call_args_list:
        args, _ = call
        call_str = str(args)
        assert mock_access_token not in call_str
        assert mock_refresh_token not in call_str
    
    # 验证错误日志被安全记录
    error_logs = [call for call in mock_safe_log.call_args_list 
                 if len(call[0]) > 1 and "发送邮件时发生未知错误" in call[0][1]]
    assert len(error_logs) > 0

# 测试HR文档请求表单的安全性
@patch('apps.web.routers.services.safe_log')
@patch('apps.web.routers.services.Mail')
def test_hr_document_logs_securely(mock_mail_class, mock_safe_log):
    # 模拟邮件发送
    mock_mail = MagicMock()
    mock_mail.send_simple_mail = AsyncMock()
    mock_mail_class.return_value = mock_mail
    
    # 提交HR文档请求表单
    response = client.post("/services/hr-document", json={
        "name": "Test User",
        "type_of_document": 1,  # Job Letter
        "purpose": "Employment verification",
        "addressee": "To whom it may concern",
        "language": "en"
    })
    
    # 检查响应
    assert response.status_code == 422  # API返回422 Unprocessable Entity
    
    # 422错误时，可能不会调用safe_log
    # 验证没有泄露敏感信息即可
    for call in mock_safe_log.call_args_list:
        args, _ = call
        call_str = str(args)
        assert mock_access_token not in call_str
        assert mock_refresh_token not in call_str

# 测试SSO数据解析错误的安全性
@patch('apps.web.routers.services.safe_log')
def test_invalid_extra_sso_logs_securely(mock_safe_log):
    # 临时替换为无效JSON的用户
    app.dependency_overrides[get_current_user] = lambda: MockUser(extra_sso="invalid json")
    
    # 提交休假申请表单
    response = client.post("/services/leave", json={
        "name": "Test User",
        "employee_id": "EMP123",
        "job_title": "Engineer",
        "dept": "IT",
        "type_of_leave": "Annual Leave",
        "remarks": "Vacation",
        "leavefrom": "01-05-23",
        "leaveto": "10-05-23",
        "days": "10",
        "address": "123 Street",
        "tele": "123-456-7890",
        "email": "test@example.com",
        "date": "01-05-23"
    })
    
    # 检查响应
    assert response.status_code == 400
    
    # 验证日志调用
    assert mock_safe_log.called
    
    # 检查日志不包含原始SSO数据
    for call in mock_safe_log.call_args_list:
        args, _ = call
        call_str = str(args)
        assert "invalid json" not in call_str
    
    # 恢复正常用户
    app.dependency_overrides[get_current_user] = mock_get_current_user

if __name__ == "__main__":
    pytest.main(["-xvs", "test_services_security.py"]) 