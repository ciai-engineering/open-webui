# API测试说明文档

本目录包含了用于测试Open-WebUI后端APIs的测试用例，主要覆盖：

1. SSO登录流程
2. 邮件发送功能
3. 用户认证与授权

## 测试文件说明

- `test_api_endpoints.py`：包含针对SSO登录和邮件发送API的测试用例
- `run_api_tests.sh`：便捷运行测试的脚本

## 如何运行测试

### 方法1：使用运行脚本

```bash
# 进入tests/apis目录
cd /path/to/open-webui/backend/tests/apis

# 运行所有API测试
./run_api_tests.sh

# 运行特定测试文件
./run_api_tests.sh test_api_endpoints.py
```

### 方法2：直接使用pytest

```bash
# 设置PYTHONPATH（确保可以正确导入模块）
export PYTHONPATH=/path/to/open-webui/backend

# 进入tests/apis目录
cd /path/to/open-webui/backend/tests/apis

# 运行测试
pytest -xvs test_api_endpoints.py
```

## 测试覆盖范围

### SSO登录测试

- 测试SSO初始化登录流程
- 测试SSO登录回调（成功和失败场景）
- 测试SSO登录状态查询

### 邮件发送测试

- 测试休假申请表单提交
- 测试HR文档请求
- 测试错误处理场景

### 用户认证测试

- 测试用户注册
- 测试用户登录
- 测试令牌刷新

## 添加新测试

1. 在`test_api_endpoints.py`中添加新的测试方法，或创建新的测试文件
2. 确保使用了适当的mock对象模拟依赖服务
3. 运行测试验证

## 注意事项

- 运行测试前请确保已安装所有依赖：`pip install -r requirements.txt`
- 测试使用mock对象模拟外部服务，不会实际发送邮件或进行SSO认证
- 测试结果和日志保存在`api_test_log.txt`文件中 