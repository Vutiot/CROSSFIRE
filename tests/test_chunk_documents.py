"""Tests for the document chunking utility."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from generation.chunk_documents import chunk_case, chunk_text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_case(
    tmp_path: Path,
    case_id: str,
    docs: list[dict],
    *,
    create_manifest: bool = True,
) -> Path:
    """Create a mock case directory with .txt files and optional corpus manifest.

    Each doc dict should have:
        title (str), content (str), word_count (int, optional),
        document_type (str, optional)
    """
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir(exist_ok=True)
    case_dir = corpus_dir / case_id
    case_dir.mkdir()

    manifest_docs = []
    for i, doc in enumerate(docs, start=1):
        filename = f"{i:03d}_{doc['title'].replace(' ', '_')}.txt"
        (case_dir / filename).write_text(doc["content"])
        manifest_docs.append({
            "filename": filename,
            "title": doc["title"],
            "document_type": doc.get("document_type", "investigation_report"),
            "word_count": doc.get("word_count", len(doc["content"].split())),
        })

    if create_manifest:
        manifest = {
            "generated_at": "2026-04-10T00:00:00+00:00",
            "cases": [
                {
                    "case_id": case_id,
                    "document_count": len(docs),
                    "documents": manifest_docs,
                    "type_distribution": {},
                }
            ],
            "summary": {
                "total_cases": 1,
                "total_documents": len(docs),
                "document_types_found": [],
            },
        }
        (corpus_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    return case_dir


# ---------------------------------------------------------------------------
# chunk_text tests
# ---------------------------------------------------------------------------


class TestChunkText:
    """Test the core text chunking algorithm."""

    def test_short_text_single_chunk(self) -> None:
        text = "This is a short document with only a few words."
        chunks = chunk_text(text, max_words=800)
        assert len(chunks) == 1
        assert chunks[0]["chunk_index"] == 0
        assert chunks[0]["char_start"] == 0
        assert chunks[0]["char_end"] == len(text)
        assert chunks[0]["text"] == text
        assert chunks[0]["word_count"] == len(text.split())

    def test_empty_text(self) -> None:
        chunks = chunk_text("")
        assert len(chunks) == 1
        assert chunks[0]["word_count"] == 0
        assert chunks[0]["char_start"] == 0
        assert chunks[0]["char_end"] == 0
        assert chunks[0]["text"] == ""

    def test_paragraph_splitting(self) -> None:
        """Text with paragraphs splits on \\n\\n boundaries."""
        para = "Word " * 30 + "end."
        text = f"{para}\n\n{para}\n\n{para}"
        chunks = chunk_text(text, max_words=40)
        assert len(chunks) >= 2
        # Verify no gaps
        reconstructed = "".join(c["text"] for c in chunks)
        assert reconstructed == text

    def test_line_splitting_within_paragraph(self) -> None:
        """A single paragraph (no \\n\\n) with lines splits on \\n."""
        line = "Word " * 30 + "end."
        text = "\n".join([line] * 5)
        chunks = chunk_text(text, max_words=40)
        assert len(chunks) >= 2
        reconstructed = "".join(c["text"] for c in chunks)
        assert reconstructed == text

    def test_word_boundary_splitting(self) -> None:
        """A very long single line splits at word boundaries."""
        text = " ".join(f"word{i}" for i in range(200))
        chunks = chunk_text(text, max_words=50)
        assert len(chunks) >= 4
        reconstructed = "".join(c["text"] for c in chunks)
        assert reconstructed == text

    @pytest.mark.parametrize(
        "text",
        [
            "Simple short text.",
            "Paragraph one.\n\nParagraph two.\n\nParagraph three.",
            "\n".join(["Line " * 20 + "end."] * 10),
            " ".join(f"w{i}" for i in range(300)),
            "Short.\n\n" + " ".join(f"long{i}" for i in range(200)) + "\n\nShort again.",
            "A\n\nB\n\nC\n\nD\n\nE\n\nF\n\nG\n\nH\n\nI\n\nJ",
        ],
        ids=[
            "short",
            "paragraphs",
            "lines",
            "long_line",
            "mixed",
            "many_short_paragraphs",
        ],
    )
    def test_no_gaps_no_overlaps(self, text: str) -> None:
        chunks = chunk_text(text, max_words=30)
        reconstructed = "".join(c["text"] for c in chunks)
        assert reconstructed == text, (
            f"Reconstruction mismatch: {len(reconstructed)} chars vs {len(text)} chars"
        )

    @pytest.mark.parametrize(
        "text",
        [
            "Hello world.",
            "Para one.\n\nPara two.\n\nPara three.",
            " ".join(f"w{i}" for i in range(100)),
        ],
        ids=["simple", "paragraphs", "long_line"],
    )
    def test_char_offsets_match_text(self, text: str) -> None:
        chunks = chunk_text(text, max_words=20)
        for chunk in chunks:
            assert text[chunk["char_start"] : chunk["char_end"]] == chunk["text"]

    def test_deterministic(self) -> None:
        text = "Para one with words.\n\nPara two with more.\n\n" + " ".join(
            f"w{i}" for i in range(100)
        )
        chunks_a = chunk_text(text, max_words=30)
        chunks_b = chunk_text(text, max_words=30)
        assert chunks_a == chunks_b

    def test_chunk_index_sequential(self) -> None:
        text = "\n\n".join(["Word " * 20 + "end."] * 5)
        chunks = chunk_text(text, max_words=30)
        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i

    def test_all_chunks_have_word_count(self) -> None:
        text = "\n\n".join(["Some words here."] * 10)
        chunks = chunk_text(text, max_words=10)
        for chunk in chunks:
            assert chunk["word_count"] > 0

    def test_custom_max_words(self) -> None:
        text = " ".join(f"word{i}" for i in range(100))
        chunks_small = chunk_text(text, max_words=20)
        chunks_large = chunk_text(text, max_words=200)
        assert len(chunks_small) > len(chunks_large)

    def test_single_word_boundary(self) -> None:
        """Exactly max_words should be a single chunk."""
        words = ["word"] * 50
        text = " ".join(words)
        chunks = chunk_text(text, max_words=50)
        assert len(chunks) == 1

    def test_whitespace_only(self) -> None:
        text = "   \n\n   \n   "
        chunks = chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0]["text"] == text


# ---------------------------------------------------------------------------
# chunk_case tests
# ---------------------------------------------------------------------------


class TestChunkCase:
    """Test per-case chunking with filesystem operations."""

    def test_creates_chunks_directory(self, tmp_path: Path) -> None:
        case_dir = _make_mock_case(tmp_path, "CASE_A", [
            {"title": "DOC ONE", "content": "Short document content."},
        ])
        chunk_case(case_dir)
        assert (case_dir / "chunks").is_dir()

    def test_chunk_files_created(self, tmp_path: Path) -> None:
        short_content = "A short document."
        long_content = " ".join(f"word{i}" for i in range(2000))
        case_dir = _make_mock_case(tmp_path, "CASE_A", [
            {"title": "SHORT DOC", "content": short_content},
            {"title": "LONG DOC", "content": long_content},
        ])
        chunk_case(case_dir, max_words=800)

        chunk_files = sorted((case_dir / "chunks").glob("*.txt"))
        # Short doc: 1 chunk; Long doc: multiple chunks
        assert len(chunk_files) >= 3  # 1 + at least 2

    def test_chunk_manifest_structure(self, tmp_path: Path) -> None:
        case_dir = _make_mock_case(tmp_path, "CASE_A", [
            {"title": "DOC ONE", "content": "Document content here."},
        ])
        result = chunk_case(case_dir)

        manifest_path = case_dir / "chunks" / "chunk_manifest.json"
        assert manifest_path.exists()

        with open(manifest_path) as f:
            manifest = json.load(f)

        assert manifest["case_id"] == "CASE_A"
        assert "generated_at" in manifest
        assert "max_words" in manifest
        assert "documents" in manifest
        assert "summary" in manifest
        assert result is not None
        assert result["case_id"] == "CASE_A"

    def test_manifest_summary_counts(self, tmp_path: Path) -> None:
        short_content = "A few words."
        long_content = " ".join(f"word{i}" for i in range(2000))
        case_dir = _make_mock_case(tmp_path, "CASE_A", [
            {"title": "SHORT", "content": short_content},
            {"title": "ALSO SHORT", "content": "Another short one."},
            {"title": "LONG", "content": long_content},
        ])
        result = chunk_case(case_dir, max_words=800)

        assert result is not None
        summary = result["summary"]
        assert summary["total_documents"] == 3
        assert summary["total_chunks"] >= 4  # 1 + 1 + at least 2
        assert summary["single_chunk_documents"] == 2
        assert summary["multi_chunk_documents"] == 1

    def test_single_chunk_document(self, tmp_path: Path) -> None:
        case_dir = _make_mock_case(tmp_path, "CASE_A", [
            {"title": "SMALL", "content": "A small document."},
        ])
        result = chunk_case(case_dir)
        assert result is not None
        assert result["documents"][0]["chunk_count"] == 1

    def test_multi_chunk_document(self, tmp_path: Path) -> None:
        long_content = " ".join(f"word{i}" for i in range(2000))
        case_dir = _make_mock_case(tmp_path, "CASE_A", [
            {"title": "LONG", "content": long_content},
        ])
        result = chunk_case(case_dir, max_words=800)
        assert result is not None
        assert result["documents"][0]["chunk_count"] > 1

    def test_chunk_content_matches_source(self, tmp_path: Path) -> None:
        content = "Para one with content.\n\nPara two.\n\n" + " ".join(
            f"w{i}" for i in range(500)
        )
        case_dir = _make_mock_case(tmp_path, "CASE_A", [
            {"title": "DOC", "content": content},
        ])
        result = chunk_case(case_dir, max_words=100)

        assert result is not None
        chunks_dir = case_dir / "chunks"
        doc = result["documents"][0]

        # Concatenate all chunk files
        reconstructed = ""
        for chunk_info in doc["chunks"]:
            chunk_path = chunks_dir / chunk_info["chunk_file"]
            reconstructed += chunk_path.read_text()

        assert reconstructed == content

    def test_metadata_from_corpus_manifest(self, tmp_path: Path) -> None:
        case_dir = _make_mock_case(tmp_path, "CASE_A", [
            {
                "title": "METEOROLOGY REPORT",
                "document_type": "meteorology_report",
                "content": "Weather data here.",
            },
        ])
        result = chunk_case(case_dir)
        assert result is not None
        assert result["documents"][0]["title"] == "METEOROLOGY REPORT"
        assert result["documents"][0]["document_type"] == "meteorology_report"

    def test_fallback_metadata_no_manifest(self, tmp_path: Path) -> None:
        case_dir = _make_mock_case(
            tmp_path,
            "CASE_A",
            [{"title": "SOME_REPORT", "content": "Content here."}],
            create_manifest=False,
        )
        result = chunk_case(case_dir)
        assert result is not None
        # Should fall back to filename-derived title
        doc = result["documents"][0]
        assert doc["document_type"] == "investigation_report"
        # Title derived from filename
        assert "SOME" in doc["title"]

    def test_deterministic_case(self, tmp_path: Path) -> None:
        content = "Paragraph one.\n\nParagraph two.\n\n" + " ".join(
            f"w{i}" for i in range(300)
        )
        case_dir = _make_mock_case(tmp_path, "CASE_A", [
            {"title": "DOC", "content": content},
        ])

        result1 = chunk_case(case_dir, max_words=100)
        result2 = chunk_case(case_dir, max_words=100)

        assert result1 is not None and result2 is not None
        # Compare everything except generated_at
        result1.pop("generated_at")
        result2.pop("generated_at")
        assert result1 == result2

    def test_returns_none_for_empty_case(self, tmp_path: Path) -> None:
        corpus_dir = tmp_path / "corpus"
        corpus_dir.mkdir()
        case_dir = corpus_dir / "EMPTY_CASE"
        case_dir.mkdir()
        result = chunk_case(case_dir)
        assert result is None

    def test_returns_none_for_missing_dir(self, tmp_path: Path) -> None:
        result = chunk_case(tmp_path / "nonexistent")
        assert result is None

    def test_chunk_filename_pattern(self, tmp_path: Path) -> None:
        case_dir = _make_mock_case(tmp_path, "CASE_A", [
            {"title": "DOC", "content": "Content here."},
        ])
        chunk_case(case_dir)
        chunk_files = list((case_dir / "chunks").glob("*_chunk_*.txt"))
        assert len(chunk_files) >= 1
        # Verify naming pattern
        for cf in chunk_files:
            assert "_chunk_" in cf.name
            assert cf.name.endswith(".txt")


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


class TestCLI:
    """Minimal CLI argument validation tests."""

    def test_mutually_exclusive_args(self) -> None:
        result = subprocess.run(
            [sys.executable, "generation/chunk_documents.py", "--case", "x", "--all"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        assert result.returncode != 0

    def test_no_args_is_error(self) -> None:
        result = subprocess.run(
            [sys.executable, "generation/chunk_documents.py"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        assert result.returncode != 0
