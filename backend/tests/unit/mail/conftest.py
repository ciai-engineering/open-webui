import pytest
import os

@pytest.fixture
def token():
    """提供测试用的访问令牌"""
    return os.getenv('TEST_TOKEN', 'dummy_token_for_testing')

@pytest.fixture
def recipient_email():
    """提供测试用的收件人邮箱"""
    return os.getenv('TEST_RECIPIENT_EMAIL', 'test@example.com')

@pytest.fixture
def attachment_path(tmp_path):
    """提供测试用的附件文件路径"""
    # 创建一个临时文件作为测试附件
    test_file = tmp_path / "test_attachment.txt"
    test_file.write_text("This is a test attachment file.")
    return str(test_file) 