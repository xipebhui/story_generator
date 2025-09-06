#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试抖音下载发布Pipeline

使用方法:
1. 测试获取视频信息（默认模式）:
   python test_douyin_pipeline.py --mode fetch
   
2. 测试下载视频:
   python test_douyin_pipeline.py --mode download
   
3. 测试完整流程（包括发布到YouTube）:
   python test_douyin_pipeline.py --mode publish --account-id YOUR_YOUTUBE_ACCOUNT_ID
   
4. 增加详细日志输出:
   python test_douyin_pipeline.py --mode download --verbose
   
5. 指定创作者ID和视频数量:
   python test_douyin_pipeline.py --mode download --creator-id CREATOR_ID --max-videos 3
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from pipelines.douyin_download_publish_pipeline import DouyinDownloadPublishPipeline

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s  - %(filename)s:%(lineno)d - %(message)s'
)


# 设置特定模块的日志级别
logging.getLogger('pipelines.douyin_download_publish_pipeline').setLevel(logging.DEBUG)
logging.getLogger('aiohttp').setLevel(logging.WARNING)  # 减少aiohttp的日志噪音

logger = logging.getLogger(__name__)


async def test_pipeline():
    """测试Pipeline执行"""
    
    # Pipeline配置
    config = {
        "api_base_url": "http://localhost:51084",
        "max_videos_per_creator": 1,  # 每个创作者默认获取1个视频
        "download_timeout": 300,
        "storage_base_path": "outputs/douyin_videos",
        "cache_dir": "outputs/douyin_cache"
    }
    
    # 创建Pipeline实例
    pipeline = DouyinDownloadPublishPipeline(config)
    
    # 执行参数
    params = {
        "creator_ids": [
            "MS4wLjABAAAAOFERtNs1K2GvCA-NWS_WtWebO_34EpBFei8F4IWOta-ctOXnft2CsodDIu29heN6"  # 示例创作者ID
        ],
        "account_id": "test_account",  # YouTube账号ID（需要是真实的账号ID）
        "max_videos_per_creator": 2     # 可选：覆盖配置中的默认值
    }
    
    logger.info("开始执行抖音下载发布Pipeline...")
    logger.info(f"参数: {params}")
    
    # 执行Pipeline
    result = await pipeline.execute(params)
    
    # 输出结果
    if result['success']:
        logger.info("✅ Pipeline执行成功!")
        logger.info(f"处理统计:")
        logger.info(f"  - 找到视频数: {result['data']['total_processed']}")
        logger.info(f"  - 下载成功数: {result['data']['total_downloaded']}")
        logger.info(f"  - 发布成功数: {result['data']['total_published']}")
        
        # 输出各阶段结果
        logger.info("\n各阶段执行结果:")
        for stage in result['stages']:
            logger.info(f"  - {stage['name']}: {'✅ 成功' if stage['success'] else '❌ 失败'}")
            if stage.get('data'):
                logger.info(f"    数据: {stage['data']}")
    else:
        logger.error(f"❌ Pipeline执行失败: {result.get('error')}")
        
    return result


async def test_fetch_only():
    """仅测试获取视频信息阶段"""
    
    logger.info("=" * 80)
    logger.info("开始测试获取视频信息")
    logger.info("=" * 80)
    
    config = {
        "api_base_url": "http://localhost:51084",
        "max_videos_per_creator": 2,  # 获取2个视频
        "storage_base_path": "outputs/douyin_videos",
        "cache_dir": "outputs/douyin_cache"
    }
    
    logger.info(f"Pipeline配置:")
    for key, value in config.items():
        logger.info(f"  {key}: {value}")
    
    pipeline = DouyinDownloadPublishPipeline(config)
    
    # 使用PipelineContext进行测试
    from pipelines.pipeline_context import PipelineContext
    
    creator_id = "MS4wLjABAAAAOFERtNs1K2GvCA-NWS_WtWebO_34EpBFei8F4IWOta-ctOXnft2CsodDIu29heN6"
    params = {
        "creator_ids": [creator_id],
        "max_videos_per_creator": 2
    }
    
    logger.info(f"执行参数:")
    logger.info(f"  creator_ids: {params['creator_ids']}")
    logger.info(f"  max_videos_per_creator: {params.get('max_videos_per_creator', 'default')}")
    
    context = PipelineContext(params)
    
    logger.info("\n开始调用 fetch_creator_videos...")
    
    try:
        videos = await pipeline.fetch_creator_videos(context, params['creator_ids'])
        
        logger.info(f"\n{'='*80}")
        logger.info(f"结果: 获取到 {len(videos)} 个未处理的视频")
        logger.info(f"{'='*80}")
        
        for idx, video in enumerate(videos, 1):
            logger.info(f"\n视频 {idx}:")
            logger.info(f"  - aweme_id: {video['aweme_id']}")
            logger.info(f"  - 标题: {video['desc'][:100]}..." if len(video['desc']) > 100 else f"  - 标题: {video['desc']}")
            logger.info(f"  - 分享链接: {video.get('share_url', 'N/A')}")
        
        if not videos:
            logger.warning("\n没有找到未处理的视频！可能的原因：")
            logger.warning("1. API没有返回数据")
            logger.warning("2. 所有视频都已被处理过")
            logger.warning("3. API响应格式发生变化")
            logger.warning("\n建议检查：")
            logger.warning("1. API服务是否正常运行")
            logger.warning("2. 清理缓存目录重新测试")
            logger.warning("3. 查看详细日志了解API响应")
            
    except Exception as e:
        logger.error(f"\n测试失败: {e}")
        logger.exception("详细错误信息:")
    
    return videos if 'videos' in locals() else []


async def test_download_only():
    """测试获取视频信息和下载阶段（不发布）"""
    
    logger.info("=" * 80)
    logger.info("开始测试视频下载")
    logger.info("=" * 80)
    
    config = {
        "api_base_url": "http://localhost:51084",
        "max_videos_per_creator": 1,  # 只下载1个视频进行测试
        "storage_base_path": "outputs/douyin_videos",
        "cache_dir": "outputs/douyin_cache",
        "download_timeout": 300
    }
    
    logger.info(f"Pipeline配置:")
    for key, value in config.items():
        logger.info(f"  {key}: {value}")
    
    pipeline = DouyinDownloadPublishPipeline(config)
    
    # 使用PipelineContext进行测试
    from pipelines.pipeline_context import PipelineContext
    
    creator_id = "MS4wLjABAAAAOFERtNs1K2GvCA-NWS_WtWebO_34EpBFei8F4IWOta-ctOXnft2CsodDIu29heN6"
    params = {
        "creator_ids": [creator_id],
        "max_videos_per_creator": 1
    }
    
    context = PipelineContext(params)
    
    try:
        # 步骤1: 获取视频信息
        logger.info("\n" + "="*60)
        logger.info("步骤1: 获取视频信息")
        logger.info("="*60)
        
        videos = await pipeline.fetch_creator_videos(context, params['creator_ids'])
        
        if not videos:
            logger.warning("没有找到未处理的视频，无法继续测试下载")
            return []
        
        logger.info(f"找到 {len(videos)} 个视频待下载")
        
        # 步骤2: 下载媒体文件
        logger.info("\n" + "="*60)
        logger.info("步骤2: 下载媒体文件")
        logger.info("="*60)
        
        downloaded_videos = await pipeline.download_media(context, videos)
        
        logger.info(f"\n下载结果: 成功下载 {len(downloaded_videos)} 个视频")
        
        for idx, video in enumerate(downloaded_videos, 1):
            logger.info(f"\n视频 {idx}:")
            logger.info(f"  - aweme_id: {video['aweme_id']}")
            logger.info(f"  - 视频文件: {video.get('video_path', 'N/A')}")
            logger.info(f"  - 封面文件: {video.get('cover_path', 'N/A')}")
            logger.info(f"  - 下载时间: {video.get('download_time', 'N/A')}")
            
            # 检查文件是否存在
            from pathlib import Path
            if video.get('video_path'):
                video_exists = Path(video['video_path']).exists()
                logger.info(f"  - 视频文件存在: {video_exists}")
            
            if video.get('cover_path'):
                cover_exists = Path(video['cover_path']).exists()
                logger.info(f"  - 封面文件存在: {cover_exists}")
        
        return downloaded_videos
        
    except Exception as e:
        logger.error(f"\n测试失败: {e}")
        logger.exception("详细错误信息:")
        return []


async def test_full_with_publish(account_id=None):
    """测试完整流程：获取、下载、发布"""
    
    logger.info("=" * 80)
    logger.info("开始测试完整流程（包含发布）")
    logger.info("=" * 80)
    
    # 使用传入的账号ID或默认测试账号
    YOUTUBE_ACCOUNT_ID = account_id if account_id else "test_account"  # 替换为真实的账号ID
    
    config = {
        "api_base_url": "http://localhost:51084",
        "max_videos_per_creator": 1,  # 只处理1个视频
        "storage_base_path": "outputs/douyin_videos",
        "cache_dir": "outputs/douyin_cache",
        "download_timeout": 300
    }
    
    # 创建Pipeline实例
    pipeline = DouyinDownloadPublishPipeline(config)
    
    # 执行参数
    params = {
        "creator_ids": [
            "MS4wLjABAAAAOFERtNs1K2GvCA-NWS_WtWebO_34EpBFei8F4IWOta-ctOXnft2CsodDIu29heN6"
        ],
        "account_id": YOUTUBE_ACCOUNT_ID,  # YouTube账号ID
        "max_videos_per_creator": 1
    }
    
    logger.info(f"Pipeline配置:")
    for key, value in config.items():
        logger.info(f"  {key}: {value}")
    
    logger.info(f"执行参数:")
    logger.info(f"  creator_ids: {params['creator_ids']}")
    logger.info(f"  account_id: {params['account_id']}")
    logger.info(f"  max_videos_per_creator: {params['max_videos_per_creator']}")
    
    if YOUTUBE_ACCOUNT_ID == "test_account":
        logger.warning("\n" + "⚠️ "*20)
        logger.warning("警告：使用的是测试账号ID，发布可能会失败！")
        logger.warning("请使用 --account-id 参数提供真实的YouTube账号ID")
        logger.warning("例如: python test_douyin_pipeline.py --mode publish --account-id YOUR_REAL_ACCOUNT_ID")
        logger.warning("⚠️ "*20 + "\n")
        
        # 询问是否继续
        response = input("是否继续测试？(y/n): ")
        if response.lower() != 'y':
            logger.info("测试已取消")
            return None
    
    # 执行完整Pipeline
    result = await pipeline.execute(params)
    
    # 输出结果
    logger.info("\n" + "="*80)
    logger.info("执行结果")
    logger.info("="*80)
    
    if result['success']:
        logger.info("✅ Pipeline执行成功!")
        logger.info(f"处理统计:")
        logger.info(f"  - 找到视频数: {result['data']['total_processed']}")
        logger.info(f"  - 下载成功数: {result['data']['total_downloaded']}")
        logger.info(f"  - 发布成功数: {result['data']['total_published']}")
        
        # 输出发布结果
        if result['data'].get('publish_results'):
            logger.info("\n发布结果详情:")
            for pr in result['data']['publish_results']:
                logger.info(f"  - 视频 {pr['aweme_id']}:")
                if pr['success']:
                    logger.info(f"    ✅ 发布成功")
                    logger.info(f"    YouTube URL: {pr.get('youtube_url', 'N/A')}")
                else:
                    logger.info(f"    ❌ 发布失败: {pr.get('error', 'Unknown error')}")
        
        # 输出各阶段结果
        logger.info("\n各阶段执行结果:")
        for stage in result['stages']:
            logger.info(f"  - {stage['name']}: {'✅ 成功' if stage['success'] else '❌ 失败'}")
            if stage.get('data'):
                logger.info(f"    数据: {stage['data']}")
    else:
        logger.error(f"❌ Pipeline执行失败: {result.get('error')}")
        
        # 输出各阶段结果，帮助定位问题
        if result.get('stages'):
            logger.info("\n各阶段执行情况:")
            for stage in result['stages']:
                logger.info(f"  - {stage['name']}: {'✅ 成功' if stage.get('success') else '❌ 失败'}")
                if stage.get('error'):
                    logger.error(f"    错误: {stage['error']}")
    
    return result


def print_test_summary():
    """打印测试模式说明"""
    summary = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                           抖音下载发布Pipeline测试工具                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  支持的测试模式:                                                               ║
║                                                                              ║
║  1. fetch    - 仅测试获取视频信息                                              ║
║     功能: 从API获取视频列表，检查去重逻辑                                         ║
║     命令: python test_douyin_pipeline.py --mode fetch                        ║
║                                                                              ║
║  2. download - 测试获取和下载                                                  ║
║     功能: 获取视频信息后下载视频和封面                                            ║
║     命令: python test_douyin_pipeline.py --mode download                     ║
║                                                                              ║
║  3. publish  - 完整流程测试                                                    ║
║     功能: 获取、下载并发布到YouTube                                             ║
║     命令: python test_douyin_pipeline.py --mode publish --account-id ACCOUNT ║
║                                                                              ║
║  可选参数:                                                                     ║
║    --verbose      显示详细的调试信息                                            ║
║    --account-id   指定YouTube账号ID（发布模式必需）                              ║
║    --max-videos   每个创作者处理的最大视频数（默认1）                              ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    print(summary)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='测试抖音下载发布Pipeline')
    parser.add_argument('--mode', 
                      choices=['fetch', 'download', 'publish', 'full'], 
                      default='fetch',
                      help='测试模式: fetch(仅获取), download(获取+下载), publish(完整流程+发布), full(旧版完整流程)')
    parser.add_argument('--verbose', action='store_true',
                      help='显示更详细的输出')
    parser.add_argument('--creator-id', type=str,
                      help='指定创作者ID进行测试（暂未实现）')
    parser.add_argument('--account-id', type=str, default='test_account',
                      help='YouTube账号ID（用于发布测试）')
    parser.add_argument('--max-videos', type=int, default=1,
                      help='每个创作者处理的最大视频数')
    
    args = parser.parse_args()
    
    # 如果是帮助模式，打印测试说明
    if len(sys.argv) == 1:
        print_test_summary()
        parser.print_help()
        return
    
    logger.info(f"运行模式: {args.mode}")
    
    if args.verbose:
        logging.getLogger('pipelines.douyin_download_publish_pipeline').setLevel(logging.DEBUG)
    
    if args.mode == 'fetch':
        # 仅测试获取视频信息
        asyncio.run(test_fetch_only())
    elif args.mode == 'download':
        # 测试获取和下载
        asyncio.run(test_download_only())
    elif args.mode == 'publish':
        # 测试完整流程（包含发布）
        asyncio.run(test_full_with_publish(args.account_id))
    else:
        # 旧版完整流程测试
        asyncio.run(test_pipeline())


if __name__ == "__main__":
    main()