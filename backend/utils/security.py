import logging
import copy
import json
import re

def mask_sensitive_data(data, sensitive_keys=None):
    """Mask sensitive data"""
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
    """Safely convert object to string, removing potentially sensitive information"""
    if obj is None:
        return "None"
        
    # Convert object to string
    s = str(obj)
    
    # Use regex to replace potential tokens
    # Match long string patterns that might be tokens
    sensitive_patterns = [
        r'eyJ[a-zA-Z0-9_-]{5,}(\.[a-zA-Z0-9_-]{5,}){0,2}', # JWT format (more comprehensive match)
        r'Bearer\s+[\w\.-]+', # Authorization header
        r'token["\']?\s*[=:]\s*["\']?[\w\.-]+["\']?', # token assignment
        r'access_token["\']?\s*[=:]\s*["\']?[\w\.-]+["\']?', # access_token assignment
        r'refresh_token["\']?\s*[=:]\s*["\']?[\w\.-]+["\']?', # refresh_token assignment
    ]
    
    for pattern in sensitive_patterns:
        s = re.sub(pattern, '******', s)
        
    return s

def safe_log(log_func, message, data=None, exception=None):
    """Safely log information, masking sensitive data"""
    # Handle regular messages
    if data:
        if isinstance(data, (dict, list)):
            masked_data = mask_sensitive_data(data)
            log_func(f"{message}: {json.dumps(masked_data)}")
        else:
            log_func(f"{message}: {safe_str(data)}")
    elif exception:
        # Safely log exception information
        log_func(f"{message}: {type(exception).__name__} - {safe_str(str(exception))}")
    else:
        log_func(message) 