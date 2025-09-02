# Tab 1: Pipeline管理

> 参考：[global_context.md](./global_context.md) - 全局上下文和规范

## 1. 前端方案

### 1.1 界面布局
```
┌─────────────────────────────────────────────────────────────────┐
│  Pipeline管理                                    [+ 创建Pipeline] │
├─────────────────────────────────────────────────────────────────┤
│  🔍 搜索: [___________] [类型▼] [状态▼]                 [搜索]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Pipeline列表（表格）                                             │
│  ┌────────┬──────────────┬──────────┬────────┬────────┬────────┐│
│  │ ID     │ 名称         │ 类型      │使用数  │ 状态   │ 操作    ││
│  ├────────┼──────────────┼──────────┼────────┼────────┼────────┤│
│  │story_v3│YouTube故事   │content   │5个配置 │ ✅启用 │查看 编辑││
│  │meta_gen│元数据生成    │metadata  │3个配置 │ ✅启用 │查看 编辑││
│  └────────┴──────────────┴──────────┴────────┴────────┴────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 组件结构
```tsx
// components/AutoPublish/PipelineManager.tsx
import React, { useState, useEffect } from 'react';
import { 
  Card, Table, Button, Modal, Form, Input, Select, 
  Tag, Space, Drawer, Descriptions, message, Popconfirm 
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons';

interface Pipeline {
  pipeline_id: string;
  pipeline_name: string;
  pipeline_type: string;
  pipeline_class: string;
  config_schema: ConfigSchema;
  supported_platforms: string[];
  version: string;
  status: 'active' | 'inactive' | 'testing';
  metadata?: any;
  created_at: string;
  updated_at: string;
  usage_count?: number;  // 关联的PublishConfig数量
}

interface ConfigSchema {
  type: 'object';
  properties: {
    [key: string]: Parameter;
  };
  required?: string[];
}

interface Parameter {
  type: 'string' | 'integer' | 'number' | 'boolean' | 'array' | 'object';
  description?: string;
  default?: any;
  minimum?: number;
  maximum?: number;
  enum?: any[];
  items?: Parameter;  // for array type
  properties?: { [key: string]: Parameter };  // for object type
}

interface PublishConfigSummary {
  config_id: string;
  config_name: string;
  group_name: string;
  is_active: boolean;
  task_count: number;
}
```

### 1.3 Pipeline创建/编辑表单

#### 1.3.1 基本信息部分
```tsx
<Form.Item name="pipeline_id" label="Pipeline ID" 
  rules={[{ required: true, pattern: /^[a-z0-9_]+$/ }]}>
  <Input placeholder="例如: youtube_story_v3" disabled={isEdit} />
</Form.Item>

<Form.Item name="pipeline_name" label="Pipeline名称" 
  rules={[{ required: true }]}>
  <Input placeholder="例如: YouTube故事生成V3" />
</Form.Item>

<Form.Item name="pipeline_type" label="类型" 
  rules={[{ required: true }]}>
  <Select>
    <Option value="content_generation">内容生成</Option>
    <Option value="metadata">元数据处理</Option>
    <Option value="content_processing">内容处理</Option>
    <Option value="analysis">分析</Option>
  </Select>
</Form.Item>

<Form.Item name="pipeline_class" label="执行类" 
  rules={[{ required: true }]}>
  <Input placeholder="例如: story_pipeline_v3_runner.StoryPipelineV3Runner" />
</Form.Item>

<Form.Item name="supported_platforms" label="支持平台">
  <Select mode="multiple">
    <Option value="youtube">YouTube</Option>
    <Option value="bilibili">Bilibili</Option>
    <Option value="douyin">抖音</Option>
    <Option value="tiktok">TikTok</Option>
  </Select>
</Form.Item>
```

#### 1.3.2 参数配置部分（动态表单）
```tsx
interface ParameterConfig {
  name: string;
  type: string;
  required: boolean;
  description?: string;
  default?: any;
  minimum?: number;
  maximum?: number;
}

const ParameterForm: React.FC = () => {
  const [parameters, setParameters] = useState<ParameterConfig[]>([]);
  
  const addParameter = () => {
    setParameters([...parameters, {
      name: '',
      type: 'string',
      required: false
    }]);
  };
  
  const removeParameter = (index: number) => {
    setParameters(parameters.filter((_, i) => i !== index));
  };
  
  return (
    <>
      {parameters.map((param, index) => (
        <Card key={index} size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={6}>
              <Input placeholder="参数名" value={param.name} 
                onChange={e => updateParameter(index, 'name', e.target.value)} />
            </Col>
            <Col span={4}>
              <Select value={param.type} 
                onChange={v => updateParameter(index, 'type', v)}>
                <Option value="string">字符串</Option>
                <Option value="integer">整数</Option>
                <Option value="number">数字</Option>
                <Option value="boolean">布尔</Option>
                <Option value="array">数组</Option>
                <Option value="object">对象</Option>
              </Select>
            </Col>
            <Col span={3}>
              <Checkbox checked={param.required}
                onChange={e => updateParameter(index, 'required', e.target.checked)}>
                必填
              </Checkbox>
            </Col>
            <Col span={8}>
              <Input placeholder="描述" value={param.description}
                onChange={e => updateParameter(index, 'description', e.target.value)} />
            </Col>
            <Col span={2}>
              <Button danger icon={<DeleteOutlined />} 
                onClick={() => removeParameter(index)} />
            </Col>
          </Row>
          
          {/* 根据类型显示额外配置 */}
          {param.type === 'integer' || param.type === 'number' ? (
            <Row gutter={16} style={{ marginTop: 8 }}>
              <Col span={6}>
                <InputNumber placeholder="最小值" value={param.minimum}
                  onChange={v => updateParameter(index, 'minimum', v)} />
              </Col>
              <Col span={6}>
                <InputNumber placeholder="最大值" value={param.maximum}
                  onChange={v => updateParameter(index, 'maximum', v)} />
              </Col>
              <Col span={6}>
                <InputNumber placeholder="默认值" value={param.default}
                  onChange={v => updateParameter(index, 'default', v)} />
              </Col>
            </Row>
          ) : null}
        </Card>
      ))}
      
      <Button type="dashed" icon={<PlusOutlined />} onClick={addParameter} block>
        添加参数
      </Button>
    </>
  );
};
```

### 1.4 Pipeline详情抽屉
```tsx
const PipelineDetail: React.FC<{ pipeline: Pipeline }> = ({ pipeline }) => {
  const [configs, setConfigs] = useState<PublishConfigSummary[]>([]);
  
  return (
    <Drawer title="Pipeline详情" width={800} visible={visible} onClose={onClose}>
      <Descriptions title="基本信息" bordered column={2}>
        <Descriptions.Item label="ID">{pipeline.pipeline_id}</Descriptions.Item>
        <Descriptions.Item label="名称">{pipeline.pipeline_name}</Descriptions.Item>
        <Descriptions.Item label="类型">{pipeline.pipeline_type}</Descriptions.Item>
        <Descriptions.Item label="版本">{pipeline.version}</Descriptions.Item>
        <Descriptions.Item label="执行类" span={2}>
          {pipeline.pipeline_class}
        </Descriptions.Item>
        <Descriptions.Item label="支持平台" span={2}>
          {pipeline.supported_platforms.map(p => (
            <Tag key={p}>{p}</Tag>
          ))}
        </Descriptions.Item>
        <Descriptions.Item label="状态">
          <Tag color={pipeline.status === 'active' ? 'green' : 'default'}>
            {pipeline.status}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="创建时间">{pipeline.created_at}</Descriptions.Item>
      </Descriptions>
      
      <Divider />
      
      <Card title="参数配置" size="small">
        {Object.entries(pipeline.config_schema.properties).map(([key, param]) => (
          <div key={key} style={{ marginBottom: 8 }}>
            <Text strong>{key}</Text>
            <Tag color={pipeline.config_schema.required?.includes(key) ? 'red' : 'default'}>
              {pipeline.config_schema.required?.includes(key) ? '必填' : '可选'}
            </Tag>
            <Tag>{param.type}</Tag>
            {param.description && <Text type="secondary"> - {param.description}</Text>}
            {param.default !== undefined && (
              <Text type="secondary"> (默认: {JSON.stringify(param.default)})</Text>
            )}
          </div>
        ))}
      </Card>
      
      <Divider />
      
      <Card title={`关联的发布配置 (${configs.length})`} size="small">
        <List
          dataSource={configs}
          renderItem={config => (
            <List.Item 
              actions={[
                <Button type="link" onClick={() => navigateToConfig(config.config_id)}>
                  查看
                </Button>
              ]}>
              <List.Item.Meta
                title={config.config_name}
                description={`${config.group_name} - ${config.task_count}次执行`}
              />
              <Tag color={config.is_active ? 'green' : 'default'}>
                {config.is_active ? '启用' : '停用'}
              </Tag>
            </List.Item>
          )}
        />
      </Card>
    </Drawer>
  );
};
```

## 2. 需要的接口

### 2.1 复用现有接口
```http
GET /api/auto-publish/pipelines
POST /api/auto-publish/pipelines/register
```

### 2.2 新增接口

#### 2.2.1 获取Pipeline详情
```http
GET /api/auto-publish/pipelines/{pipeline_id}

响应:
{
  "pipeline_id": "youtube_story_v3",
  "pipeline_name": "YouTube故事生成V3",
  "pipeline_type": "content_generation",
  "pipeline_class": "story_pipeline_v3_runner.StoryPipelineV3Runner",
  "config_schema": {
    "type": "object",
    "properties": {
      "video_id": {
        "type": "string",
        "description": "YouTube视频ID"
      },
      "image_library": {
        "type": "string",
        "description": "图库名称",
        "default": "default",
        "enum": ["default", "nature", "cartoon", "abstract"]
      },
      "image_duration": {
        "type": "integer",
        "description": "单个图片持续时长(秒)",
        "default": 5,
        "minimum": 3,
        "maximum": 10
      }
    },
    "required": ["video_id"]
  },
  "supported_platforms": ["youtube", "bilibili"],
  "version": "3.0.0",
  "status": "active",
  "metadata": {},
  "created_at": "2024-12-25T10:00:00Z",
  "updated_at": "2024-12-25T10:00:00Z",
  "usage_count": 5
}
```

#### 2.2.2 更新Pipeline
```http
PUT /api/auto-publish/pipelines/{pipeline_id}

请求体: 同创建，但pipeline_id不可修改

响应: 更新后的Pipeline对象
```

#### 2.2.3 删除Pipeline
```http
DELETE /api/auto-publish/pipelines/{pipeline_id}

响应:
{
  "success": true,
  "message": "Pipeline deleted successfully"
}
```

#### 2.2.4 获取Pipeline关联的配置
```http
GET /api/auto-publish/pipelines/{pipeline_id}/configs

Query参数:
  - page: number (默认1)
  - page_size: number (默认10)

响应:
{
  "configs": [
    {
      "config_id": "config_001",
      "config_name": "每日故事发布",
      "group_id": "story_channels",
      "group_name": "故事频道组",
      "is_active": true,
      "task_count": 156,
      "last_execution": "2024-12-25T20:00:00Z"
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 10
}
```

## 3. 后端执行流程

### 3.1 Pipeline注册流程
```python
@router.post("/pipelines/register")
async def register_pipeline(
    request: RegisterPipelineRequest,
    current_user = Depends(get_current_user)
):
    """注册新的Pipeline"""
    registry = get_pipeline_registry()
    
    # 1. 验证pipeline_id唯一性
    existing = registry.get_pipeline(request.pipeline_id)
    if existing:
        raise HTTPException(400, "Pipeline ID already exists")
    
    # 2. 验证config_schema格式
    try:
        validate_json_schema(request.config_schema)
    except Exception as e:
        raise HTTPException(400, f"Invalid config schema: {e}")
    
    # 3. 验证pipeline_class存在（可选）
    if not verify_pipeline_class(request.pipeline_class):
        logger.warning(f"Pipeline class not found: {request.pipeline_class}")
    
    # 4. 注册Pipeline
    success = registry.register_pipeline(
        pipeline_id=request.pipeline_id,
        pipeline_name=request.pipeline_name,
        pipeline_type=request.pipeline_type,
        pipeline_class=request.pipeline_class,
        config_schema=request.config_schema,
        supported_platforms=request.supported_platforms,
        version=request.version,
        metadata=request.metadata
    )
    
    if not success:
        raise HTTPException(500, "Failed to register pipeline")
    
    return {"success": True, "pipeline_id": request.pipeline_id}
```

### 3.2 获取Pipeline详情流程
```python
@router.get("/pipelines/{pipeline_id}")
async def get_pipeline_detail(
    pipeline_id: str,
    current_user = Depends(get_current_user)
):
    """获取Pipeline详细信息"""
    registry = get_pipeline_registry()
    db = get_db_manager()
    
    # 1. 获取Pipeline基本信息
    pipeline = registry.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(404, "Pipeline not found")
    
    # 2. 统计使用情况
    usage_count = db.query_one("""
        SELECT COUNT(*) as count
        FROM publish_configs
        WHERE pipeline_id = ? AND is_active = 1
    """, (pipeline_id,))['count']
    
    # 3. 组装返回数据
    result = pipeline.to_dict()
    result['usage_count'] = usage_count
    
    return result
```

### 3.3 更新Pipeline流程
```python
@router.put("/pipelines/{pipeline_id}")
async def update_pipeline(
    pipeline_id: str,
    request: UpdatePipelineRequest,
    current_user = Depends(get_current_user)
):
    """更新Pipeline配置"""
    registry = get_pipeline_registry()
    
    # 1. 检查Pipeline是否存在
    pipeline = registry.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(404, "Pipeline not found")
    
    # 2. 验证是否有活跃的任务
    db = get_db_manager()
    active_tasks = db.query_one("""
        SELECT COUNT(*) as count
        FROM auto_publish_tasks
        WHERE pipeline_id = ? 
          AND pipeline_status IN ('pending', 'running')
    """, (pipeline_id,))['count']
    
    if active_tasks > 0:
        raise HTTPException(400, "Cannot update pipeline with active tasks")
    
    # 3. 更新Pipeline
    update_fields = {}
    if request.pipeline_name:
        update_fields['pipeline_name'] = request.pipeline_name
    if request.config_schema:
        validate_json_schema(request.config_schema)
        update_fields['config_schema'] = request.config_schema
    if request.supported_platforms:
        update_fields['supported_platforms'] = request.supported_platforms
    if request.version:
        update_fields['version'] = request.version
    if request.status:
        update_fields['status'] = request.status
    
    success = registry.update_pipeline(pipeline_id, **update_fields)
    
    if not success:
        raise HTTPException(500, "Failed to update pipeline")
    
    return registry.get_pipeline(pipeline_id).to_dict()
```

## 4. 数据模型

### 4.1 使用现有模型
```python
# pipeline_registry.py中的PipelineModel
class PipelineModel(Base):
    __tablename__ = 'pipeline_registry'
    
    pipeline_id = Column(String(50), primary_key=True)
    pipeline_name = Column(String(100), nullable=False)
    pipeline_type = Column(String(50), nullable=False)
    pipeline_class = Column(String(200), nullable=False)
    config_schema = Column(JSON)
    supported_platforms = Column(JSON, default=["youtube"])
    version = Column(String(20), default="1.0.0")
    status = Column(String(20), default="active")
    extra_metadata = Column('metadata', JSON)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
```

### 4.2 扩展方法
```python
class PipelineRegistry:
    def update_pipeline(self, pipeline_id: str, **kwargs) -> bool:
        """更新Pipeline信息"""
        with self.get_session() as session:
            pipeline = session.query(PipelineModel).filter_by(
                pipeline_id=pipeline_id
            ).first()
            
            if not pipeline:
                return False
            
            for key, value in kwargs.items():
                if hasattr(pipeline, key):
                    setattr(pipeline, key, value)
            
            pipeline.updated_at = datetime.now()
            session.commit()
            return True
    
    def delete_pipeline(self, pipeline_id: str) -> bool:
        """删除Pipeline（软删除）"""
        return self.update_pipeline(pipeline_id, status='deleted')
    
    def get_pipeline_configs(self, pipeline_id: str, page: int = 1, 
                           page_size: int = 10) -> dict:
        """获取Pipeline关联的配置"""
        with self.get_session() as session:
            query = session.query(PublishConfigModel).filter_by(
                pipeline_id=pipeline_id,
                is_active=True
            )
            
            total = query.count()
            configs = query.offset((page - 1) * page_size).limit(page_size).all()
            
            return {
                'configs': [c.to_dict() for c in configs],
                'total': total,
                'page': page,
                'page_size': page_size
            }
```

## 5. 数据库交互

### 5.1 核心SQL查询

```sql
-- 获取Pipeline列表（含使用统计）
SELECT 
    pr.*,
    COUNT(DISTINCT pc.config_id) as usage_count,
    COUNT(DISTINCT apt.task_id) as task_count
FROM pipeline_registry pr
LEFT JOIN publish_configs pc ON pr.pipeline_id = pc.pipeline_id AND pc.is_active = 1
LEFT JOIN auto_publish_tasks apt ON pr.pipeline_id = apt.pipeline_id
WHERE pr.status != 'deleted'
GROUP BY pr.pipeline_id
ORDER BY pr.created_at DESC;

-- 获取Pipeline关联的配置详情
SELECT 
    pc.*,
    ag.group_name,
    COUNT(apt.task_id) as task_count,
    MAX(apt.created_at) as last_execution
FROM publish_configs pc
LEFT JOIN account_groups ag ON pc.group_id = ag.group_id
LEFT JOIN auto_publish_tasks apt ON pc.config_id = apt.config_id
WHERE pc.pipeline_id = ?
  AND pc.is_active = 1
GROUP BY pc.config_id
ORDER BY pc.created_at DESC
LIMIT ? OFFSET ?;

-- 检查Pipeline是否可以删除
SELECT 
    COUNT(DISTINCT pc.config_id) as active_configs,
    COUNT(DISTINCT apt.task_id) as pending_tasks
FROM pipeline_registry pr
LEFT JOIN publish_configs pc ON pr.pipeline_id = pc.pipeline_id AND pc.is_active = 1
LEFT JOIN auto_publish_tasks apt ON pr.pipeline_id = apt.pipeline_id 
    AND apt.pipeline_status IN ('pending', 'running')
WHERE pr.pipeline_id = ?;
```

## 6. 前端实现要点

### 6.1 参数配置的动态表单
```tsx
// 将参数配置转换为表单值
const schemaToFormValues = (schema: ConfigSchema) => {
  const parameters = Object.entries(schema.properties).map(([name, param]) => ({
    name,
    type: param.type,
    required: schema.required?.includes(name) || false,
    description: param.description,
    default: param.default,
    minimum: param.minimum,
    maximum: param.maximum,
    enum: param.enum
  }));
  return parameters;
};

// 将表单值转换为schema
const formValuesToSchema = (parameters: ParameterConfig[]): ConfigSchema => {
  const properties: any = {};
  const required: string[] = [];
  
  parameters.forEach(param => {
    properties[param.name] = {
      type: param.type,
      description: param.description,
      default: param.default,
      minimum: param.minimum,
      maximum: param.maximum,
      enum: param.enum
    };
    
    if (param.required) {
      required.push(param.name);
    }
  });
  
  return {
    type: 'object',
    properties,
    required: required.length > 0 ? required : undefined
  };
};
```

### 6.2 跨Tab跳转
```tsx
const navigateToConfig = (configId: string) => {
  // 跳转到发布配置Tab，并高亮指定配置
  navigate(`/auto-publish?tab=config&highlight=${configId}`);
};
```

### 6.3 搜索和筛选
```tsx
const [filters, setFilters] = useState({
  search: '',
  type: '',
  status: 'active'
});

const filteredPipelines = pipelines.filter(p => {
  const matchSearch = !filters.search || 
    p.pipeline_id.includes(filters.search) ||
    p.pipeline_name.includes(filters.search);
  
  const matchType = !filters.type || p.pipeline_type === filters.type;
  const matchStatus = !filters.status || p.status === filters.status;
  
  return matchSearch && matchType && matchStatus;
});
```

## 7. 测试要点

### 7.1 功能测试
- [ ] Pipeline创建功能
- [ ] 参数动态添加/删除
- [ ] Pipeline编辑（包括参数修改）
- [ ] Pipeline删除（检查关联）
- [ ] 搜索和筛选功能
- [ ] 跨Tab跳转功能

### 7.2 验证测试
- [ ] Pipeline ID格式验证
- [ ] 参数类型验证
- [ ] 必填项验证
- [ ] 数值范围验证

### 7.3 边界测试
- [ ] 大量参数的Pipeline
- [ ] 复杂嵌套的参数结构
- [ ] 并发创建/更新

## 8. 实施要求

1. **Pipeline ID命名规范**：使用小写字母、数字和下划线，格式：`^[a-z0-9_]+$`，长度3-50字符
2. **版本管理**：Pipeline更新时版本号递增，格式：`v{major}.{minor}.{patch}`
3. **兼容性**：修改参数schema时保持向后兼容，新增字段设置默认值
4. **权限控制**：创建和查看需要普通权限，更新和删除需要管理员权限
5. **数据一致性**：Pipeline删除前检查是否有关联的配置，有则禁止删除