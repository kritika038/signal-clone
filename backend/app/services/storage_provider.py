from __future__ import annotations

import hashlib
import logging
import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class VirusScanner(ABC):
    @abstractmethod
    async def scan(self, file_bytes: bytes, filename: str) -> None:
        raise NotImplementedError


class NoOpVirusScanner(VirusScanner):
    async def scan(self, file_bytes: bytes, filename: str) -> None:
        return None


class StorageProvider(ABC):
    def __init__(self, virus_scanner: VirusScanner | None = None):
        self._virus_scanner = virus_scanner or NoOpVirusScanner()

    @abstractmethod
    async def upload_file(self, file_bytes: bytes, filename: str, mime_type: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def delete_file(self, storage_key: str) -> bool:
        raise NotImplementedError

    def validate_file(self, file_bytes: bytes, mime_type: str) -> None:
        if len(file_bytes) > settings.STORAGE_MAX_FILE_SIZE_BYTES:
            raise ValueError("File exceeds maximum limit of 10MB")
        if mime_type.lower() not in settings.STORAGE_ALLOWED_MIME_TYPES:
            raise ValueError(f"Mime-type '{mime_type}' is not supported")

    async def run_security_hooks(self, file_bytes: bytes, filename: str) -> None:
        await self._virus_scanner.scan(file_bytes, filename)

    def calculate_checksum(self, file_bytes: bytes) -> str:
        return hashlib.sha256(file_bytes).hexdigest()

    def generate_presigned_url(self, storage_key: str) -> str:
        return f"{settings.STORAGE_PUBLIC_BASE_URL}/{storage_key}"

    def build_result(
        self, storage_key: str, filename: str, mime_type: str, file_bytes: bytes
    ) -> dict[str, Any]:
        checksum = self.calculate_checksum(file_bytes)
        return {
            "storage_key": storage_key,
            "original_filename": filename,
            "mime_type": mime_type,
            "size": len(file_bytes),
            "checksum": checksum,
            "playback_url": self.generate_presigned_url(storage_key),
            "thumbnail_url": None,
        }

    def healthcheck(self) -> dict[str, object]:
        return {"ok": True, "backend": self.__class__.__name__}


class LocalStorageProvider(StorageProvider):
    def __init__(self, upload_dir: str | None = None):
        super().__init__()
        self.upload_dir = Path(upload_dir or settings.STORAGE_LOCAL_PATH)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def upload_file(self, file_bytes: bytes, filename: str, mime_type: str) -> dict[str, Any]:
        self.validate_file(file_bytes, mime_type)
        await self.run_security_hooks(file_bytes, filename)
        storage_key = f"{uuid.uuid4().hex}{Path(filename).suffix}"
        path = self.upload_dir / storage_key
        path.write_bytes(file_bytes)
        logger.info("uploads.local.saved", extra={"storage_key": storage_key, "filename": filename})
        return self.build_result(storage_key, filename, mime_type, file_bytes)

    async def delete_file(self, storage_key: str) -> bool:
        path = self.upload_dir / storage_key
        if path.exists():
            path.unlink()
            return True
        return False

    def healthcheck(self) -> dict[str, object]:
        return {
            "ok": self.upload_dir.exists(),
            "backend": self.__class__.__name__,
            "path": str(self.upload_dir),
        }


class ObjectStorageProvider(StorageProvider):
    backend_name = "object-storage"

    async def upload_file(self, file_bytes: bytes, filename: str, mime_type: str) -> dict[str, Any]:
        self.validate_file(file_bytes, mime_type)
        await self.run_security_hooks(file_bytes, filename)
        storage_key = f"{self.backend_name}-{uuid.uuid4().hex}-{filename}"
        logger.info("uploads.object.stub", extra={"backend": self.backend_name, "storage_key": storage_key})
        return self.build_result(storage_key, filename, mime_type, file_bytes)

    async def delete_file(self, storage_key: str) -> bool:
        logger.info("uploads.object.delete.stub", extra={"backend": self.backend_name, "storage_key": storage_key})
        return True


class MinIOStorageProvider(ObjectStorageProvider):
    backend_name = "minio"


class S3StorageProvider(ObjectStorageProvider):
    backend_name = "s3"


class CloudflareR2StorageProvider(ObjectStorageProvider):
    backend_name = "r2"
