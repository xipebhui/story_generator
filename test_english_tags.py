#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试英文标签过滤功能
"""

import re
import json

def filter_english_tags(tags_data):
    """模拟publish_service中的英文标签过滤逻辑"""
    english_tags = []
    
    if isinstance(tags_data, dict):
        # 首先获取english标签
        if 'english' in tags_data and tags_data['english']:
            english_tags = tags_data['english'].copy()
        
        # 如果english标签为空或不足，从mixed中过滤英文标签
        if len(english_tags) < 10 and 'mixed' in tags_data:
            for tag in tags_data['mixed']:
                # 判断是否为英文标签（只包含英文字母、数字、空格和常见符号）
                if tag and re.match(r'^[a-zA-Z0-9\s\-\'&.,!]+$', tag):
                    if tag not in english_tags:  # 避免重复
                        english_tags.append(tag)
                        if len(english_tags) >= 20:  # YouTube限制最多20个标签
                            break
        
        return english_tags[:20]
    elif isinstance(tags_data, list):
        # 如果是列表格式，过滤出英文标签
        for tag in tags_data:
            if tag and re.match(r'^[a-zA-Z0-9\s\-\'&.,!]+$', tag):
                english_tags.append(tag)
                if len(english_tags) >= 20:
                    break
        return english_tags
    else:
        return []

def test_cases():
    """测试各种标签数据格式"""
    print("="*60)
    print("测试英文标签过滤功能")
    print("="*60)
    
    # 测试案例1：有english标签的情况
    print("\n测试1: 有english标签")
    tags1 = {
        'chinese': ['中文标签1', '测试', '小说'],
        'english': ['Story', 'Romance', 'Love Story', 'Drama'],
        'mixed': ['混合tag', 'Test123', '测试mixed']
    }
    result1 = filter_english_tags(tags1)
    print(f"输入: {json.dumps(tags1, ensure_ascii=False)}")
    print(f"结果: {result1}")
    print(f"数量: {len(result1)}")
    
    # 测试案例2：english标签为空，需要从mixed中提取
    print("\n测试2: english为空，从mixed提取")
    tags2 = {
        'chinese': ['中文标签1', '测试', '小说'],
        'english': [],
        'mixed': ['Chef Redemption', '背叛', 'Betrayal Story', '励志故事', 'True Love', 'Women Empowerment', '逆袭', 'Married a CEO']
    }
    result2 = filter_english_tags(tags2)
    print(f"输入: {json.dumps(tags2, ensure_ascii=False)}")
    print(f"结果: {result2}")
    print(f"数量: {len(result2)}")
    
    # 测试案例3：english标签不足，需要从mixed补充
    print("\n测试3: english不足10个，从mixed补充")
    tags3 = {
        'chinese': ['中文1', '中文2'],
        'english': ['Story', 'Drama'],  # 只有2个
        'mixed': ['Life Story', 'Success Story', '成功故事', 'Inspirational', '励志', 'CEO Romance', 'Love & Betrayal', 'Women Power']
    }
    result3 = filter_english_tags(tags3)
    print(f"输入: {json.dumps(tags3, ensure_ascii=False)}")
    print(f"结果: {result3}")
    print(f"数量: {len(result3)}")
    
    # 测试案例4：列表格式的标签
    print("\n测试4: 列表格式标签")
    tags4 = ['Story', '故事', 'Romance', '爱情', 'Drama', 'Love Story', '小说', 'CEO', '总裁']
    result4 = filter_english_tags(tags4)
    print(f"输入: {tags4}")
    print(f"结果: {result4}")
    print(f"数量: {len(result4)}")
    
    # 测试案例5：包含特殊字符的标签
    print("\n测试5: 包含特殊字符的英文标签")
    tags5 = {
        'chinese': [],
        'english': [],
        'mixed': ["Chef's Redemption", 'Love & Marriage', 'Day-1 Story', 'Test!', '测试@#$', 'Valid-Tag', 'Also, Valid']
    }
    result5 = filter_english_tags(tags5)
    print(f"输入: {json.dumps(tags5, ensure_ascii=False)}")
    print(f"结果: {result5}")
    print(f"数量: {len(result5)}")
    
    # 测试案例6：超过20个标签的情况
    print("\n测试6: 超过20个标签（应该限制为20个）")
    tags6 = {
        'english': [f'Tag{i}' for i in range(25)]  # 25个标签
    }
    result6 = filter_english_tags(tags6)
    print(f"输入: {len(tags6['english'])}个英文标签")
    print(f"结果数量: {len(result6)}")
    print(f"前5个: {result6[:5]}")
    print(f"后5个: {result6[-5:]}")
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)

if __name__ == "__main__":
    test_cases()