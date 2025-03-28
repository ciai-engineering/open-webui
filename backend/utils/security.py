import logging
import copy
import json
import re

def mask_sensitive_data(data, sensitive_keys=None):
    """遮盖敏感数据"""
    if sensitive_keys is None:
        sensitive_keys = [
            "access_token", 
            "refresh_token", 
            "token", 
            "authorization", 
            "password", 
            "secret", 
            "api_key"
        ]
    
    if isinstance(data, dict):
        masked_data = copy.deepcopy(data)
        for key in masked_data:
            if key.lower() in [s.lower() for s in sensitive_keys]:
                masked_data[key] = masked_data[key][:3] + "******"
            elif isinstance(masked_data[key], (dict, list)):
                masked_data[key] = mask_sensitive_data(masked_data[key], sensitive_keys)
        return masked_data
    elif isinstance(data, list):
        return [mask_sensitive_data(item, sensitive_keys) for item in data]
    else:
        return data

def safe_str(obj):
    """安全地将对象转换为字符串，去除可能包含的敏感信息"""
    if obj is None:
        return "None"
        
    # 将对象转为字符串
    s = str(obj)
    
    # 使用正则表达式替换可能的令牌
    # 匹配可能是令牌的长字符串样式
    sensitive_patterns = [
        r'eyJ[a-zA-Z0-9_-]{5,}(\.[a-zA-Z0-9_-]{5,}){0,2}', # JWT格式（更全面的匹配）
        r'Bearer\s+[\w\.-]+', # 授权头
        r'token["\']?\s*[=:]\s*["\']?[\w\.-]+["\']?', # token赋值
        r'access_token["\']?\s*[=:]\s*["\']?[\w\.-]+["\']?', # access_token赋值
        r'refresh_token["\']?\s*[=:]\s*["\']?[\w\.-]+["\']?', # refresh_token赋值
    ]
    
    for pattern in sensitive_patterns:
        s = re.sub(pattern, '******', s)
        
    return s

def safe_log(log_func, message, data=None, exception=None):
    """安全记录信息，遮盖敏感数据"""
    # 处理普通消息
    if data:
        if isinstance(data, (dict, list)):
            masked_data = mask_sensitive_data(data)
            log_func(f"{message}: {json.dumps(masked_data)}")
        else:
            log_func(f"{message}: {safe_str(data)}")
    elif exception:
        # 安全地记录异常信息
        log_func(f"{message}: {type(exception).__name__} - {safe_str(str(exception))}")
    else:
        log_func(message) 