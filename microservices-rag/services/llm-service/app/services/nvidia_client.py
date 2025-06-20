"""
NVIDIA Cloud LLM クライアント

NVIDIA Cloud APIを使用したLLM推論サービス
"""

import httpx
import json
import time
from typing import Dict, Any, Optional, List
from uuid import uuid4

from shared.utils.config import LLMServiceConfig
from shared.utils.logging import get_logger
from shared.utils.exceptions import ProcessingError

logger = get_logger(__name__)

class NVIDIACloudClient:
    """NVIDIA Cloud LLM クライアント"""
    
    def __init__(self, config: LLMServiceConfig):
        self.config = config
        self.api_key = config.nvidia_api_key
        self.base_url = config.nvidia_nim_endpoint or "https://integrate.api.nvidia.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # デフォルトモデル設定
        self.default_model = "nvidia/llama-3.1-nemotron-70b-instruct"
        
        logger.info(f"🤖 NVIDIA Client initialized: {self.base_url}")
    
    def validate_config(self) -> bool:
        """設定の検証"""
        if not self.api_key:
            logger.error("NVIDIA API key not configured")
            return False
        return True
    
    async def generate_response(
        self,
        question: str,
        context: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """質問応答生成"""
        
        if not self.validate_config():
            raise ProcessingError("nvidia_config", "NVIDIA API key not configured")
        
        start_time = time.time()
        
        # パラメータ設定
        model = model or self.default_model
        max_tokens = max_tokens or self.config.default_max_tokens
        temperature = temperature or self.config.default_temperature
        
        # プロンプト構築
        prompt = self._build_prompt(question, context)
        
        # リクエストペイロード
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.9,
            "stream": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"🚀 Sending request to NVIDIA API: {model}")
                
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                
                response.raise_for_status()
                data = response.json()
                
                processing_time = time.time() - start_time
                
                # レスポンス解析
                if "choices" in data and len(data["choices"]) > 0:
                    answer = data["choices"][0]["message"]["content"].strip()
                    
                    logger.info(f"✅ NVIDIA API response received in {processing_time:.3f}s")
                    
                    return {
                        "answer": answer,
                        "model_used": model,
                        "processing_time": processing_time,
                        "token_usage": data.get("usage", {}),
                        "request_id": str(uuid4())
                    }
                else:
                    raise ProcessingError("nvidia_response", "Invalid response format from NVIDIA API")
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"NVIDIA API HTTP error: {e.response.status_code} - {e.response.text}")
            raise ProcessingError("nvidia_api", f"HTTP error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"NVIDIA API request error: {e}")
            raise ProcessingError("nvidia_connection", "Failed to connect to NVIDIA API")
        except Exception as e:
            logger.error(f"NVIDIA API unexpected error: {e}")
            raise ProcessingError("nvidia_unknown", str(e))
    
    def _build_prompt(self, question: str, context: str) -> str:
        """RAG用プロンプト構築"""
        return f"""以下のコンテキストを参考にして、質問に答えてください。コンテキストに含まれていない情報については「コンテキストに情報がありません」と回答してください。

コンテキスト:
{context}

質問: {question}

回答:"""
    
    async def test_connection(self) -> Dict[str, Any]:
        """接続テスト"""
        if not self.validate_config():
            return {
                "status": "error",
                "message": "NVIDIA API key not configured"
            }
        
        try:
            test_payload = {
                "model": self.default_model,
                "messages": [
                    {
                        "role": "user", 
                        "content": "Hello, this is a connection test."
                    }
                ],
                "max_tokens": 10,
                "temperature": 0.1
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=test_payload
                )
                
                if response.status_code == 200:
                    return {
                        "status": "success",
                        "message": "NVIDIA API connection successful",
                        "model": self.default_model
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"HTTP {response.status_code}: {response.text}"
                    }
                    
        except Exception as e:
            return {
                "status": "error",
                "message": f"Connection failed: {str(e)}"
            }