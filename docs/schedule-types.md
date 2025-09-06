# 定时发布调度类型说明

## 概述

系统支持多种灵活的调度方式，包括间隔执行、Cron表达式、每日/每周/每月定时等。所有调度配置都通过 `trigger_config` 参数设置。

## 支持的调度类型

### 1. 每日定时 (daily)

每天在固定时间执行一次。

**配置示例：**
```json
{
  "schedule_type": "daily",
  "schedule_time": "10:30"  // 每天10:30执行
}
```

### 2. 每周定时 (weekly)

每周的指定日期和时间执行。

**配置示例：**
```json
{
  "schedule_type": "weekly",
  "schedule_days": [1, 3, 5],  // 周一、周三、周五
  "schedule_time": "14:00"      // 14:00执行
}
```

**说明：**
- `schedule_days`: 星期几的数组，0=周日，1=周一，...，6=周六

### 3. 每月定时 (monthly)

每月的指定日期和时间执行。

**配置示例：**
```json
{
  "schedule_type": "monthly",
  "schedule_dates": [1, 15],  // 每月1号和15号
  "schedule_time": "09:00"     // 09:00执行
}
```

**说明：**
- `schedule_dates`: 日期数组，范围1-31
- 如果指定的日期在某月不存在（如2月30日），会自动跳过

### 4. 间隔执行 (interval)

按照固定时间间隔重复执行。

**配置示例：**
```json
{
  "schedule_type": "interval",
  "schedule_interval": 30,           // 间隔数值
  "schedule_interval_unit": "minutes" // 间隔单位
}
```

**支持的间隔单位：**
- `minutes`: 分钟
- `hours`: 小时
- `days`: 天

**使用场景：**
- 每30分钟执行一次
- 每2小时执行一次
- 每3天执行一次

### 5. Cron表达式 (cron)

使用标准的Cron表达式定义复杂的调度规则。

**配置示例：**
```json
{
  "schedule_type": "cron",
  "schedule_cron": "0 */2 * * *"  // 每2小时的第0分钟执行
}
```

**Cron表达式格式：**
```
分 时 日 月 周
┬  ┬  ┬  ┬  ┬
│  │  │  │  └─ 星期几 (0-7，0和7都代表周日)
│  │  │  └──── 月份 (1-12)
│  │  └─────── 日期 (1-31)
│  └────────── 小时 (0-23)
└───────────── 分钟 (0-59)
```

**常用Cron示例：**
- `0 * * * *` - 每小时的第0分钟
- `*/15 * * * *` - 每15分钟
- `0 */2 * * *` - 每2小时
- `0 9,14,18 * * *` - 每天9:00、14:00、18:00
- `0 10 * * 1-5` - 工作日每天10:00
- `0 0 1 * *` - 每月1号0:00
- `0 8 * * 1` - 每周一8:00

**特殊字符说明：**
- `*` - 匹配任意值
- `,` - 多个值（如 `1,3,5`）
- `-` - 范围（如 `1-5`）
- `/` - 间隔（如 `*/5` 表示每5个单位）

### 6. 一次性执行 (once)

在指定时间执行一次后自动禁用。

**配置示例：**
```json
{
  "schedule_type": "once",
  "scheduled_time": "2024-12-25T10:00:00"  // ISO格式时间
}
```

## API使用示例

### 创建间隔发布配置

```bash
curl -X POST http://localhost:51082/api/auto-publish/publish-configs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "config_name": "每2小时发布",
    "group_id": "group_001",
    "pipeline_id": "story_gen_v5",
    "trigger_type": "scheduled",
    "trigger_config": {
      "schedule_type": "interval",
      "schedule_interval": 2,
      "schedule_interval_unit": "hours"
    },
    "priority": 50
  }'
```

### 创建Cron表达式配置

```bash
curl -X POST http://localhost:51082/api/auto-publish/publish-configs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "config_name": "高峰时段发布",
    "group_id": "group_001",
    "pipeline_id": "story_gen_v5",
    "trigger_type": "scheduled",
    "trigger_config": {
      "schedule_type": "cron",
      "schedule_cron": "0 8,12,18,22 * * *"
    },
    "priority": 80
  }'
```

### 测试调度配置

测试配置并查看下次运行时间：

```bash
curl -X POST http://localhost:51082/api/auto-publish/schedule/test/{config_id} \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**响应示例：**
```json
{
  "config_id": "config_001",
  "schedule_type": "interval",
  "trigger_config": {
    "schedule_type": "interval",
    "schedule_interval": 30,
    "schedule_interval_unit": "minutes"
  },
  "next_run_time": "2024-12-20T14:30:00",
  "message": "下次运行时间: 2024-12-20 14:30:00"
}
```

### 查看调度状态

```bash
curl -X GET http://localhost:51082/api/auto-publish/schedule/status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**响应示例：**
```json
{
  "total": 3,
  "schedules": [
    {
      "config_id": "config_001",
      "schedule_type": "interval",
      "is_active": true,
      "last_run_time": "2024-12-20T14:00:00",
      "next_run_time": "2024-12-20T14:30:00",
      "schedule_config": {
        "schedule_type": "interval",
        "schedule_interval": 30,
        "schedule_interval_unit": "minutes"
      }
    }
  ]
}
```

## 调度管理操作

### 暂停调度

```bash
curl -X PUT http://localhost:51082/api/auto-publish/schedule/pause/{config_id} \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 恢复调度

```bash
curl -X PUT http://localhost:51082/api/auto-publish/schedule/resume/{config_id} \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 删除调度

```bash
curl -X DELETE http://localhost:51082/api/auto-publish/schedule/{config_id} \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 前端集成

前端在创建发布配置时，根据用户选择的调度类型动态显示相应的配置项：

1. **间隔执行**：显示数值输入框和单位选择器
2. **Cron表达式**：显示文本输入框，可提供Cron表达式构建器
3. **每日/每周/每月**：显示时间选择器和日期选择器

## 注意事项

1. **时区处理**：所有时间都使用服务器本地时区，建议统一使用UTC或明确指定时区
2. **调度精度**：检查间隔为60秒，实际执行时间可能有±60秒的偏差
3. **并发控制**：同一配置的多个任务不会并发执行，新任务会等待前一个完成
4. **失败重试**：任务失败后会根据配置的重试策略自动重试
5. **性能考虑**：大量高频率的间隔任务可能影响系统性能，建议合理设置间隔时间

## 最佳实践

1. **间隔发布**：适合需要持续更新内容的场景，如新闻、实时信息等
2. **Cron表达式**：适合复杂的调度需求，如特定时间段密集发布
3. **每日定时**：适合固定栏目或日常更新
4. **避免重叠**：设置合理的间隔时间，确保前一个任务完成后再执行下一个
5. **监控告警**：配置失败告警，及时发现和处理问题