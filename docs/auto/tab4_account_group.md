# Tab 4: 账号组管理

> 参考：[global_context.md](./global_context.md) - 全局上下文和规范

## 1. 前端方案

### 1.1 界面布局
```
┌─────────────────────────────────────────────────────────────────┐
│  账号组管理                                        [+ 创建账号组] │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  账号组列表（表格）                                               │
│  ┌────────┬──────────┬──────────┬────────┬────────┬───────────┐│
│  │组ID    │组名称    │类型      │账号数  │状态    │操作        ││
│  ├────────┼──────────┼──────────┼────────┼────────┼───────────┤│
│  │grp_001 │故事频道组│production│5个     │✅启用  │查看 编辑 删除││
│  │grp_002 │测试组    │test      │3个     │✅启用  │查看 编辑 删除││
│  └────────┴──────────┴──────────┴────────┴────────┴───────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 组件结构（使用现有组件）
```tsx
// components/AutoPublish/AccountGroupManager.tsx
// 保持现有组件，确保CRUD功能正常

interface AccountGroup {
  group_id: string;
  group_name: string;
  group_type: 'experiment' | 'production' | 'test';
  description?: string;
  is_active: boolean;
  member_count?: number;
  members?: AccountMember[];
  created_at: string;
  updated_at: string;
  // 扩展统计信息
  stats?: {
    total_tasks: number;
    active_configs: number;
    success_rate: number;
  };
}

interface AccountMember {
  account_id: string;
  account_name: string;
  platform: string;
  role: 'control' | 'experiment' | 'member';
  join_date: string;
  is_active: boolean;
  // 账号统计
  stats?: {
    total_tasks: number;
    success_tasks: number;
    total_views: number;
  };
}
```

### 1.3 创建/编辑账号组表单
```tsx
const AccountGroupForm: React.FC = () => {
  const [form] = Form.useForm();
  const [availableAccounts, setAvailableAccounts] = useState<any[]>([]);
  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([]);
  
  return (
    <Modal
      title={isEdit ? "编辑账号组" : "创建账号组"}
      visible={visible}
      onOk={handleSubmit}
      onCancel={onCancel}
      width={800}>
      
      <Form form={form} layout="vertical">
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item 
              name="group_name" 
              label="组名称" 
              rules={[
                { required: true, message: '请输入组名称' },
                { max: 50, message: '名称不能超过50个字符' }
              ]}>
              <Input placeholder="例如: 故事频道组" />
            </Form.Item>
          </Col>
          
          <Col span={12}>
            <Form.Item 
              name="group_type" 
              label="组类型" 
              rules={[{ required: true }]}>
              <Select placeholder="选择组类型">
                <Option value="production">
                  <Tag color="green">生产组</Tag> - 正式发布
                </Option>
                <Option value="test">
                  <Tag color="blue">测试组</Tag> - 测试使用
                </Option>
                <Option value="experiment">
                  <Tag color="orange">实验组</Tag> - A/B测试
                </Option>
              </Select>
            </Form.Item>
          </Col>
        </Row>
        
        <Form.Item name="description" label="描述">
          <TextArea rows={3} placeholder="账号组的用途说明" />
        </Form.Item>
        
        <Form.Item label="选择账号成员">
          <Transfer
            dataSource={availableAccounts}
            targetKeys={selectedAccounts}
            onChange={setSelectedAccounts}
            render={item => (
              <Space>
                <Avatar size="small" style={{ backgroundColor: getPlatformColor(item.platform) }}>
                  {item.platform.substring(0, 1).toUpperCase()}
                </Avatar>
                {item.account_name}
              </Space>
            )}
            titles={['可选账号', '已选账号']}
            listStyle={{ width: 350, height: 300 }}
            showSearch
            filterOption={(inputValue, option) =>
              option.account_name.toLowerCase().includes(inputValue.toLowerCase())
            }
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};
```

### 1.4 账号组详情抽屉
```tsx
const AccountGroupDetail: React.FC<{ group: AccountGroup }> = ({ group }) => {
  const [members, setMembers] = useState<AccountMember[]>([]);
  const [configs, setConfigs] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  
  useEffect(() => {
    loadGroupDetails();
  }, [group.group_id]);
  
  return (
    <Drawer
      title="账号组详情"
      width={900}
      visible={visible}
      onClose={onClose}>
      
      {/* 基本信息 */}
      <Descriptions title="基本信息" bordered column={2}>
        <Descriptions.Item label="组ID">{group.group_id}</Descriptions.Item>
        <Descriptions.Item label="组名称">{group.group_name}</Descriptions.Item>
        <Descriptions.Item label="组类型">
          <Tag color={getTypeColor(group.group_type)}>
            {getTypeText(group.group_type)}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="状态">
          <Badge status={group.is_active ? 'success' : 'default'} 
            text={group.is_active ? '启用' : '停用'} />
        </Descriptions.Item>
        <Descriptions.Item label="创建时间">{group.created_at}</Descriptions.Item>
        <Descriptions.Item label="更新时间">{group.updated_at}</Descriptions.Item>
        <Descriptions.Item label="描述" span={2}>
          {group.description || '-'}
        </Descriptions.Item>
      </Descriptions>
      
      <Divider />
      
      {/* 统计信息 */}
      <Card title="统计信息" size="small">
        <Row gutter={16}>
          <Col span={6}>
            <Statistic title="账号数量" value={members.length} />
          </Col>
          <Col span={6}>
            <Statistic title="关联配置" value={configs.length} />
          </Col>
          <Col span={6}>
            <Statistic title="总任务数" value={stats?.total_tasks || 0} />
          </Col>
          <Col span={6}>
            <Statistic 
              title="成功率" 
              value={stats?.success_rate || 0} 
              suffix="%" />
          </Col>
        </Row>
      </Card>
      
      <Divider />
      
      {/* 成员列表 */}
      <Card title={`成员账号 (${members.length})`} size="small">
        <Table
          dataSource={members}
          rowKey="account_id"
          size="small"
          pagination={false}
          columns={[
            {
              title: '账号ID',
              dataIndex: 'account_id',
              width: 120
            },
            {
              title: '账号名称',
              dataIndex: 'account_name',
              width: 150
            },
            {
              title: '平台',
              dataIndex: 'platform',
              width: 100,
              render: (platform: string) => (
                <Tag color={getPlatformColor(platform)}>
                  {platform.toUpperCase()}
                </Tag>
              )
            },
            {
              title: '角色',
              dataIndex: 'role',
              width: 100,
              render: (role: string) => {
                const config = {
                  'control': { color: 'blue', text: '对照组' },
                  'experiment': { color: 'orange', text: '实验组' },
                  'member': { color: 'default', text: '成员' }
                }[role];
                return <Tag color={config.color}>{config.text}</Tag>;
              }
            },
            {
              title: '加入时间',
              dataIndex: 'join_date',
              width: 150,
              render: (date: string) => moment(date).format('YYYY-MM-DD')
            },
            {
              title: '任务统计',
              width: 150,
              render: (_: any, record: AccountMember) => (
                <Space size="small">
                  <Text type="secondary">
                    任务: {record.stats?.total_tasks || 0}
                  </Text>
                  <Text type="secondary">
                    成功: {record.stats?.success_tasks || 0}
                  </Text>
                </Space>
              )
            },
            {
              title: '操作',
              width: 100,
              render: (_: any, record: AccountMember) => (
                <Space>
                  <Button 
                    type="link" 
                    size="small"
                    onClick={() => viewAccountDetail(record.account_id)}>
                    查看
                  </Button>
                  <Popconfirm
                    title="确定要移除该账号吗？"
                    onConfirm={() => removeMember(record.account_id)}>
                    <Button type="link" size="small" danger>
                      移除
                    </Button>
                  </Popconfirm>
                </Space>
              )
            }
          ]}
        />
      </Card>
      
      <Divider />
      
      {/* 关联配置 */}
      <Card title={`关联的发布配置 (${configs.length})`} size="small">
        <List
          dataSource={configs}
          renderItem={config => (
            <List.Item
              actions={[
                <Button 
                  type="link" 
                  onClick={() => navigateToConfig(config.config_id)}>
                  查看配置
                </Button>
              ]}>
              <List.Item.Meta
                title={config.config_name}
                description={`Pipeline: ${config.pipeline_name} | 任务数: ${config.task_count}`}
              />
              <Badge 
                status={config.is_active ? 'success' : 'default'} 
                text={config.is_active ? '启用' : '停用'} />
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
GET /api/auto-publish/account-groups
POST /api/auto-publish/account-groups
GET /api/auto-publish/account-groups/{group_id}/members
```

### 2.2 新增接口

#### 2.2.1 更新账号组
```http
PUT /api/auto-publish/account-groups/{group_id}

请求体:
{
  "group_name": "更新的名称",
  "group_type": "production",
  "description": "更新的描述",
  "is_active": true
}

响应: 更新后的账号组对象
```

#### 2.2.2 删除账号组
```http
DELETE /api/auto-publish/account-groups/{group_id}

响应:
{
  "success": true,
  "message": "Account group deleted successfully"
}
```

#### 2.2.3 添加成员
```http
POST /api/auto-publish/account-groups/{group_id}/members

请求体:
{
  "account_ids": ["acc_001", "acc_002"],
  "role": "member"
}

响应:
{
  "success": true,
  "added": 2
}
```

#### 2.2.4 移除成员
```http
DELETE /api/auto-publish/account-groups/{group_id}/members/{account_id}

响应:
{
  "success": true
}
```

#### 2.2.5 获取账号组统计
```http
GET /api/auto-publish/account-groups/{group_id}/stats

响应:
{
  "total_tasks": 156,
  "success_tasks": 145,
  "failed_tasks": 11,
  "success_rate": 92.9,
  "active_configs": 5,
  "total_views": 123456,
  "member_stats": [
    {
      "account_id": "acc_001",
      "account_name": "账号1",
      "total_tasks": 52,
      "success_tasks": 48,
      "total_views": 45678
    }
  ]
}
```

#### 2.2.6 获取账号组关联的配置
```http
GET /api/auto-publish/account-groups/{group_id}/configs

响应:
{
  "configs": [
    {
      "config_id": "config_001",
      "config_name": "每日故事发布",
      "pipeline_id": "story_v3",
      "pipeline_name": "YouTube故事生成V3",
      "is_active": true,
      "task_count": 156
    }
  ],
  "total": 5
}
```

## 3. 后端执行流程

### 3.1 创建账号组流程
```python
@router.post("/account-groups")
async def create_account_group(
    request: CreateAccountGroupRequest,
    current_user = Depends(get_current_user)
):
    """创建账号组"""
    db = get_db_manager()
    
    # 1. 验证组名称唯一性
    existing = db.query_one(
        "SELECT * FROM account_groups WHERE group_name = ?",
        (request.group_name,)
    )
    if existing:
        raise HTTPException(400, "Group name already exists")
    
    # 2. 验证账号存在
    if request.account_ids:
        accounts = db.query(
            f"SELECT account_id FROM accounts WHERE account_id IN ({','.join(['?']*len(request.account_ids))})",
            request.account_ids
        )
        if len(accounts) != len(request.account_ids):
            raise HTTPException(400, "Some accounts not found")
    
    # 3. 创建账号组
    group_id = f"grp_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    with db.get_session() as session:
        group = AccountGroupModel(
            group_id=group_id,
            group_name=request.group_name,
            group_type=request.group_type,
            description=request.description,
            is_active=True
        )
        session.add(group)
        
        # 4. 添加成员
        for account_id in request.account_ids:
            member = AccountGroupMemberModel(
                group_id=group_id,
                account_id=account_id,
                role='member',
                is_active=True
            )
            session.add(member)
        
        session.commit()
    
    return {
        "group_id": group_id,
        "group_name": request.group_name,
        "member_count": len(request.account_ids)
    }
```

### 3.2 获取账号组统计流程
```python
@router.get("/account-groups/{group_id}/stats")
async def get_group_stats(
    group_id: str,
    current_user = Depends(get_current_user)
):
    """获取账号组统计信息"""
    db = get_db_manager()
    
    # 1. 获取任务统计
    task_stats = db.query_one("""
        SELECT 
            COUNT(*) as total_tasks,
            SUM(CASE WHEN pipeline_status = 'completed' THEN 1 ELSE 0 END) as success_tasks,
            SUM(CASE WHEN pipeline_status = 'failed' THEN 1 ELSE 0 END) as failed_tasks
        FROM auto_publish_tasks
        WHERE group_id = ?
    """, (group_id,))
    
    # 2. 获取配置数量
    config_count = db.query_one("""
        SELECT COUNT(*) as count
        FROM publish_configs
        WHERE group_id = ? AND is_active = 1
    """, (group_id,))['count']
    
    # 3. 获取成员统计
    member_stats = db.query("""
        SELECT 
            a.account_id,
            a.account_name,
            COUNT(apt.task_id) as total_tasks,
            SUM(CASE WHEN apt.pipeline_status = 'completed' THEN 1 ELSE 0 END) as success_tasks,
            SUM(JSON_EXTRACT(apt.metadata, '$.performance.views')) as total_views
        FROM accounts a
        JOIN account_group_members agm ON a.account_id = agm.account_id
        LEFT JOIN auto_publish_tasks apt ON a.account_id = apt.account_id
        WHERE agm.group_id = ?
        GROUP BY a.account_id
    """, (group_id,))
    
    # 4. 计算成功率
    success_rate = 0
    if task_stats['total_tasks'] > 0:
        success_rate = round(
            task_stats['success_tasks'] / task_stats['total_tasks'] * 100, 
            1
        )
    
    return {
        "total_tasks": task_stats['total_tasks'],
        "success_tasks": task_stats['success_tasks'],
        "failed_tasks": task_stats['failed_tasks'],
        "success_rate": success_rate,
        "active_configs": config_count,
        "member_stats": member_stats
    }
```

### 3.3 更新账号组流程
```python
@router.put("/account-groups/{group_id}")
async def update_account_group(
    group_id: str,
    request: UpdateAccountGroupRequest,
    current_user = Depends(get_current_user)
):
    """更新账号组"""
    db = get_db_manager()
    
    # 1. 验证账号组存在
    group = db.query_one(
        "SELECT * FROM account_groups WHERE group_id = ?",
        (group_id,)
    )
    if not group:
        raise HTTPException(404, "Account group not found")
    
    # 2. 如果更改名称，验证唯一性
    if request.group_name and request.group_name != group['group_name']:
        existing = db.query_one(
            "SELECT * FROM account_groups WHERE group_name = ? AND group_id != ?",
            (request.group_name, group_id)
        )
        if existing:
            raise HTTPException(400, "Group name already exists")
    
    # 3. 更新账号组
    update_fields = []
    params = []
    
    if request.group_name:
        update_fields.append("group_name = ?")
        params.append(request.group_name)
    if request.group_type:
        update_fields.append("group_type = ?")
        params.append(request.group_type)
    if request.description is not None:
        update_fields.append("description = ?")
        params.append(request.description)
    if request.is_active is not None:
        update_fields.append("is_active = ?")
        params.append(request.is_active)
    
    if update_fields:
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(group_id)
        
        db.execute(f"""
            UPDATE account_groups 
            SET {', '.join(update_fields)}
            WHERE group_id = ?
        """, params)
    
    return {"success": True}
```

## 4. 数据模型

使用现有模型：
- `account_groups` - 账号组表
- `account_group_members` - 账号组成员表
- `accounts` - 账号表

## 5. 数据库交互

### 5.1 核心SQL查询

```sql
-- 获取账号组列表（含统计）
SELECT 
    ag.*,
    COUNT(DISTINCT agm.account_id) as member_count,
    COUNT(DISTINCT pc.config_id) as config_count
FROM account_groups ag
LEFT JOIN account_group_members agm ON ag.group_id = agm.group_id AND agm.is_active = 1
LEFT JOIN publish_configs pc ON ag.group_id = pc.group_id AND pc.is_active = 1
WHERE ag.is_active = 1
GROUP BY ag.group_id
ORDER BY ag.created_at DESC;

-- 获取账号组成员详情
SELECT 
    a.*,
    agm.role,
    agm.join_date,
    COUNT(apt.task_id) as total_tasks,
    SUM(CASE WHEN apt.pipeline_status = 'completed' THEN 1 ELSE 0 END) as success_tasks
FROM accounts a
JOIN account_group_members agm ON a.account_id = agm.account_id
LEFT JOIN auto_publish_tasks apt ON a.account_id = apt.account_id
WHERE agm.group_id = ?
  AND agm.is_active = 1
GROUP BY a.account_id;

-- 获取账号组关联的配置
SELECT 
    pc.*,
    pr.pipeline_name,
    COUNT(apt.task_id) as task_count
FROM publish_configs pc
LEFT JOIN pipeline_registry pr ON pc.pipeline_id = pr.pipeline_id
LEFT JOIN auto_publish_tasks apt ON pc.config_id = apt.config_id
WHERE pc.group_id = ?
  AND pc.is_active = 1
GROUP BY pc.config_id;

-- 检查账号组是否可以删除
SELECT 
    COUNT(DISTINCT pc.config_id) as active_configs,
    COUNT(DISTINCT apt.task_id) as running_tasks
FROM account_groups ag
LEFT JOIN publish_configs pc ON ag.group_id = pc.group_id AND pc.is_active = 1
LEFT JOIN auto_publish_tasks apt ON ag.group_id = apt.group_id 
    AND apt.pipeline_status IN ('pending', 'running')
WHERE ag.group_id = ?;
```

## 6. 前端实现要点

### 6.1 批量操作
```tsx
const batchAddMembers = async (accountIds: string[]) => {
  try {
    await autoPublishService.addGroupMembers(groupId, accountIds);
    message.success(`成功添加 ${accountIds.length} 个账号`);
    loadMembers();
  } catch (error) {
    message.error('添加成员失败');
  }
};
```

### 6.2 角色管理
```tsx
const updateMemberRole = async (accountId: string, role: string) => {
  try {
    await autoPublishService.updateMemberRole(groupId, accountId, role);
    message.success('角色更新成功');
    loadMembers();
  } catch (error) {
    message.error('角色更新失败');
  }
};
```

### 6.3 删除前检查
```tsx
const handleDelete = async (groupId: string) => {
  // 先检查是否有关联配置
  const checkResult = await autoPublishService.checkGroupDeletable(groupId);
  
  if (checkResult.active_configs > 0) {
    Modal.warning({
      title: '无法删除',
      content: `该账号组有 ${checkResult.active_configs} 个活跃配置，请先删除或禁用这些配置`
    });
    return;
  }
  
  if (checkResult.running_tasks > 0) {
    Modal.warning({
      title: '无法删除',
      content: `该账号组有 ${checkResult.running_tasks} 个正在运行的任务，请等待完成`
    });
    return;
  }
  
  // 确认删除
  Modal.confirm({
    title: '确认删除',
    content: '确定要删除这个账号组吗？此操作不可恢复。',
    onOk: async () => {
      await autoPublishService.deleteAccountGroup(groupId);
      message.success('删除成功');
      loadGroups();
    }
  });
};
```

## 7. 测试要点

### 7.1 功能测试
- [ ] 账号组CRUD操作
- [ ] 成员管理（添加/移除）
- [ ] 角色设置
- [ ] 批量操作
- [ ] 删除前检查

### 7.2 数据一致性
- [ ] 成员数量统计准确性
- [ ] 关联配置统计
- [ ] 任务统计数据

### 7.3 权限测试
- [ ] 创建权限
- [ ] 编辑权限
- [ ] 删除权限

## 8. 注意事项

1. **删除保护**：有活跃配置或运行中任务的组不能删除
2. **成员去重**：同一账号不能重复加入同一组
3. **角色管理**：A/B测试时需要设置对照组和实验组角色
4. **性能优化**：大量成员时使用分页
5. **事务处理**：批量操作需要事务支持