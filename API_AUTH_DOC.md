# API 认证系统文档

## 概述

本API服务支持Bearer Token认证机制，提供用户注册、登录、密码管理等功能。认证可通过环境变量配置开启或关闭。

## 环境配置

在 `.env` 文件中配置以下参数：

```bash
# 是否启用认证 (true/false)
AUTH_ENABLED=true

# 注册邀请码
INVITE_CODE=15361578057  

# 是否启用CORS (true/false)
CORS_ENABLED=true

# CORS允许的来源
CORS_ORIGIN=http://localhost:3000
```

## 认证流程

1. **注册账号**：使用邀请码注册新用户
2. **登录获取API Key**：使用用户名密码登录，获取API Key
3. **使用API Key访问接口**：在请求头中携带Bearer Token

## API 接口说明

### 1. 用户注册

**接口**: `POST /api/auth/register`

**请求体**:
```json
{
    "username": "testuser",
    "password": "password123",
    "invite_code": "15361578057"
}
```

**响应**:
```json
{
    "username": "testuser",
    "api_key": "550e8400-e29b-41d4-a716-446655440000",
    "message": "注册成功"
}
```

**错误响应**:
- 400: 无效的邀请码 / 用户名已存在
- 500: 注册失败

### 2. 用户登录

**接口**: `POST /api/auth/login`

**请求体**:
```json
{
    "username": "testuser",
    "password": "password123"
}
```

**响应**:
```json
{
    "username": "testuser",
    "api_key": "550e8400-e29b-41d4-a716-446655440000",
    "message": "登录成功"
}
```

**错误响应**:
- 401: 用户名或密码错误
- 403: 用户已被禁用

### 3. 修改密码

**接口**: `POST /api/auth/change-password`

**认证**: 需要Bearer Token

**请求头**:
```
Authorization: Bearer {api_key}
```

**请求体**:
```json
{
    "old_password": "password123",
    "new_password": "newpassword456"
}
```

**响应**:
```json
{
    "message": "密码修改成功"
}
```

**错误响应**:
- 400: 旧密码错误
- 401: 未授权（缺少或无效的Token）
- 500: 密码修改失败

### 4. 重置API Key

**接口**: `POST /api/auth/reset-api-key`

**认证**: 需要Bearer Token

**请求头**:
```
Authorization: Bearer {api_key}
```

**响应**:
```json
{
    "username": "testuser",
    "api_key": "新的-uuid-api-key",
    "message": "API Key重置成功"
}
```

**错误响应**:
- 401: 未授权（缺少或无效的Token）
- 500: API Key重置失败

## 使用Bearer Token访问其他接口

当 `AUTH_ENABLED=true` 时，所有业务接口都需要在请求头中携带Bearer Token：

```bash
# 示例：获取任务状态
curl -X GET http://localhost:51082/api/pipeline/status/{task_id} \
  -H "Authorization: Bearer 550e8400-e29b-41d4-a716-446655440000"

# 示例：运行Pipeline
curl -X POST http://localhost:51082/api/pipeline/run \
  -H "Authorization: Bearer 550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "test123",
    "creator_id": "user1"
  }'
```

## 认证开关说明

### 启用认证 (AUTH_ENABLED=true)
- 所有业务接口需要Bearer Token认证
- 未提供Token或Token无效将返回401错误
- 用户账号被禁用返回403错误

### 禁用认证 (AUTH_ENABLED=false)
- 所有业务接口可以自由访问，无需Token
- 认证相关接口（修改密码、重置API Key）仍需要Token
- 适用于开发环境或内网环境

## Python 客户端示例

```python
import requests

# 基础URL
BASE_URL = "http://localhost:51082"

# 1. 注册
def register(username, password, invite_code):
    response = requests.post(f"{BASE_URL}/api/auth/register", json={
        "username": username,
        "password": password,
        "invite_code": invite_code
    })
    return response.json()

# 2. 登录
def login(username, password):
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": username,
        "password": password
    })
    return response.json()

# 3. 使用API Key访问接口
def call_api_with_auth(api_key):
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    # 示例：获取统计信息
    response = requests.get(
        f"{BASE_URL}/api/pipeline/statistics",
        headers=headers
    )
    return response.json()

# 使用示例
if __name__ == "__main__":
    # 注册新用户
    reg_result = register("testuser", "password123", "15361578057")
    print(f"注册成功，API Key: {reg_result['api_key']}")
    
    # 登录获取API Key
    login_result = login("testuser", "password123")
    api_key = login_result['api_key']
    
    # 使用API Key访问接口
    stats = call_api_with_auth(api_key)
    print(f"统计信息: {stats}")
```

## JavaScript/TypeScript 客户端示例

```typescript
// 基础配置
const BASE_URL = 'http://localhost:51082';
let apiKey: string | null = null;

// 注册
async function register(username: string, password: string, inviteCode: string) {
    const response = await fetch(`${BASE_URL}/api/auth/register`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username,
            password,
            invite_code: inviteCode
        })
    });
    return response.json();
}

// 登录
async function login(username: string, password: string) {
    const response = await fetch(`${BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username,
            password
        })
    });
    const data = await response.json();
    apiKey = data.api_key; // 保存API Key
    return data;
}

// 带认证的API调用
async function apiCall(endpoint: string, options: RequestInit = {}) {
    const headers = {
        ...options.headers,
        'Authorization': `Bearer ${apiKey}`
    };
    
    const response = await fetch(`${BASE_URL}${endpoint}`, {
        ...options,
        headers
    });
    
    if (response.status === 401) {
        throw new Error('未授权，请重新登录');
    }
    
    return response.json();
}

// 使用示例
async function example() {
    // 登录
    await login('testuser', 'password123');
    
    // 调用需要认证的接口
    const stats = await apiCall('/api/pipeline/statistics');
    console.log('统计信息:', stats);
}
```

## 安全建议

1. **生产环境必须启用HTTPS**：API Key在HTTP传输中是明文的
2. **定期更换API Key**：使用重置API Key接口定期更新
3. **保护好邀请码**：不要将邀请码提交到公开代码仓库
4. **使用强密码**：密码使用bcrypt加密存储
5. **监控异常登录**：记录和监控登录失败次数

## 故障排查

### 常见错误

1. **401 Unauthorized**
   - 检查是否提供了Authorization头
   - 确认Bearer Token格式正确
   - 验证API Key是否有效

2. **403 Forbidden**
   - 用户账号可能已被禁用
   - 联系管理员激活账号

3. **400 Bad Request**
   - 检查请求体格式是否正确
   - 验证邀请码是否正确（注册时）

4. **500 Internal Server Error**
   - 数据库连接问题
   - 查看服务器日志获取详细错误信息

## 迁移说明

从无认证迁移到有认证系统：

1. 安装依赖：
```bash
pip install passlib[bcrypt] python-jose[cryptography]
```

2. 配置环境变量（见上方配置说明）

3. 重启服务，数据库会自动创建users表

4. 使用邀请码注册第一个用户账号

5. 更新客户端代码，添加Bearer Token认证头