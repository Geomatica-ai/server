# Copyright (C) Lutra Consulting Limited
#
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-MerginMaps-Commercial

import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    import boto3

    _boto3_available = True
except ImportError:
    _boto3_available = False
    logger.info("boto3 not installed — S3 version archiving disabled")


class S3ArchiveClient:
    """Upload old project version files to S3 before local deletion.

    S3 is optional — if boto3 is not installed or S3_ARCHIVE_BUCKET is not set,
    from_app_config() returns None and archiving is silently skipped.

    Archive key format: {prefix}/{project_id}/v{version}/{relative_file_path}
    """

    def __init__(self, bucket: str, key_prefix: str = "version_archives", region: str = ""):
        self.bucket = bucket
        self.key_prefix = key_prefix
        self.region = region
        self._client = None

    @classmethod
    def from_app_config(cls, app_config: dict) -> Optional["S3ArchiveClient"]:
        """Return a configured instance, or None if S3 archiving is not set up."""
        bucket = app_config.get("S3_ARCHIVE_BUCKET", "").strip()
        if not _boto3_available or not bucket:
            return None
        return cls(
            bucket=bucket,
            key_prefix=app_config.get("S3_ARCHIVE_KEY_PREFIX", "version_archives"),
            region=app_config.get("S3_ARCHIVE_REGION", ""),
        )

    def _get_client(self):
        if self._client is None:
            kwargs = {}
            if self.region:
                kwargs["region_name"] = self.region
            self._client = boto3.client("s3", **kwargs)
        return self._client

    def archive_version(
        self,
        project_id: str,
        project_dir: str,
        version_number: int,
        file_locations: List[str],
    ) -> bool:
        """Upload physical files for a version to S3.

        Args:
            project_id:      Project UUID string (used as S3 path segment).
            project_dir:     Absolute path to the project's local root directory.
            version_number:  Integer version number (e.g. 3).
            file_locations:  List of relative paths within project_dir
                             (e.g. ["v3/survey.gpkg", "v3/photo.jpg"]).

        Returns:
            True if all files were uploaded (or list was empty).
            False on any error — caller should log and continue with local deletion.
        """
        if not _boto3_available:
            return False

        client = self._get_client()
        success = True

        for relative_path in file_locations:
            abs_path = os.path.join(project_dir, relative_path)
            if not os.path.exists(abs_path):
                # File may have been cleaned up already by optimize_storage — skip silently
                continue

            s3_key = "/".join(
                filter(None, [self.key_prefix, str(project_id), relative_path])
            )
            try:
                client.upload_file(abs_path, self.bucket, s3_key)
                logger.debug("Archived %s -> s3://%s/%s", abs_path, self.bucket, s3_key)
            except Exception as exc:
                logger.error(
                    "S3 upload failed for %s -> s3://%s/%s: %s",
                    abs_path,
                    self.bucket,
                    s3_key,
                    exc,
                )
                success = False

        return success
