#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理数据库中的progress字段脏数据
将所有非字符串的值转换为字符串
"""

import sqlite3
import json
import os
import sys
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clean_progress_field(db_path):
    """清理progress字段中的非字符串值"""
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return False
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        logger.info(f"连接到数据库: {db_path}")
        
        # 查询所有包含progress字段的任务
        cursor.execute("SELECT id, progress FROM pipeline_tasks WHERE progress IS NOT NULL AND progress != ''")
        tasks = cursor.fetchall()
        
        logger.info(f"找到 {len(tasks)} 个包含progress字段的任务")
        
        fixed_count = 0
        for task_id, progress_str in tasks:
            try:
                # 解析JSON
                progress = json.loads(progress_str)
                
                # 检查是否需要修复
                needs_fix = False
                fixed_progress = {}
                
                for key, value in progress.items():
                    if not isinstance(value, str):
                        needs_fix = True
                        # 转换为字符串
                        if isinstance(value, bool):
                            # 布尔值特殊处理
                            if key == 'manual_subtitle':
                                fixed_progress[key] = 'uploaded' if value else 'pending'
                            else:
                                fixed_progress[key] = 'completed' if value else 'pending'
                        else:
                            fixed_progress[key] = str(value)
                        logger.info(f"  任务 {task_id}: 修复 {key}: {value} ({type(value).__name__}) -> {fixed_progress[key]} (str)")
                    else:
                        fixed_progress[key] = value
                
                if needs_fix:
                    # 更新数据库
                    cursor.execute(
                        "UPDATE pipeline_tasks SET progress = ? WHERE id = ?",
                        (json.dumps(fixed_progress, ensure_ascii=False), task_id)
                    )
                    fixed_count += 1
                    logger.info(f"✅ 任务 {task_id} 的progress字段已修复")
                    
            except json.JSONDecodeError as e:
                logger.warning(f"任务 {task_id} 的progress字段不是有效的JSON: {e}")
                continue
            except Exception as e:
                logger.error(f"处理任务 {task_id} 时出错: {e}")
                continue
        
        # 提交更改
        conn.commit()
        
        logger.info(f"\n修复完成！")
        logger.info(f"总共检查了 {len(tasks)} 个任务")
        logger.info(f"修复了 {fixed_count} 个任务的progress字段")
        
        # 显示修复后的示例
        if fixed_count > 0:
            cursor.execute("SELECT id, progress FROM pipeline_tasks WHERE progress IS NOT NULL AND progress != '' LIMIT 3")
            examples = cursor.fetchall()
            logger.info("\n修复后的示例:")
            for task_id, progress_str in examples:
                try:
                    progress = json.loads(progress_str)
                    logger.info(f"  任务 {task_id}:")
                    for key, value in progress.items():
                        logger.info(f"    {key}: {value} (type: {type(value).__name__})")
                except:
                    pass
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"清理失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    # 获取数据库路径
    db_path = os.environ.get('DB_PATH', './data/pipeline_tasks.db')
    
    if not os.path.exists(db_path):
        # 尝试其他可能的路径
        possible_paths = [
            './data/pipeline_tasks.db',
            '../data/pipeline_tasks.db',
            './pipeline_tasks.db',
            '../pipeline_tasks.db'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                db_path = path
                break
        else:
            logger.error("找不到数据库文件")
            logger.info(f"尝试过的路径: {possible_paths}")
            sys.exit(1)
    
    logger.info("="*60)
    logger.info("数据库清理工具 - 修复progress字段中的非字符串值")
    logger.info("="*60)
    logger.info(f"\n数据库路径: {os.path.abspath(db_path)}")
    
    # 创建备份
    backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        logger.info(f"已创建备份: {backup_path}")
    except Exception as e:
        logger.warning(f"创建备份失败: {e}")
        response = input("是否继续清理？(y/n): ")
        if response.lower() != 'y':
            logger.info("取消清理")
            sys.exit(0)
    
    # 执行清理
    if clean_progress_field(db_path):
        logger.info("\n✅ 清理成功！progress字段中的所有值现在都是字符串类型。")
        logger.info(f"备份文件保存在: {backup_path}")
    else:
        logger.error("\n❌ 清理失败！数据库未更改。")
        logger.info(f"如需恢复，可使用备份文件: {backup_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()