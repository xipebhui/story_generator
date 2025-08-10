# TTS 文本转语音客户端

这是一个用于调用本地TTS服务的Python脚本，可以将文本转换为MP3音频文件。

## 安装依赖

```bash
pip install requests
```

## 使用方法

### 1. 基本用法

#### 直接指定文本
```bash
python tts_client.py -t "Hello, world!" -o hello.mp3
```

#### 从文件读取文本
```bash
python tts_client.py -f example_text.txt -o story.mp3
```

### 2. 高级选项

#### 使用中文语音
```bash
python tts_client.py -t "你好，世界！" -v zh-CN-XiaoxiaoNeural -o chinese.mp3
```

#### 调整语速（加快50%）
```bash
python tts_client.py -t "Faster speech" -r "+50%" -o fast.mp3
```

#### 调整音量（增大20%）
```bash
python tts_client.py -t "Louder voice" -vol "+20%" -o loud.mp3
```

#### 调整音调（提高5Hz）
```bash
python tts_client.py -t "Higher pitch" -p "+5Hz" -o high_pitch.mp3
```

#### 组合使用多个参数
```bash
python tts_client.py -f story.txt -v en-US-JennyNeural -r "+30%" -vol "+10%" -o story_custom.mp3
```

## 参数说明

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `-t, --text` | 要转换的文本内容 | - | "Hello world" |
| `-f, --file` | 包含文本的文件路径 | - | story.txt |
| `-o, --output` | 输出MP3文件名 | output.mp3 | audio.mp3 |
| `-v, --voice` | 语音类型 | en-US-AriaNeural | zh-CN-XiaoxiaoNeural |
| `-r, --rate` | 语速调整 | +25% | -50%, 0%, +100% |
| `-p, --pitch` | 音调调整 | 0Hz | -10Hz, +5Hz |
| `-vol, --volume` | 音量调整 | 0% | -50%, +50% |

## 常用语音选项

### 英语语音
- `en-US-AriaNeural` - 女声（默认）
- `en-US-JennyNeural` - 女声
- `en-US-GuyNeural` - 男声
- `en-US-DavisNeural` - 男声

### 中文语音
- `zh-CN-XiaoxiaoNeural` - 女声
- `zh-CN-YunyangNeural` - 女声
- `zh-CN-YunxiNeural` - 男声
- `zh-CN-YunjianNeural` - 男声

## 使用Python代码调用

```python
from tts_client import TTSClient

# 创建客户端
client = TTSClient(
    text="Hello, this is a test.",
    output_file="test.mp3",
    voice="en-US-AriaNeural",
    rate="+25%",
    pitch="0Hz",
    volume="0%"
)

# 执行转换
client.convert()
```

## 注意事项

1. 确保TTS服务正在运行（默认地址：http://localhost:3000）
2. 较长的文本可能需要更多时间进行转换
3. 输出文件会自动添加.mp3扩展名（如果未指定）
4. 使用百分比符号时，在命令行中需要转义（如 `+25%%`）

## 故障排除

- **连接错误**：确保TTS服务正在运行
- **文件未找到**：检查文本文件路径是否正确
- **音频质量问题**：尝试调整语速、音调和音量参数