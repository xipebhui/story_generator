#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Debug test for YouTube metadata generation
"""

import sys
import io
import json
import logging
from pathlib import Path

# Fix encoding issue for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from pipeline_context_v3 import PipelineContextV3
from pipeline_steps_youtube_metadata import GenerateYouTubeMetadataStep
from gemini_client import GeminiClient

def test_youtube_metadata_debug():
    """Debug test for YouTube metadata generation"""
    
    print("="*60)
    print("Debug YouTube Metadata Generation")
    print("="*60)
    
    # Create test context
    video_id = "aSiVP7rJsqQ"
    context = PipelineContextV3(
        video_id=video_id,
        creator_name="test",
        cache_dir=Path("story_result/test") / video_id
    )
    context.save_intermediate = True
    
    # Load framework data
    try:
        framework_file = context.cache_dir / "processing" / "framework_v3.json"
        if framework_file.exists():
            with open(framework_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"Framework file size: {len(content)} bytes")
                
                # Try to parse it
                try:
                    data = json.loads(content)
                    print(f"Framework parsed successfully, keys: {list(data.keys())}")
                    
                    # Check if 'json' key exists
                    if 'json' in data:
                        framework_json = data['json']
                        if isinstance(framework_json, str):
                            print("WARNING: framework json is a string, parsing it...")
                            # The json field might be a JSON string that needs parsing
                            try:
                                framework_json = json.loads(framework_json)
                                print(f"Parsed framework json, keys: {list(framework_json.keys()) if isinstance(framework_json, dict) else 'not a dict'}")
                            except json.JSONDecodeError as e:
                                print(f"ERROR parsing framework json string: {e}")
                                print(f"String preview: {framework_json[:200]}...")
                        
                        context.framework_v3_json = framework_json
                    else:
                        print("ERROR: No 'json' key in framework data")
                        context.framework_v3_json = {}
                        
                except json.JSONDecodeError as e:
                    print(f"ERROR parsing framework file: {e}")
                    print(f"Error at position {e.pos}")
                    print(f"Content around error: {content[max(0, e.pos-50):min(len(content), e.pos+50)]}")
                    return False
        else:
            print(f"Framework file not found: {framework_file}")
            return False
            
    except Exception as e:
        print(f"ERROR loading framework: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Load story
    story_file = context.cache_dir / "final" / "story.txt"
    if story_file.exists():
        with open(story_file, 'r', encoding='utf-8') as f:
            context.final_story = f.read()
            print(f"Story loaded, length: {len(context.final_story)}")
    
    # Load video info
    video_info_file = context.cache_dir / "raw" / "video_info.json"
    if video_info_file.exists():
        with open(video_info_file, 'r', encoding='utf-8') as f:
            context.video_info = json.load(f)
            print(f"Video info loaded")
    
    # Set segment count
    parsed_file = context.cache_dir / "processing" / "parsed_segments.json"
    if parsed_file.exists():
        with open(parsed_file, 'r', encoding='utf-8') as f:
            parsed_data = json.load(f)
            context.segment_count = parsed_data.get('segment_count', 0)
            print(f"Segment count: {context.segment_count}")
    
    # Create Gemini client
    gemini_client = GeminiClient(api_key="sk-oFdSWMX8z3cAYYCrGYCcwAupxMdiErcOKBsfi5k0QdRxELCu")
    
    # Create step
    step = GenerateYouTubeMetadataStep(gemini_client)
    
    # Execute
    print("\nExecuting YouTube metadata generation...")
    result = step.execute(context)
    
    if result.success:
        print("✅ Generation successful")
        if result.data:
            print(f"Generated metadata keys: {list(result.data.keys())}")
    else:
        print("❌ Generation failed")
    
    return result.success

if __name__ == "__main__":
    success = test_youtube_metadata_debug()
    sys.exit(0 if success else 1)