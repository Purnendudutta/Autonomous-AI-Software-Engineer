"""
Semantic code chunker for AST-guided and sliding-window codebase decomposition.

Preserves logical code boundaries (classes, functions, methods, routes) and
maintains line-number fidelity, symbol metadata, and SHA-256 content hashes.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Optional

from app.core.logging import get_logger
from app.repository.parser import parse_source_file

logger = get_logger(__name__)


class CodeChunk:
    """A semantic chunk of source code ready for embedding and indexing."""

    def __init__(
        self,
        file_path: str,
        content: str,
        language: Optional[str] = None,
        symbol_type: Optional[str] = None,
        symbol_name: Optional[str] = None,
        start_line: int = 1,
        end_line: int = 1,
        chunk_metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        self.file_path = file_path
        self.content = content.strip()
        self.language = language
        self.symbol_type = symbol_type
        self.symbol_name = symbol_name
        self.start_line = start_line
        self.end_line = end_line
        self.chunk_metadata = chunk_metadata or {}
        self.content_hash = hashlib.sha256(self.content.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "content": self.content,
            "language": self.language,
            "symbol_type": self.symbol_type,
            "symbol_name": self.symbol_name,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "content_hash": self.content_hash,
            "chunk_metadata": self.chunk_metadata,
        }


def chunk_file_by_lines(
    file_path: str,
    content: str,
    language: Optional[str] = None,
    chunk_lines: int = 60,
    overlap_lines: int = 12,
) -> list[CodeChunk]:
    """
    Sliding window chunker for generic or non-AST files.
    """
    lines = content.splitlines()
    if not lines:
        return []

    chunks: list[CodeChunk] = []
    total_lines = len(lines)
    start = 0

    while start < total_lines:
        end = min(start + chunk_lines, total_lines)
        chunk_content = "\n".join(lines[start:end])

        if chunk_content.strip():
            chunks.append(
                CodeChunk(
                    file_path=file_path,
                    content=chunk_content,
                    language=language,
                    symbol_type="block",
                    symbol_name=f"lines_{start + 1}_{end}",
                    start_line=start + 1,
                    end_line=end,
                    chunk_metadata={"total_lines": total_lines},
                )
            )

        if end >= total_lines:
            break
        start += chunk_lines - overlap_lines

    return chunks


def chunk_source_file(
    file_path: Path | str,
    content: str,
    language: Optional[str] = None,
    max_chunk_lines: int = 100,
) -> list[CodeChunk]:
    """
    Parse a source file and generate semantic code chunks based on symbol boundaries.

    Falls back to sliding-window line chunking if no symbols are found.

    Args:
        file_path: Path or relative path string of the file.
        content: Raw source code text.
        language: Optional language name.
        max_chunk_lines: Maximum lines before splitting oversized symbols.

    Returns:
        List of CodeChunk instances.
    """
    path_obj = Path(file_path) if isinstance(file_path, str) else file_path
    rel_path_str = str(file_path).replace("\\", "/")
    lines = content.splitlines()

    if not lines or not content.strip():
        return []

    # 1. Extract AST symbols and imports
    symbols, imports = parse_source_file(path_obj, content, language)

    # If no symbols extracted (or flat config file), use line-based chunking
    if not symbols:
        return chunk_file_by_lines(rel_path_str, content, language=language)

    chunks: list[CodeChunk] = []

    # 2. Add header / imports chunk if there are significant module-level imports
    first_symbol_start = min(s.start_line for s in symbols) if symbols else 1
    if first_symbol_start > 5:
        header_content = "\n".join(lines[: first_symbol_start - 1]).strip()
        if header_content:
            chunks.append(
                CodeChunk(
                    file_path=rel_path_str,
                    content=header_content,
                    language=language,
                    symbol_type="module_header",
                    symbol_name="imports_and_header",
                    start_line=1,
                    end_line=first_symbol_start - 1,
                    chunk_metadata={"imports": imports[:20]},
                )
            )

    # 3. Create chunks for each discovered symbol
    for sym in symbols:
        start_idx = max(0, sym.start_line - 1)
        end_idx = min(len(lines), sym.end_line)
        symbol_lines = lines[start_idx:end_idx]

        if not symbol_lines:
            continue

        symbol_content = "\n".join(symbol_lines)

        # If a single symbol exceeds max_chunk_lines, sub-chunk it
        if len(symbol_lines) > max_chunk_lines:
            sub_chunks = chunk_file_by_lines(
                rel_path_str,
                symbol_content,
                language=language,
                chunk_lines=max_chunk_lines,
                overlap_lines=15,
            )
            for sc in sub_chunks:
                sc.symbol_name = f"{sym.name} (partial)"
                sc.symbol_type = sym.symbol_type
                sc.start_line = sym.start_line + sc.start_line - 1
                sc.end_line = sym.start_line + sc.end_line - 1
                chunks.append(sc)
        else:
            chunks.append(
                CodeChunk(
                    file_path=rel_path_str,
                    content=symbol_content,
                    language=language,
                    symbol_type=sym.symbol_type,
                    symbol_name=sym.name,
                    start_line=sym.start_line,
                    end_line=sym.end_line,
                    chunk_metadata={
                        "docstring": sym.docstring,
                        "parameters": sym.parameters,
                        "decorators": sym.decorators,
                        **sym.metadata,
                    },
                )
            )

    return chunks
