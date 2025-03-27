import logging
import re
import uuid
import json
import asyncio
import time
import aiohttp
from typing import Dict, Optional, Any, Coroutine, Union, List, cast, TypeVar, Awaitable, Callable, Type, Protocol, runtime_checkable, TypedDict, NotRequired, Literal, overload, NoReturn

from fastapi import Request, Depends, HTTPException, status, APIRouter
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from utils.avatar import generate_avatar
from utils.security import safe_log, mask_sensitive_data
from apps.web.exceptions.exception import IllegalAccountException
import httpcore
import httpx

from apps.web.models.auths import (
    SigninForm,
    SignupForm,
    AddUserForm,
    UpdateProfileForm,
    UpdatePasswordForm,
    UserResponse,
    SigninResponse,
    Auths,
    ApiKey,
)
from apps.web.models.users import Users
from apps.web.models.staffs import Staffs
from apps.web.models.sso import SSOUser

from utils.utils import (
    get_password_hash,
    get_current_user,
    get_admin_user,
    create_token,
    create_api_key,
)
from utils.misc import parse_duration, validate_email_format
from utils.webhook import post_webhook
from constants import ERROR_MESSAGES, WEBHOOK_MESSAGES
from config import (
    WEBUI_AUTH_TRUSTED_EMAIL_HEADER,
    CLIENT_ID,
    CLIENT_SECRET,
    TENANT,
    REDIRECT_URI,
)

router = APIRouter()

############################
# GetSessionUser
############################


@router.get("/", response_model=UserResponse)
async def get_session_user(user=Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "profile_image_url": user.profile_image_url,
        "extra_sso": user.extra_sso,
    }


############################
# Update Profile
############################


@router.post("/update/profile", response_model=UserResponse)
async def update_profile(
    form_data: UpdateProfileForm, session_user=Depends(get_current_user)
):
    if session_user:
        user = Users.update_user_by_id(
            session_user.id,
            {"profile_image_url": form_data.profile_image_url, "name": form_data.name},
        )
        if user:
            return user
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_CRED)


############################
# Update Password
############################


@router.post("/update/password", response_model=bool)
async def update_password(
    form_data: UpdatePasswordForm, session_user=Depends(get_current_user)
):
    if WEBUI_AUTH_TRUSTED_EMAIL_HEADER:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.ACTION_PROHIBITED)
    if session_user:
        user = Auths.authenticate_user(session_user.email, form_data.password)

        if user:
            hashed = get_password_hash(form_data.new_password)
            return Auths.update_user_password_by_id(user.id, hashed)
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_PASSWORD)
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_CRED)


############################
# SignIn
############################


@router.post("/signin", response_model=SigninResponse)
async def signin(request: Request, form_data: SigninForm):
    if WEBUI_AUTH_TRUSTED_EMAIL_HEADER:
        if WEBUI_AUTH_TRUSTED_EMAIL_HEADER not in request.headers:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_TRUSTED_HEADER)

        trusted_email = request.headers[WEBUI_AUTH_TRUSTED_EMAIL_HEADER].lower()
        if not Users.get_user_by_email(trusted_email.lower()):
            await signup(
                request,
                SignupForm(
                    email=trusted_email, password=str(uuid.uuid4()), name=trusted_email
                ),
            )
        user = Auths.authenticate_user_by_trusted_header(trusted_email)
    else:
        user = Auths.authenticate_user(form_data.email.lower(), form_data.password)

    if user:
        token = create_token(
            data={"id": user.id},
            expires_delta=parse_duration(request.app.state.JWT_EXPIRES_IN),
        )

        return {
            "token": token,
            "token_type": "Bearer",
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "profile_image_url": user.profile_image_url,
            "extra_sso": "",
        }
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_CRED)


############################
# SignUp
############################


@router.post("/signup", response_model=SigninResponse)
async def signup(request: Request, form_data: SignupForm):
    if not request.app.state.ENABLE_SIGNUP:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED
        )

    if not validate_email_format(form_data.email.lower()):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_EMAIL_FORMAT
        )

    if Users.get_user_by_email(form_data.email.lower()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.EMAIL_TAKEN)

    try:
        role = (
            "admin"
            if Users.get_num_users() == 0
            else request.app.state.DEFAULT_USER_ROLE
        )
        hashed = get_password_hash(form_data.password)
        user = Auths.insert_new_auth(
            form_data.email.lower(),
            hashed,
            form_data.name,
            form_data.profile_image_url or "/user.png",
            form_data.extra_sso or "{}",
            role,
        )

        if user:
            token = create_token(
                data={"id": user.id},
                expires_delta=parse_duration(request.app.state.JWT_EXPIRES_IN),
            )

            if request.app.state.WEBHOOK_URL:
                post_webhook(
                    request.app.state.WEBHOOK_URL,
                    WEBHOOK_MESSAGES.USER_SIGNUP(user.name),
                    {
                        "action": "signup",
                        "message": WEBHOOK_MESSAGES.USER_SIGNUP(user.name),
                        "user": user.model_dump_json(exclude_none=True),
                    },
                )

            return {
                "token": token,
                "token_type": "Bearer",
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "profile_image_url": user.profile_image_url,
                "extra_sso": "",
            }
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_MESSAGES.CREATE_USER_ERROR)
    except Exception as err:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_MESSAGES.DEFAULT(str(err)))


############################
# AddUser
############################


@router.post("/add", response_model=SigninResponse)
async def add_user(form_data: AddUserForm, user=Depends(get_admin_user)):
    if not validate_email_format(form_data.email.lower()):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_EMAIL_FORMAT
        )

    if Users.get_user_by_email(form_data.email.lower()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.EMAIL_TAKEN)

    try:
        hashed = get_password_hash(form_data.password)
        user = Auths.insert_new_auth(
            form_data.email.lower(),
            hashed,
            form_data.name,
            form_data.profile_image_url or "/user.png",
            form_data.extra_sso or "{}",
            form_data.role or "user",
        )

        if user:
            token = create_token(data={"id": user.id})
            return {
                "token": token,
                "token_type": "Bearer",
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "profile_image_url": user.profile_image_url,
                "extra_sso": "",
            }
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_MESSAGES.CREATE_USER_ERROR)
    except Exception as err:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_MESSAGES.DEFAULT(str(err)))


############################
# ToggleSignUp
############################


@router.get("/signup/enabled", response_model=bool)
async def get_sign_up_status(request: Request, user=Depends(get_admin_user)):
    return request.app.state.ENABLE_SIGNUP


@router.get("/signup/enabled/toggle", response_model=bool)
async def toggle_sign_up(request: Request, user=Depends(get_admin_user)):
    request.app.state.ENABLE_SIGNUP = not request.app.state.ENABLE_SIGNUP
    return request.app.state.ENABLE_SIGNUP


############################
# Default User Role
############################


@router.get("/signup/user/role")
async def get_default_user_role(request: Request, user=Depends(get_admin_user)):
    return request.app.state.DEFAULT_USER_ROLE


class UpdateRoleForm(BaseModel):
    role: str


@router.post("/signup/user/role")
async def update_default_user_role(
    request: Request, form_data: UpdateRoleForm, user=Depends(get_admin_user)
):
    if form_data.role in ["pending", "user", "admin"]:
        request.app.state.DEFAULT_USER_ROLE = form_data.role
    return request.app.state.DEFAULT_USER_ROLE


############################
# JWT Expiration
############################


@router.get("/token/expires")
async def get_token_expires_duration(request: Request, user=Depends(get_admin_user)):
    return request.app.state.JWT_EXPIRES_IN


class UpdateJWTExpiresDurationForm(BaseModel):
    duration: str


@router.post("/token/expires/update")
async def update_token_expires_duration(
    request: Request,
    form_data: UpdateJWTExpiresDurationForm,
    user=Depends(get_admin_user),
):
    pattern = r"^(-1|0|(-?\d+(\.\d+)?)(ms|s|m|h|d|w))$"

    # Check if the input string matches the pattern
    if re.match(pattern, form_data.duration):
        request.app.state.JWT_EXPIRES_IN = form_data.duration
        return request.app.state.JWT_EXPIRES_IN
    else:
        return request.app.state.JWT_EXPIRES_IN


############################
# API Key
############################


# create api key
@router.post("/api_key", response_model=ApiKey)
async def create_api_key_(user=Depends(get_current_user)):
    api_key = create_api_key()
    success = Users.update_user_api_key_by_id(user.id, api_key)
    if success:
        return {
            "api_key": api_key,
        }
    else:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_MESSAGES.CREATE_API_KEY_ERROR)


# delete api key
@router.delete("/api_key", response_model=bool)
async def delete_api_key(user=Depends(get_current_user)):
    success = Users.update_user_api_key_by_id(user.id, "")
    return success


# get api key
@router.get("/api_key", response_model=ApiKey)
async def get_api_key(user=Depends(get_current_user)):

    try:
        api_key = user.api_key
        return {"api_key": api_key}
    except Exception as e:
        logging.error(f"Error getting API key for user {user.id}. Exception: {e}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_MESSAGES.DEFAULT())

############################
# SignIn with Microsoft Entra ID - SSO
############################
logging.info("Init MicrosoftSSO")
from utils.auth.msal_auth import MSALAuth
auth = MSALAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    tenant_id=TENANT,
    scopes=["User.Read", "Directory.Read.All", "User.ReadBasic.All", "Mail.Read", "Mail.Send"],
    redirect_uri=REDIRECT_URI
)

@router.get("/signin/sso", response_model=SigninResponse)
async def signin_with_sso():
    """Initialize auth and redirect"""
    logging.info("signin_with_sso")

    # 获取登录URL
    login_url = auth.get_login_url()
    return RedirectResponse(url=login_url, status_code=status.HTTP_303_SEE_OTHER)


ACCESS_TOKEN = "access_token"
REFRESH_TOKEN = "refresh_token"
EXPIRES_AT = "expires_at"

@router.get("/signin/callback", response_model=SigninResponse)
async def signin_callback(request: Request):
    """Verify login"""
    try:
        # 记录请求参数（安全地遮盖敏感信息）
        safe_log(logging.info, "Request query params", request.headers)
        
        # 获取SSO用户
        sso_user = await retry_operation(lambda: get_sso_user(request))
        
        # 获取员工信息
        staff_dict = await retry_operation(lambda: get_staff_dict(sso_user, request))
        
        # 获取用户
        user = await retry_operation(lambda: get_or_create_user(request, sso_user, staff_dict))
        token = create_token(data={"id": user.id}, expires_delta=parse_duration(request.app.state.JWT_EXPIRES_IN))

        return {
            "token": token,
            "token_type": "Bearer",
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "profile_image_url": user.profile_image_url,
            "extra_sso": user.extra_sso,
        }
    except IllegalAccountException as e:
        logging.error(f"Illegal account exception: {e}", exc_info=True)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.INVALID_ACCOUNT)
    except Exception as e:
        logging.error(f"Error in signin_callback: {e}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error in signin_callback: {str(e)}")

async def retry_operation(operation, retries=5, delay=1):
    """Retry operation"""
    for attempt in range(retries):
        try:
            return await operation()
        except (httpcore.ConnectError, httpx.ConnectError) as e:
            logging.warning(f"Connection error on attempt {attempt + 1}/{retries}: {e}", exc_info=True)
            if attempt == retries - 1:
                raise
        await asyncio.sleep(delay)
    raise Exception("All retry attempts failed")

async def get_sso_user(request: Request):
    """Get SSO user information"""
    async def operation():
        # 获取授权码
        code = request.query_params.get("code")
        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code not found"
            )
        
        # 使用 auth 处理回调，获取令牌和用户信息
        result = await auth.handle_callback(code)
        user_info: Dict[str, Any] = result["user_info"]
        
        # 构造与 OpenID 格式一致的用户信息
        sso_user: SSOUser = SSOUser(user_info)
        sso_user.set_tokens(
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token"),
            expires_in=result.get("expires_in")
        )
        
        logging.debug(f"Access token: {sso_user.access_token}")
        logging.debug(f"sso_user: {sso_user}")
        return sso_user

    return await retry_operation(operation)

async def get_staff_dict(sso_user: SSOUser, request: Optional[Request] = None):
    """获取员工信息"""
    try:
        # 从SSO用户获取电子邮件
        email = sso_user.email.lower()
        safe_log(logging.info, f"获取用户信息", {"email": email})
        staff_dict = Staffs.get_staff_by_email(email)
        if staff_dict is None:
            raise IllegalAccountException(f"No staff record found for email: {email}")
        if not isinstance(staff_dict, dict):
            raise TypeError(f"Expected dict, got {type(staff_dict)} for staff_dict")
        
        # 获取令牌和过期时间
        staff_dict[ACCESS_TOKEN] = sso_user.access_token
        staff_dict[REFRESH_TOKEN] = sso_user.refresh_token
        staff_dict[EXPIRES_AT] = sso_user.token_expires_at

        # 安全记录用户信息（不含敏感数据）
        safe_log(logging.info, f"从MSSQL获取到{email}的员工信息", mask_sensitive_data(staff_dict))

        return json.dumps(staff_dict)
    except Exception as e:
        logging.error(f"Error getting staff_dict: {e}", exc_info=True)
        raise

async def get_or_create_user(request: Request, sso_user, staff_dict):
    """Get or create user"""
    sso_user_email = sso_user.email.lower()
    user = Users.get_user_by_email(sso_user_email)
    if not user:
        logging.info("User not found. Then going to signup.")
        await signup(
            request,
            SignupForm(
                email=sso_user_email,
                password=str(uuid.uuid4()),
                name=sso_user.display_name,
                profile_image_url=generate_avatar(sso_user.first_name, sso_user.last_name),
                extra_sso=staff_dict
            ),
        )
        logging.info("Signup done.")
        user = Auths.authenticate_user_by_trusted_header(sso_user_email)
        if user:
            num_users = Users.get_num_users()
            if num_users is not None:
                role = "admin" if num_users <= 2 else "user"
                user = Users.update_user_role_by_id(user.id, role)
                logging.info(f"Update user's role to {role}.")
    else:
        user_info = user.__dict__.copy()
        if "extra_sso" in user_info:
            extra_sso = json.loads(user_info["extra_sso"])
            if "access_token" in extra_sso:
                extra_sso["access_token"] = "******"
            user_info["extra_sso"] = json.dumps(extra_sso)
        logging.info(f"User found {user_info}. Then going to update user's extra_sso.")
        user = Users.update_user_by_id(user.id, {"extra_sso": staff_dict})
    return user


SSO_LOGOUT_REDIRECT_URL = "https://hr.ciai-mbzuai.ac.ae/auth"
@router.get("/signin/ssoout", )
# async def signin_sso_logout(request: Request, user=Depends(get_current_user)):
async def signin_sso_logout(request: Request):
    """Logout from SSO"""
    # logging.info(f"Signing out from SSO. user: {user}")
    redirect_url = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/logout?post_logout_redirect_uri={SSO_LOGOUT_REDIRECT_URL}"
    logging.info(f"Redirecting to {redirect_url}")
    return RedirectResponse(redirect_url)