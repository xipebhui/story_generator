# youtube_analyzer/clients/gemini_client.py
import logging
import os
import argparse
import json
import requests
import base64
from typing import Optional, Dict
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

class GeminiClient:
    """A simplified client for interacting with Gemini via NewAPI."""
    def __init__(self, api_key: Optional[str] = None):
        logger.info("Initializing GeminiClient with NewAPI")
        
        # 获取 API key
        self.api_key = api_key or os.getenv('NEWAPI_API_KEY')
        if not self.api_key:
            logger.error("No NEWAPI_API_KEY found in environment variables.")
            raise ValueError("NEWAPI_API_KEY is required to initialize GeminiClient.")
        
        # 从环境变量获取基础 URL，如果没有则使用默认值
        self.base_url = os.getenv("NEWAPI_BASE_URL", "http://27.152.58.86:51099")
        
        self.model = "gemini-2.5-flash"
        
        logger.info(f"GeminiClient initialized with NewAPI (key: {'*' * 10 + self.api_key[-4:] if self.api_key else 'None'})")

    def analyze_text(self, text: str, prompt: str) -> Optional[str]:
        """
        Analyzes the given text using the specified prompt and returns the raw JSON string.
        """
        if not text or not prompt:
            logger.warning("Text and prompt cannot be empty.")
            return None
        
        full_prompt = f"{prompt}\n\n---\n\n{text}"
        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": full_prompt}]
            }],
            "generationConfig": {
                "response_mime_type": "application/json"
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            
            result = response.json()
            if "candidates" in result and result["candidates"]:
                content = result["candidates"][0].get("content", {})
                if "parts" in content and content["parts"]:
                    logger.info("Successfully received response from NewAPI.")
                    return content["parts"][0].get("text", "")
            
            logger.error(f"Unexpected response format: {result}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API call failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return None
    
    def generate_content_with_history(self, prompt: str, history: list = None) -> Optional[str]:
        """
        生成内容，支持对话历史
        
        Args:
            prompt: 当前提示
            history: 对话历史列表
            
        Returns:
            生成的内容
        """
        if not prompt:
            logger.warning("Prompt cannot be empty.")
            return None
        
        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        # 构建内容
        if history:
            # 使用提供的历史记录
            contents = history.copy()
            # 如果最后一条不是用户消息，添加当前提示作为新的用户消息
            if contents and contents[-1].get("role") != "user":
                contents.append({
                    "role": "user",
                    "parts": [{"text": prompt}]
                })
        else:
            # 没有历史，只使用当前提示
            contents = [{
                "role": "user",
                "parts": [{"text": prompt}]
            }]
        
        payload = {
            "contents": contents
        }
        
        try:
            response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            
            result = response.json()
            if "candidates" in result and result["candidates"]:
                content = result["candidates"][0].get("content", {})
                if "parts" in content and content["parts"]:
                    logger.info("Successfully received response with history context.")
                    return content["parts"][0].get("text", "")
            
            logger.error(f"Unexpected response format: {result}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API call with history failed: {e}")
            raise e 
    
    def generate_content(self, prompt: str, use_file_for_long_content: bool = True) -> Optional[str]:
        """
        Generates content based on the given prompt (for non-JSON responses).
        For very long prompts, can use file upload to avoid token limits.
        """
        if not prompt:
            logger.warning("Prompt cannot be empty.")
            return None
        
        # 检查是否需要使用文件上传（超过30000字符）
        if use_file_for_long_content and len(prompt) > 30000:
            logger.info(f"Prompt is very long ({len(prompt)} chars), using inline data method")
            return self._generate_with_file_upload(prompt)
        logger.info(f"input apikey = {self.api_key}")
        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        try:
            response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            
            result = response.json()
            if "candidates" in result and result["candidates"]:
                content = result["candidates"][0].get("content", {})
                if "parts" in content and content["parts"]:
                    logger.info("Successfully received response from NewAPI.")
                    return content["parts"][0].get("text", "")
            
            logger.error(f"Unexpected response format: {result}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API call failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return None
    
    def _generate_with_file_upload(self, content: str) -> Optional[str]:
        """使用 base64 inline data 处理超长内容"""
        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        # 将内容转换为 base64
        content_bytes = content.encode('utf-8')
        content_base64 = base64.b64encode(content_bytes).decode('utf-8')
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": "请阅读并分析以下内容："},
                    {
                        "inline_data": {
                            "mime_type": "text/plain",
                            "data": content_base64
                        }
                    },
                    {"text": "\n请根据内容完成相应的分析和创作任务。"}
                ]
            }]
        }
        
        try:
            response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            
            result = response.json()
            if "candidates" in result and result["candidates"]:
                content = result["candidates"][0].get("content", {})
                if "parts" in content and content["parts"]:
                    logger.info("Successfully received response from NewAPI using inline data.")
                    return content["parts"][0].get("text", "")
            
            logger.error(f"Unexpected response format: {result}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API call with inline data failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return None
    
    async def generate_content_async(self, prompt: str) -> Optional[str]:
        """
        Async wrapper for generate_content (actually runs synchronously).
        """
        return self.generate_content(prompt)

def main():
    """
    Main function to run the script from the command line.
    It takes text and prompt as arguments, calls the Gemini API,
    and prints the JSON output to stdout.
    """
    api_key = 'sk-oFdSWMX8z3cAYYCrGYCcwAupxMdiErcOKBsfi5k0QdRxELCu'
    prompt = "你好"
    text = "gemini"
    try:
        client = GeminiClient(api_key=api_key)
        analysis_json = client.analyze_text(text , prompt)
        
        if analysis_json:
            # Print the raw JSON output directly to stdout
            print(analysis_json)
        else:
            logger.error("Failed to get analysis from Gemini.")
            exit(1)

    except ValueError as e:
        logger.error(e)
        exit(1)

if __name__ == '__main__':
    main()