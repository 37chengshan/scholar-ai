"""Storage service for S3 and local file operations.

Provides unified interface for file storage:
- upload_file: Upload to S3 or local storage
- download_file: Download from S3 or copy from local
- get_file_url: Generate presigned URL or local path
- delete_file: Delete from S3 or local
- get_file_size: Get file size in bytes

Supports both S3-compatible storage (MinIO, AWS S3) and local filesystem.
Per D-07: Configuration-driven storage backend selection.
"""

import os
from pathlib import Path
from typing import Optional
from uuid import uuid4

import aiofiles

# Handle optional boto3 import
try:
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    ClientError = Exception  # Fallback type

from app.config import settings
from app.utils.logger import logger


class StorageService:
    """Service for file storage operations.

    Supports both S3-compatible storage and local filesystem.
    Configuration is driven by settings.USE_LOCAL_STORAGE.

    Usage:
        storage = StorageService()

        # Upload file
        key = await storage.upload_file(content, "papers/doc.pdf", "application/pdf")

        # Get file URL
        url = await storage.get_file_url(key)

        # Download file
        await storage.download_file(key, "/local/path.pdf")

        # Delete file
        await storage.delete_file(key)
    """

    def __init__(self):
        """Initialize storage service based on configuration."""
        self.use_local = settings.USE_LOCAL_STORAGE
        self.local_storage_path = Path(settings.LOCAL_STORAGE_PATH)
        self.s3_bucket = settings.S3_BUCKET
        self._s3_client = None

        if not self.use_local:
            self._init_s3_client()

        # Ensure local storage directory exists
        if self.use_local:
            self.local_storage_path.mkdir(parents=True, exist_ok=True)
            logger.info(
                "StorageService initialized with local storage",
                path=str(self.local_storage_path),
            )
        else:
            logger.info(
                "StorageService initialized with S3 storage",
                bucket=self.s3_bucket,
                endpoint=settings.S3_ENDPOINT,
            )

    def _init_s3_client(self):
        """Initialize S3 client for object storage."""
        if not BOTO3_AVAILABLE:
            logger.warning("boto3/botocore not installed, falling back to local storage")
            self.use_local = True
            self.local_storage_path.mkdir(parents=True, exist_ok=True)
            return

        try:
            import boto3
            from botocore.config import Config

            # Configure S3 client with MinIO compatibility
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                config=Config(
                    signature_version="s3v4",
                    s3={"addressing_style": "path"},  # Required for MinIO
                ),
            )

            # Verify bucket exists
            try:
                self._s3_client.head_bucket(Bucket=self.s3_bucket)
            except ClientError:
                # Create bucket if it doesn't exist
                self._s3_client.create_bucket(Bucket=self.s3_bucket)
                logger.info("Created S3 bucket", bucket=self.s3_bucket)

        except Exception as e:
            logger.warning(f"S3 initialization failed: {e}, falling back to local storage")
            self.use_local = True
            self.local_storage_path.mkdir(parents=True, exist_ok=True)

    @property
    def s3_client(self):
        """Lazy S3 client initialization."""
        if self._s3_client is None and not self.use_local:
            self._init_s3_client()
        return self._s3_client

    def _get_local_path(self, key: str) -> Path:
        """Get local file path for a storage key.

        Args:
            key: Storage key

        Returns:
            Path to local file
        """
        # Prevent path traversal
        safe_key = key.replace("../", "").replace("..\\", "")
        return self.local_storage_path / safe_key

    async def upload_file(
        self,
        file_content: bytes,
        key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload file to storage.

        Args:
            file_content: File content as bytes
            key: Storage key (path/filename)
            content_type: MIME type

        Returns:
            Storage key

        Raises:
            IOError: If upload fails
        """
        if self.use_local:
            return await self._upload_local(file_content, key)
        else:
            return await self._upload_s3(file_content, key, content_type)

    async def _upload_local(
        self,
        file_content: bytes,
        key: str,
    ) -> str:
        """Upload file to local storage."""
        local_path = self._get_local_path(key)

        # Ensure parent directory exists
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file asynchronously
        async with aiofiles.open(local_path, "wb") as f:
            await f.write(file_content)

        logger.info("File uploaded to local storage", key=key, size=len(file_content))
        return key

    async def _upload_s3(
        self,
        file_content: bytes,
        key: str,
        content_type: str,
    ) -> str:
        """Upload file to S3."""
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=file_content,
                ContentType=content_type,
            )

            logger.info("File uploaded to S3", key=key, size=len(file_content))
            return key

        except ClientError as e:
            logger.error("S3 upload failed", key=key, error=str(e))
            raise IOError(f"Failed to upload file to S3: {e}")

    async def download_file(
        self,
        key: str,
        local_path: str,
    ) -> None:
        """Download file from storage to local path.

        Args:
            key: Storage key
            local_path: Local file path to save to

        Raises:
            FileNotFoundError: If file not found in storage
            IOError: If download fails
        """
        if self.use_local:
            await self._download_local(key, local_path)
        else:
            await self._download_s3(key, local_path)

    async def _download_local(
        self,
        key: str,
        local_path: str,
    ) -> None:
        """Download file from local storage."""
        source_path = self._get_local_path(key)

        if not source_path.exists():
            raise FileNotFoundError(f"File not found: {key}")

        # Ensure target directory exists
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)

        # Copy file asynchronously
        async with aiofiles.open(source_path, "rb") as src:
            content = await src.read()

        async with aiofiles.open(local_path, "wb") as dst:
            await dst.write(content)

        logger.info("File downloaded from local storage", key=key, local_path=local_path)

    async def _download_s3(
        self,
        key: str,
        local_path: str,
    ) -> None:
        """Download file from S3."""
        try:
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=key,
            )

            # Ensure target directory exists
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

            # Write file asynchronously
            content = response["Body"].read()
            async with aiofiles.open(local_path, "wb") as f:
                await f.write(content)

            logger.info("File downloaded from S3", key=key, local_path=local_path)

        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(f"File not found: {key}")
            logger.error("S3 download failed", key=key, error=str(e))
            raise IOError(f"Failed to download file from S3: {e}")

    async def get_file_url(
        self,
        key: str,
        expiry: int = 3600,
    ) -> str:
        """Generate URL for file access.

        Args:
            key: Storage key
            expiry: URL expiry in seconds (default 1 hour)

        Returns:
            Presigned URL for S3 or local file path for local storage
        """
        if self.use_local:
            # Return local file path for local storage
            local_path = self._get_local_path(key)
            return str(local_path)
        else:
            return self._get_presigned_url(key, expiry)

    def _get_presigned_url(
        self,
        key: str,
        expiry: int,
    ) -> str:
        """Generate presigned URL for S3 object."""
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.s3_bucket,
                    "Key": key,
                },
                ExpiresIn=expiry,
            )

            logger.debug("Generated presigned URL", key=key, expiry=expiry)
            return url

        except ClientError as e:
            logger.error("Failed to generate presigned URL", key=key, error=str(e))
            raise IOError(f"Failed to generate presigned URL: {e}")

    async def delete_file(self, key: str) -> None:
        """Delete file from storage.

        Args:
            key: Storage key

        Note:
            Does not raise error if file doesn't exist.
        """
        if self.use_local:
            await self._delete_local(key)
        else:
            await self._delete_s3(key)

    async def _delete_local(self, key: str) -> None:
        """Delete file from local storage."""
        local_path = self._get_local_path(key)

        try:
            if local_path.exists():
                local_path.unlink()
                logger.info("File deleted from local storage", key=key)
        except Exception as e:
            logger.warning("Failed to delete local file", key=key, error=str(e))

    async def _delete_s3(self, key: str) -> None:
        """Delete file from S3."""
        try:
            self.s3_client.delete_object(
                Bucket=self.s3_bucket,
                Key=key,
            )

            logger.info("File deleted from S3", key=key)

        except ClientError as e:
            logger.warning("Failed to delete S3 object", key=key, error=str(e))

    async def get_file_size(self, key: str) -> int:
        """Get file size in bytes.

        Args:
            key: Storage key

        Returns:
            File size in bytes

        Raises:
            FileNotFoundError: If file not found
        """
        if self.use_local:
            return await self._get_local_file_size(key)
        else:
            return self._get_s3_file_size(key)

    async def _get_local_file_size(self, key: str) -> int:
        """Get local file size."""
        local_path = self._get_local_path(key)

        if not local_path.exists():
            raise FileNotFoundError(f"File not found: {key}")

        return local_path.stat().st_size

    def _get_s3_file_size(self, key: str) -> int:
        """Get S3 object size."""
        try:
            response = self.s3_client.head_object(
                Bucket=self.s3_bucket,
                Key=key,
            )

            return response["ContentLength"]

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise FileNotFoundError(f"File not found: {key}")
            logger.error("Failed to get S3 object size", key=key, error=str(e))
            raise IOError(f"Failed to get file size: {e}")

    async def file_exists(self, key: str) -> bool:
        """Check if file exists in storage.

        Args:
            key: Storage key

        Returns:
            True if file exists
        """
        if self.use_local:
            local_path = self._get_local_path(key)
            return local_path.exists()
        else:
            try:
                self.s3_client.head_object(
                    Bucket=self.s3_bucket,
                    Key=key,
                )
                return True
            except ClientError:
                return False


# Singleton instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get singleton StorageService instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service


__all__ = ["StorageService", "get_storage_service"]