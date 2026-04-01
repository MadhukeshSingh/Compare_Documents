"""
In-Memory Diff Processor
Replaces the original FastAPI router.
Called directly from Streamlit — no database, no disk storage.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from diff_service import DiffEngine, DiffResult, DocumentExtractor
from upload_service import FileProcessor

logger = logging.getLogger(__name__)


@dataclass
class CompareRequest:
    file1_bytes: bytes
    file1_name: str
    file2_bytes: bytes
    file2_name: str


class InMemoryDiffProcessor:
    """
    Stateless coordinator.
    1. Validates both files via FileProcessor
    2. Runs DiffEngine.compare_documents
    3. Returns DiffResult
    """

    def __init__(self):
        self._file_processor = FileProcessor()
        self._extractor = DocumentExtractor()
        self._engine = DiffEngine(self._extractor)

    def compare(self, req: CompareRequest) -> DiffResult:
        # Validate file 1
        meta1 = self._file_processor.process(req.file1_name, req.file1_bytes)
        if not meta1["ok"]:
            raise ValueError(f"File 1 error: {meta1['error']}")

        # Validate file 2
        meta2 = self._file_processor.process(req.file2_name, req.file2_bytes)
        if not meta2["ok"]:
            raise ValueError(f"File 2 error: {meta2['error']}")

        logger.info(
            f"Comparing '{meta1['filename']}' ({meta1['file_size']} bytes) "
            f"vs '{meta2['filename']}' ({meta2['file_size']} bytes)"
        )

        result = self._engine.compare_documents(
            doc1_bytes=req.file1_bytes,
            doc1_name=meta1["filename"],
            doc2_bytes=req.file2_bytes,
            doc2_name=meta2["filename"],
        )

        logger.info(
            f"Comparison done — "
            f"added={result.summary['words_added']} "
            f"removed={result.summary['words_removed']} "
            f"replaced={result.summary['words_replaced']} "
            f"total={result.summary['total_changes']}"
        )
        return result


# Module-level singleton — imported by app.py
processor = InMemoryDiffProcessor()
