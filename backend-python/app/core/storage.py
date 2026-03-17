"""Object storage client for S3-compatible storage (MinIO/OSS)

Provides async interface for downloading/uploading files from object storage.
Supports local file storage mode for development.
"""

import os
import shutil
from pathlib import Path
from typing import Optional

from minio import Minio
from minio.error import S3Error

from app.utils.logger import logger


class ObjectStorage:
    """S3-compatible object storage client using MinIO, with local file fallback."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: Optional[str] = None,
        bucket: Optional[str] = None,
        secure: bool = True,
    ):
        """
        Initialize object storage client.

        Args:
            endpoint: S3 endpoint (defaults to OSS_ENDPOINT env var)
            access_key: Access key (defaults to OSS_ACCESS_KEY_ID env var)
            secret_key: Secret key (defaults to OSS_ACCESS_KEY_SECRET env var)
            region: Region (defaults to OSS_REGION env var or us-east-1)
            bucket: Bucket name (defaults to OSS_BUCKET env var)
            secure: Use HTTPS (default True)
        """
        self.endpoint = endpoint or os.getenv("OSS_ENDPOINT", "play.minio.io")
        self.access_key = access_key or os.getenv("OSS_ACCESS_KEY_ID", "")
        self.secret_key = secret_key or os.getenv("OSS_ACCESS_KEY_SECRET", "")
        self.region = region or os.getenv("OSS_REGION", "us-east-1")
        self.bucket = bucket or os.getenv("OSS_BUCKET", "scholarai-papers")
        self.secure = secure

        # Check if using local storage mode
        self.use_local_storage = self.endpoint == "local"
        self.local_storage_path = Path(
            os.getenv("LOCAL_STORAGE_PATH", "./uploads")
        ).resolve()

        if not self.use_local_storage:
            self.client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                region=self.region,
                secure=self.secure,
            )
        else:
            self.client = None
            # Ensure local storage directory exists
            self.local_storage_path.mkdir(parents=True, exist_ok=True)
            logger.info(
                "Using local file storage",
                path=str(self.local_storage_path),
            )

    def _get_local_path(self, storage_key: str) -> Path:
        """Get local file path for a storage key."""
        # Prevent path traversal
        safe_key = storage_key.replace("../", "").replace("./", "")
        return self.local_storage_path / safe_key

    async def download_file(self, storage_key: str, local_path: str) -> None:
        """
        Download file from object storage to local path.
        In local storage mode, copies from local storage path.

        Args:
            storage_key: Object key in storage
            local_path: Local file path to save to

        Raises:
            S3Error: If download fails (S3 mode)
            FileNotFoundError: If file not found (local mode)
        """
        if self.use_local_storage:
            source_path = self._get_local_path(storage_key)
            try:
                logger.info(
                    "Copying file from local storage",
                    source=str(source_path),
                    destination=local_path,
                )
                Path(local_path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, local_path)
                logger.info(
                    "File copied successfully",
                    source=str(source_path),
                    destination=local_path,
                )
            except FileNotFoundError:
                logger.error(
                    "File not found in local storage",
                    source=str(source_path),
                )
                raise
            return

        try:
            logger.info(
                "Downloading file from storage",
                bucket=self.bucket,
                key=storage_key,
                destination=local_path,
            )
            self.client.fget_object(self.bucket, storage_key, local_path)
            logger.info(
                "File downloaded successfully",
                key=storage_key,
                local_path=local_path,
            )
        except S3Error as e:
            logger.error(
                "Failed to download file",
                key=storage_key,
                error=str(e),
            )
            raise

    async def upload_file(
        self, storage_key: str, local_path: str, content_type: Optional[str] = None
    ) -> None:
        """
        Upload local file to object storage.
        In local storage mode, copies to local storage path.

        Args:
            storage_key: Object key in storage
            local_path: Local file path to upload
            content_type: Optional MIME type

        Raises:
            S3Error: If upload fails (S3 mode)
        """
        if self.use_local_storage:
            dest_path = self._get_local_path(storage_key)
            try:
                logger.info(
                    "Copying file to local storage",
                    source=local_path,
                    destination=str(dest_path),
                )
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(local_path, dest_path)
                logger.info(
                    "File copied successfully",
                    destination=str(dest_path),
                )
            except Exception as e:
                logger.error(
                    "Failed to copy file to local storage",
                    error=str(e),
                )
                raise
            return

        try:
            logger.info(
                "Uploading file to storage",
                bucket=self.bucket,
                key=storage_key,
                source=local_path,
            )
            self.client.fput_object(
                self.bucket,
                storage_key,
                local_path,
                content_type=content_type,
            )
            logger.info(
                "File uploaded successfully",
                key=storage_key,
                local_path=local_path,
            )
        except S3Error as e:
            logger.error(
                "Failed to upload file",
                key=storage_key,
                error=str(e),
            )
            raise

    async def delete_file(self, storage_key: str) -> None:
        """
        Delete file from object storage.
        In local storage mode, deletes from local storage path.

        Args:
            storage_key: Object key to delete

        Raises:
            S3Error: If deletion fails (S3 mode)
        """
        if self.use_local_storage:
            file_path = self._get_local_path(storage_key)
            try:
                logger.info(
                    "Deleting file from local storage",
                    path=str(file_path),
                )
                file_path.unlink()
                logger.info("File deleted successfully", path=str(file_path))
            except FileNotFoundError:
                logger.warning(
                    "File not found for deletion",
                    path=str(file_path),
                )
            return

        try:
            logger.info(
                "Deleting file from storage",
                bucket=self.bucket,
                key=storage_key,
            )
            self.client.remove_object(self.bucket, storage_key)
            logger.info("File deleted successfully", key=storage_key)
        except S3Error as e:
            logger.error(
                "Failed to delete file",
                key=storage_key,
                error=str(e),
            )
            raise

    async def file_exists(self, storage_key: str) -> bool:
        """
        Check if file exists in object storage.
        In local storage mode, checks local storage path.

        Args:
            storage_key: Object key to check

        Returns:
            True if file exists, False otherwise
        """
        if self.use_local_storage:
            file_path = self._get_local_path(storage_key)
            exists = file_path.exists()
            logger.debug(
                "Checking local file existence",
                path=str(file_path),
                exists=exists,
            )
            return exists

        try:
            self.client.stat_object(self.bucket, storage_key)
            return True
        except S3Error:
            return False


# Global storage instance
storage = ObjectStorage()


async def store_pdf(paper_id: str, pdf_content: bytes) -> str:
    """Store PDF content to object storage.

    Args:
        paper_id: The paper ID to use as part of the storage key
        pdf_content: The PDF file content as bytes

    Returns:
        The storage key/path for the stored file
    """
    storage_key = f"papers/{paper_id}/paper.pdf"

    if storage.use_local_storage:
        # Local storage mode: write to file directly
        dest_path = storage._get_local_path(storage_key)
        try:
            logger.info(
                "Storing PDF to local storage",
                paper_id=paper_id,
                destination=str(dest_path),
                size=len(pdf_content),
            )
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(pdf_content)
            logger.info(
                "PDF stored successfully",
                paper_id=paper_id,
                storage_key=storage_key,
            )
            return storage_key
        except Exception as e:
            logger.error(
                "Failed to store PDF to local storage",
                paper_id=paper_id,
                error=str(e),
            )
            raise
    else:
        # S3-compatible storage: use put_object
        try:
            from io import BytesIO

            logger.info(
                "Storing PDF to object storage",
                paper_id=paper_id,
                bucket=storage.bucket,
                key=storage_key,
                size=len(pdf_content),
            )
            storage.client.put_object(
                storage.bucket,
                storage_key,
                BytesIO(pdf_content),
                length=len(pdf_content),
                content_type="application/pdf",
            )
            logger.info(
                "PDF stored successfully",
                paper_id=paper_id,
                storage_key=storage_key,
            )
            return storage_key
        except S3Error as e:
            logger.error(
                "Failed to store PDF",
                paper_id=paper_id,
                error=str(e),
            )
            raise
