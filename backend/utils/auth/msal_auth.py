import logging
import msal
import aiohttp
import jwt
import time
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from utils.security import safe_log

class MSALAuth:
    """Microsoft Authentication Library (MSAL) 认证工具类"""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        scopes: list[str],
        redirect_uri: str
    ):
        """
        初始化 MSAL 认证工具
        
        Args:
            client_id: Azure AD 应用程序 ID
            client_secret: Azure AD 应用程序密钥
            tenant_id: Azure AD 租户 ID
            scopes: 请求的权限范围
            redirect_uri: 回调 URI
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.scopes = scopes
        self.redirect_uri = redirect_uri
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.logger = logging.getLogger(__name__)
        
        # 初始化 MSAL 应用
        self.app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=self.authority
        )
    
    def get_login_url(self) -> str:
        """
        获取登录 URL
        
        Returns:
            str: 登录 URL
        """
        try:
            auth_url = self.app.get_authorization_request_url(
                scopes=self.scopes,
                redirect_uri=self.redirect_uri
            )
            safe_log(self.logger.info, "Generated login URL successfully")
            return auth_url
        except Exception as e:
            safe_log(self.logger.error, "Failed to generate login URL", exception=e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate login URL"
            )
    
    async def handle_callback(self, code: str) -> Dict[str, Any]:
        """
        处理回调，获取访问令牌
        
        Args:
            code: 授权码
            
        Returns:
            Dict[str, Any]: 包含访问令牌和用户信息的字典
        """
        try:
            # 使用授权码获取令牌
            result = self.app.acquire_token_by_authorization_code(
                code=code,
                scopes=self.scopes,
                redirect_uri=self.redirect_uri
            )
            logging.debug(f"Token acquisition result: {result}")
            
            if isinstance(result, dict) and "error" in result:
                safe_log(self.logger.error, f"Token acquisition failed: {result.get('error')}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Token acquisition failed: {result.get('error')}"
                )
            
            # 获取用户信息
            user_info = await self._get_user_info(result["access_token"])
            
            logging.debug(f"User info: {user_info}")

            return {
                "access_token": result["access_token"],
                "refresh_token": result.get("refresh_token"),
                "id_token": result.get("id_token"),
                "expires_in": result.get("expires_in"),
                "user_info": user_info
            }
            
        except Exception as e:
            safe_log(self.logger.error, "Failed to handle callback", exception=e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to handle callback"
            )
    
    async def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        获取用户信息
        
        Args:
            access_token: 访问令牌
            
        Returns:
            Dict[str, Any]: 用户信息
        """
        try:
            # 使用 Graph API 获取用户信息
            headers = {"Authorization": f"Bearer {access_token}"}
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers=headers
                ) as response:
                    if response.status != 200:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Failed to get user info"
                        )
                    return await response.json()
        except Exception as e:
            safe_log(self.logger.error, "Failed to get user info", exception=e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get user info"
            )
    
    def validate_token(self, token: str) -> bool:
        """
        验证令牌
        
        Args:
            token: 要验证的令牌
            
        Returns:
            bool: 令牌是否有效
        """
        try:
            # 解码令牌
            decoded_token = jwt.decode(
                token,
                options={"verify_signature": False}
            )
            
            # 记录令牌信息
            safe_log(self.logger.debug, f"Token claims: {decoded_token}")
            
            # 验证令牌声明
            if not self._validate_claims(decoded_token):
                return False
                
            # 验证令牌范围
            if not self._validate_scopes(decoded_token):
                return False
                
            # 验证令牌时间
            if not self._validate_timing(decoded_token):
                return False
                
            return True
            
        except Exception as e:
            safe_log(self.logger.error, "Token validation failed", exception=e)
            return False
            
    def _validate_claims(self, decoded_token: dict) -> bool:
        """验证令牌声明"""
        # Azure AD token issuer format is https://sts.windows.net/{tenant_id}/
        expected_issuer = f"https://sts.windows.net/{self.tenant_id}/"
        if decoded_token.get("iss") != expected_issuer:
            safe_log(self.logger.error, f"Invalid issuer. Expected: {expected_issuer}, Got: {decoded_token.get('iss')}")
            return False
            
        # Accept both client ID and Microsoft Graph API identifier as valid audiences
        valid_audiences = [
            self.client_id,
            "00000003-0000-0000-c000-000000000000"  # Microsoft Graph API identifier
        ]
        if decoded_token.get("aud") not in valid_audiences:
            safe_log(self.logger.error, f"Invalid audience. Expected one of: {valid_audiences}, Got: {decoded_token.get('aud')}")
            return False
            
        return True
        
    def _validate_scopes(self, decoded_token: dict) -> bool:
        """验证令牌范围"""
        # Get scopes from token, handle both 'scp' and 'scope' claims
        token_scopes = decoded_token.get("scp", "").split()
        if not token_scopes:
            token_scopes = decoded_token.get("scope", "").split()
            
        # Log scopes for debugging
        safe_log(self.logger.debug, f"Token scopes: {token_scopes}")
        safe_log(self.logger.debug, f"Required scopes: {self.scopes}")
        
        # Check if all required scopes are present
        if not all(scope in token_scopes for scope in self.scopes):
            safe_log(self.logger.error, f"Missing required scopes. Token scopes: {token_scopes}, Required scopes: {self.scopes}")
            return False
            
        return True
        
    def _validate_timing(self, decoded_token: dict) -> bool:
        """验证令牌时间"""
        current_time = time.time()
        
        # 验证过期时间
        exp = decoded_token.get("exp")
        if exp is None or exp < current_time:
            safe_log(self.logger.error, "Token expired")
            return False
            
        # 验证生效时间
        if decoded_token.get("nbf", 0) > current_time:
            safe_log(self.logger.error, "Token not yet valid")
            return False
            
        return True
    
    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        刷新访问令牌
        
        Args:
            refresh_token: 刷新令牌
            
        Returns:
            Optional[Dict[str, Any]]: 新的令牌信息
        """
        try:
            result = self.app.acquire_token_by_refresh_token(
                refresh_token=refresh_token,
                scopes=self.scopes
            )
            
            if isinstance(result, dict) and "error" in result:
                safe_log(self.logger.error, f"Token refresh failed: {result.get('error')}")
                return None
                
            return result
        except Exception as e:
            safe_log(self.logger.error, "Failed to refresh token", exception=e)
            return None 