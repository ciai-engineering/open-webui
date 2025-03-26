#!/usr/bin/env python
"""
测试脚本，用于验证令牌验证功能是否正常工作。
"""
import os
import sys
import json
import asyncio
import logging
import traceback
import pytest
from configparser import ConfigParser
from types import SimpleNamespace

# 添加项目根目录到sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
sys.path.append(project_root)

from utils.mail.graph import Graph
from utils.security import safe_log


@pytest.mark.asyncio
async def test_token_validation(token):
    """测试令牌验证功能"""
    try:
        print(f"开始测试令牌验证...")
        
        # 设置测试配置
        config = ConfigParser()
        config.add_section('graph')
        config['graph']['client_id'] = "2b0e50f6-6937-4a32-9501-94bf7357e883"
        config['graph']['tenant_id'] = "c93272d3-1b07-4b3d-a3b6-19b34a973915"
        config['graph']['graph_user_scopes'] = "Mail.Send"
        config['graph']['authorization'] = f"Bearer {token}"
        config['graph']['refresh_token'] = ""
        config['graph']['client_secret'] = ""
        
        # 创建Graph对象
        graph = Graph(config['graph'])
        
        # 测试令牌验证
        print("测试validate_token方法...")
        is_valid = await graph.validate_token()
        print(f"令牌验证结果: {'有效' if is_valid else '无效'}")
        
        return is_valid
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("使用方法: python test_token.py <access_token>")
        sys.exit(1)
    
    # 获取令牌
    token = sys.argv[1]
    
    # 运行测试
    result = asyncio.run(test_token_validation(token))
    
    # 根据结果设置退出代码
    sys.exit(0 if result else 1) 