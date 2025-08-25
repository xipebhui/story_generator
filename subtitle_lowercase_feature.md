# 字幕小写转换功能

## 功能描述
字幕文件中的所有文本内容会自动转换为小写字母，以保持统一的字幕风格。

## 实现位置

### 1. 字幕解析阶段
**文件**: `draft_gen/jianying_subtitle_service.py`
- 在 `parse_srt()` 方法中，解析SRT文件时自动将文本转换为小写
- 位置：第148-149行

```python
# 提取文本（可能多行）并转换为小写
text = ' '.join(lines[2:]).strip()
text = text.lower()  # 转换为小写
```

### 2. 字幕合并阶段
**文件**: `voice_gen/tts_client.py`
- 在 `_merge_srt_files()` 方法中，合并多个SRT文件时转换为小写
- 位置：第572-579行

```python
# 处理文本：去除标点符号并转换为小写
cleaned_text_lines = []
for text_line in text_lines:
    cleaned_text = self._remove_punctuation(text_line)
    # 转换为小写
    cleaned_text = cleaned_text.lower()
    if cleaned_text.strip():
        cleaned_text_lines.append(cleaned_text)
```

## 处理流程

1. **TTS生成阶段**: 生成的SRT字幕文件保持原始大小写
2. **字幕合并阶段**: 在合并多个SRT文件时，文本会被：
   - 去除标点符号
   - 转换为小写
3. **剪映草稿生成阶段**: 在创建剪映字幕轨道时，读取的SRT文本已经是小写

## 效果示例

**原始字幕**:
```
1
00:00:00,000 --> 00:00:02,000
HELLO WORLD! This Is A Test.

2
00:00:02,000 --> 00:00:04,000
Another Line WITH MIXED CASE Text.
```

**处理后字幕**:
```
1
00:00:00,000 --> 00:00:02,000
hello world this is a test

2
00:00:02,000 --> 00:00:04,000
another line with mixed case text
```

## 测试验证

运行测试脚本验证功能：
```bash
python test_lowercase_subtitle.py
```

测试内容包括：
- SRT文件解析时的小写转换
- SRT文件合并时的小写转换和标点符号去除

## 注意事项

1. 小写转换同时会去除标点符号，使字幕更简洁
2. 数字和时间戳不受影响
3. 适用于英文字幕，中文字幕不受影响（中文没有大小写区分）