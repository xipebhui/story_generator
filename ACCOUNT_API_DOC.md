# 账号管理API文档

## 概述
本文档描述了YouTube账号管理相关的API接口，包括账号的创建、查询、更新和删除功能。

## 认证
所有接口都需要Bearer Token认证：
```
Authorization: Bearer {api_key}
```

## 接口列表

### 1. 创建账号
**POST** `/api/accounts`

创建新的YouTube发布账号。

#### 请求体
```json
{
  "account_id": "string",        // 必需：账号唯一标识
  "account_name": "string",      // 必需：账号名称
  "profile_id": "string",        // 必需：比特浏览器Profile ID
  "window_number": "string",     // 可选：窗口序号
  "description": "string",       // 可选：描述信息
  "is_active": true,            // 可选：是否激活（默认true）
  "channel_url": "string"        // 可选：YouTube频道URL
}
```

#### 响应示例
```json
{
  "message": "账号 测试账号 创建成功",
  "account": {
    "account_id": "test_001",
    "account_name": "测试账号",
    "profile_id": "abc123",
    "window_number": "1001",
    "description": "测试账号描述",
    "is_active": true,
    "channel_url": "https://www.youtube.com/@testchannel",
    "created_at": "2025-08-28 10:00:00",
    "updated_at": "2025-08-28 10:00:00"
  }
}
```

#### 错误响应
- `400 Bad Request`: 账号ID已存在或缺少必需字段
- `401 Unauthorized`: 认证失败

---

### 2. 删除账号
**DELETE** `/api/accounts/{account_id}`

删除指定账号。如果账号有相关的发布任务，将标记为不活跃而非真正删除。

#### 路径参数
- `account_id`: 账号ID

#### 查询参数
- `force`: 布尔值，是否强制删除（默认false）

#### 响应示例

**完全删除的情况：**
```json
{
  "message": "账号 测试账号 已删除",
  "action": "deleted",
  "account_id": "test_001"
}
```

**软删除的情况（有发布任务）：**
```json
{
  "message": "账号 测试账号 有相关发布任务，已标记为不活跃",
  "action": "deactivated",
  "account_id": "test_001"
}
```

#### 错误响应
- `404 Not Found`: 账号不存在
- `500 Internal Server Error`: 删除失败

---

### 3. 查询账号列表
**GET** `/api/accounts`

获取所有账号列表。

#### 查询参数
- `active_only`: 布尔值，是否只返回活跃账号（默认true）

#### 响应示例
```json
{
  "total": 10,
  "accounts": [
    {
      "account_id": "yt_001",
      "account_name": "YouTube账号001",
      "profile_id": "abc123",
      "window_number": "1001",
      "description": "窗口序号: 1001",
      "is_active": true,
      "channel_url": "https://www.youtube.com/@channel001",
      "created_at": "2025-08-20 10:00:00",
      "updated_at": "2025-08-20 10:00:00"
    }
  ]
}
```

---

### 4. 查询单个账号
**GET** `/api/accounts/{account_id}`

获取指定账号的详细信息。

#### 路径参数
- `account_id`: 账号ID

#### 响应示例
```json
{
  "account_id": "yt_001",
  "account_name": "YouTube账号001",
  "profile_id": "abc123",
  "window_number": "1001",
  "description": "窗口序号: 1001",
  "is_active": true,
  "channel_url": "https://www.youtube.com/@channel001",
  "created_at": "2025-08-20 10:00:00",
  "updated_at": "2025-08-20 10:00:00"
}
```

#### 错误响应
- `404 Not Found`: 账号不存在

---

### 5. 更新账号状态
**PUT** `/api/accounts/{account_id}/status`

更新账号的激活状态。

#### 路径参数
- `account_id`: 账号ID

#### 查询参数
- `is_active`: 布尔值，是否激活

#### 响应示例
```json
{
  "message": "账号状态已更新为 激活"
}
```

#### 错误响应
- `404 Not Found`: 账号不存在

---

### 6. 获取账号统计信息
**GET** `/api/accounts/{account_id}/statistics`

获取账号的统计信息，包括发布数量、成功率等。

#### 路径参数
- `account_id`: 账号ID

#### 响应示例
```json
{
  "account_id": "yt_001",
  "total_published": 25,
  "successful_published": 20,
  "failed_published": 5,
  "success_rate": 0.8,
  "last_publish_time": "2025-08-28 09:30:00"
}
```

---

## 数据模型

### Account 对象
```typescript
interface Account {
  account_id: string;         // 账号唯一标识
  account_name: string;       // 账号名称
  profile_id: string;         // 比特浏览器Profile ID
  window_number?: string;     // 窗口序号
  channel_url?: string;       // YouTube频道URL
  description?: string;       // 描述信息
  is_active: boolean;         // 是否激活
  created_at: string;         // 创建时间
  updated_at: string;         // 更新时间
}
```

## 业务逻辑说明

### 账号删除策略
1. **无发布任务的账号**：直接从数据库中删除
2. **有发布任务的账号**：
   - 默认行为：将账号标记为不活跃（`is_active = false`），保留数据
   - 强制删除：使用 `force=true` 参数可以强制删除（不推荐）

### 账号ID规范
- 建议格式：`yt_xxx_description`
- 必须唯一，不可重复
- 一旦创建不可修改

### Profile ID说明
- 必须是有效的比特浏览器Profile ID
- 用于YouTube自动化发布时识别浏览器窗口
- 每个账号必须对应唯一的Profile ID

## 使用示例

### Python示例
```python
import requests

# 配置
BASE_URL = "http://localhost:8000"
API_KEY = "your_api_key"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 创建账号
account_data = {
    "account_id": "yt_new_001",
    "account_name": "新YouTube账号",
    "profile_id": "profile_abc123",
    "description": "测试账号",
    "is_active": True
}

response = requests.post(
    f"{BASE_URL}/api/accounts",
    headers=headers,
    json=account_data
)

if response.status_code == 200:
    print("账号创建成功")
    print(response.json())
else:
    print(f"创建失败: {response.text}")

# 查询账号列表
response = requests.get(
    f"{BASE_URL}/api/accounts",
    headers=headers
)
accounts = response.json()
print(f"共有 {accounts['total']} 个账号")

# 删除账号
account_id = "yt_new_001"
response = requests.delete(
    f"{BASE_URL}/api/accounts/{account_id}",
    headers=headers
)
print(response.json())
```

### JavaScript/TypeScript示例
```javascript
// 创建账号
const createAccount = async () => {
  const response = await fetch('http://localhost:8000/api/accounts', {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer your_api_key',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      account_id: 'yt_new_001',
      account_name: '新YouTube账号',
      profile_id: 'profile_abc123',
      description: '测试账号',
      is_active: true
    })
  });
  
  if (response.ok) {
    const result = await response.json();
    console.log('账号创建成功:', result);
  } else {
    console.error('创建失败:', await response.text());
  }
};

// 删除账号
const deleteAccount = async (accountId) => {
  const response = await fetch(`http://localhost:8000/api/accounts/${accountId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': 'Bearer your_api_key'
    }
  });
  
  const result = await response.json();
  console.log(result.message);
};
```

## 注意事项
1. 所有接口都需要认证，请确保在请求头中包含有效的API密钥
2. 账号ID一旦创建不可修改，请谨慎命名
3. 删除账号前请确认是否有相关的发布任务
4. Profile ID必须是有效的比特浏览器配置
5. 建议定期备份账号数据