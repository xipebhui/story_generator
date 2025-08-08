# YouTube Story Generator V2 - 文档中心

欢迎使用 YouTube Story Generator V2！这是一个基于AI的自动化故事创作系统。

## 📚 文档导航

### 新手入门
- 🚀 **[快速开始指南](QUICK_START.md)** - 5分钟上手教程
  - 环境配置
  - 基础命令
  - 常见用例

### 系统文档
- 📖 **[完整系统文档](SYSTEM_DOCUMENTATION.md)** - 详细的功能和使用说明
  - 系统概述
  - 核心功能
  - 工作流程
  - 配置说明
  - 故障排除

### 技术文档
- 🔧 **[技术架构文档](TECHNICAL_ARCHITECTURE.md)** - 深入的技术细节
  - 系统架构
  - 核心组件
  - 算法实现
  - 优化策略
  - 扩展性设计

---

## 🎯 快速链接

### 最常用命令
```bash
# 基础使用
python youtube_story_creator_v2.py VIDEO_ID CREATOR_NAME

# 自定义配置
python youtube_story_creator_v2.py VIDEO_ID CREATOR_NAME \
    --segments 12 \
    --images-per-segment 2 \
    --length 40000
```

### 关键特性
- ✨ **9步叙事结构** - 经过验证的故事框架
- 🎨 **智能图片生成** - 自动生成SD提示词
- 📝 **争议性改编** - 基于观众反馈的"槽点放大"策略
- 🔄 **断点续写** - 支持中断后继续生成
- ⚡ **简化流程** - 独立API调用，手动上下文控制

---

## 📂 项目结构

```
story-generator/
├── docs/                       # 文档目录
│   ├── README.md              # 本文件
│   ├── QUICK_START.md         # 快速开始
│   ├── SYSTEM_DOCUMENTATION.md # 系统文档
│   └── TECHNICAL_ARCHITECTURE.md # 技术架构
├── prompts/                    # 提示词模板
│   ├── dna_extractor.md      # DNA提取
│   ├── framework_generate.md  # 框架生成
│   ├── segment_generator.md   # 片段生成
│   └── final_polish.md        # 最终润色
├── youtube_story_creator_v2.py # 主程序
├── youtube_client.py          # YouTube客户端
├── gemini_client.py           # Gemini客户端
├── text_processor.py          # 文本处理器
└── story_result/              # 输出目录
```

---

## 🔄 版本信息

### 当前版本：V2.0
发布日期：2025-08-08

### 主要更新
- ✅ 简化的片段生成流程
- ✅ 9步结构支持
- ✅ 优化的图片生成
- ✅ 角色视觉一致性
- ✅ 可配置的图片密度

### 即将推出
- 🔜 Web界面
- 🔜 批量处理模式
- 🔜 多语言支持
- 🔜 实时进度显示

---

## 💡 最佳实践

### 推荐配置
- **片段数量**：9-15个片段
- **故事长度**：30000-50000字
- **图片密度**：每片段1-2张
- **API调用**：每5个片段暂停2秒

### 性能优化
1. 使用缓存避免重复生成
2. 合理设置片段数量
3. 控制图片生成密度
4. 定期清理旧缓存

---

## 🐛 问题反馈

如果遇到问题，请按以下步骤处理：

1. 查看 [故障排除](SYSTEM_DOCUMENTATION.md#故障排除) 章节
2. 检查日志文件：`story_result/[creator]/[video_id]/generation.log`
3. 提交Issue时请包含：
   - 错误信息
   - 使用的命令
   - 日志片段

---

## 📝 更新日志

### 2025-08-08
- 发布V2.0版本
- 新增优化的图片生成流程
- 完善文档系统
- 修复编码问题

### 2025-08-07
- 实现9步结构支持
- 简化片段生成流程
- 添加断点续写功能

---

## 🤝 贡献指南

欢迎贡献代码和文档！请遵循以下准则：

1. Fork项目
2. 创建特性分支
3. 提交更改
4. 发起Pull Request

---

## 📜 许可证

本项目采用 MIT 许可证

---

## 🙏 致谢

感谢所有贡献者和用户的支持！

---

*如有任何问题，请查阅相应文档或提交Issue。*

**Happy Creating! 🎉**