#!/usr/bin/env python3
"""
测试运行脚本，用于执行邮件服务和Graph API的单元测试和集成测试。
可以使用真实API或模拟API进行测试。

使用方法:
    python run_tests.py                # 运行所有测试
    python run_tests.py --unit-only    # 只运行单元测试
    python run_tests.py --real-api     # 尝试使用真实API运行测试
    python run_tests.py --mock-only    # 强制使用模拟API
"""
import os
import sys
import argparse
import unittest
import pytest
import asyncio
from pathlib import Path

# 添加项目根目录到sys.path
current_dir = Path(__file__).parent
backend_dir = current_dir.parent.parent.parent
sys.path.append(str(backend_dir))

# 导入测试配置模块
from tests.utils.mail.test_config import create_sample_config_file

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='运行邮件服务和Graph API测试')
    parser.add_argument('--unit-only', action='store_true', help='只运行单元测试')
    parser.add_argument('--real-api', action='store_true', help='尝试使用真实API运行测试')
    parser.add_argument('--mock-only', action='store_true', help='强制使用模拟API')
    return parser.parse_args()

def run_unit_tests():
    """运行单元测试"""
    print("=== 运行单元测试 ===")
    unittest_loader = unittest.TestLoader()
    
    # 发现并运行单元测试
    test_suite = unittest_loader.discover(
        start_dir=str(current_dir),
        pattern='test_*.py'
    )
    
    unittest_runner = unittest.TextTestRunner(verbosity=2)
    result = unittest_runner.run(test_suite)
    
    return result.wasSuccessful()

def run_integration_tests(mock_only=False):
    """运行集成测试"""
    print("=== 运行集成测试 ===")
    
    # 设置环境变量来控制测试模式
    if mock_only:
        os.environ['FORCE_MOCK_TESTS'] = 'true'
        print("已强制使用模拟API进行测试")
    
    # 使用pytest运行标记为asyncio的测试
    args = [
        str(current_dir),  # 测试目录
        "-v",              # 详细输出
        "-xvs",            # 失败时立即停止，详细，不捕获输出
    ]
    
    result = pytest.main(args)
    return result == 0  # 0表示成功

def create_test_config_if_not_exists():
    """如果配置文件不存在，创建示例配置"""
    config_path = os.path.join(current_dir, 'test_ms_config.json')
    
    if not os.path.exists(config_path):
        # 创建示例配置文件
        create_sample_config_file()

def main():
    """主函数"""
    args = parse_args()
    
    # 创建配置文件（如果不存在）
    create_test_config_if_not_exists()
    
    success = True
    
    # 运行单元测试
    if not args.real_api or args.unit_only:
        unit_success = run_unit_tests()
        success = success and unit_success
    
    # 运行集成测试
    if not args.unit_only:
        integration_success = run_integration_tests(mock_only=args.mock_only)
        success = success and integration_success
    
    # 返回适当的退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 