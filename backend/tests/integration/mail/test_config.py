"""
测试配置文件，提供用于测试的Microsoft Graph API配置。
支持真实API测试和模拟测试两种模式。
"""
import os
import json
from typing import Dict, Optional, List

# 从环境变量中获取测试配置
def get_test_config() -> Dict:
    """从环境变量或配置文件中获取测试配置"""
    # 优先从环境变量获取配置
    client_id = os.environ.get('TEST_MS_CLIENT_ID')
    tenant_id = os.environ.get('TEST_MS_TENANT_ID')
    client_secret = os.environ.get('TEST_MS_CLIENT_SECRET')
    test_token = os.environ.get('TEST_MS_TOKEN')
    test_refresh_token = os.environ.get('TEST_MS_REFRESH_TOKEN')
    
    # 如果环境变量不存在，尝试从配置文件加载
    if not all([client_id, tenant_id, client_secret]):
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'test_ms_config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    client_id = config.get('client_id', '')
                    tenant_id = config.get('tenant_id', '')
                    client_secret = config.get('client_secret', '')
                    test_token = config.get('test_token', '')
                    test_refresh_token = config.get('test_refresh_token', '')
        except Exception as e:
            print(f"无法加载测试配置文件: {e}")
    
    return {
        "client_id": client_id,
        "tenant_id": tenant_id,
        "client_secret": client_secret,
        "authorization": f"Bearer {test_token}" if test_token else "",
        "refresh_token": test_refresh_token,
        "graph_user_scopes": ["Mail.Send", "Mail.Read"]
    }

def can_run_real_api_tests() -> bool:
    """判断是否可以运行真实API测试"""
    config = get_test_config()
    return all([config["client_id"], config["tenant_id"], config["client_secret"]])

def get_test_mode() -> str:
    """获取测试模式: 'real' 或 'mock'"""
    if os.environ.get('FORCE_MOCK_TESTS') == 'true':
        return 'mock'
    
    return 'real' if can_run_real_api_tests() else 'mock'

# 创建一个模板配置文件示例
def create_sample_config_file():
    """创建示例配置文件，用户可以基于此填写自己的凭据"""
    sample_config = {
        "client_id": "your_client_id",
        "tenant_id": "your_tenant_id",
        "client_secret": "your_client_secret",
        "test_token": "your_test_access_token",
        "test_refresh_token": "your_test_refresh_token"
    }
    
    config_path = os.path.join(os.path.dirname(__file__), 'test_ms_config.json.sample')
    with open(config_path, 'w') as f:
        json.dump(sample_config, f, indent=2)
    
    print(f"示例配置文件已创建: {config_path}")
    print("请复制此文件为test_ms_config.json并填写您的测试凭据")

if __name__ == "__main__":
    # 如果直接运行此文件，创建示例配置
    create_sample_config_file() 