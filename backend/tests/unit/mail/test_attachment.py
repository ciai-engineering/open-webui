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


@pytest.mark.asyncio
async def test_attachment_sending(token, recipient_email, attachment_path):
    """测试附件发送功能"""
    try:
        print(f"开始测试附件邮件发送功能...")
        
        # 检查附件是否存在
        if not os.path.isfile(attachment_path):
            print(f"错误: 附件文件不存在: {attachment_path}")
            return False
            
        print(f"附件文件: {attachment_path}")
        print(f"文件大小: {os.path.getsize(attachment_path)} 字节")
        
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
        print("验证令牌...")
        is_valid = await graph.validate_token()
        if not is_valid:
            print("令牌验证失败")
            return False
            
        print("令牌验证成功")
        
        # 构造测试邮件内容
        subject = "测试邮件 - 附件测试"
        body = """
        这是一封测试邮件，用于测试附件发送功能。
        
        如果您收到这封邮件和附件，说明功能正常。
        
        测试时间: {}
        """.format(asyncio.get_event_loop().time())
        
        # 发送测试邮件
        print("尝试发送带附件的测试邮件...")
        await graph.send_leave_mail(
            subject=subject,
            leave_body=body,
            recipient=recipient_email,
            attachment_path=attachment_path,
            attachment_name=os.path.basename(attachment_path)
        )
        
        print("邮件发送成功！")
        return True
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