"""BaseEmbeddingService abstract interface for embedding services.

Provides:
- Abstract interface for all embedding implementations
- Support for text, image, and table inputs (multimodal)
- Model lifecycle management
- Unified embedding dimension (2048-dim for Qwen3-VL, 1024-dim for BGE-M3)

Design decisions (per D-01, D-02):
- Unified interface supports text-only and multimodal embeddings
- Configuration-driven model selection via factory
- Abstract methods for encode_text(), encode_image(), encode_table()
- supports_multimodal() to differentiate capabilities
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Union
from PIL import Image


class BaseEmbeddingService(ABC):
    """Abstract interface for embedding services.
    
    All embedding implementations must inherit from this base class
    and implement the abstract methods.
    
    Features:
    - Text, image, and table encoding support
    - Model lifecycle management (load, is_loaded)
    - Unified return format (list of floats)
    - Model information retrieval
    - Multimodal capability indication
    
    Example implementation:
        class BGEEmbeddingService(BaseEmbeddingService):
            def supports_multimodal(self) -> bool:
                return False  # Text-only embedding
            
            def encode_text(self, text):
                # Implementation using BGE-M3 (1024-dim)
                ...
            
            def encode_image(self, image):
                raise NotImplementedError("BGE-M3 is text-only")
            
            def encode_table(self, caption, headers, rows):
                # Serialize table to text and encode
                ...
    
        class Qwen3VLEmbeddingService(BaseEmbeddingService):
            def supports_multimodal(self) -> bool:
                return True  # Multimodal embedding
            
            def encode_text(self, text):
                # Implementation using Qwen3-VL (2048-dim)
                ...
            
            def encode_image(self, image):
                # Direct pixel processing (2048-dim)
                ...
            
            def encode_table(self, caption, headers, rows):
                # Serialize table to text and encode (2048-dim)
                ...
    """

    @abstractmethod
    def load_model(self) -> None:
        """Load model into memory.
        
        Called at application startup to initialize the embedding model.
        Should set internal state to indicate model is loaded.
        
        Raises:
            RuntimeError: If model loading fails
        """
        pass

    @abstractmethod
    def encode_text(
        self, 
        text: Union[str, List[str]]
    ) -> Union[List[float], List[List[float]]]:
        """Encode text(s) to embedding vectors.
        
        Args:
            text: Single text string or list of strings
            
        Returns:
            Single embedding vector (2048-dim or 1024-dim depending on model)
            or list of vectors for batch input
            
        Raises:
            RuntimeError: If model not loaded (call load_model() first)
        """
        pass

    @abstractmethod
    def encode_image(
        self,
        image: Union[str, Image.Image, List[Image.Image]]
    ) -> Union[List[float], List[List[float]]]:
        """Encode image(s) to embedding vectors.
        
        Args:
            image: Image path (str), PIL.Image object, or list of images
            
        Returns:
            Single embedding vector (2048-dim for multimodal models)
            or list of vectors for batch input
            
        Raises:
            RuntimeError: If model not loaded
            NotImplementedError: For text-only models (supports_multimodal() == False)
        """
        pass

    @abstractmethod
    def encode_table(
        self,
        caption: str = "",
        headers: List[str] = [],
        rows: List[Dict] = []
    ) -> List[float]:
        """Encode table to embedding vector.
        
        Serializes table structure to text format per D-02:
        "Table: {caption}\nColumns: {headers}\nSample data: {rows}"
        
        Args:
            caption: Table caption/title
            headers: Column headers (list of strings)
            rows: Row data (list of dicts, max 3 rows used)
            
        Returns:
            Embedding vector (2048-dim or 1024-dim depending on model)
            
        Raises:
            RuntimeError: If model not loaded
        """
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if model is loaded and ready for use.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, str]:
        """Return model name and version information.
        
        Returns:
            Dict with keys:
            - "name": Model name/identifier
            - "version": Model version or "unknown"
            - "type": "text-only" or "multimodal"
            - "dimension": Embedding dimension (e.g., "2048" or "1024")
        """
        pass

    @abstractmethod
    def supports_multimodal(self) -> bool:
        """Check if embedding service supports multimodal inputs.
        
        Returns:
            True if service can process images + text + tables
            False if service only processes text
        """
        pass