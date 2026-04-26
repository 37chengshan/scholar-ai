"""Pipeline context and stage tracking for parallel PDF processing.

Per D-01: Complete refactor from serial to parallel architecture.
Per D-04: Four-stage parallel extraction (IMRaD, metadata, images, tables).
Per D-12-D-15: Strict error handling with critical/auxiliary distinction.
Per Review Fix #8: trace_id for full-pipeline tracing.
"""

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PipelineStage(Enum):
    """Pipeline processing stages.

    Tracks the current stage of PDF processing through the parallel pipeline.
    """
    DOWNLOAD = "download"
    PARSING = "parsing"
    EXTRACTION = "extraction"
    STORAGE = "storage"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PipelineContext:
    """Pipeline context that carries state through all stages.

    Carries task metadata and stage results through the parallel pipeline.
    Per D-12: Critical stage failures block the pipeline.
    Per D-15: Auxiliary failures logged in errors list, not blocking.
    Per Review Fix #8: trace_id for full-pipeline tracing.

    Attributes:
        task_id: UUID of the processing task
        paper_id: UUID of the paper being processed
        user_id: UUID of the paper owner
        storage_key: Object storage key for the PDF
        trace_id: UUID for full-pipeline log tracing (auto-generated)

        local_path: Local filesystem path after download
        parse_result: Raw parser output (markdown, items, page_count)
        parse_artifact: Canonical ParseArtifact payload
        imrad: IMRaD structure extraction result
        metadata: Paper metadata (title, authors, abstract, etc.)
        image_results: Image extraction and embedding results
        table_results: Table extraction and embedding results
        chunk_results: Text chunking and embedding results
        chunk_artifacts: Canonical chunk artifacts grouped by stage
        notes: Generated reading notes

        current_stage: Current processing stage
        errors: List of auxiliary failure messages
    """
    task_id: str
    paper_id: str
    user_id: str
    storage_key: str

    # Per Review Fix #8: trace_id for full-pipeline tracing
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Stage results (populated during processing)
    local_path: Optional[str] = None
    parse_result: Optional[Dict[str, Any]] = None
    parse_artifact: Optional[Dict[str, Any]] = None
    imrad: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    image_results: Optional[List[Dict[str, Any]]] = None
    table_results: Optional[List[Dict[str, Any]]] = None
    chunk_results: Optional[List[Dict[str, Any]]] = None
    chunk_artifacts: Optional[Dict[str, List[Dict[str, Any]]]] = None
    notes: Optional[str] = None

    # Status tracking
    current_stage: PipelineStage = PipelineStage.DOWNLOAD
    errors: List[str] = field(default_factory=list)

    def add_error(self, error: str) -> None:
        """Add error to context.

        Per D-15: Auxiliary failures logged, not blocking.
        Critical failures raise PipelineError instead.

        Args:
            error: Error message to log
        """
        self.errors.append(error)