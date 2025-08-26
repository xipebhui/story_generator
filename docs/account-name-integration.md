# Account Name 集成说明

## 概述
`account_name` 字段已完全集成到视频生成 pipeline 中，用于跟踪视频发布到的具体账号。该字段贯穿整个任务流程，从 task_id 生成到所有输出文件命名。

## 更新内容

### 1. API 层 (api_with_db.py)
- **任务ID生成**: 包含 account_name
  ```python
  # 有 account_name 时
  task_id = f"{creator_id}_{account_name}_{video_id}_{uuid}"
  
  # 无 account_name 时
  task_id = f"{creator_id}_{video_id}_{uuid}"
  ```

### 2. 数据库层 (database.py)
- **PipelineTask 表**: 新增 `account_name` 字段
  ```python
  account_name = Column(String(100), nullable=True)
  ```

### 3. Pipeline 核心 (pipeline_core.py)

#### 输出目录结构
```
# 有 account_name
outputs/{creator_id}/{account_name}/{video_id}/

# 无 account_name
outputs/{creator_id}/{video_id}/
```

#### 日志文件命名
```
# 有 account_name
logs/pipeline_{creator_id}_{account_name}_{video_id}_{timestamp}.log

# 无 account_name
logs/pipeline_{creator_id}_{video_id}_{timestamp}.log
```

#### 音频和字幕文件
```
# 有 account_name
output/{creator_id}_{account_name}_{video_id}_story.mp3
output/{creator_id}_{account_name}_{video_id}_story.srt

# 无 account_name
output/{creator_id}_{video_id}_story.mp3
output/{creator_id}_{video_id}_story.srt
```

#### 草稿文件
```
# 有 account_name
output/drafts/{creator_id}_{account_name}_{video_id}_story/
DRAFT_LOCAL_DIR/{creator_id}_{account_name}_{video_id}_{timestamp}/

# 无 account_name
output/drafts/{creator_id}_{video_id}_story/
DRAFT_LOCAL_DIR/{creator_id}_{video_id}_{timestamp}/
```

#### 视频文件
```
# 有 account_name
{creator_id}_{account_name}_{video_id}_{timestamp}.mp4
{creator_id}_{account_name}_{video_id}_{timestamp}_preview.mp4

# 无 account_name
{creator_id}_{video_id}_{timestamp}.mp4
{creator_id}_{video_id}_{timestamp}_preview.mp4
```

## 使用方式

### 创建任务时指定 account_name
```bash
curl -X POST http://localhost:51082/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "abc123",
    "creator_id": "user001",
    "account_name": "my_channel",  # 可选字段
    "gender": 1,
    "export_video": true
  }'
```

### 响应中的 task_id
```json
{
  "task_id": "user001_my_channel_abc123_f3d8a9b2",
  "message": "任务已启动",
  "status_url": "/api/pipeline/status/user001_my_channel_abc123_f3d8a9b2",
  "result_url": "/api/pipeline/result/user001_my_channel_abc123_f3d8a9b2"
}
```

## 追踪视频发布

通过 account_name 字段，系统可以：

1. **识别视频来源**: 通过文件名立即知道视频是为哪个账号生成的
2. **管理多账号**: 同一个 creator 可以为多个账号生成不同的视频
3. **避免冲突**: 相同的 creator_id + video_id 但不同的 account_name 会生成不同的文件
4. **发布追踪**: 在发布时可以验证视频是否与目标账号匹配

## 子脚本集成

为了完全支持 account_name，相关的子脚本也需要更新以接受 `--account` 参数：

- `voice_gen/tts_client.py` - 需要支持 `--account` 参数
- `draft_gen/generateDraftService.py` - 需要支持 `--account` 参数

这些脚本应该使用 account_name 来生成对应的输出文件名，以保持一致性。

## 并发安全性

有了 account_name 后，文件路径冲突的风险进一步降低：
- 不同账号的任务会写入完全不同的目录
- 文件名包含 account_name，避免覆盖
- 结合视频导出信号量，确保系统稳定运行

## 注意事项

1. account_name 是可选字段，系统向后兼容
2. 如果不提供 account_name，系统使用原有的命名规则
3. account_name 应该是合法的文件名字符（避免特殊字符）
4. 建议使用英文或拼音，避免中文字符可能带来的编码问题