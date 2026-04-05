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

from typing import Dict, List, Optional, Union
from pathlib import Path
import torch

from PIL import Image
from transformers import AutoModel, AutoTokenizer, BitsAndBytesConfig

from app.core.config import settings
from app.utils.logger import logger


class Qwen3VLMultimodalEmbedding:
    """Qwen3-VL multimodal embedding service.

    Features:
    - 2048-dimensional embeddings
    - Direct pixel processing for images (no text conversion)
    - Table serialization to text format
    - INT4/FP16 quantization support
    - Device auto-detection
    """

    # Model path relative to project root (not backend-python)
    # Project root is: /Users/cc/scholar-ai-deploy/schlar ai
    MODEL_PATH = str(Path(__file__).parent.parent.parent.parent.parent / "Qwen" / "Qwen3-VL-Embedding-2B")
    EMBEDDING_DIM = 2048

    def __init__(self, quantization: str = "fp16", device: str = "auto"):
        """Initialize Qwen3-VL embedding service.

        Args:
            quantization: Quantization type - "int4" or "fp16" (default)
            device: Device to use - "auto", "cuda", "mps", or "cpu"
        """
        self.quantization = quantization
        self.device = self._detect_device(device)
        self.model: Optional[AutoModel] = None
        self.processor: Optional[AutoTokenizer] = None
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
        Supports INT4 quantization per D-11.
        """
        if self._initialized:
            return

        try:
            logger.info(
                "Loading Qwen3-VL-Embedding model",
                model_path=self.MODEL_PATH,
                quantization=self.quantization,
                device=self.device,
            )

            # Check if local model exists
            local_path = Path(self.MODEL_PATH)
            if not local_path.exists():
                logger.warning(
                    "Local model path not found, falling back to HuggingFace download",
                    path=self.MODEL_PATH,
                )
                model_path = "Qwen/Qwen3-VL-Embedding-2B"
            else:
                model_path = str(local_path)
                logger.info("Using local Qwen3-VL-Embedding model", path=model_path)

            # Quantization config per D-11
            quantization_config = None
            torch_dtype = torch.float16

            if self.quantization == "int4":
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                )
                logger.info("Using INT4 quantization (NF4)")
            elif self.quantization == "fp16":
                torch_dtype = torch.float16
                logger.info("Using FP16 precision")

            # Load model with device_map="auto" for automatic placement
            self.model = AutoModel.from_pretrained(
                model_path,
                torch_dtype=torch_dtype,
                device_map=self.device,
                trust_remote_code=True,
                quantization_config=quantization_config,
            )

            # Load processor/tokenizer
            self.processor = AutoTokenizer.from_pretrained(
                model_path,
                trust_remote_code=True,
            )

            self._initialized = True

            logger.info(
                "Qwen3-VL-Embedding model loaded successfully",
                embedding_dim=self.EMBEDDING_DIM,
                device=self.device,
                quantization=self.quantization,
            )

        except Exception as e:
            logger.error("Failed to load Qwen3-VL-Embedding model", error=str(e))
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

        # Handle single vs batch input
        is_single = not isinstance(image, list)
        if is_single:
            images = [image]
        else:
            images = image

        embeddings = []

        for img in images:
            # Process input: convert path/URL to PIL.Image
            if isinstance(img, str):
                if img.startswith("http"):
                    import requests
                    img = Image.open(requests.get(img, stream=True).raw)
                else:
                    img = Image.open(img)

            # Ensure RGB format
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Encode image using model
            # Note: Qwen3-VL-Embedding processes images directly via pixel values
            # The processor handles image preprocessing internally
            inputs = self.processor(
                images=img,
                return_tensors="pt",
            )

            # Move inputs to device
            if self.device != "cpu":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                # Get image features (2048-dim)
                outputs = self.model(**inputs)
                embedding = outputs.last_hidden_state.mean(dim=1)  # Pool over sequence

            # Normalize to unit vector (COSINE distance)
            embedding = torch.nn.functional.normalize(embedding, p=2, dim=1)

            embeddings.append(embedding.cpu().tolist()[0])

        # Return single vector for single input, list for batch
        if is_single:
            return embeddings[0]
        return embeddings

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

        # Filter out empty strings
        non_empty_texts = [t for t in texts if t and t.strip()]

        if not non_empty_texts:
            # All texts were empty
            if is_single:
                return [0.0] * self.EMBEDDING_DIM
            return [[0.0] * self.EMBEDDING_DIM for _ in texts]

        # Tokenize
        inputs = self.processor(
            text=non_empty_texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=8192,
        )

        # Move to device
        if self.device != "cpu":
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            # Pool over sequence (mean pooling)
            embeddings = outputs.last_hidden_state.mean(dim=1)

        # Normalize to unit vectors
        embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

        embeddings_list = embeddings.cpu().tolist()

        # Merge back with empty positions
        result = []
        non_empty_idx = 0
        for t in texts:
            if not t or not t.strip():
                result.append([0.0] * self.EMBEDDING_DIM)
            else:
                result.append(embeddings_list[non_empty_idx])
                non_empty_idx += 1

        if is_single:
            return result[0]
        return result

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