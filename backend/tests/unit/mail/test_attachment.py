#!/usr/bin/env python
"""
测试脚本，专门用于测试带附件的邮件发送功能。

使用方法:
python test_attachment.py <access_token> <recipient_email> <attachment_path>
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
from utils.mail.mail import send_email_with_attachments


@pytest.mark.asyncio
async def test_attachment_sending(token, recipient_email, attachment_path):
    """测试附件发送功能"""
    try:
        print(f"\n开始测试附件发送功能...")
        print(f"收件人: {recipient_email}")
        print(f"附件路径: {attachment_path}")
        
        # 构造测试邮件内容
        subject = "测试邮件 - 附件发送测试"
        body = """
        这是一封测试邮件，用于测试附件发送功能。
        
        如果您收到这封邮件和附件，说明功能正常。
        
        测试时间: {}
        """.format(asyncio.get_event_loop().time())
        
        # 发送测试邮件
        print("尝试发送带附件的测试邮件...")
        success = await send_email_with_attachments(
            access_token=token,
            to_email=recipient_email,
            subject=subject,
            body=body,
            attachment_paths=[attachment_path],  # 发送附件
            cc_emails=[],  # 不抄送
            bcc_emails=[]  # 不密送
        )
        
        if success:
            print("邮件发送成功！")
        else:
            print("邮件发送失败！")
            
        return success
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) < 4:
        print("使用方法: python test_attachment.py <access_token> <recipient_email> <attachment_path>")
        sys.exit(1)
    
    # 获取参数
    token = sys.argv[1]
    recipient_email = sys.argv[2]
    attachment_path = sys.argv[3]
    
    # 运行测试
    result = asyncio.run(test_attachment_sending(token, recipient_email, attachment_path))
    
    # 根据结果设置退出代码
    sys.exit(0 if result else 1) 