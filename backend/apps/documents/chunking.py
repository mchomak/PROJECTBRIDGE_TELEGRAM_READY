from dataclasses import dataclass

from apps.documents.extraction import ExtractedSegment

DEFAULT_CHUNK_SIZE = 1_000
DEFAULT_CHUNK_OVERLAP = 150


@dataclass(frozen=True)
class DocumentChunkInput:
    chunk_index: int
    content: str
    page_number: int | None
    metadata: dict[str, int]


def chunk_segments(
    segments: list[ExtractedSegment],
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[DocumentChunkInput]:
    if chunk_size < 1 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Chunk overlap must be nonnegative and smaller than size.")

    chunks = []
    for segment in segments:
        start = 0
        while start < len(segment.text):
            end = min(start + chunk_size, len(segment.text))
            location = {
                **segment.location,
                "start_char": segment.location.get("start_char", 0) + start,
                "end_char": segment.location.get("start_char", 0) + end,
            }
            chunks.append(
                DocumentChunkInput(
                    chunk_index=len(chunks),
                    content=segment.text[start:end],
                    page_number=segment.page_number,
                    metadata=location,
                )
            )
            if end == len(segment.text):
                break
            start = end - overlap
    return chunks
