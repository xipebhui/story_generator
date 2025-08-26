# Pipeline 并发执行问题分析报告

## 已知问题

### 1. 视频导出服务单线程瓶颈 ✅
- **位置**: `export_video.py` → `EXPORT_VIDEO_URL` 服务
- **问题**: 视频导出服务是单线程，多个任务同时导出会排队等待
- **影响**: 并发任务会在视频导出阶段产生瓶颈

---

## 潜在的并发问题

### 2. 🚨 文件路径冲突风险 - **最严重的问题**

#### 2.1 相同 creator_id + video_id 的并发任务
```python
# pipeline_core.py line 119-123
if request.account_name:
    self.output_dir = Path(f"outputs/{request.creator_id}/{request.account_name}/{request.video_id}")
else:
    self.output_dir = Path(f"outputs/{request.creator_id}/{request.video_id}")
self.output_dir.mkdir(parents=True, exist_ok=True)
```

**问题场景**：
- 如果两个任务有相同的 `creator_id` + `video_id`（没有 account_name 或相同 account_name）
- 它们会写入同一个目录：`outputs/creator_001/video_001/`
- 文件会相互覆盖，特别是：
  - `story.txt`
  - `audio.mp3`
  - `draft.jy`
  - `final_video.mp4`

**影响程度**: 🔴 **严重** - 数据相互覆盖，结果错乱

#### 2.2 草稿移动路径冲突
```python
# pipeline_core.py line 654-686
draft_dir = os.environ.get('DRAFT_LOCAL_DIR')
# 草稿文件夹格式: {creator_id}_{video_id}_{uuid}
```

**问题场景**：
- 多个任务生成草稿后移动到 `DRAFT_LOCAL_DIR`
- 如果草稿文件夹命名相同（虽然有UUID，但如果并发时间接近可能产生冲突）

---

### 3. ⚠️ 故事生成文件冲突

#### 3.1 故事文件路径固定
```python
# story_pipeline_v3_runner.py → 最终会写入
# ./story_result/{creator_id}/{video_id}/final/story.txt
```

**问题场景**：
- 相同 `creator_id` + `video_id` 的任务会覆盖彼此的故事文件
- **没有使用 account_name 进行路径隔离**

**影响程度**: 🟡 **中等** - 故事内容可能被覆盖

---

### 4. ⚠️ 语音生成输出路径

```python
# voice_gen/tts_client.py 
# 输出路径: output/{creator_id}_{video_id}_story.mp3
```

**问题场景**：
- 相同 `creator_id` + `video_id` 会覆盖音频文件
- **没有使用 account_name 或任务ID进行隔离**

**影响程度**: 🟡 **中等** - 音频文件可能被覆盖

---

### 5. ⚠️ 日志文件命名虽有时间戳但精度不够

```python
# pipeline_core.py line 130
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
self.log_file = log_dir / f"pipeline_{creator_id}_{account_name}_{video_id}_{timestamp}.log"
```

**问题场景**：
- 如果两个相同参数的任务在同一秒内启动
- 日志文件会冲突（虽然概率较小）

**建议**: 添加毫秒或使用UUID

---

### 6. 🟠 子进程资源竞争

#### 6.1 Gemini API 并发限制
- 多个任务同时调用 Gemini API 可能触发限流
- 需要考虑 API 的 QPS 限制

#### 6.2 TTS 服务并发
- 语音生成服务可能有并发限制
- 需要确认 TTS 服务的并发处理能力

---

## 问题严重性分级

| 级别 | 问题 | 影响 | 发生概率 |
|------|------|------|----------|
| 🔴 严重 | 相同creator_id+video_id的文件覆盖 | 数据丢失、结果错乱 | 高（如果允许重试或重复提交） |
| 🟡 中等 | 故事/语音文件路径冲突 | 部分数据覆盖 | 中（取决于任务参数） |
| 🟠 低 | API限流、子进程竞争 | 性能下降、部分失败 | 低（取决于并发量） |

---

## 建议解决方案

### 方案1: 使用唯一任务ID隔离路径 ✅ **推荐**

```python
# 修改所有文件路径，加入task_id
# pipeline_core.py
def __init__(self, request: PipelineRequest, task_id: str = None, ...):
    self.task_id = task_id or str(uuid.uuid4())
    
    # 使用task_id作为路径的一部分
    self.output_dir = Path(f"outputs/{self.task_id}/{request.creator_id}/{request.video_id}")
    
    # 或者更简洁的方式
    self.output_dir = Path(f"outputs/{self.task_id}")
```

**优点**:
- 每个任务完全隔离，不会相互影响
- 简单有效，改动最小

**需要修改的地方**:
1. `pipeline_core.py`: 添加 task_id 参数，修改所有路径
2. `story_pipeline_v3_runner.py`: 传递 task_id 到故事生成路径
3. `voice_gen/tts_client.py`: 使用 task_id 生成唯一音频路径
4. `draft_gen/generateDraftService.py`: 使用 task_id 生成草稿路径

### 方案2: 添加分布式锁

```python
import fcntl  # Unix/Linux
import msvcrt  # Windows

def acquire_task_lock(creator_id, video_id):
    lock_file = f"/tmp/pipeline_{creator_id}_{video_id}.lock"
    # 获取文件锁，防止并发执行相同任务
```

**优点**: 防止相同参数的任务并发执行
**缺点**: 增加复杂度，需要处理锁的释放

### 方案3: 任务去重队列

在 API 层面进行控制：
```python
# api_with_db.py
pending_tasks = {}  # {(creator_id, video_id): task_id}

def run_pipeline(request):
    key = (request.creator_id, request.video_id)
    if key in pending_tasks:
        return {"error": "相同视频的任务正在执行中"}
    # 继续创建任务...
```

### 方案4: 增强文件命名唯一性

```python
# 为所有关键文件添加时间戳+随机数
import time
import random

def get_unique_suffix():
    timestamp = int(time.time() * 1000)  # 毫秒级时间戳
    random_num = random.randint(1000, 9999)
    return f"{timestamp}_{random_num}"

# 使用示例
audio_file = f"output/{creator_id}_{video_id}_{get_unique_suffix()}_story.mp3"
```

---

## 立即可行的改进措施

### 1. 短期方案（最小改动）
- 在 API 层面检查是否有相同的 creator_id + video_id 任务正在运行
- 如果有，拒绝新任务或排队等待

### 2. 中期方案（推荐）
- 修改 `pipeline_core.py` 构造函数，接收 task_id
- 所有文件路径使用 task_id 进行隔离
- 确保每个任务的文件完全独立

### 3. 长期方案
- 实现完整的任务队列系统
- 使用消息队列（如 RabbitMQ、Redis Queue）
- 控制并发数，实现任务调度和重试机制

---

## 测试建议

### 并发测试脚本
```python
import asyncio
import aiohttp

async def create_task(session, video_id, creator_id):
    url = "http://localhost:51082/api/pipeline/run"
    data = {
        "video_id": video_id,
        "creator_id": creator_id,
        "gender": 1,
        "export_video": False
    }
    async with session.post(url, json=data) as resp:
        return await resp.json()

async def test_concurrent_same_params():
    """测试相同参数的并发任务"""
    async with aiohttp.ClientSession() as session:
        # 创建5个相同参数的任务
        tasks = [
            create_task(session, "test_video", "test_creator")
            for _ in range(5)
        ]
        results = await asyncio.gather(*tasks)
        print(results)

if __name__ == "__main__":
    asyncio.run(test_concurrent_same_params())
```

---

## 总结

最严重的问题是 **文件路径冲突**，当多个任务使用相同的 `creator_id` 和 `video_id` 时，会导致文件相互覆盖。建议：

1. **立即**: 在 API 层面添加任务去重检查
2. **尽快**: 使用 task_id 隔离所有文件路径
3. **未来**: 实现完整的任务队列系统

这样可以确保并发执行时不会出现数据错乱的问题。