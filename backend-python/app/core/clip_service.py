"""CLIP (SigLIP) embedding service for multimodal image/table embeddings.

Provides:
- SigLIP model loading and caching at startup
- Image embedding generation (768-dim)
- Text embedding generation (768-dim)
- Device auto-detection (CUDA/CPU)
- Normalized embeddings for cosine similarity
"""

from pathlib import Path
from typing import List, Union, Optional
import torch
from PIL import Image
from transformers import AutoModel, AutoProcessor

from app.utils.logger import logger


class CLIPService:
    """SigLIP embedding service with model caching."""

    MODEL_NAME = "google/siglip-base-patch16-256"
    EMBEDDING_DIM = 768

    def __init__(self):
        self.model = None
        self.processor = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._initialized = False

    def load_model(self) -> None:
        """Load model and processor into memory. Called at app startup."""
        if self._initialized:
            return

        try:
            logger.info(
                "Loading SigLIP model",
                model=self.MODEL_NAME,
                device=self.device
            )

            self.processor = AutoProcessor.from_pretrained(self.MODEL_NAME)
            self.model = AutoModel.from_pretrained(self.MODEL_NAME)
            self.model.to(self.device)
            self.model.eval()
            self._initialized = True

            logger.info(
                "SigLIP model loaded successfully",
                embedding_dim=self.EMBEDDING_DIM,
                device=self.device
            )
        except Exception as e:
            logger.error("Failed to load SigLIP model", error=str(e))
            raise

    @torch.no_grad()
    def encode_image(
        self,
        image: Union[Image.Image, Path, str]
    ) -> List[float]:
        """Generate normalized embedding for an image.

        Args:
            image: PIL Image, file path, or Path object

        Returns:
            Normalized 768-dimensional float vector
        """
        if not self._initialized:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Load image if path provided
        if isinstance(image, (str, Path)):
            image = Image.open(image).convert("RGB")

        # Process image
        inputs = self.processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Generate embeddings
        outputs = self.model.get_image_features(**inputs)

        # Normalize to unit vector for cosine similarity
        embedding = outputs[0] / outputs[0].norm()

        return embedding.cpu().tolist()

    @torch.no_grad()
    def encode_text(self, text: str) -> List[float]:
        """Generate normalized embedding for text.

        Args:
            text: Input text string

        Returns:
            Normalized 768-dimensional float vector
        """
        if not self._initialized:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Process text
        inputs = self.processor(
            text=[text],
            padding=True,
            return_tensors="pt"
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Generate embeddings
        outputs = self.model.get_text_features(**inputs)

        # Normalize to unit vector for cosine similarity
        embedding = outputs[0] / outputs[0].norm()

        return embedding.cpu().tolist()

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._initialized

    def get_device(self) -> str:
        """Get the device being used (cuda/cpu)."""
        return self.device

    def get_embedding_dim(self) -> int:
        """Get the embedding dimension."""
        return self.EMBEDDING_DIM


# Singleton instance
_clip_service: Optional[CLIPService] = None


def get_clip_service() -> CLIPService:
    """Get or create CLIPService singleton."""
    global _clip_service
    if _clip_service is None:
        _clip_service = CLIPService()
    return _clip_service


async def create_clip_service() -> CLIPService:
    """Create and initialize CLIPService.

    Returns:
        Initialized CLIPService instance
    """
    service = get_clip_service()
    service.load_model()
    return service
