#!/usr/bin/env python3
"""Deterministic document chunker for source corpus files.

Splits corpus documents into LLM-processable segments (~800 words) for the
fan-out agentic pipeline.  Chunks are intermediate artifacts — they do NOT
ship with the final dataset.

Usage:
    python generation/chunk_documents.py --case corpus/ntsb/DCA19FA089/
    python generation/chunk_documents.py --all
    python generation/chunk_documents.py --all --max-words 600
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path so we can import from crossfire if needed
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from loguru import logger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _title_from_filename(filename: str) -> str:
    """Derive a document title from a filename.

    Strips numeric prefix and .txt extension, replaces underscores with spaces.
    """
    stem = Path(filename).stem
    stem = re.sub(r"^\d+_", "", stem)
    return stem.replace("_", " ")


def _split_with_offsets(text: str, separator: str) -> list[tuple[int, int, str]]:
    """Split *text* on *separator*, returning (char_start, char_end, segment) tuples.

    The separator characters are attached to the **end** of the preceding
    segment so that concatenating all segment texts reproduces the original
    string exactly (no gaps, no overlaps).
    """
    if not text:
        return [(0, 0, "")]

    # re.split with a capturing group keeps the separators as elements
    parts = re.split(f"({re.escape(separator)})", text)

    segments: list[tuple[int, int, str]] = []
    offset = 0

    i = 0
    while i < len(parts):
        segment = parts[i]
        # Attach any following separator to this segment
        if i + 1 < len(parts) and parts[i + 1] == separator:
            segment += parts[i + 1]
            i += 2
        else:
            i += 1
        start = offset
        end = offset + len(segment)
        segments.append((start, end, segment))
        offset = end

    return segments


def _split_at_word_boundary(
    text: str, char_start: int, max_words: int
) -> list[tuple[int, int, str]]:
    """Split a single long line at word boundaries into segments of ≤ *max_words*.

    Returns (char_start, char_end, segment_text) tuples with offsets relative
    to the **original document** (shifted by *char_start*).
    """
    words = text.split(" ")
    segments: list[tuple[int, int, str]] = []
    local_offset = 0

    for batch_start in range(0, len(words), max_words):
        batch = words[batch_start : batch_start + max_words]
        chunk_text = " ".join(batch)
        # Preserve the original whitespace by slicing from text
        # Find the start of this batch in the original text
        seg_start = local_offset
        seg_end = seg_start + len(chunk_text)
        # If there's a trailing space in the original text, include it
        if seg_end < len(text) and text[seg_end] == " ":
            seg_end += 1
            chunk_text = text[seg_start:seg_end]
        else:
            chunk_text = text[seg_start:seg_end]
        segments.append((char_start + seg_start, char_start + seg_end, chunk_text))
        local_offset = seg_end

    # Handle any remaining characters (shouldn't happen normally, but defensive)
    if local_offset < len(text):
        remaining = text[local_offset:]
        segments.append(
            (char_start + local_offset, char_start + len(text), remaining)
        )

    return segments


def _split_segments(text: str, max_words: int) -> list[tuple[int, int, str]]:
    """Three-level splitting: paragraphs → lines → word boundaries.

    Returns a flat list of atomic (char_start, char_end, segment_text) tuples.
    """
    if not text:
        return [(0, 0, "")]

    # Level 1: split on paragraph boundaries (\n\n)
    para_segments = _split_with_offsets(text, "\n\n")

    atomic: list[tuple[int, int, str]] = []

    for p_start, p_end, p_text in para_segments:
        word_count = len(p_text.split())
        if word_count <= max_words:
            atomic.append((p_start, p_end, p_text))
            continue

        # Level 2: split oversized paragraph on single newlines
        line_segments = _split_with_offsets(p_text, "\n")
        for l_start, l_end, l_text in line_segments:
            l_word_count = len(l_text.split())
            abs_start = p_start + l_start
            abs_end = p_start + l_end
            if l_word_count <= max_words:
                atomic.append((abs_start, abs_end, l_text))
            else:
                # Level 3: split at word boundaries
                word_segs = _split_at_word_boundary(l_text, abs_start, max_words)
                atomic.extend(word_segs)

    return atomic


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------


def chunk_text(text: str, max_words: int = 800) -> list[dict]:
    """Split *text* into deterministic chunks of approximately *max_words*.

    Returns a list of dicts, each with:
        chunk_index  (int)   – 0-based index
        char_start   (int)   – inclusive start offset into *text*
        char_end     (int)   – exclusive end offset into *text*
        word_count   (int)   – number of words in the chunk
        text         (str)   – the chunk content

    Invariant: ``"".join(c["text"] for c in chunks) == text``
    """
    # Trivial case: fits in one chunk
    if len(text.split()) <= max_words:
        return [
            {
                "chunk_index": 0,
                "char_start": 0,
                "char_end": len(text),
                "word_count": len(text.split()),
                "text": text,
            }
        ]

    segments = _split_segments(text, max_words)

    # Accumulate segments into chunks
    chunks: list[dict] = []
    buf_segments: list[tuple[int, int, str]] = []
    buf_words = 0

    for seg in segments:
        seg_start, seg_end, seg_text = seg
        seg_words = len(seg_text.split())

        if buf_segments and buf_words + seg_words > max_words:
            # Flush buffer as a chunk
            chunk_start = buf_segments[0][0]
            chunk_end = buf_segments[-1][1]
            chunk_content = text[chunk_start:chunk_end]
            chunks.append(
                {
                    "chunk_index": len(chunks),
                    "char_start": chunk_start,
                    "char_end": chunk_end,
                    "word_count": len(chunk_content.split()),
                    "text": chunk_content,
                }
            )
            buf_segments = [seg]
            buf_words = seg_words
        else:
            buf_segments.append(seg)
            buf_words += seg_words

    # Flush remaining buffer
    if buf_segments:
        chunk_start = buf_segments[0][0]
        chunk_end = buf_segments[-1][1]
        chunk_content = text[chunk_start:chunk_end]
        chunks.append(
            {
                "chunk_index": len(chunks),
                "char_start": chunk_start,
                "char_end": chunk_end,
                "word_count": len(chunk_content.split()),
                "text": chunk_content,
            }
        )

    return chunks


def chunk_case(
    case_dir: Path,
    max_words: int = 800,
    corpus_dir: Path | None = None,
) -> dict | None:
    """Chunk all documents in a single case directory.

    Reads metadata from the corpus manifest, chunks each ``.txt`` file, writes
    chunk files to ``case_dir/chunks/``, and produces a ``chunk_manifest.json``.

    Returns the manifest dict, or ``None`` on failure.
    """
    case_dir = Path(case_dir).resolve()
    case_id = case_dir.name

    if not case_dir.is_dir():
        logger.error(f"Case directory not found: {case_dir}")
        return None

    # Resolve corpus root for manifest lookup
    if corpus_dir is None:
        corpus_dir = case_dir.parent

    # Load corpus manifest for metadata
    doc_meta_lookup: dict[str, dict] = {}
    manifest_path = corpus_dir / "manifest.json"
    if manifest_path.exists():
        try:
            with open(manifest_path) as f:
                corpus_manifest = json.load(f)
            for case in corpus_manifest.get("cases", []):
                if case["case_id"] == case_id:
                    for doc in case.get("documents", []):
                        doc_meta_lookup[doc["filename"]] = doc
                    break
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning(f"Failed to read corpus manifest: {exc}")

    # Find all .txt files (sorted for determinism)
    txt_files = sorted(f for f in case_dir.iterdir() if f.suffix == ".txt")

    if not txt_files:
        logger.warning(f"No .txt files in {case_dir}")
        return None

    # Prepare chunks directory
    chunks_dir = case_dir / "chunks"
    chunks_dir.mkdir(exist_ok=True)

    documents: list[dict] = []
    total_chunks = 0
    single_chunk_count = 0
    multi_chunk_count = 0

    for txt_file in txt_files:
        try:
            content = txt_file.read_text(errors="replace")
        except OSError as exc:
            logger.warning(f"Cannot read {txt_file.name}: {exc}")
            continue

        if not content.strip():
            logger.warning(f"Empty file: {txt_file.name}")

        # Get metadata from corpus manifest or derive from filename
        meta = doc_meta_lookup.get(txt_file.name)
        if meta:
            title = meta["title"]
            document_type = meta["document_type"]
        else:
            title = _title_from_filename(txt_file.name)
            document_type = "investigation_report"

        chunks = chunk_text(content, max_words)

        # Write chunk files
        chunk_records: list[dict] = []
        for chunk in chunks:
            chunk_num = chunk["chunk_index"] + 1  # 1-based for filenames
            chunk_filename = f"{txt_file.stem}_chunk_{chunk_num:03d}.txt"
            chunk_path = chunks_dir / chunk_filename
            chunk_path.write_text(chunk["text"])

            chunk_records.append(
                {
                    "chunk_file": chunk_filename,
                    "chunk_index": chunk["chunk_index"],
                    "char_start": chunk["char_start"],
                    "char_end": chunk["char_end"],
                    "word_count": chunk["word_count"],
                }
            )

        doc_word_count = len(content.split())
        is_single = len(chunks) == 1

        if is_single:
            single_chunk_count += 1
        else:
            multi_chunk_count += 1

        total_chunks += len(chunks)

        documents.append(
            {
                "source_file": txt_file.name,
                "title": title,
                "document_type": document_type,
                "total_words": doc_word_count,
                "chunk_count": len(chunks),
                "chunks": chunk_records,
            }
        )

    # Build manifest
    manifest = {
        "case_id": case_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "max_words": max_words,
        "documents": documents,
        "summary": {
            "total_documents": len(documents),
            "total_chunks": total_chunks,
            "single_chunk_documents": single_chunk_count,
            "multi_chunk_documents": multi_chunk_count,
        },
    }

    manifest_out = chunks_dir / "chunk_manifest.json"
    with open(manifest_out, "w") as f:
        json.dump(manifest, f, indent=2)

    logger.info(
        f"Chunked {case_id}: {len(documents)} documents → {total_chunks} chunks"
    )

    return manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="{time:HH:mm:ss} | {level:<7} | {message}",
    )

    parser = argparse.ArgumentParser(
        description="Chunk source corpus documents for agentic processing"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--case", type=Path, help="Path to a single case directory"
    )
    group.add_argument(
        "--all", action="store_true", help="Chunk all cases in corpus"
    )
    parser.add_argument(
        "--max-words",
        type=int,
        default=800,
        help="Maximum words per chunk (default: 800)",
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=Path("corpus"),
        help="Corpus root directory (default: corpus)",
    )

    args = parser.parse_args()

    if args.case:
        # Single case mode
        if not args.case.is_dir():
            logger.error(f"Case directory not found: {args.case}")
            sys.exit(1)

        result = chunk_case(args.case, args.max_words, args.corpus_dir)
        if result is None:
            logger.error(f"Failed to chunk case: {args.case}")
            sys.exit(1)

    else:
        # All-cases mode — traverse corpus/{source_id}/{case_id}/
        if not args.corpus_dir.is_dir():
            logger.error(f"Corpus directory not found: {args.corpus_dir}")
            sys.exit(1)

        case_dirs = sorted(
            case_dir
            for source_dir in args.corpus_dir.iterdir()
            if source_dir.is_dir()
            for case_dir in source_dir.iterdir()
            if case_dir.is_dir()
        )

        if not case_dirs:
            logger.error(f"No case directories in {args.corpus_dir}")
            sys.exit(1)

        total_docs = 0
        total_chunks = 0
        success_count = 0

        for case_dir in case_dirs:
            result = chunk_case(case_dir, args.max_words, args.corpus_dir)
            if result is not None:
                total_docs += result["summary"]["total_documents"]
                total_chunks += result["summary"]["total_chunks"]
                success_count += 1
            else:
                logger.warning(f"Skipped case: {case_dir.name}")

        if success_count == 0:
            logger.error("All cases failed")
            sys.exit(1)

        logger.info(
            f"Chunked {success_count} cases: "
            f"{total_docs} documents → {total_chunks} chunks"
        )


if __name__ == "__main__":
    main()
