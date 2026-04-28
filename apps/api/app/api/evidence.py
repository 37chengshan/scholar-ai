from fastapi import APIRouter, HTTPException, status

from app.services.evidence_contract_service import get_evidence_source_payload

router = APIRouter()


@router.get("/source/{source_chunk_id}")
async def get_evidence_source(source_chunk_id: str):
    item = get_evidence_source_payload(source_chunk_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="source chunk not found",
        )

    return item
