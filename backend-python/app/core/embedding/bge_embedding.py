"""BGEEmbeddingService adapter for BGE-M3 text-only embedding.

Provides:
- Text-only embedding (1024-dim vectors)
- Table encoding via serialization
- Implements BaseEmbeddingService interface
- Wraps existing BGEM3Service
- Backward compatible with old API

Design decisions (per D-01, D-02):
- Text-only model (supports_multimodal() == False)
- 1024-dim output for backward compatibility
- Wraps existing BGEM3Service singleton
- encode_image() raises NotImplementedError
"""

from typing import List, Dict, Union
from PIL import Image

from app.core.embedding.base import BaseEmbeddingService
from app.core.bge_m3_service import get_bge_m3_service
from app.utils.logger import logger


class BGEEmbeddingService(BaseEmbeddingService):
    """BGE-M3 embedding adapter (text-only).
    
    Features:
    - 1024-dimensional embeddings
    - Text and table encoding
    - No image support (text-only model)
    - Backward compatible with BGEM3Service
    
    Implementation:
    - Wraps existing BGEM3Service singleton
    - Forward all method calls to underlying service
    - Preserve 1024-dim output for backward compatibility
    
    Example:
        service = BGEEmbeddingService()
        service.load_model()
        
        # Encode text
        embedding = service.encode_text("search query")
        # Returns: [0.1, 0.2, ...] (1024-dim)
        
        # Encode table
        table_embedding = service.encode_table(
            caption="Results",
            headers=["Metric", "Value"],
            rows=[{"Metric": "Acc", "Value": "95%"}]
        )
        # Returns: [0.3, 0.4, ...] (1024-dim)
        
        # Image encoding not supported
        try:
            service.encode_image("test.jpg")
        except NotImplementedError:
            pass  # BGE-M3 is text-only
    """

    def __init__(self):
        """Initialize BGE embedding adapter.
        
        Uses existing BGEM3Service singleton via get_bge_m3_service().
        """
        self._service = get_bge_m3_service()
        logger.debug("BGEEmbeddingService initialized")

    def load_model(self) -> None:
        """Load BGE-M3 model into memory.
        
        Calls underlying BGEM3Service.load_model().
        """
        self._service.load_model()
        logger.info(
            "BGE-M3 model loaded via adapter",
            dimension=1024,
            type="text-only"
        )

    def encode_text(
        self, 
        text: Union[str, List[str]]
    ) -> Union[List[float], List[List[float]]]:
        """Encode text(s) to 1024-dim vectors.
        
        Args:
            text: Single text string or list of strings
            
        Returns:
            Single 1024-dim vector for single input,
            or list of vectors for batch input
            
        Raises:
            RuntimeError: If model not loaded
        """
        return self._service.encode_text(text)

    def encode_image(
        self,
        image: Union[str, Image.Image, List[Image.Image]]
    ) -> Union[List[float], List[List[float]]]:
        """Encode image(s) - NOT SUPPORTED for BGE-M3.
        
        BGE-M3 is a text-only model and cannot process images.
        
        Args:
            image: Image path, PIL.Image, or list of images
            
        Returns:
            Never returns - always raises NotImplementedError
            
        Raises:
            NotImplementedError: BGE-M3 is text-only
        """
        raise NotImplementedError(
            "BGE-M3 embedding model is text-only and does not support image encoding. "
            "Use Qwen3VLEmbeddingService for multimodal embedding."
        )

    def encode_table(
        self,
        caption: str = "",
        headers: List[str] = [],
        rows: List[Dict] = []
    ) -> List[float]:
        """Encode table to 1024-dim vector.
        
        Serializes table structure to text and encodes it.
        Format per D-02:
        "Table: {caption}\nColumns: {headers}\nSample data: {rows}"
        
        Args:
            caption: Table caption/title
            headers: Column headers
            rows: Row data (max 3 rows used)
            
        Returns:
            1024-dimensional embedding vector
        """
        return self._service.encode_table(
            caption=caption,
            description="",  # Not used in new format
            headers=headers,
            sample_rows=rows
        )

    def is_loaded(self) -> bool:
        """Check if BGE-M3 model is loaded.
        
        Returns:
            True if model loaded, False otherwise
        """
        return self._service.is_loaded()

    def get_model_info(self) -> Dict[str, str]:
        """Return BGE-M3 model information.
        
        Returns:
            Dict with:
            - name: "BAAI/bge-m3"
            - version: "unknown"
            - type: "text-only"
            - dimension: "1024"
        """
        return {
            "name": "BAAI/bge-m3",
            "version": "unknown",
            "type": "text-only",
            "dimension": "1024"
        }

    def supports_multimodal(self) -> bool:
        """Check if embedding supports multimodal inputs.
        
        BGE-M3 is text-only and cannot process images.
        
        Returns:
            False (text-only model)
        """
        return False


# Backward compatible function (preserves old API)
def get_bge_embedding_service() -> BGEEmbeddingService:
    """Get or create BGEEmbeddingService instance.
    
    Backward compatible function for existing code.
    
    Returns:
        BGEEmbeddingService instance
    """
    return BGEEmbeddingService()