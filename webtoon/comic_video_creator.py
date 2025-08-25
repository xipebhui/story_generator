#!/usr/bin/env python3
"""
漫画解说视频生成器 - 命令行入口
"""

import argparse
import sys
import os
from pathlib import Path
import asyncio
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from comic_pipeline import ComicVideoPipeline, ComicPipelineConfig
from download_webtoon import SimpleWebtoonDownloader


def download_comic(url: str, output_dir: str = "outputs/webtoon") -> str:
    """下载漫画"""
    print(f"开始下载漫画: {url}")
    downloader = SimpleWebtoonDownloader(save_dir=output_dir)
    
    # 异步下载
    asyncio.run(downloader.download_webtoon(url))
    
    # 获取下载的目录（假设是最新创建的）
    output_path = Path(output_dir)
    comic_dirs = sorted(
        [d for d in output_path.iterdir() if d.is_dir()],
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    if comic_dirs:
        return str(comic_dirs[0])
    else:
        raise ValueError("下载失败，没有找到漫画目录")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="漫画解说视频生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 下载并处理Webtoon漫画
  %(prog)s --url "https://www.webtoons.com/..." --download
  
  # 处理已下载的漫画目录
  %(prog)s --dir "outputs/webtoon/comic_name/001_chapter"
  
  # 指定配置文件
  %(prog)s --dir "path/to/comic" --config "custom_config.yaml"
  
  # 只处理前N张图片（测试用）
  %(prog)s --dir "path/to/comic" --limit 5
        """
    )
    
    # 输入源（二选一）
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--url',
        type=str,
        help='Webtoon漫画URL'
    )
    input_group.add_argument(
        '--dir',
        type=str,
        help='本地漫画目录路径'
    )
    
    # 下载选项
    parser.add_argument(
        '--download',
        action='store_true',
        help='下载漫画（配合--url使用）'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='outputs/webtoon',
        help='下载输出目录（默认: outputs/webtoon）'
    )
    
    # Pipeline配置
    parser.add_argument(
        '--config',
        type=str,
        help='配置文件路径（YAML格式）'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='限制处理的图片数量（用于测试）'
    )
    
    parser.add_argument(
        '--chapter',
        type=str,
        help='指定章节名称'
    )
    
    # 输出选项
    parser.add_argument(
        '--no-draft',
        action='store_true',
        help='不生成剪映草稿'
    )
    
    parser.add_argument(
        '--no-merge',
        action='store_true',
        help='不合并音频文件'
    )
    
    # 调试选项
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='显示详细日志'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='只分析不生成（用于测试）'
    )
    
    args = parser.parse_args()
    
    # 打印标题
    print("="*60)
    print("漫画解说视频生成器 v1.0")
    print("="*60)
    
    try:
        # Step 1: 确定漫画目录
        if args.url:
            if args.download:
                # 下载漫画
                comic_dir = download_comic(args.url, args.output_dir)
                print(f"✓ 漫画下载完成: {comic_dir}")
            else:
                print("错误: 使用--url时需要添加--download参数")
                return 1
        else:
            comic_dir = args.dir
            if not Path(comic_dir).exists():
                print(f"错误: 目录不存在 - {comic_dir}")
                return 1
        
        # 如果是漫画主目录，选择第一个章节
        comic_path = Path(comic_dir)
        if comic_path.is_dir():
            # 检查是否有子目录（章节）
            subdirs = [d for d in comic_path.iterdir() if d.is_dir()]
            if subdirs and any('_' in d.name for d in subdirs):
                # 看起来像章节目录，选择第一个
                chapters = sorted(subdirs)
                if chapters:
                    print(f"检测到 {len(chapters)} 个章节")
                    comic_dir = str(chapters[0])
                    print(f"处理第一个章节: {chapters[0].name}")
        
        # Step 2: 加载配置
        if args.config:
            config = ComicPipelineConfig.from_yaml(args.config)
            print(f"✓ 加载配置文件: {args.config}")
        else:
            config = ComicPipelineConfig()
            # 检查是否有默认配置文件
            default_config = Path(__file__).parent / "comic_config.yaml"
            if default_config.exists():
                config = ComicPipelineConfig.from_yaml(str(default_config))
                print(f"✓ 使用默认配置: {default_config}")
        
        # 检查NewAPI密钥（GeminiClient会自动从环境变量读取）
        api_key = os.getenv("NEWAPI_API_KEY")
        if not api_key:
            print("错误: 未设置NEWAPI_API_KEY环境变量")
            print("请设置: export NEWAPI_API_KEY='your-api-key'")
            return 1
        
        # Step 3: 创建Pipeline
        pipeline = ComicVideoPipeline(config=config)
        
        # Step 4: 执行Pipeline
        print(f"\n开始处理: {comic_dir}")
        print("-"*60)
        
        if args.dry_run:
            print("【演示模式】只进行分析，不生成实际文件")
            # TODO: 实现dry-run逻辑
            return 0
        
        result = pipeline.process_comic_chapter(
            comic_dir=comic_dir,
            chapter_name=args.chapter,
            skip_download=True
        )
        
        # Step 5: 显示结果
        if result.success:
            print("\n" + "="*60)
            print("✅ 处理成功！")
            print("="*60)
            print(result.get_summary())
            return 0
        else:
            print("\n" + "="*60)
            print("❌ 处理失败")
            print("="*60)
            print(f"错误: {result.error_message}")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠ 用户中断")
        return 130
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())