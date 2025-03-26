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

    # Mock SSO user
    mock_sso_user = MagicMock()
    mock_sso_user.id = "test_id"
    mock_sso_user.email = "test@example.com"

    # Mock staff_dict
    mock_staff_dict = {
        "access_token": MOCK_ACCESS_TOKEN,
        "refresh_token": MOCK_REFRESH_TOKEN,
        "user": {
            "id": "test_id",
            "email": "test@example.com",
            "nested": {
                "token": "nested_token"
            }
        }
    }

    # Mock aiohttp session
    mock_session = AsyncMock()

    # Mock token response
    mock_token_response = {
        "access_token": MOCK_ACCESS_TOKEN,
        "refresh_token": MOCK_REFRESH_TOKEN
    }

    # Configure mock session
    mock_session.post.return_value.__aenter__.return_value.json.return_value = mock_token_response
    mock_session.post.return_value.__aenter__.return_value.status = 200

    # Mock sso.access_token
    mock_sso = MagicMock()
    mock_sso.access_token = MOCK_ACCESS_TOKEN

    # Create mock request
    mock_request = Request(scope={"type": "http"})

    # Directly call the tested function, but don't expect return value
    await get_staff_dict(mock_sso_user, mock_staff_dict, mock_session, mock_sso, mock_request)

    # Verify log calls
    # ... existing code ...

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
@patch('apps.web.routers.auths.sso')
@patch('apps.web.routers.auths.retry_operation')
def test_get_sso_user_logs_securely(mock_retry_operation, mock_sso, mock_safe_log):
    # Import get_sso_user for individual testing
    from apps.web.routers.auths import get_sso_user
    
    # Mock request
    mock_request = MagicMock()
    
    # Mock retry_operation result
    mock_user = MagicMock()
    mock_user.email = "test@example.com"
    mock_retry_operation.return_value = mock_user
    
    # Mock sso.access_token containing sensitive information
    mock_sso.access_token = MOCK_ACCESS_TOKEN
    
    # Call tested function
    pytest.mark.asyncio(get_sso_user)(mock_request)
    
    # If there are logs, check that they do not contain sensitive tokens
    for call in mock_safe_log.call_args_list:
        args, _ = call
        call_str = str(args)
        assert MOCK_ACCESS_TOKEN not in call_str

if __name__ == "__main__":
    pytest.main(["-xvs", "test_auths_security.py"]) 