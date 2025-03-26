import unittest
import logging
import json
import re
import sys
import os

# Add project root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from utils.security import mask_sensitive_data, safe_str, safe_log

class TestSecurity(unittest.TestCase):
    def setUp(self):
        # 设置测试数据
        self.sensitive_dict = {
            "user": "test_user",
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0",
            "refresh_token": "refresh_123456789",
            "nested": {
                "api_key": "api_123456789",
                "normal": "normal_data"
            }
        }
        self.sensitive_str = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
        
        # 创建自定义记录器进行测试
        self.log_records = []
        self.test_logger = logging.getLogger("test_logger")
        self.test_logger.setLevel(logging.INFO)
        
        # 移除所有现有处理器，以防止测试日志输出到控制台
        for handler in self.test_logger.handlers[:]:
            self.test_logger.removeHandler(handler)
        
        # 创建自定义处理器来捕获日志消息
        class TestLogHandler(logging.Handler):
            def __init__(self, log_records):
                super().__init__()
                self.log_records = log_records
                
            def emit(self, record):
                self.log_records.append(record.getMessage())
                
        self.log_handler = TestLogHandler(self.log_records)
        self.test_logger.addHandler(self.log_handler)
    
    def test_mask_sensitive_data_dict(self):
        # 测试字典敏感数据遮盖
        masked = mask_sensitive_data(self.sensitive_dict)
        
        # 验证敏感字段被遮盖
        self.assertEqual(masked["access_token"], "******")
        self.assertEqual(masked["refresh_token"], "******")
        self.assertEqual(masked["nested"]["api_key"], "******")
        
        # 验证非敏感字段未变
        self.assertEqual(masked["user"], "test_user")
        self.assertEqual(masked["nested"]["normal"], "normal_data")
    
    def test_mask_sensitive_data_list(self):
        # 测试列表敏感数据遮盖
        test_list = [self.sensitive_dict, {"password": "123456"}]
        masked = mask_sensitive_data(test_list)
        
        self.assertEqual(masked[0]["access_token"], "******")
        self.assertEqual(masked[1]["password"], "******")
    
    def test_safe_str(self):
        # 测试安全字符串处理
        safe = safe_str(self.sensitive_str)
        
        # 验证敏感字符串被遮盖
        self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", safe)
        self.assertIn("******", safe)
    
    def test_safe_log_with_dict(self):
        # 测试带字典的安全日志记录
        safe_log(self.test_logger.info, "测试消息", self.sensitive_dict)
        
        # 验证日志消息
        log_msg = self.log_records[-1]
        self.assertIn("测试消息", log_msg)
        self.assertIn("******", log_msg)
        self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", log_msg)
    
    def test_safe_log_with_exception(self):
        # 测试带异常的安全日志记录
        test_exception = Exception("Error with token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
        safe_log(self.test_logger.error, "错误消息", exception=test_exception)
        
        # 验证日志消息
        log_msg = self.log_records[-1]
        self.assertIn("错误消息", log_msg)
        self.assertIn("Exception", log_msg)
        self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", log_msg)
        
    def test_safe_log_with_simple_data(self):
        # 测试带普通字符串的安全日志记录
        safe_log(self.test_logger.info, "普通消息", "这是普通数据")
        
        # 验证日志消息
        log_msg = self.log_records[-1]
        self.assertIn("普通消息", log_msg)
        self.assertIn("这是普通数据", log_msg)
        
    def test_safe_log_without_data(self):
        # 测试不带数据的安全日志记录
        safe_log(self.test_logger.info, "仅消息")
        
        # 验证日志消息
        log_msg = self.log_records[-1]
        self.assertEqual("仅消息", log_msg)

if __name__ == '__main__':
    unittest.main() 