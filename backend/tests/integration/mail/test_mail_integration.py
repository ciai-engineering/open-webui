#!/usr/bin/env python
"""
集成测试脚本，用于测试电子邮件发送功能。
该脚本直接使用我们更新的HTTP请求方法，绕过Microsoft Graph SDK。

使用方法:
python test_mail_integration.py <access_token> <recipient_email>
"""
import os
import sys
import json
import asyncio
import logging
import traceback
from types import SimpleNamespace
from configparser import ConfigParser

# 添加项目根目录到sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
sys.path.append(project_root)

from utils.mail.graph import Graph
from utils.security import safe_log


def get_test_config():
    """获取测试配置"""
    config = ConfigParser()
    config.add_section('graph')
    config['graph']['client_id'] = os.getenv('CLIENT_ID', '')
    config['graph']['tenant_id'] = os.getenv('TENANT', '')
    config['graph']['graph_user_scopes'] = 'Mail.Send'
    config['graph']['authorization'] = os.getenv('AUTHORIZATION', '')
    config['graph']['refresh_token'] = os.getenv('REFRESH_TOKEN', '')
    config['graph']['client_secret'] = os.getenv('CLIENT_SECRET', '')
    return config['graph']


async def test_token_validation(token):
    """测试令牌验证功能"""
    try:
        print(f"\n开始测试令牌验证功能...")
        
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
        print("尝试验证令牌...")
        is_valid = await graph.validate_token()
        
        if is_valid:
            print("令牌验证成功！")
            return True, graph
        else:
            print("令牌验证失败。")
            return False, None
    except Exception as e:
        print(f"令牌验证过程中发生错误: {e}")
        traceback.print_exc()
        return False, None


async def test_email_sending(graph, recipient_email):
    """测试邮件发送功能"""
    try:
        print(f"\n开始测试邮件发送功能...")
        print(f"收件人: {recipient_email}")
        
        # 构造测试邮件内容
        subject = "测试邮件 - 来自集成测试脚本"
        body = """
        这是一封测试邮件，用于验证邮件发送功能是否正常工作。
        
        如果您收到这封邮件，说明邮件发送功能正常。
        
        测试环境: 集成测试脚本
        测试时间: {}
        """.format(asyncio.get_event_loop().time())
        
        # 发送测试邮件
        print("尝试发送测试邮件...")
        await graph.send_leave_mail(
            subject=subject,
            leave_body=body,
            recipient=recipient_email,
            attachment_path="",
            attachment_name=""
        )
        
        print("邮件发送成功！")
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        traceback.print_exc()
        return False


async def run_full_test(token, recipient_email=None):
    """运行完整的测试流程"""
    print("=" * 50)
    print("开始完整的集成测试")
    print("=" * 50)
    
    # 令牌验证测试
    token_valid, graph = await test_token_validation(token)
    if not token_valid:
        print("令牌验证失败，测试终止")
        return False
    
    # 邮件发送测试
    if recipient_email:
        email_success = await test_email_sending(graph, recipient_email)
        if not email_success:
            print("邮件发送测试失败")
            return False
    else:
        print("未提供收件人邮箱，跳过邮件发送测试")
    
    print("=" * 50)
    print("集成测试完成")
    print("=" * 50)
    return True


if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("使用方法: python test_mail_integration.py <access_token> [recipient_email]")
        sys.exit(1)
    
    # 获取令牌
    token = sys.argv[1]
    
    # 获取收件人邮箱（可选）
    recipient_email = None
    if len(sys.argv) >= 3:
        recipient_email = sys.argv[2]
    
    # 运行测试
    result = asyncio.run(run_full_test(token, recipient_email))
    
    # 根据结果设置退出代码
    sys.exit(0 if result else 1) 