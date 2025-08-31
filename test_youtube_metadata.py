#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 YouTube Metadata 生成功能
"""

import json
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import logging

# 添加项目根目录到系统路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_youtube_metadata_generation():
    """测试 YouTube metadata 生成功能"""
    
    # 导入必要的模块
    from pipeline_steps_youtube_metadata import GenerateYouTubeMetadataStep
    from pipeline_context_v3 import PipelineContextV3
    from gemini_client import GeminiClient
    
    print("=" * 60)
    print("测试 YouTube Metadata 生成功能")
    print("=" * 60)
    
    # 1. 创建模拟的 Gemini 客户端
    mock_gemini = Mock(spec=GeminiClient)
    
    # 模拟 AI 返回的简化 JSON 响应
    mock_response = """```json
{
  "title": "She Discovered Her Husband's Dark Secret After 20 Years - What Happened Next Will Shock You",
  "description": "A woman's perfect life unravels when she accidentally discovers a hidden room in their basement after two decades of marriage. What started as a simple home renovation project turned into a life-changing revelation that nobody saw coming. This true story explores trust, secrets, and the choices we make when everything we believed turns out to be a lie. Tags: #truecrime #mystery #shocking #storytime #viral #mustsee #realstory #marriage #secrets #thriller",
  "tags": ["truecrime", "mystery", "shocking", "storytime", "viral", "mustsee", "realstory", "marriage", "secrets", "thriller", "basement", "discovery", "revelation", "suspense", "unexpected"],
  "image_prompt": "Dark atmospheric basement scene with dramatic lighting, a woman in her 40s standing at the top of basement stairs looking down with shocked expression, mysterious shadows below, cinematic composition, photorealistic style, moody color grading with blues and amber highlights, ^20 YEARS OF LIES^ text overlay in bold white letters with red glow effect"
}
```"""
    
    mock_gemini.generate_content.return_value = mock_response
    
    # 2. 创建测试上下文
    context = PipelineContextV3(
        video_id="test_video_123",
        creator_name="test_creator",
        cache_dir=Path("./test_output/test_creator/test_video_123")
    )
    
    # 设置必要的上下文数据
    context.save_intermediate = True
    context.framework_v3_json = {
        'adaptationAnalysis': {
            'newStoryTitle': 'The Basement Secret',
            'coreConcept': 'A story about hidden truths and family secrets',
            'mainCharacters': ['Sarah', 'John'],
            'openingReplicationStrategy': {
                'hook': 'Shocking discovery in the basement'
            }
        }
    }
    context.video_info = {
        'title': 'Original Video Title for Testing'
    }
    context.final_story = "This is a test story about a woman who discovered something shocking in her basement after 20 years of marriage. The story continues with many twists and turns..." * 10
    context.segment_count = 5
    
    # 3. 创建 metadata 生成步骤
    metadata_step = GenerateYouTubeMetadataStep(mock_gemini)
    
    # 4. 执行生成
    print("\n开始生成 YouTube Metadata...")
    result = metadata_step.execute(context)
    
    # 5. 验证结果
    print("\n验证结果...")
    assert result.success, "生成应该成功"
    
    # 检查生成的 metadata
    metadata = context.youtube_metadata
    assert metadata is not None, "应该生成 metadata"
    
    print("\n生成的 Metadata 结构:")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    
    # 验证必要的字段
    required_fields = ['title', 'description', 'tags', 'image_prompt']
    for field in required_fields:
        assert field in metadata, f"缺少必要字段: {field}"
        print(f"✓ 字段 '{field}' 存在")
    
    # 验证字段类型
    assert isinstance(metadata['title'], str), "title 应该是字符串"
    assert isinstance(metadata['description'], str), "description 应该是字符串"
    assert isinstance(metadata['tags'], list), "tags 应该是列表"
    assert isinstance(metadata['image_prompt'], str), "image_prompt 应该是字符串"
    print("✓ 所有字段类型正确")
    
    # 验证内容特征
    assert len(metadata['title']) > 10, "标题应该有实质内容"
    assert len(metadata['description']) > 50, "描述应该有实质内容"
    assert len(metadata['tags']) >= 10, "应该有至少10个标签"
    assert '^' in metadata['image_prompt'], "图片提示词应该包含用^标记的文字"
    print("✓ 内容验证通过")
    
    # 验证文件保存
    json_file = context.cache_dir / "final" / "youtube_metadata.json"
    if json_file.exists():
        print(f"✓ JSON 文件已保存: {json_file}")
        with open(json_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            print("\n保存的 JSON 内容:")
            print(json.dumps(saved_data, ensure_ascii=False, indent=2))
    
    print("\n" + "=" * 60)
    print("✅ 测试通过！YouTube Metadata 生成功能符合预期")
    print("=" * 60)
    
    return metadata


def test_prompt_file():
    """测试提示词文件是否正确"""
    print("\n测试提示词文件...")
    
    prompt_file = Path("prompts/youtube_meta_gen.md")
    if not prompt_file.exists():
        print(f"❌ 提示词文件不存在: {prompt_file}")
        return False
    
    with open(prompt_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查关键内容
    assert "title" in content.lower(), "提示词应包含 title"
    assert "description" in content.lower(), "提示词应包含 description"
    assert "tags" in content.lower(), "提示词应包含 tags"
    assert "image_prompt" in content.lower(), "提示词应包含 image_prompt"
    assert "^" in content, "提示词应包含 ^ 符号说明"
    
    print("✓ 提示词文件验证通过")
    print(f"  文件路径: {prompt_file}")
    print(f"  文件大小: {len(content)} 字符")
    
    return True


def main():
    """主测试函数"""
    try:
        # 创建测试输出目录
        test_dir = Path("./test_output/test_creator/test_video_123/final")
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # 测试提示词文件
        test_prompt_file()
        
        # 测试生成功能
        metadata = test_youtube_metadata_generation()
        
        print("\n🎉 所有测试通过！")
        print("\n生成的简化结构示例:")
        print(f"- 标题: {metadata['title'][:50]}...")
        print(f"- 描述: {metadata['description'][:100]}...")
        print(f"- 标签数量: {len(metadata['tags'])} 个")
        print(f"- 图片提示词长度: {len(metadata['image_prompt'])} 字符")
        
        # 清理测试文件
        import shutil
        if Path("./test_output").exists():
            shutil.rmtree("./test_output")
            print("\n已清理测试文件")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()