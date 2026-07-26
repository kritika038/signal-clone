from __future__ import annotations

from typing import Any

from app.services.metrics_service import metrics_service


class AttachmentService:
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

    def validate_attachment(self, attachment_in: dict[str, Any]) -> None:
        size = attachment_in.get("size", 0)
        if size > self.MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"Attachment exceeds maximum file size limit of {self.MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB"
            )
        for required_key in ("storage_key", "original_filename", "mime_type"):
            if not attachment_in.get(required_key):
                raise ValueError(f"Missing {required_key} for attachment")

    def process_metadata(self, attachment_in: dict[str, Any]) -> dict[str, Any]:
        metrics_service.record_upload()
        return {
            "storage_key": attachment_in["storage_key"],
            "original_filename": attachment_in["original_filename"],
            "mime_type": attachment_in["mime_type"],
            "size": attachment_in["size"],
            "width": attachment_in.get("width"),
            "height": attachment_in.get("height"),
            "duration": attachment_in.get("duration"),
            "thumbnail_url": attachment_in.get("thumbnail_url"),
            "checksum": attachment_in.get("checksum"),
        }
