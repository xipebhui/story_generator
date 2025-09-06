#!/bin/bash
# 创建真实的间隔调度配置

# 配置参数
GROUP_ID="group_20250903165020"  # 实际的group1
PIPELINE_ID="story_gen_v5"        # 使用最新的pipeline

# 创建6小时间隔配置
curl -X POST http://localhost:51082/api/auto-publish/publish-configs \
  -H "Content-Type: application/json" \
  -d "{
    \"config_name\": \"6小时自动发布_$(date +%m%d_%H%M)\",
    \"group_id\": \"$GROUP_ID\",
    \"pipeline_id\": \"$PIPELINE_ID\",
    \"trigger_type\": \"scheduled\",
    \"trigger_config\": {
      \"schedule_type\": \"interval\",
      \"schedule_interval\": 6,
      \"schedule_interval_unit\": \"hours\"
    },
    \"priority\": 60,
    \"pipeline_params\": {}
  }"

echo ""
echo "配置创建完成！"
echo "可以通过以下命令查看时间槽:"
echo "sqlite3 data/pipeline_tasks.db \"SELECT * FROM ring_schedule_slots ORDER BY slot_date, slot_hour, slot_minute LIMIT 10;\""
