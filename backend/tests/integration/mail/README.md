# 邮件服务和 Microsoft Graph API 测试

本目录包含用于测试邮件服务和Microsoft Graph API集成的测试代码。这些测试旨在验证应用程序中的邮件发送功能，包括授权令牌处理、邮件发送、错误处理等。

## 测试类型

测试分为两种类型：

1. **单元测试**：使用模拟(mock)对象测试各个组件的独立功能
2. **集成测试**：测试组件之间的交互，可选择使用真实的Microsoft Graph API

## 设置测试环境

### 基本设置

1. 确保已安装所有依赖项：
   ```bash
   pip install pytest pytest-asyncio
   ```

2. 首次运行测试脚本将创建示例配置文件：
   ```bash
   python run_tests.py
   ```

### 配置真实API测试

要使用真实的Microsoft Graph API进行测试，您需要：

1. 复制示例配置文件并填写您的凭据：
   ```bash
   cp test_ms_config.json.sample test_ms_config.json
   ```

2. 编辑`test_ms_config.json`文件，填写以下信息：
   ```json
   {
     "client_id": "你的应用程序ID",
     "tenant_id": "你的租户ID",
     "client_secret": "你的客户端密钥",
     "test_token": "测试访问令牌",
     "test_refresh_token": "测试刷新令牌"
   }
   ```

3. 或者，您可以通过环境变量提供这些值：
   ```bash
   export TEST_MS_CLIENT_ID="你的应用程序ID"
   export TEST_MS_TENANT_ID="你的租户ID"
   export TEST_MS_CLIENT_SECRET="你的客户端密钥"
   export TEST_MS_TOKEN="测试访问令牌"
   export TEST_MS_REFRESH_TOKEN="测试刷新令牌"
   ```

## 运行测试

### 运行所有测试

```bash
python run_tests.py
```

### 只运行单元测试

```bash
python run_tests.py --unit-only
```

### 尝试使用真实API

```bash
python run_tests.py --real-api
```

### 强制使用模拟API

```bash
python run_tests.py --mock-only
```

## 主要测试用例

### Graph API 测试

1. **基本功能测试**
   - 测试令牌验证
   - 测试邮件发送
   - 测试刷新令牌

2. **错误处理测试**
   - 测试令牌验证失败
   - 测试刷新令牌失败
   - 测试邮件发送失败

3. **安全日志测试**
   - 确保敏感信息不会被记录到日志

### 邮件服务测试

1. **邮件发送功能**
   - 测试发送带附件的邮件
   - 测试发送简单邮件

2. **令牌管理**
   - 测试令牌自动刷新
   - 测试令牌过期处理

3. **错误处理**
   - 测试权限错误处理
   - 测试其他异常处理

## 特殊注意事项

1. **请勿在生产环境中使用测试配置**：测试配置包含敏感信息，应妥善保管，避免泄露。

2. **邮件发送测试**：真实API测试中，邮件发送测试默认被跳过，以避免发送不必要的邮件。

3. **错误处理改进**：我们最近修复了两个主要问题：
   - `BaseRequestConfiguration`对象的使用方式错误
   - `PermissionError`异常使用关键字参数的问题

这些测试已更新，以确保这些问题在将来不会再次出现。 