# Webtoon 漫画下载器

一个简洁的脚本，用于下载 Webtoon 平台上的漫画。

## 功能特点

- ✅ 自动获取漫画所有章节
- ✅ 按章节组织保存图片
- ✅ 处理懒加载图片
- ✅ 跳过付费章节
- ✅ 友好的进度提示

## 安装

1. 安装 Python 依赖：
```bash
pip install -r requirements_downloader.txt
```

2. 安装 Playwright 浏览器：
```bash
playwright install chromium
```

## 使用方法

```bash
python download_webtoon.py <webtoon_url>
```

### 示例

```bash
# 下载指定的 Webtoon 漫画
python download_webtoon.py "https://www.webtoons.com/en/romance/lore-olympus/list?title_no=1320"
```

## 输出结构

下载的文件会保存在 `downloads/` 目录下：

```
downloads/
└── 漫画标题/
    ├── 001_第一章标题/
    │   ├── 001.jpg
    │   ├── 002.jpg
    │   └── ...
    ├── 002_第二章标题/
    │   └── ...
    └── ...
```

## 注意事项

- 只能下载免费章节
- 请尊重版权，仅供个人学习使用
- 下载速度已限制，避免对服务器造成压力
- 如果下载中断，重新运行会跳过已下载的文件

## 故障排除

如果遇到问题：

1. 确保网络连接正常
2. 检查 URL 是否正确
3. 更新 Playwright: `playwright install chromium --force`
4. 查看详细日志了解错误信息