import logging
from typing import Dict, Optional, Any
import asyncio
import aiohttp
import json
from datetime import datetime

# LLM7.io integration
try:
    from langchain_llm7 import ChatLLM7
except ImportError:
    ChatLLM7 = None

# OpenAI fallback
import openai

from ..config import settings

logger = logging.getLogger(__name__)


class LLMAdapter:
    """
    Multi-provider LLM adapter with llm7.io as primary and OpenAI as fallback
    """

    def __init__(self):
        self.llm7_client = None
        self.openai_client = None
        self.primary_model = "gpt-4.1-nano-2025-04-14"
        self.fallback_model = "gpt-4-1106-preview"
        self.llm7_base_url = "https://llm7.io/v1"
        
        self._init_llm7()
        self._init_openai()

    def _init_llm7(self):
        """Initialize llm7.io client"""
        try:
            if hasattr(settings, 'llm7_api_key') and settings.llm7_api_key:
                # Try to use langchain wrapper first
                if ChatLLM7:
                    try:
                        self.llm7_client = ChatLLM7(
                            api_key=settings.llm7_api_key,
                            model=self.primary_model,
                            base_url=self.llm7_base_url
                        )
                        logger.info("LLM7.io client initialized with langchain wrapper")
                        return
                    except Exception as e:
                        logger.warning(f"Langchain wrapper failed: {str(e)}, will use direct HTTP")
                
                # Use direct HTTP as fallback
                self.llm7_client = "direct_http"  # Flag to use direct HTTP
                logger.info("LLM7.io client initialized with direct HTTP")
            else:
                logger.warning("LLM7.io client not available - missing API key")
        except Exception as e:
            logger.error(f"Failed to initialize LLM7.io client: {str(e)}")
            self.llm7_client = None

    def _init_openai(self):
        """Initialize OpenAI client as fallback"""
        try:
            if settings.openai_api_key:
                self.openai_client = openai.OpenAI(api_key=settings.openai_api_key)
                logger.info("OpenAI fallback client initialized successfully")
            else:
                logger.warning("OpenAI fallback not available - missing API key")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            self.openai_client = None

    async def chat_completion(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        timeout: int = 30
    ) -> Optional[str]:
        """
        Generate chat completion using primary provider with fallback
        """
        # Try llm7.io first
        if self.llm7_client:
            try:
                logger.debug(f"Attempting LLM7.io completion with model {self.primary_model}")
                response = await asyncio.wait_for(
                    self._call_llm7(prompt, temperature, max_tokens),
                    timeout=timeout
                )
                if response:
                    logger.info("Successfully completed request with LLM7.io")
                    return response
            except asyncio.TimeoutError:
                logger.warning(f"LLM7.io request timed out after {timeout}s, trying fallback")
            except Exception as e:
                logger.warning(f"LLM7.io request failed: {str(e)}, trying fallback")

        # Fallback to OpenAI
        if self.openai_client:
            try:
                logger.debug(f"Attempting OpenAI completion with model {self.fallback_model}")
                response = await asyncio.wait_for(
                    self._call_openai(prompt, temperature, max_tokens),
                    timeout=timeout
                )
                if response:
                    logger.info("Successfully completed request with OpenAI fallback")
                    return response
            except asyncio.TimeoutError:
                logger.error(f"OpenAI request also timed out after {timeout}s")
            except Exception as e:
                logger.error(f"OpenAI fallback also failed: {str(e)}")

        logger.error("All LLM providers failed")
        return None

    async def _call_llm7(self, prompt: str, temperature: float, max_tokens: int) -> Optional[str]:
        """Call LLM7.io API"""
        try:
            if self.llm7_client == "direct_http":
                # Use direct HTTP calls
                return await self._call_llm7_direct(prompt, temperature, max_tokens)
            elif hasattr(self.llm7_client, 'invoke'):
                # Use langchain wrapper
                response = await asyncio.to_thread(
                    self.llm7_client.invoke,
                    prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                if hasattr(response, 'content'):
                    return response.content.strip()
                elif isinstance(response, str):
                    return response.strip()
                else:
                    logger.error(f"Unexpected response type from LLM7: {type(response)}")
                    return None
            else:
                logger.error("LLM7 client not properly initialized")
                return None
                
        except Exception as e:
            logger.error(f"LLM7.io API call failed: {str(e)}")
            raise
    
    async def _call_llm7_direct(self, prompt: str, temperature: float, max_tokens: int) -> Optional[str]:
        """Call LLM7.io API directly via HTTP"""
        headers = {
            "Authorization": f"Bearer {settings.llm7_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.primary_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.llm7_base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'choices' in data and len(data['choices']) > 0:
                        return data['choices'][0]['message']['content'].strip()
                    else:
                        logger.error(f"Unexpected LLM7 response format: {data}")
                        return None
                else:
                    error_text = await response.text()
                    logger.error(f"LLM7 HTTP error {response.status}: {error_text}")
                    raise Exception(f"HTTP {response.status}: {error_text}")

    async def _call_openai(self, prompt: str, temperature: float, max_tokens: int) -> Optional[str]:
        """Call OpenAI API"""
        try:
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=self.fallback_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            raise

    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        return {
            "llm7": {
                "available": self.llm7_client is not None,
                "model": self.primary_model,
                "endpoint": "https://llm7.io"
            },
            "openai": {
                "available": self.openai_client is not None,
                "model": self.fallback_model,
                "endpoint": "https://api.openai.com"
            },
            "primary_provider": "llm7.io",
            "fallback_provider": "openai"
        }

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to all available providers"""
        results = {}
        test_prompt = "Hello! Please respond with 'Connection successful' to confirm you're working."

        # Test LLM7.io
        if self.llm7_client:
            try:
                start_time = datetime.now()
                response = await self._call_llm7(test_prompt, 0.1, 50)
                end_time = datetime.now()

                results["llm7"] = {
                    "status": "success" if response else "failed",
                    "response_time_ms": int((end_time - start_time).total_seconds() * 1000),
                    "response": response[:100] if response else None
                }
            except Exception as e:
                results["llm7"] = {
                    "status": "error",
                    "error": str(e)
                }
        else:
            results["llm7"] = {"status": "unavailable", "reason": "Client not initialized"}

        # Test OpenAI
        if self.openai_client:
            try:
                start_time = datetime.now()
                response = await self._call_openai(test_prompt, 0.1, 50)
                end_time = datetime.now()

                results["openai"] = {
                    "status": "success" if response else "failed",
                    "response_time_ms": int((end_time - start_time).total_seconds() * 1000),
                    "response": response[:100] if response else None
                }
            except Exception as e:
                results["openai"] = {
                    "status": "error",
                    "error": str(e)
                }
        else:
            results["openai"] = {"status": "unavailable", "reason": "Client not initialized"}

        return results


# Global instance
llm_adapter = LLMAdapter()
