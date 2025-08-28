# 图库管理功能文档

## 功能概述

图库管理功能允许用户预设多个图片库，在创建Pipeline任务时可以从下拉框选择，而不需要手动输入图片路径。剪映草稿生成时会从指定的图库中随机选择图片。

## 系统架构

### 1. 数据库设计

**表名**: `image_libraries`

| 字段 | 类型 | 说明 |
|-----|------|-----|
| id | INTEGER | 主键 |
| library_name | VARCHAR(100) | 图库名称（唯一） |
| library_path | VARCHAR(500) | 图库文件夹路径 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 2. 参数传递流程

```
前端界面
    ↓ (选择图库名称，如 "default")
API接口 (/api/pipeline/run)
    ↓ image_dir = "default"
数据库存储 (pipeline_tasks.image_dir)
    ↓ 保存图库名称
Pipeline执行 (pipeline_core.py)
    ↓ 传递 --image_dir default
草稿生成服务 (generateDraftService.py)
    ↓ 查询数据库获取实际路径
使用图片路径生成草稿
```

## API接口说明

### 获取图库列表

**请求**
```http
GET /api/image_libraries
Authorization: Bearer YOUR_API_KEY
```

**响应**
```json
{
    "success": true,
    "libraries": [
        {
            "id": 1,
            "library_name": "default",
            "library_path": "/Users/xxx/output/images",
            "created_at": "2025-08-28T15:30:45.123456",
            "updated_at": null
        }
    ],
    "count": 1
}
```

### 创建Pipeline任务

**请求**
```http
POST /api/pipeline/run
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
    "video_id": "test_video",
    "creator_id": "test_creator",
    "image_dir": "default",  // 使用图库名称
    "duration": 60,
    "gender": 1,
    "export_video": false,
    "enable_subtitle": true
}
```

## 使用方法

### 1. 初始化默认图库

```bash
python init_image_libraries.py
```

这会创建一个名为 "default" 的图库，路径指向 `./output/images`。

### 2. 添加新图库

```python
from database import get_db_manager

db = get_db_manager()
db.create_image_library({
    'library_name': 'anime',
    'library_path': '/path/to/anime/images'
})
```

### 3. 命令行使用

```bash
# 使用图库名称
python draft_gen/generateDraftService.py \
    --cid test_creator \
    --vid test_video \
    --duration 3 \
    --image_dir default

# 使用绝对路径（向后兼容）
python draft_gen/generateDraftService.py \
    --cid test_creator \
    --vid test_video \
    --duration 3 \
    --image_dir /absolute/path/to/images
```

### 4. 前端集成示例

```javascript
// 获取图库列表
const getImageLibraries = async () => {
    const response = await fetch('/api/image_libraries', {
        headers: {
            'Authorization': `Bearer ${apiKey}`
        }
    });
    const data = await response.json();
    return data.libraries;
};

// 渲染选择框
<select name="image_dir" value={selectedLibrary} onChange={handleChange}>
    {libraries.map(lib => (
        <option key={lib.id} value={lib.library_name}>
            {lib.library_name}
        </option>
    ))}
</select>

// 创建任务
const createTask = async (formData) => {
    const taskData = {
        video_id: formData.video_id,
        creator_id: formData.creator_id,
        image_dir: formData.image_dir || 'default',
        // ... 其他字段
    };
    
    await createPipelineTask(taskData);
};
```

## 特性说明

### 1. 智能解析
- 如果 `image_dir` 是图库名称（如 "default"），自动查询数据库获取路径
- 如果是绝对路径，直接使用（向后兼容）
- 如果找不到指定的图库，自动回退到默认图库

### 2. 默认行为
- 不指定 `image_dir` 时，使用 "default" 图库
- "default" 图库不存在时，使用 `./output/images` 路径

### 3. 扩展性
- 可以随时添加新图库，无需修改代码
- 前端自动显示所有可用图库
- 支持多种图片格式：jpg, jpeg, png, gif, bmp, webp

## 测试验证

### 1. 测试图库功能
```bash
python test_image_library.py
```

### 2. 测试参数传递
```bash
python test_image_library_flow.py
```

### 3. 测试草稿生成
```bash
python test_draft_with_library.py
```

## 注意事项

1. **路径要求**: 图库路径必须存在且包含图片文件
2. **图片格式**: 支持 jpg, jpeg, png, gif, bmp, webp 格式
3. **权限要求**: 确保程序有读取图库路径的权限
4. **向后兼容**: 旧版本直接传递路径的方式仍然支持

## 故障排查

### 问题1: 找不到图库
**原因**: 数据库中没有对应的图库记录
**解决**: 运行 `python init_image_libraries.py` 初始化默认图库

### 问题2: 图片路径无效
**原因**: 图库路径不存在或没有权限
**解决**: 检查路径是否正确，确保有读取权限

### 问题3: API返回401
**原因**: 未提供有效的认证token
**解决**: 在请求头中添加 `Authorization: Bearer YOUR_API_KEY`