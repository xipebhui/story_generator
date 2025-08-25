#!/usr/bin/env python3
"""
简洁的 Webtoon 漫画下载脚本
使用方法: python download_webtoon.py <webtoon_url>
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse

import aiofiles
import httpx
from loguru import logger
from playwright.async_api import async_playwright

# 禁用系统代理
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.pop('all_proxy', None)
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('ALL_PROXY', None)


class SimpleWebtoonDownloader:
    """简单的 Webtoon 下载器"""
    
    def __init__(self, save_dir: str = "outputs/webtoon"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
    async def download_webtoon(self, url: str) -> None:
        """下载整个 Webtoon 漫画"""
        logger.info(f"开始下载: {url}")
        
        async with async_playwright() as p:
            # 启动浏览器
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            try:
                # 访问漫画主页
                await page.goto(url, wait_until="networkidle")
                await page.wait_for_timeout(2000)
                
                # 获取漫画信息
                comic_info = await page.evaluate("""
                    () => {
                        const title = document.querySelector('h1.subj, .detail_header .subj')?.textContent.trim() || 'Unknown';
                        const author = document.querySelector('.info .author, .detail_header .author')?.textContent.trim() || 'Unknown';
                        return { title, author };
                    }
                """)
                
                logger.info(f"漫画: {comic_info['title']} - 作者: {comic_info['author']}")
                
                # 创建漫画文件夹
                comic_dir = self.save_dir / self._sanitize_filename(comic_info['title'])
                comic_dir.mkdir(exist_ok=True)
                
                # 获取章节列表
                chapters = await self._get_chapters(page)
                
                # 下载每个章节
                for i, chapter in enumerate(chapters, 1):
                    if not chapter['is_free']:
                        logger.warning(f"跳过付费章节: {chapter['title']}")
                        continue
                        
                    logger.info(f"[{i}/{len(chapters)}] 下载章节: {chapter['title']}")
                    
                    # 创建章节文件夹
                    chapter_dir = comic_dir / f"{i:03d}_{self._sanitize_filename(chapter['title'])}"
                    chapter_dir.mkdir(exist_ok=True)
                    
                    # 下载章节图片
                    await self._download_chapter(page, chapter['url'], chapter_dir)
                    
                    # 避免请求过快
                    await page.wait_for_timeout(1000)
                
                logger.info(f"✅ 下载完成! 保存在: {comic_dir}")
                
            finally:
                await browser.close()
    
    async def _scroll_to_load_all_chapters(self, page) -> None:
        """滚动章节列表页面以加载所有章节"""
        last_count = 0
        same_count_times = 0
        max_scrolls = 30
        
        for _ in range(max_scrolls):
            # 获取当前章节数量
            current_count = await page.evaluate("""
                () => document.querySelectorAll('#_listUl li, .episode_list li').length
            """)
            
            # 检查是否有新章节加载
            if current_count == last_count:
                same_count_times += 1
                if same_count_times >= 3:
                    break
            else:
                same_count_times = 0
                last_count = current_count
            
            # 向下滚动
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)
            
            logger.debug(f"加载章节中... 当前数量: {current_count}")
    
    async def _get_chapters(self, page) -> list:
        """获取所有章节信息"""
        # 等待章节列表加载
        await page.wait_for_selector("#_listUl, .episode_list", timeout=10000)
        
        # 滚动到底部以加载所有章节
        await self._scroll_to_load_all_chapters(page)
        
        # 提取章节信息
        chapters = await page.evaluate("""
            () => {
                const episodes = [];
                const elements = document.querySelectorAll('#_listUl li, .episode_list li');
                
                elements.forEach(elem => {
                    const link = elem.querySelector('a');
                    if (!link) return;
                    
                    const title = elem.querySelector('.subj, .episode_title')?.textContent.trim() || '';
                    const isLocked = !!elem.querySelector('.ico_lock, .lock_icon');
                    
                    // 尝试提取章节号
                    const episodeMatch = title.match(/[Ee]p\.?\s*(\d+)/);
                    const episodeNumber = episodeMatch ? parseInt(episodeMatch[1]) : null;
                    
                    episodes.push({
                        title: title,
                        url: link.href,
                        is_free: !isLocked,
                        episode_number: episodeNumber
                    });
                });
                
                // 智能排序：优先使用章节号，否则反转顺序（因为最新的通常在前）
                if (episodes.every(ep => ep.episode_number !== null)) {
                    // 如果所有章节都有章节号，按章节号排序
                    episodes.sort((a, b) => a.episode_number - b.episode_number);
                } else {
                    // 否则反转顺序（假设网页显示最新章节在前）
                    episodes.reverse();
                }
                
                return episodes;
            }
        """)
        
        logger.info(f"找到 {len(chapters)} 个章节")
        
        # 输出前几个章节以便调试
        if chapters:
            logger.info(f"第一章: {chapters[0]['title']}")
            if len(chapters) > 1:
                logger.info(f"最后一章: {chapters[-1]['title']}")
        
        return chapters
    
    async def _download_chapter(self, page, chapter_url: str, save_dir: Path) -> None:
        """下载单个章节的所有图片"""
        # 访问章节页面（增加超时时间到60秒）
        await page.goto(chapter_url, wait_until="networkidle", timeout=60000)
        await page.wait_for_selector("#_imageList", timeout=30000)
        
        # 滚动加载所有图片
        await self._scroll_to_load_all(page)
        
        # 获取所有图片URL
        image_urls = await page.evaluate("""
            () => {
                const images = document.querySelectorAll('#_imageList img');
                return Array.from(images).map((img, index) => ({
                    url: img.src,
                    index: index + 1
                }));
            }
        """)
        
        logger.info(f"  找到 {len(image_urls)} 张图片")
        
        # 下载图片
        async with httpx.AsyncClient() as client:
            for img_data in image_urls:
                await self._download_image(
                    client,
                    img_data['url'],
                    save_dir / f"{img_data['index']:03d}.jpg",
                    chapter_url
                )
    
    async def _scroll_to_load_all(self, page) -> None:
        """滚动页面加载所有懒加载图片"""
        last_height = 0
        same_height_count = 0
        max_scrolls = 50
        
        for _ in range(max_scrolls):
            # 获取当前页面高度
            current_height = await page.evaluate("document.documentElement.scrollHeight")
            
            # 检查是否还有新内容
            if current_height == last_height:
                same_height_count += 1
                if same_height_count >= 3:
                    break
            else:
                same_height_count = 0
                last_height = current_height
            
            # 向下滚动
            await page.evaluate("window.scrollBy(0, 800)")
            
            # 等待图片加载
            await page.wait_for_timeout(500)
            
            # 触发懒加载
            await page.evaluate("""
                () => {
                    const images = document.querySelectorAll('img[data-src]');
                    images.forEach(img => {
                        if (img.dataset.src && !img.src) {
                            img.src = img.dataset.src;
                        }
                    });
                }
            """)
    
    async def _download_image(self, client: httpx.AsyncClient, url: str, save_path: Path, referer: str) -> None:
        """下载单张图片"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": referer,
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            }
            
            response = await client.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            async with aiofiles.open(save_path, "wb") as f:
                await f.write(response.content)
                
            logger.debug(f"  ✓ 下载: {save_path.name}")
            
        except Exception as e:
            logger.error(f"  ✗ 下载失败 {save_path.name}: {e}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除不合法字符和特殊字符"""
        # 替换特殊的Unicode字符
        replacements = {
            ''': '',  # Unicode右单引号
            ''': '',  # Unicode左单引号  
            '"': '',  # Unicode左双引号
            '"': '',  # Unicode右双引号
            '–': '-', # En dash
            '—': '-', # Em dash
            '…': '...',  # 省略号
            ' ': '_',  # 空格替换为下划线
            '.': '_',  # 点号替换为下划线（除了扩展名）
            ',': '',   # 逗号移除
            '!': '',   # 感叹号移除
            '?': '',   # 问号移除
            ':': '_',  # 冒号替换为下划线
            ';': '_',  # 分号替换为下划线
            '/': '_',  # 斜杠替换为下划线
            '\\': '_', # 反斜杠替换为下划线
            '<': '',   # 小于号移除
            '>': '',   # 大于号移除
            '|': '_',  # 管道符替换为下划线
            '*': '',   # 星号移除
            '"': '',   # 普通双引号移除
            "'": '',   # 普通单引号移除
        }
        
        # 应用替换
        for old, new in replacements.items():
            filename = filename.replace(old, new)
        
        # 移除其他非ASCII字符（可选，如果需要更严格的清理）
        # filename = ''.join(c if c.isascii() else '_' for c in filename)
        
        # 移除多余的下划线
        while '__' in filename:
            filename = filename.replace('__', '_')
        
        # 移除开头和结尾的下划线
        filename = filename.strip('_')
        
        # 确保文件名不为空
        if not filename:
            filename = 'unnamed'
            
        return filename


async def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python download_webtoon.py <webtoon_url>")
        print("示例: python download_webtoon.py 'https://www.webtoons.com/en/...'")
        sys.exit(1)
    
    url = sys.argv[1]
    
    # 验证URL
    if "webtoons.com" not in url:
        print("错误: 请提供有效的 Webtoon URL")
        sys.exit(1)
    
    # 配置日志
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    # 开始下载
    downloader = SimpleWebtoonDownloader()
    try:
        await downloader.download_webtoon(url)
    except Exception as e:
        logger.error(f"下载失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())