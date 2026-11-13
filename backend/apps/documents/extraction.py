import io
from dataclasses import dataclass
from pathlib import PurePosixPath

from docx import Document as WordDocument
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader

from .docx_safety import DocxArchiveError, docx_archive_names

MAX_EXTRACTED_TEXT_CHARS = 2_000_000
MAX_PDF_PAGES = 5_000


class DocumentExtractionError(Exception):
    """The supported document could not be read safely."""


class NoExtractableTextError(Exception):
    """The document has no searchable text layer."""


@dataclass(frozen=True)
class ExtractedSegment:
    text: str
    location: dict[str, int]
    page_number: int | None = None


def _decode_text(contents: bytes) -> str:
    try:
        if contents.startswith((b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
            return contents.decode("utf-32")
        if contents.startswith((b"\xff\xfe", b"\xfe\xff")):
            return contents.decode("utf-16")
        return contents.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DocumentExtractionError("Text is not valid Unicode.") from exc


def _text_segment(text: str) -> list[ExtractedSegment]:
    if not text.strip():
        raise NoExtractableTextError
    if len(text) > MAX_EXTRACTED_TEXT_CHARS:
        raise DocumentExtractionError("Extracted text exceeds the processing limit.")
    return [ExtractedSegment(text, {"start_char": 0, "end_char": len(text)})]


def _extract_pdf(contents: bytes) -> list[ExtractedSegment]:
    try:
        reader = PdfReader(io.BytesIO(contents), strict=True)
        if len(reader.pages) > MAX_PDF_PAGES:
            raise DocumentExtractionError("PDF exceeds the page processing limit.")
        segments = []
        total_chars = 0
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if not text:
                continue
            total_chars += len(text)
            if total_chars > MAX_EXTRACTED_TEXT_CHARS:
                raise DocumentExtractionError(
                    "Extracted text exceeds the processing limit."
                )
            segments.append(
                ExtractedSegment(
                    text,
                    {"start_char": 0, "end_char": len(text)},
                    page_number,
                )
            )
    except DocumentExtractionError:
        raise
    except Exception as exc:
        raise DocumentExtractionError("PDF could not be parsed.") from exc
    if not segments:
        raise NoExtractableTextError
    return segments


def _extract_docx(contents: bytes) -> list[ExtractedSegment]:
    try:
        names = docx_archive_names(contents)
        if "[Content_Types].xml" not in names or "word/document.xml" not in names:
            raise DocumentExtractionError("DOCX package structure is incomplete.")
        document = WordDocument(io.BytesIO(contents))
    except DocumentExtractionError:
        raise
    except DocxArchiveError as exc:
        raise DocumentExtractionError(
            "DOCX exceeds archive processing limits."
        ) from exc
    except Exception as exc:
        raise DocumentExtractionError("DOCX could not be parsed.") from exc

    segments = []
    total_chars = 0

    def append_paragraph(paragraph, location):
        nonlocal total_chars
        text = paragraph.text.strip()
        if not text:
            return
        total_chars += len(text)
        if total_chars > MAX_EXTRACTED_TEXT_CHARS:
            raise DocumentExtractionError(
                "Extracted text exceeds the processing limit."
            )
        segments.append(
            ExtractedSegment(
                text,
                {**location, "start_char": 0, "end_char": len(text)},
            )
        )

    paragraph_index = 0
    table_index = 0
    for block in document.iter_inner_content():
        if isinstance(block, Paragraph):
            append_paragraph(block, {"paragraph": paragraph_index})
            paragraph_index += 1
        elif isinstance(block, Table):
            seen_cells = set()
            for row_index, row in enumerate(block.rows):
                for cell_index, cell in enumerate(row.cells):
                    if cell._tc in seen_cells:
                        continue
                    seen_cells.add(cell._tc)
                    for cell_paragraph_index, paragraph in enumerate(cell.paragraphs):
                        append_paragraph(
                            paragraph,
                            {
                                "table_index": table_index,
                                "row_index": row_index,
                                "cell_index": cell_index,
                                "paragraph_index": cell_paragraph_index,
                            },
                        )
            table_index += 1
    if not segments:
        raise NoExtractableTextError
    return segments


def extract_segments(*, filename: str, contents: bytes) -> list[ExtractedSegment]:
    """Extract searchable text with stable page/paragraph source locations."""
    extension = PurePosixPath(filename).suffix.lower()
    if extension in {".txt", ".md", ".markdown"}:
        return _text_segment(_decode_text(contents))
    if extension == ".pdf":
        return _extract_pdf(contents)
    if extension == ".docx":
        return _extract_docx(contents)
    raise NoExtractableTextError("Unsupported document extension.")
