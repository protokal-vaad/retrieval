"""Chunking Quality Evaluator — checks metadata, section distribution, Hebrew health, chunk counts."""
import logging
import re
from collections import defaultdict

from google.cloud import firestore

from src.models import ChunkingIssue, CategoryReport


_VALID_SECTION_TYPES = {"Header and Agenda", "Topic Discussion", "Closing and Decisions"}

# Regex for broken Unicode replacement characters
_BROKEN_ENCODING_RE = re.compile(r"\ufffd")

# Minimum content length to consider a chunk valid
_MIN_CONTENT_LENGTH = 50

# Chunk count bounds per document
_MIN_CHUNKS = 2
_MAX_CHUNKS = 20


class ChunkingEvaluator:
    """Evaluates the quality of chunks stored in Firestore."""

    def __init__(
        self,
        project_id: str,
        database_id: str,
        collection_name: str,
        logger: logging.Logger,
    ):
        self._project_id = project_id
        self._database_id = database_id
        self._collection_name = collection_name
        self._logger = logger

    def evaluate_all(self) -> CategoryReport:
        """Pull all chunks from Firestore and run quality checks."""
        client = firestore.Client(project=self._project_id, database=self._database_id)
        collection_ref = client.collection(self._collection_name)

        self._logger.info("Fetching all chunks from Firestore collection: %s", self._collection_name)
        docs = list(collection_ref.stream())
        self._logger.info("Fetched %d chunks", len(docs))

        if not docs:
            return CategoryReport(
                category="chunking",
                score=0.0,
                status="fail",
                metrics={"total_chunks": 0},
                details=[],
            )

        issues: list[ChunkingIssue] = []
        docs_by_file: dict[str, list[dict]] = defaultdict(list)

        for doc in docs:
            data = doc.to_dict() or {}
            content = data.get("content", "")
            metadata = data.get("metadata", {})
            source_file = metadata.get("source_file", "unknown")
            section_type = metadata.get("section_type")
            document_date = metadata.get("document_date")

            docs_by_file[source_file].append(data)

            # Check 1: Metadata completeness
            if not source_file or source_file == "unknown":
                issues.append(ChunkingIssue(
                    source_file=source_file,
                    issue_type="missing_metadata",
                    detail="Missing source_file in metadata",
                ))

            if not section_type:
                issues.append(ChunkingIssue(
                    source_file=source_file,
                    issue_type="missing_metadata",
                    detail="Missing section_type in metadata",
                ))
            elif section_type not in _VALID_SECTION_TYPES:
                issues.append(ChunkingIssue(
                    source_file=source_file,
                    issue_type="missing_metadata",
                    detail=f"Invalid section_type: '{section_type}'",
                ))

            if document_date is None:
                issues.append(ChunkingIssue(
                    source_file=source_file,
                    issue_type="missing_metadata",
                    detail="Missing document_date (null)",
                ))

            # Check 2: Empty content
            if not content or not content.strip():
                issues.append(ChunkingIssue(
                    source_file=source_file,
                    issue_type="empty_content",
                    detail="Chunk has empty or whitespace-only content",
                ))
            elif len(content.strip()) < _MIN_CONTENT_LENGTH:
                issues.append(ChunkingIssue(
                    source_file=source_file,
                    issue_type="empty_content",
                    detail=f"Chunk content too short ({len(content.strip())} chars < {_MIN_CONTENT_LENGTH})",
                ))

            # Check 3: Hebrew text health — broken encoding
            if content and _BROKEN_ENCODING_RE.search(content):
                issues.append(ChunkingIssue(
                    source_file=source_file,
                    issue_type="encoding_error",
                    detail="Content contains broken Unicode replacement characters (U+FFFD)",
                ))

        # Check 4: Section distribution per document
        for source_file, chunks in docs_by_file.items():
            section_types = [c.get("metadata", {}).get("section_type", "") for c in chunks]
            header_count = section_types.count("Header and Agenda")
            topic_count = section_types.count("Topic Discussion")
            closing_count = section_types.count("Closing and Decisions")

            if header_count == 0:
                issues.append(ChunkingIssue(
                    source_file=source_file,
                    issue_type="bad_section_dist",
                    detail="Missing 'Header and Agenda' chunk",
                ))
            if header_count > 1:
                issues.append(ChunkingIssue(
                    source_file=source_file,
                    issue_type="bad_section_dist",
                    detail=f"Multiple 'Header and Agenda' chunks ({header_count})",
                ))
            if topic_count == 0:
                issues.append(ChunkingIssue(
                    source_file=source_file,
                    issue_type="bad_section_dist",
                    detail="No 'Topic Discussion' chunks found",
                ))
            if closing_count > 1:
                issues.append(ChunkingIssue(
                    source_file=source_file,
                    issue_type="bad_section_dist",
                    detail=f"Multiple 'Closing and Decisions' chunks ({closing_count})",
                ))

            # Check 5: Chunk count sanity
            chunk_count = len(chunks)
            if chunk_count < _MIN_CHUNKS:
                issues.append(ChunkingIssue(
                    source_file=source_file,
                    issue_type="bad_chunk_count",
                    detail=f"Too few chunks ({chunk_count} < {_MIN_CHUNKS})",
                ))
            elif chunk_count > _MAX_CHUNKS:
                issues.append(ChunkingIssue(
                    source_file=source_file,
                    issue_type="bad_chunk_count",
                    detail=f"Too many chunks ({chunk_count} > {_MAX_CHUNKS})",
                ))

        # Calculate scores
        total_chunks = len(docs)
        total_files = len(docs_by_file)
        issue_counts = defaultdict(int)
        for issue in issues:
            issue_counts[issue.issue_type] += 1

        # Files with issues
        files_with_issues = len({i.source_file for i in issues})
        clean_file_rate = (total_files - files_with_issues) / total_files if total_files else 0.0

        # Overall score: percentage of clean files
        overall = clean_file_rate * 100

        if clean_file_rate >= 0.90:
            status = "pass"
        elif clean_file_rate >= 0.70:
            status = "warn"
        else:
            status = "fail"

        self._logger.info(
            "Chunking results — %d chunks across %d files | %d issues | Clean rate: %.1f%% | Status: %s",
            total_chunks, total_files, len(issues), clean_file_rate * 100, status,
        )

        return CategoryReport(
            category="chunking",
            score=round(overall, 1),
            status=status,
            metrics={
                "total_chunks": total_chunks,
                "total_files": total_files,
                "total_issues": len(issues),
                "clean_file_rate": round(clean_file_rate, 3),
                "issues_by_type": dict(issue_counts),
            },
            details=[i.model_dump() for i in issues],
        )
