"""Qwen3VLEmbeddingService adapter for Qwen3-VL multimodal embedding.

Provides:
- Multimodal embedding (text, image, table)
- 2048-dim vectors for all modalities
- Implements BaseEmbeddingService interface
- Wraps existing Qwen3VLMultimodalEmbedding
- Direct pixel processing for images

Design decisions (per D-01, D-02):
- Multimodal model (supports_multimodal() == True)
- 2048-dim output for all modalities
- Wraps existing Qwen3VLMultimodalEmbedding singleton
- Image encoding via direct pixel processing (no text conversion)
"""

from typing import List, Dict, Union
from PIL import Image

from app.core.embedding.base import BaseEmbeddingService
from app.core.qwen3vl_service import get_qwen3vl_service
from app.utils.logger import logger


class Qwen3VLEmbeddingService(BaseEmbeddingService):
    """Qwen3-VL embedding adapter (multimodal).
    
    Features:
    - 2048-dimensional embeddings
    - Text, image, and table encoding
    - Direct pixel processing for images
    - Unified embedding space across modalities
    
    Implementation:
    - Wraps existing Qwen3VLMultimodalEmbedding singleton
    - Forward all method calls to underlying service
    - 2048-dim output for all modalities
    
    Example:
        service = Qwen3VLEmbeddingService()
        service.load_model()
        
        # Encode text
        text_embedding = service.encode_text("search query")
        # Returns: [0.1, 0.2, ...] (2048-dim)
        
        # Encode image
        image_embedding = service.encode_image("image.png")
        # Returns: [0.3, 0.4, ...] (2048-dim, direct pixel processing)
        
        # Encode table
        table_embedding = service.encode_table(
            caption="Results",
            headers=["Metric", "Value"],
            rows=[{"Metric": "Acc", "Value": "95%"}]
        )
        # Returns: [0.5, 0.6, ...] (2048-dim)
    """

    def __init__(self, quantization: str = "int4", device: str = "auto"):
        """Initialize Qwen3-VL embedding adapter.
        
        Uses existing Qwen3VLMultimodalEmbedding singleton via get_qwen3vl_service().
        
        Args:
            quantization: Quantization type ("int4" or "fp16")
            device: Device to use ("auto", "cuda", "mps", or "cpu")
        """
        self._service = get_qwen3vl_service()
        self.quantization = quantization
        self.device = device
        logger.debug(
            "Qwen3VLEmbeddingService initialized",
            quantization=quantization,
            device=device
        )

    def load_model(self) -> None:
        """Load Qwen3-VL model into memory.
        
        Calls underlying Qwen3VLMultimodalEmbedding.load_model().
        """
        self._service.load_model()
        logger.info(
            "Qwen3-VL-Embedding model loaded via adapter",
            dimension=2048,
            type="multimodal",
            quantization=self.quantization,
            device=self.device
        )

    def encode_text(
        self, 
        text: Union[str, List[str]]
    ) -> Union[List[float], List[List[float]]]:
        """Encode text(s) to 2048-dim vectors.
        
        Args:
            text: Single text string or list of strings
            
        Returns:
            Single 2048-dim vector for single input,
            or list of vectors for batch input
            
        Raises:
            RuntimeError: If model not loaded
        """
        return self._service.encode_text(text)

    def encode_image(
        self,
        image: Union[str, Image.Image, List[Image.Image]]
    ) -> Union[List[float], List[List[float]]]:
        """Encode image(s) to 2048-dim vectors.
        
        Direct pixel processing per D-01 (no text conversion).
        
        Args:
            image: Image path (str), PIL.Image object, or list of images
            
        Returns:
            Single 2048-dim vector for single input,
            or list of vectors for batch input
            
        Raises:
            RuntimeError: If model not loaded
        """
        return self._service.encode_image(image)

    def encode_table(
        self,
        caption: str = "",
        headers: List[str] = [],
        rows: List[Dict] = []
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
        return self._service.encode_table(
            caption=caption,
            headers=headers,
            rows=rows
        )

    def is_loaded(self) -> bool:
        """Check if Qwen3-VL model is loaded.
        
        Returns:
            True if model loaded, False otherwise
        """
        return self._service.is_loaded()

    def get_model_info(self) -> Dict[str, str]:
        """Return Qwen3-VL model information.
        
        Returns:
            Dict with:
            - name: "Qwen3-VL-Embedding-2B"
            - version: "unknown"
            - type: "multimodal"
            - dimension: "2048"
        """
        return {
            "name": "Qwen3-VL-Embedding-2B",
            "version": "unknown",
            "type": "multimodal",
            "dimension": "2048"
        }

    def supports_multimodal(self) -> bool:
        """Check if embedding supports multimodal inputs.
        
        Qwen3-VL can process text, images, and tables.
        
        Returns:
            True (multimodal model)
        """
        return True


# Backward compatible function (preserves old API)
def get_qwen3vl_embedding_service(
    quantization: str = "int4",
    device: str = "auto"
) -> Qwen3VLEmbeddingService:
    """Get or create Qwen3VLEmbeddingService instance.
    
    Backward compatible function for existing code.
    
    Args:
        quantization: Quantization type ("int4" or "fp16")
        device: Device to use ("auto", "cuda", "mps", or "cpu")
    
    Returns:
        Qwen3VLEmbeddingService instance
    """
    return Qwen3VLEmbeddingService(quantization=quantization, device=device)