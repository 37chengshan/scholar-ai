"""Image caption generation service using Zhipu AI API.

Provides:
- Vision-language model for academic figure caption generation
- Uses Zhipu AI API (glm-4v model) for image understanding
- Retry logic with exponential backoff
- Graceful fallback on API failures
"""

import base64
import io
from typing import Optional
import httpx
from PIL import Image
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.utils.logger import logger


class ImageCaptionService:
    """Image caption service using Zhipu AI API (glm-4v vision model)."""

    API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    MODEL_NAME = "glm-4v"
    DEFAULT_MAX_TOKENS = 150
    DEFAULT_TEMPERATURE = 0.3

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the caption service.

        Args:
            api_key: Optional Zhipu API key (defaults to settings.ZHIPU_API_KEY)
        """
        self.api_key = api_key or getattr(settings, 'ZHIPU_API_KEY', '')
        self.client = httpx.AsyncClient(timeout=30.0)

    def _build_prompt(self) -> str:
        """Build the academic-focused caption prompt.

        Returns:
            Prompt string for academic figure caption generation
        """
        return """请用一句话描述这张学术图片的核心内容。这是来自学术论文的图表。

要求：
- 一句话概括图片展示的内容
- 提及图表类型（如：柱状图、折线图、流程图、示意图等）
- 指出关键数据趋势或核心发现（如果有）
- 不超过80字
"""

    def _encode_image(self, image: Image.Image) -> str:
        """Encode PIL Image to base64 string.

        Args:
            image: PIL Image object

        Returns:
            Base64-encoded image string
        """
        # Convert to RGB if necessary (handle RGBA, etc.)
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Save to bytes buffer
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=85)
        image_bytes = buffer.getvalue()

        # Encode to base64
        return base64.b64encode(image_bytes).decode('utf-8')

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def _call_api(self, image_base64: str) -> str:
        """Call Zhipu AI API with retry logic.

        Args:
            image_base64: Base64-encoded image

        Returns:
            Generated caption text

        Raises:
            Exception: If API call fails after retries
        """
        if not self.api_key:
            raise ValueError("ZHIPU_API_KEY not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        prompt = self._build_prompt()

        payload = {
            "model": self.MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": self.DEFAULT_MAX_TOKENS,
            "temperature": self.DEFAULT_TEMPERATURE
        }

        response = await self.client.post(
            self.API_URL,
            headers=headers,
            json=payload
        )
        response.raise_for_status()

        data = response.json()
        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"]["content"].strip()
        else:
            raise ValueError(f"Unexpected API response: {data}")

    async def generate_caption(
        self,
        image: Image.Image,
        max_length: int = 100
    ) -> str:
        """Generate a caption for an academic figure.

        Args:
            image: PIL Image object
            max_length: Maximum caption length (default 100 chars)

        Returns:
            Caption string, or fallback caption if generation fails
        """
        try:
            # Encode image to base64
            image_base64 = self._encode_image(image)

            logger.debug(
                "Generating image caption via Zhipu AI",
                image_size=image.size,
                model=self.MODEL_NAME
            )

            caption = await self._call_api(image_base64)

            # Validate caption length
            if not caption or len(caption) < 10:
                logger.warning(
                    "Caption too short, using fallback",
                    caption=caption,
                    fallback="Figure showing research data"
                )
                return "Figure showing research data"

            if len(caption) > max_length:
                caption = caption[:max_length] + "..."

            logger.info(
                "Caption generated successfully",
                caption_length=len(caption)
            )
            return caption

        except Exception as e:
            logger.error(
                "Caption generation failed",
                error=str(e),
                fallback="Figure showing research data"
            )
            return "Figure showing research data"

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance
_image_caption_service: Optional[ImageCaptionService] = None


def get_image_caption_service() -> ImageCaptionService:
    """Get or create ImageCaptionService singleton."""
    global _image_caption_service
    if _image_caption_service is None:
        _image_caption_service = ImageCaptionService()
    return _image_caption_service


async def create_image_caption_service() -> ImageCaptionService:
    """Create and initialize ImageCaptionService.

    Returns:
        ImageCaptionService instance
    """
    return get_image_caption_service()
