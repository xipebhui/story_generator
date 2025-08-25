# SRT字幕生成修复方案

## 问题描述
TTS生成音频后，output目录下没有生成对应的SRT字幕文件。

## 问题原因分析

1. **EasyVoice API可能不返回字幕数据**
   - 旧版EasyVoice API可能没有`subtitle_text`字段
   - 或者该字段返回为空

2. **字幕生成流程**
   - TTS客户端依赖服务返回的`subtitle_text`字段
   - 如果服务没有返回字幕，则不会生成SRT文件

## 解决方案

### 1. 创建本地字幕生成器
创建了 `voice_gen/subtitle_generator.py` 模块，可以：
- 根据文本内容自动生成时间轴
- 智能分割长句子为合适的字幕片段
- 估算朗读时长（基于语速和标点停顿）
- 生成标准SRT格式

### 2. 修改TTS客户端
修改了 `voice_gen/tts_client.py`：
- 如果服务返回了`subtitle_text`，使用服务提供的字幕
- 如果服务没有返回字幕，使用本地生成器生成字幕
- 确保每个音频片段都有对应的SRT文件

### 3. 改进字幕合并逻辑
- 即使某些片段缺少字幕，也会合并已有的字幕
- 更好的错误处理和日志输出

## 使用方法

### 生成故事音频和字幕
```bash
# 通过TTS客户端生成音频和字幕
python voice_gen/tts_client.py --cid <creator_id> --vid <voice_id> --gender <0|1>

# 输出文件：
# - ./output/<cid>_<vid>_story.mp3  # 音频文件
# - ./output/<cid>_<vid>_story.srt  # 字幕文件
```

### 测试字幕生成
```bash
# 运行测试脚本
python test_srt_generation.py --all

# 单独测试
python test_srt_generation.py --simple  # 测试简单TTS生成
python test_srt_generation.py --story   # 检查故事音频字幕
python test_srt_generation.py --temp    # 检查临时文件
```

### 验证草稿中的字幕
```bash
# 检查剪映草稿是否包含字幕
python test_subtitle_generation.py
```

## 技术细节

### SubtitleGenerator类
主要功能：
- `estimate_duration(text)`: 估算文本朗读时长
- `split_into_subtitles(text)`: 智能分割文本为字幕片段
- `generate_srt(text)`: 生成SRT格式字幕
- `generate_srt_for_segments(segments)`: 为多段文本生成字幕

### 时长估算算法
```python
# 基于语速（默认150词/分钟）
duration = word_count / words_per_second

# 添加标点停顿
duration += periods * 0.5  # 句号停顿0.5秒
duration += commas * 0.2   # 逗号停顿0.2秒
```

### 字幕分割规则
- 每个字幕最多80个字符
- 优先按句子分割
- 长句子按逗号、分号分割
- 超长内容按单词边界强制分割

## 验证步骤

1. **检查音频文件生成**
   ```bash
   ls -la ./output/*_story.mp3
   ```

2. **检查字幕文件生成**
   ```bash
   ls -la ./output/*_story.srt
   ```

3. **查看字幕内容**
   ```bash
   head -20 ./output/*_story.srt
   ```

4. **在剪映中验证**
   - 打开生成的草稿
   - 检查字幕轨道是否存在
   - 验证字幕时间轴是否正确

## 注意事项

1. **字幕质量**
   - 本地生成的字幕基于估算，可能与实际音频略有偏差
   - 如果需要精确字幕，建议使用支持字幕的TTS服务

2. **编码问题**
   - SRT文件使用UTF-8编码
   - Windows系统注意使用正确的编码打开

3. **性能考虑**
   - 字幕生成是轻量级操作，不会显著影响性能
   - 合并大量字幕文件时可能需要几秒钟

## 后续优化建议

1. **集成语音识别**
   - 使用ASR服务生成更准确的字幕
   - 可以获得精确的时间戳

2. **字幕样式定制**
   - 支持自定义字体、颜色、位置
   - 添加字幕特效（打字机效果等）

3. **多语言支持**
   - 根据不同语言调整语速估算
   - 支持中文、日文等语言的字幕生成