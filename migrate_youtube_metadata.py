#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
迁移脚本：将数据库中的 YouTube metadata 从旧格式转换为新的简化格式
"""

import json
import sqlite3
from pathlib import Path
import logging
from typing import Dict, Any, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def convert_metadata_to_new_format(old_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    将旧格式的 metadata 转换为新格式
    
    旧格式:
    {
        "titles": {"chinese": [...], "english": [...]},
        "descriptions": {"chinese": "...", "english": "..."},
        "tags": {"chinese": [...], "english": [...], "mixed": [...]},
        "thumbnail": {
            "visual_focus": "...",
            "text_overlay": {"chinese": "...", "english": "..."},
            "color_scheme": "...",
            "emotion": "..."
        }
    }
    
    新格式:
    {
        "title": "单个英文标题",
        "description": "英文描述",
        "tags": ["tag1", "tag2", ...],
        "image_prompt": "图片提示词，包含 ^文字叠加^"
    }
    """
    
    # 如果已经是新格式，直接返回
    if 'title' in old_metadata and isinstance(old_metadata.get('title'), str):
        logger.debug("数据已经是新格式，跳过转换")
        return old_metadata
    
    new_metadata = {}
    
    # 转换标题 - 取英文标题的第一个
    if 'titles' in old_metadata:
        english_titles = old_metadata.get('titles', {}).get('english', [])
        if english_titles and len(english_titles) > 0:
            # 优先选择包含悬念词汇的标题
            suspense_keywords = ['secret', 'shocking', 'revealed', 'never', 'changed', 'discovered', 'truth']
            for title in english_titles:
                if any(keyword.lower() in title.lower() for keyword in suspense_keywords):
                    new_metadata['title'] = title
                    break
            # 如果没有找到悬念标题，使用第一个
            if 'title' not in new_metadata:
                new_metadata['title'] = english_titles[0]
    
    # 如果旧格式中直接有 title 字段
    if 'title' in old_metadata and isinstance(old_metadata['title'], str):
        new_metadata['title'] = old_metadata['title']
    
    # 转换描述 - 取英文描述，并在末尾添加标签
    if 'descriptions' in old_metadata:
        english_desc = old_metadata.get('descriptions', {}).get('english', '')
        if english_desc:
            new_metadata['description'] = english_desc
            
            # 如果描述中没有标签，从tags中添加
            if 'Tags:' not in english_desc and '#' not in english_desc:
                tags = []
                if 'tags' in old_metadata:
                    if isinstance(old_metadata['tags'], dict):
                        tags = old_metadata['tags'].get('english', [])[:10]  # 最多10个标签
                    elif isinstance(old_metadata['tags'], list):
                        tags = old_metadata['tags'][:10]
                
                if tags:
                    tag_str = ' '.join([f'#{tag}' for tag in tags])
                    new_metadata['description'] = f"{english_desc}\n\nTags: {tag_str}"
    
    # 如果旧格式中直接有 description 字段
    if 'description' in old_metadata and isinstance(old_metadata['description'], str):
        new_metadata['description'] = old_metadata['description']
    
    # 转换标签 - 取英文标签
    if 'tags' in old_metadata:
        if isinstance(old_metadata['tags'], dict):
            english_tags = old_metadata['tags'].get('english', [])
            if english_tags:
                new_metadata['tags'] = english_tags
        elif isinstance(old_metadata['tags'], list):
            new_metadata['tags'] = old_metadata['tags']
    
    # 转换缩略图信息为 image_prompt
    if 'thumbnail' in old_metadata:
        thumbnail = old_metadata['thumbnail']
        prompt_parts = []
        
        # 添加视觉焦点
        if thumbnail.get('visual_focus'):
            prompt_parts.append(thumbnail['visual_focus'])
        
        # 添加配色方案
        if thumbnail.get('color_scheme'):
            prompt_parts.append(f"Color scheme: {thumbnail['color_scheme']}")
        
        # 添加情感表达
        if thumbnail.get('emotion'):
            prompt_parts.append(f"Emotion: {thumbnail['emotion']}")
        
        # 组合提示词
        image_prompt = '. '.join(prompt_parts) if prompt_parts else "Dramatic thumbnail design"
        
        # 添加文字叠加（用^标记）
        if thumbnail.get('text_overlay'):
            text_overlay = thumbnail['text_overlay']
            if isinstance(text_overlay, dict):
                # 优先使用英文文字
                overlay_text = text_overlay.get('english') or text_overlay.get('chinese', '')
            else:
                overlay_text = str(text_overlay)
            
            if overlay_text:
                image_prompt = f"{image_prompt}. Text overlay: ^{overlay_text}^"
        
        new_metadata['image_prompt'] = image_prompt
    
    # 如果旧格式中直接有 image_prompt 字段
    if 'image_prompt' in old_metadata and isinstance(old_metadata['image_prompt'], str):
        new_metadata['image_prompt'] = old_metadata['image_prompt']
    
    # 确保所有必要字段都存在
    if 'title' not in new_metadata:
        new_metadata['title'] = "Untitled Story"
    if 'description' not in new_metadata:
        new_metadata['description'] = "No description available"
    if 'tags' not in new_metadata:
        new_metadata['tags'] = []
    if 'image_prompt' not in new_metadata:
        new_metadata['image_prompt'] = "Dramatic story thumbnail with emotional impact"
    
    return new_metadata


def migrate_database(db_path: str = "./data/pipeline_tasks.db"):
    """
    迁移数据库中的 YouTube metadata
    """
    
    if not Path(db_path).exists():
        logger.error(f"数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 查询所有包含 youtube_metadata 的任务
        cursor.execute("""
            SELECT task_id, youtube_metadata 
            FROM pipeline_tasks 
            WHERE youtube_metadata IS NOT NULL AND youtube_metadata != ''
        """)
        
        rows = cursor.fetchall()
        logger.info(f"找到 {len(rows)} 个包含 YouTube metadata 的任务")
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for task_id, metadata_json in rows:
            try:
                # 解析 JSON
                if isinstance(metadata_json, str):
                    old_metadata = json.loads(metadata_json)
                else:
                    old_metadata = metadata_json
                
                # 检查是否已经是新格式
                if 'title' in old_metadata and isinstance(old_metadata.get('title'), str) and \
                   'titles' not in old_metadata and 'thumbnail' not in old_metadata:
                    logger.debug(f"任务 {task_id} 已经是新格式，跳过")
                    skipped_count += 1
                    continue
                
                # 转换为新格式
                new_metadata = convert_metadata_to_new_format(old_metadata)
                
                # 更新数据库
                cursor.execute("""
                    UPDATE pipeline_tasks 
                    SET youtube_metadata = ? 
                    WHERE task_id = ?
                """, (json.dumps(new_metadata, ensure_ascii=False), task_id))
                
                updated_count += 1
                logger.info(f"✓ 更新任务 {task_id}")
                
                # 显示转换示例
                if updated_count == 1:
                    logger.info("转换示例:")
                    logger.info(f"  标题: {new_metadata.get('title', 'N/A')[:80]}...")
                    logger.info(f"  描述长度: {len(new_metadata.get('description', ''))} 字符")
                    logger.info(f"  标签数量: {len(new_metadata.get('tags', []))} 个")
                    if new_metadata.get('image_prompt'):
                        import re
                        text_match = re.search(r'\^([^\^]+)\^', new_metadata['image_prompt'])
                        if text_match:
                            logger.info(f"  封面文字: {text_match.group(1)}")
                
            except json.JSONDecodeError as e:
                logger.error(f"任务 {task_id} 的 JSON 解析失败: {e}")
                error_count += 1
            except Exception as e:
                logger.error(f"任务 {task_id} 转换失败: {e}")
                error_count += 1
        
        # 提交更改
        conn.commit()
        
        # 显示统计
        logger.info("=" * 60)
        logger.info("迁移完成!")
        logger.info(f"  更新: {updated_count} 个任务")
        logger.info(f"  跳过: {skipped_count} 个任务（已是新格式）")
        logger.info(f"  错误: {error_count} 个任务")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"迁移过程出错: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def verify_migration(db_path: str = "./data/pipeline_tasks.db"):
    """
    验证迁移结果
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT task_id, youtube_metadata 
            FROM pipeline_tasks 
            WHERE youtube_metadata IS NOT NULL AND youtube_metadata != ''
            LIMIT 5
        """)
        
        rows = cursor.fetchall()
        
        logger.info("\n验证迁移结果（前5个）:")
        logger.info("=" * 60)
        
        for task_id, metadata_json in rows:
            try:
                metadata = json.loads(metadata_json)
                logger.info(f"\n任务 ID: {task_id}")
                logger.info(f"  格式: {'新格式 ✓' if 'title' in metadata and 'titles' not in metadata else '旧格式 ✗'}")
                logger.info(f"  字段: {', '.join(metadata.keys())}")
                
                if 'title' in metadata:
                    logger.info(f"  标题: {metadata['title'][:50]}...")
                if 'tags' in metadata and isinstance(metadata['tags'], list):
                    logger.info(f"  标签: {', '.join(metadata['tags'][:5])}...")
                    
            except Exception as e:
                logger.error(f"任务 {task_id} 验证失败: {e}")
        
    finally:
        conn.close()


def backup_database(db_path: str):
    """
    备份数据库
    """
    import shutil
    from datetime import datetime
    
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    logger.info(f"数据库已备份到: {backup_path}")
    return backup_path


def main():
    """
    主函数
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='迁移 YouTube metadata 到新格式')
    parser.add_argument('--db', default='./data/pipeline_tasks.db', help='数据库文件路径')
    parser.add_argument('--verify-only', action='store_true', help='仅验证，不执行迁移')
    parser.add_argument('--no-backup', action='store_true', help='不创建备份')
    parser.add_argument('--verbose', action='store_true', help='显示详细日志')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.verify_only:
        logger.info("仅验证模式")
        verify_migration(args.db)
    else:
        # 创建备份
        if not args.no_backup:
            backup_path = backup_database(args.db)
            logger.info(f"如需恢复，运行: cp {backup_path} {args.db}")
        
        logger.info(f"开始迁移数据库: {args.db}")
        migrate_database(args.db)
        logger.info("\n验证迁移结果...")
        verify_migration(args.db)


if __name__ == "__main__":
    main()