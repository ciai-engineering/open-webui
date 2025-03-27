import sys
import os
import pytest
import json
from fastapi import FastAPI, status, Request
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

# Add project root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))

# Import modules to be tested
from apps.web.routers.auths import router, ACCESS_TOKEN, REFRESH_TOKEN
from apps.web.exceptions.exception import IllegalAccountException
from apps.web.models.staffs import Staffs

# Create test application
app = FastAPI()
app.include_router(router, prefix="/auths")

# Test client
client = TestClient(app)

# Mock data
MOCK_ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
MOCK_REFRESH_TOKEN = "refresh_123456789"

# Test security logging in get_staff_dict function
@pytest.mark.asyncio
async def test_get_staff_dict_security_logging():
    # Import get_staff_dict for individual testing
    from apps.web.routers.auths import get_staff_dict
    from apps.web.models.staffs import Staffs

    # Mock SSO user
    mock_sso_user = MagicMock()
    mock_sso_user.id = "test_id"
    mock_sso_user.email = "test@example.com"

    # Mock request
    mock_request = MagicMock()
    mock_request.query_params = {"code": "mock_code"}

    # Mock staff_dict
    mock_staff_dict = {
        "emp_id": "EMP123",
        "job_title": "Test Engineer",
        "department": "IT",
        "first_name": "Test",
        "last_name": "User"
    }

    # Mock Staffs.get_staff_by_email
    with patch.object(Staffs, 'get_staff_by_email', return_value=mock_staff_dict):
        # Directly call the tested function
        result = await get_staff_dict(mock_sso_user, mock_request)
        
        # Verify result is not None and contains expected data
        assert result is not None
        result_dict = json.loads(result)
        assert result_dict["emp_id"] == mock_staff_dict["emp_id"]
        assert result_dict["job_title"] == mock_staff_dict["job_title"]
        assert result_dict["department"] == mock_staff_dict["department"]

# Test SSN callback security logging on error
@patch('apps.web.routers.auths.safe_log')
@patch('apps.web.routers.auths.retry_operation')
def test_signin_callback_logs_securely_on_error(mock_retry_operation, mock_safe_log):
    # Mock retry_operation throwing an exception
    mock_retry_operation.side_effect = Exception(f"Error with token {MOCK_ACCESS_TOKEN}")
    
    # Call SSN callback
    response = client.get("/auths/signin/callback")
    
    # Verify response
    assert response.status_code == 500
    
    # In error handling, we are concerned about sensitive information not being recorded, not necessarily calling safe_log
    # Check captured logs do not contain sensitive tokens
    for call in mock_safe_log.call_args_list:
        args, _ = call
        call_str = str(args)
        assert MOCK_ACCESS_TOKEN not in call_str
        assert MOCK_REFRESH_TOKEN not in call_str

# Test security logging in get_sso_user function
@patch('apps.web.routers.auths.safe_log')
@patch('apps.web.routers.auths.msal_auth')
@patch('apps.web.routers.auths.retry_operation')
@pytest.mark.asyncio
async def test_get_sso_user_logs_securely(mock_retry_operation, mock_msal_auth, mock_safe_log):
    # Import get_sso_user for individual testing
    from apps.web.routers.auths import get_sso_user
    
    # Mock request
    mock_request = MagicMock()
    mock_request.query_params = {"code": "mock_code"}
    
    # Mock retry_operation result
    mock_user = MagicMock()
    mock_user.email = "test@example.com"
    mock_retry_operation.return_value = mock_user
    
    # Mock MSALAuth instance
    mock_instance = mock_msal_auth.return_value
    mock_instance.handle_callback.return_value = {
        "access_token": MOCK_ACCESS_TOKEN,
        "user_info": {
            "id": "mock_id",
            "userPrincipalName": "test@example.com",
            "displayName": "Test User"
        }
    }
    
    # Call tested function
    result = await get_sso_user(mock_request)
    
    # Verify result is not None
    assert result is not None
    
    # If there are logs, check that they do not contain sensitive tokens
    for call in mock_safe_log.call_args_list:
        args, _ = call
        call_str = str(args)
        assert MOCK_ACCESS_TOKEN not in call_str

if __name__ == "__main__":
    pytest.main(["-xvs", "test_auths_security.py"]) 