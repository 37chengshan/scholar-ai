import pytest

from app.core.storage import ObjectStorage
from app.services.storage_service import StorageService


@pytest.mark.asyncio
async def test_object_storage_blocks_path_traversal(monkeypatch, tmp_path):
    monkeypatch.setenv("OSS_ENDPOINT", "local")
    monkeypatch.setenv("LOCAL_STORAGE_PATH", str(tmp_path))

    storage = ObjectStorage()

    with pytest.raises(ValueError, match="Path traversal attempt"):
        storage._get_local_path("../../etc/passwd")


@pytest.mark.asyncio
async def test_storage_service_blocks_path_traversal(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCAL_STORAGE_PATH", str(tmp_path))

    storage = StorageService()

    with pytest.raises(ValueError, match="Path traversal attempt"):
        storage._get_local_path("../secrets.txt")
