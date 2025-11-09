"""vLLM backend client for forwarding requests."""
import aiohttp
from typing import Dict, Any
from shared.config import settings


class VLLMClient:
    """Client for communicating with vLLM OpenAI-compatible server."""

    def __init__(self):
        self.base_url = settings.vllm_base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=300.0)
        self.session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self.session

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def completions(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Forward completion request to vLLM.

        Args:
            request_data: Completion request payload

        Returns:
            Completion response from vLLM
        """
        url = f"{self.base_url}/v1/completions"
        session = await self._get_session()

        try:
            async with session.post(url, json=request_data) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            print(f"vLLM request failed: {e.status} - {e.message}")
            raise
        except aiohttp.ClientError as e:
            print(f"vLLM connection error: {str(e)}")
            raise
        except Exception as e:
            print(f"Unexpected error calling vLLM: {str(e)}")
            raise

    async def chat_completions(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Forward chat completion request to vLLM.

        Args:
            request_data: Chat completion request payload

        Returns:
            Chat completion response from vLLM
        """
        url = f"{self.base_url}/v1/chat/completions"
        session = await self._get_session()

        try:
            async with session.post(url, json=request_data) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            print(f"vLLM request failed: {e.status} - {e.message}")
            raise
        except aiohttp.ClientError as e:
            print(f"vLLM connection error: {str(e)}")
            raise
        except Exception as e:
            print(f"Unexpected error calling vLLM: {str(e)}")
            raise

    async def models(self) -> Dict[str, Any]:
        """
        Get available models from vLLM.

        Returns:
            Models list response
        """
        url = f"{self.base_url}/v1/models"
        session = await self._get_session()

        try:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            print(f"Failed to get models from vLLM: {str(e)}")
            # Return default model info if vLLM models endpoint fails
            return {
                "object": "list",
                "data": [
                    {
                        "id": settings.vllm_default_model,
                        "object": "model",
                        "created": 0,
                        "owned_by": "internal",
                    }
                ],
            }

    async def health_check(self) -> bool:
        """
        Check if vLLM backend is healthy.

        Returns:
            True if vLLM is responding, False otherwise
        """
        try:
            url = f"{self.base_url}/v1/models"
            session = await self._get_session()
            async with session.get(url) as response:
                return response.status == 200
        except Exception as e:
            print(f"vLLM health check failed: {str(e)}")
            return False


# Global vLLM client instance
vllm_client = VLLMClient()
