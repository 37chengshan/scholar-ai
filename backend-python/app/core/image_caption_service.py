"""Image caption generation service using local Qwen2-VL-2B model.

Provides:
- Local VLM for academic figure caption generation
- Memory-efficient loading with FP16 precision
- Lazy initialization with retry logic
- Graceful fallback on model failures
"""

from typing import Optional
import torch
from PIL import Image
from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

from app.utils.logger import logger


class ImageCaptionService:
    """Image caption service using local Qwen2-VL-2B-Instruct model."""

    MODEL_NAME = "Qwen/Qwen2-VL-2B-Instruct"
    DEFAULT_MAX_LENGTH = 100

    def __init__(self, model_name: Optional[str] = None):
        """Initialize the caption service.

        Args:
            model_name: Optional custom model name (defaults to Qwen2-VL-2B-Instruct)
        """
        self.model_name = model_name or self.MODEL_NAME
        self.model: Optional[Qwen2VLForConditionalGeneration] = None
        self.processor: Optional[AutoProcessor] = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._initialized = False

    def _load_model(self) -> bool:
        """Lazy load the model and processor.

        Returns:
            True if loaded successfully, False otherwise
        """
        if self._initialized:
            return True

        try:
            logger.info(
                "Loading Qwen2-VL model",
                model=self.model_name,
                device=self.device
            )

            self.processor = AutoProcessor.from_pretrained(self.model_name)
            self.model = Qwen2VLForConditionalGeneration.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16,
                device_map="auto"
            )
            self.model.eval()
            self._initialized = True

            logger.info(
                "Qwen2-VL model loaded successfully",
                model=self.model_name,
                device=self.device
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to load Qwen2-VL model",
                error=str(e),
                model=self.model_name
            )
            return False

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
        # Lazy load model on first use
        if not self._load_model():
            logger.warning(
                "Model not loaded, using fallback caption",
                fallback="Academic figure from research paper"
            )
            return "Academic figure from research paper"

        try:
            prompt = self._build_prompt()

            # Prepare conversation format for Qwen2-VL
            conversation = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": prompt}
                    ]
                }
            ]

            # Apply chat template
            text_prompt = self.processor.apply_chat_template(
                conversation,
                add_generation_prompt=True
            )

            # Process inputs
            inputs = self.processor(
                text=[text_prompt],
                images=[image],
                return_tensors="pt"
            )
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

            # Generate caption
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=128,
                    temperature=0.3,
                    do_sample=True,
                    top_p=0.9
                )

            # Decode output
            generated_ids = outputs[0][inputs['input_ids'].shape[1]:]
            caption = self.processor.decode(generated_ids, skip_special_tokens=True)

            # Clean up caption
            caption = caption.strip()

            # Clear CUDA cache if available
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            # Validate caption length
            if len(caption) < 10:
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

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._initialized

    def get_device(self) -> str:
        """Get the device being used (cuda/cpu)."""
        return self.device


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
        ImageCaptionService instance (model not loaded until first use)
    """
    return get_image_caption_service()
