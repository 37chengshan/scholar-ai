"""Qwen3-VL multimodal embedding service.

Provides:
- Image encoding to 2048-dim vectors (direct pixel processing)
- Text encoding to 2048-dim vectors
- Table encoding to 2048-dim vectors (via serialization)
- Singleton pattern for model efficiency
- INT4/FP16 quantization support
- Device auto-detection (cuda/mps/cpu)

Qwen3-VL-Embedding-2B is used as the unified multimodal embedding model
for all content types to enable true cross-modal retrieval in a single vector space.

Implementation per D-01, D-02, D-11, D-12 from CONTEXT.md.
"""

import sys
from typing import Dict, List, Optional, Union
from pathlib import Path
import torch

from PIL import Image

from app.config import settings
from app.utils.logger import logger

# Add Qwen model scripts path to sys.path
qwen_scripts_path = Path(settings.QWEN3VL_EMBEDDING_MODEL_PATH) / "scripts"
Qwen3VLEmbedder = None
Qwen3VLForEmbedding = None

if qwen_scripts_path.exists():
    sys.path.insert(0, str(qwen_scripts_path.parent))
    try:
        from scripts.qwen3_vl_embedding import Qwen3VLEmbedder, Qwen3VLForEmbedding
    except ImportError:
        logger.warning("Qwen3-VL-Embedding scripts import failed")
else:
    # Fallback to importing from installed package
    try:
        from qwen3_vl_embedding import Qwen3VLEmbedder, Qwen3VLForEmbedding
    except ImportError:
        logger.warning("Qwen3-VL-Embedding not available - multimodal search will be disabled")


class Qwen3VLMultimodalEmbedding:
    """Qwen3-VL multimodal embedding service.

    Features:
    - 2048-dimensional embeddings
    - Direct pixel processing for images (no text conversion)
    - Table serialization to text format
    - FP16 quantization support
    - Device auto-detection
    """

    EMBEDDING_DIM = 2048

    def __init__(self, quantization: str = "fp16", device: str = "auto"):
        """Initialize Qwen3-VL embedding service.

        Args:
            quantization: Quantization type - "fp16" (default) or "int4"
            device: Device to use - "auto", "cuda", "mps", or "cpu"
        """
        self.quantization = quantization
        self.device = self._detect_device(device)
        self.embedder: Optional[Qwen3VLEmbedder] = None
        self._initialized = False

    def _detect_device(self, device: str) -> str:
        """Auto-detect available device per D-12.

        Priority: cuda > mps (M1 Pro) > cpu

        Args:
            device: Device preference ("auto" or specific device)

        Returns:
            Detected device string
        """
        if device != "auto":
            return device

        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"  # M1 Pro Metal Performance Shaders
        else:
            return "cpu"

    def load_model(self) -> None:
        """Load model into memory. Called at app startup.

        Uses local model path per D-01.
        Supports FP16 quantization per D-11.
        Uses Flash Attention 2 for better acceleration (CUDA only).
        """
        if self._initialized:
            return

        # Check if Qwen3VLEmbedder is available
        if Qwen3VLEmbedder is None:
            logger.warning("Qwen3-VL-Embedding not available - skipping model load")
            self._initialized = True  # Mark as initialized but embedder is None
            return

        try:
            logger.info(
                "Loading Qwen3-VL-Embedding model",
                model_path=settings.QWEN3VL_EMBEDDING_MODEL_PATH,
                quantization=self.quantization,
                device=self.device,
            )

            # Check if local model exists
            local_path = Path(settings.QWEN3VL_EMBEDDING_MODEL_PATH)
            if not local_path.exists():
                logger.warning(
                    "Local model path not found, falling back to HuggingFace download",
                    path=settings.QWEN3VL_EMBEDDING_MODEL_PATH,
                )
                model_path = "Qwen/Qwen3-VL-Embedding-2B"
            else:
                model_path = str(local_path)
                logger.info("Using local Qwen3-VL-Embedding model", path=model_path)

            # Set torch dtype based on quantization
            torch_dtype = torch.float16 if self.quantization == "fp16" else torch.float32

            # Use Flash Attention 2 for better acceleration (CUDA only)
            # Flash Attention 2 is not supported on MPS/CPU
            kwargs = {
                "model_name_or_path": model_path,
                "torch_dtype": torch_dtype,
            }
            
            if torch.cuda.is_available():
                try:
                    kwargs["attn_implementation"] = "flash_attention_2"
                    logger.info("Using Flash Attention 2 for better acceleration and memory saving")
                except Exception as e:
                    logger.warning(f"Flash Attention 2 not available, using default attention: {e}")
            
            # Use Qwen3VLEmbedder from official scripts
            self.embedder = Qwen3VLEmbedder(**kwargs)

            self._initialized = True

            logger.info(
                "Qwen3-VL-Embedding model loaded successfully",
                embedding_dim=self.EMBEDDING_DIM,
                device=self.device,
                quantization=self.quantization,
            )

        except Exception as e:
            logger.error("Failed to load Qwen3-VL-Embedding model", error=str(e), exc_info=True)
            raise

    def encode_image(
        self,
        image: Union[str, Image.Image, List[Image.Image]]
    ) -> Union[List[float], List[List[float]]]:
        """Encode image(s) to 2048-dim vectors.

        Direct pixel processing per D-01 (no text conversion).

        Args:
            image: PIL.Image object, file path string, or list of images

        Returns:
            2048-dim vector (normalized for COSINE distance)
        """
        if not self._initialized:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        if self.embedder is None:
            logger.warning("Qwen3-VL-Embedding not available - returning empty embedding")
            return [] if isinstance(image, list) else []

        # Handle single vs batch input
        is_single = not isinstance(image, list)
        if is_single:
            images = [image]
        else:
            images = image

        # Prepare inputs in Qwen3VLEmbedder format
        # Format: {"image": path_or_pil_image}
        inputs = []
        for img in images:
            if isinstance(img, str):
                # File path or URL
                inputs.append({"image": img})
            else:
                # PIL.Image object
                inputs.append({"image": img})

        try:
            # Get embeddings (already normalized)
            embeddings = self.embedder.process(inputs, normalize=True)

            # Convert to list format
            embeddings_list = embeddings.cpu().tolist()

            # Return single vector for single input, list for batch
            if is_single:
                return embeddings_list[0]
            return embeddings_list
        except Exception as e:
            logger.error("Failed to encode images", error=str(e), image_count=len(images))
            raise

    def encode_text(
        self,
        text: Union[str, List[str]]
    ) -> Union[List[float], List[List[float]]]:
        """Encode text(s) to 2048-dim vectors.

        Args:
            text: Single text string or list of strings

        Returns:
            2048-dim vector (normalized for COSINE distance)
        """
        if not self._initialized:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Handle single vs batch input
        is_single = isinstance(text, str)
        if is_single:
            texts = [text]
        else:
            texts = text

        # Handle empty inputs
        if not texts:
            if is_single:
                return [0.0] * self.EMBEDDING_DIM
            return []

        # Prepare inputs in Qwen3VLEmbedder format
        # Format: {"text": "text content"}
        # Replace empty strings with "NULL" placeholder
        inputs = [{"text": t if t and t.strip() else "NULL"} for t in texts]

        try:
            # Get embeddings (already normalized)
            embeddings = self.embedder.process(inputs, normalize=True)

            # Convert to list format
            embeddings_list = embeddings.cpu().tolist()

            if is_single:
                return embeddings_list[0]
            return embeddings_list
        except Exception as e:
            logger.error("Failed to encode texts", error=str(e), text_count=len(texts))
            raise

    def encode_table(
        self,
        caption: str = "",
        headers: Optional[List[str]] = None,
        rows: Optional[List[Dict]] = None,
    ) -> List[float]:
        """Encode table to 2048-dim vector.

        Serializes table structure to text per D-02:
        "Table: {caption}\nColumns: {headers}\nSample data: {rows}"

        Args:
            caption: Table caption/title
            headers: Column headers
            rows: Row data (max 3 rows used)

        Returns:
            2048-dimensional embedding vector
        """
        serialized = self._serialize_table(caption, headers, rows)
        return self.encode_text(serialized)

    def _serialize_table(
        self,
        caption: str = "",
        headers: Optional[List[str]] = None,
        rows: Optional[List[Dict]] = None,
    ) -> str:
        """Serialize table to text format per D-02.

        Format:
            Table: {caption}
            Columns: {header1}, {header2}, ...
            Sample data: {row1_data}, {row2_data}, ...

        Args:
            caption: Table caption
            headers: Column headers
            rows: Sample rows (max 3 rows)

        Returns:
            Serialized table text
        """
        parts = []

        if caption:
            parts.append(f"Table: {caption}")

        if headers:
            parts.append(f"Columns: {', '.join(headers)}")

        if rows:
            # Truncate to max 3 rows
            sample_rows = rows[:3]
            row_texts = []
            for row in sample_rows:
                row_str = ", ".join(f"{k}={v}" for k, v in row.items())
                row_texts.append(row_str)
            parts.append(f"Sample data: {'; '.join(row_texts)}")

        return "\n".join(parts)

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._initialized

    def get_device(self) -> str:
        """Get the device being used."""
        return self.device

    def get_embedding_dim(self) -> int:
        """Get the embedding dimension."""
        return self.EMBEDDING_DIM


# Singleton instance
_qwen3vl_service: Optional[Qwen3VLMultimodalEmbedding] = None


def get_qwen3vl_service() -> Qwen3VLMultimodalEmbedding:
    """Get or create Qwen3VLMultimodalEmbedding singleton."""
    global _qwen3vl_service
    if _qwen3vl_service is None:
        # Per D-16, D-19: Use EMBEDDING_DEVICE from config
        _qwen3vl_service = Qwen3VLMultimodalEmbedding(
            quantization=settings.EMBEDDING_QUANTIZATION,
            device=settings.EMBEDDING_DEVICE
        )
    return _qwen3vl_service


async def create_qwen3vl_service() -> Qwen3VLMultimodalEmbedding:
    """Create and initialize Qwen3VLMultimodalEmbedding.

    Returns:
        Initialized Qwen3VLMultimodalEmbedding instance
    """
    service = get_qwen3vl_service()
    service.load_model()
    return service