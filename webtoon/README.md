# 漫画解说视频生成系统

将漫画自动转换为带解说的视频，支持Webtoon等在线漫画平台。

## 功能特性

- 🎯 **精确时长对齐**：每张图片独立生成音频，确保画面与解说完美同步
- 🤖 **智能内容理解**：使用Gemini AI分析画面内容和故事情节
- 📝 **连贯文案生成**：保持上下文连贯的解说词生成
- 🎵 **自动语音合成**：支持多种语音和语速调整
- 🎬 **剪映草稿输出**：自动生成可直接导入剪映的草稿文件

## 系统架构

```
webtoon/
├── download_webtoon.py       # 漫画下载器
├── comic_video_creator.py    # 命令行入口
├── comic_config.yaml         # 配置文件
└── comic_pipeline/           # 核心Pipeline
    ├── models.py             # 数据模型
    ├── config.py             # 配置管理
    ├── pipeline.py           # 主Pipeline
    └── stages/               # 处理阶段
        ├── image_analyzer.py    # 图片分析
        ├── narration_generator.py # 文案生成
        └── audio_generator.py    # 音频生成
```

## 快速开始

### 1. 安装依赖

```bash
# 基础依赖
pip install -r requirements.txt

# 漫画下载依赖
pip install -r requirements_downloader.txt
```

### 2. 设置API密钥

```bash
export GEMINI_API_KEY="your-gemini-api-key"
```

### 3. 下载并处理漫画

```bash
# 下载Webtoon漫画并生成视频
python webtoon/comic_video_creator.py \
    --url "https://www.webtoons.com/en/fantasy/comic-name/list?title_no=1234" \
    --download

# 处理已下载的漫画
python webtoon/comic_video_creator.py \
    --dir "outputs/webtoon/comic_name/001_chapter"
```

## 配置说明

编辑 `comic_config.yaml` 自定义配置：

```yaml
# Gemini AI配置
gemini:
  model: "gemini-1.5-flash"
  temperature: 0.7

# 语音配置
tts:
  voice: "zh-CN-XiaoxiaoNeural"  # 中文女声
  rate: "+0%"     # 语速调整
  
# 文案生成配置
narration:
  words_per_second: 2.5  # 每秒字数
  min_words_per_image: 30
  max_words_per_image: 80
  narration_style: "生动活泼"

# 场景时长配置
scene_durations:
  action: [3, 5]      # 动作场景3-5秒
  dialog: [5, 8]      # 对话场景5-8秒
  transition: [2, 3]  # 过渡场景2-3秒
  climax: [8, 10]     # 高潮场景8-10秒
```

## 工作流程

1. **下载漫画**：从Webtoon下载漫画图片
2. **图片分析**：使用Gemini AI理解画面内容
3. **故事理解**：分析整体故事脉络和角色
4. **文案生成**：为每张图片生成解说词
5. **音频合成**：将文案转换为语音
6. **时长对齐**：精确测量每段音频时长
7. **草稿生成**：创建剪映项目文件

## 核心设计

### 时长对齐方案

采用**逐图独立生成**方案，确保100%精确对齐：

```python
for image in images:
    # 生成文案
    narration = generate_narration(image, context)
    
    # 生成音频
    audio_file = tts.generate(narration)
    
    # 测量精确时长
    duration = get_audio_duration(audio_file)
    
    # 记录时间轴
    timeline.append({
        "image": image,
        "audio": audio_file,
        "duration": duration
    })
```

### 连贯性保证

通过上下文传递保持故事连贯：

```python
context = NarrationContext(
    previous_narrations=[...],  # 前文内容
    story_outline="...",         # 故事大纲
    current_emotion="紧张"       # 情绪基调
)
```

## 命令行参数

```bash
# 基本用法
python comic_video_creator.py --dir <漫画目录>

# 完整参数
--url URL           # Webtoon URL
--dir DIR           # 本地漫画目录
--download          # 下载漫画
--config FILE       # 配置文件路径
--limit N           # 限制处理图片数量
--chapter NAME      # 指定章节名称
--no-draft          # 不生成剪映草稿
--no-merge          # 不合并音频
--verbose           # 详细日志
--dry-run           # 测试模式
```

## 输出文件

```
output/comic_videos/
├── comic_name/
│   ├── audio/           # 音频文件
│   │   ├── narration_001.mp3
│   │   ├── narration_002.mp3
│   │   └── merged_audio.mp3
│   └── drafts/          # 剪映草稿
│       └── comic_chapter/
│           ├── draft_content.json
│           ├── draft_meta_info.json
│           └── materials/
```

## 注意事项

1. **API配额**：Gemini API有调用限制，处理大量图片时注意配额
2. **图片顺序**：确保图片按正确顺序命名（如001.jpg, 002.jpg）
3. **内存使用**：处理大量图片时可能占用较多内存
4. **网络要求**：下载和API调用需要稳定的网络连接

## 故障排除

### 常见问题

1. **下载失败**
   - 检查网络连接
   - 确认URL正确
   - 某些地区可能需要代理

2. **API错误**
   - 确认API密钥正确
   - 检查API配额
   - 降低请求频率

3. **音频生成失败**
   - 确认edge-tts已安装
   - 检查文本编码
   - 尝试更换语音

## 开发计划

- [ ] 支持更多漫画平台
- [ ] 批量章节处理
- [ ] 自动字幕生成
- [ ] 背景音乐添加
- [ ] 画面特效增强
- [ ] 多语言支持

## License

MIT