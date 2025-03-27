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

from utils.mail.mail import send_email_with_attachments
from utils.security import safe_log


def get_test_config():
    """获取测试配置"""
    config = ConfigParser()
    config.add_section('graph')
    config['graph']['client_id'] = os.getenv('CLIENT_ID', '')
    config['graph']['tenant_id'] = os.getenv('TENANT', '')
    config['graph']['graph_user_scopes'] = 'Mail.Send'
    config['graph']['authorization'] = os.getenv('AUTHORIZATION', '')
    return config['graph']


async def test_email_sending(access_token: str, recipient_email: str):
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
        success = await send_email_with_attachments(
            access_token=access_token,
            to_email=recipient_email,
            subject=subject,
            body=body,
            attachment_paths=[],  # 不发送附件
            cc_emails=[],  # 不抄送
            bcc_emails=[]  # 不密送
        )
        
        if success:
            print("邮件发送成功！")
        else:
            print("邮件发送失败！")
            
        return success
    except Exception as e:
        print(f"邮件发送失败: {e}")
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    if len(sys.argv) != 3:
        print("使用方法: python test_mail_integration.py <access_token> <recipient_email>")
        sys.exit(1)
        
    access_token = sys.argv[1]
    recipient_email = sys.argv[2]
    
    success = await test_email_sending(access_token, recipient_email)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main()) 