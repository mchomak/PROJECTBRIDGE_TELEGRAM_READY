import io
import struct
import zipfile

MAX_DOCX_SOURCE_BYTES = 20 * 1024 * 1024
MAX_DOCX_ARCHIVE_ENTRIES = 10_000
MAX_DOCX_CENTRAL_DIRECTORY_BYTES = 2 * 1024 * 1024
MAX_DOCX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_DOCX_MEMBER_COMPRESSION_RATIO = 200

_END_OF_CENTRAL_DIRECTORY = struct.Struct("<4s4H2LH")
_EOCD_SIGNATURE = b"PK\x05\x06"
_CENTRAL_DIRECTORY_SIGNATURE = b"PK\x01\x02"
_CENTRAL_DIRECTORY_ENTRY_SIZE = 46


class DocxArchiveError(Exception):
    """The DOCX ZIP archive exceeds safety limits or is malformed."""


def _preflight_docx_directory(contents: bytes) -> None:
    if len(contents) > MAX_DOCX_SOURCE_BYTES:
        raise DocxArchiveError("DOCX exceeds the compressed file limit.")
    if len(contents) < _END_OF_CENTRAL_DIRECTORY.size:
        raise DocxArchiveError("DOCX archive is malformed.")

    search_start = max(0, len(contents) - _END_OF_CENTRAL_DIRECTORY.size - 65_535)
    eocd_offset = contents.rfind(_EOCD_SIGNATURE, search_start)
    if eocd_offset < 0 or eocd_offset + _END_OF_CENTRAL_DIRECTORY.size > len(contents):
        raise DocxArchiveError("DOCX archive directory is missing.")

    (
        signature,
        disk_number,
        directory_disk,
        entries_on_disk,
        entry_count,
        directory_size,
        directory_offset,
        comment_length,
    ) = _END_OF_CENTRAL_DIRECTORY.unpack_from(contents, eocd_offset)
    if signature != _EOCD_SIGNATURE or eocd_offset + 22 + comment_length != len(
        contents
    ):
        raise DocxArchiveError("DOCX archive directory is malformed.")
    if disk_number or directory_disk or entries_on_disk != entry_count:
        raise DocxArchiveError("Multi-disk DOCX archives are unsupported.")
    if (
        entry_count == 0xFFFF
        or directory_size == 0xFFFFFFFF
        or directory_offset == 0xFFFFFFFF
    ):
        raise DocxArchiveError("ZIP64 DOCX archives are unsupported.")
    if entry_count > MAX_DOCX_ARCHIVE_ENTRIES:
        raise DocxArchiveError("DOCX contains too many archive entries.")
    if directory_size > MAX_DOCX_CENTRAL_DIRECTORY_BYTES:
        raise DocxArchiveError("DOCX archive directory is too large.")
    if directory_offset + directory_size > eocd_offset:
        raise DocxArchiveError("DOCX archive directory bounds are invalid.")

    directory_end = directory_offset + directory_size
    cursor = directory_offset
    actual_entry_count = 0
    while cursor < directory_end:
        if (
            cursor + _CENTRAL_DIRECTORY_ENTRY_SIZE > directory_end
            or contents[cursor : cursor + 4] != _CENTRAL_DIRECTORY_SIGNATURE
        ):
            raise DocxArchiveError("DOCX archive directory entry is malformed.")
        filename_length, extra_length, comment_length = struct.unpack_from(
            "<HHH", contents, cursor + 28
        )
        entry_size = (
            _CENTRAL_DIRECTORY_ENTRY_SIZE
            + filename_length
            + extra_length
            + comment_length
        )
        if cursor + entry_size > directory_end:
            raise DocxArchiveError("DOCX archive directory entry is truncated.")
        actual_entry_count += 1
        if actual_entry_count > MAX_DOCX_ARCHIVE_ENTRIES:
            raise DocxArchiveError("DOCX contains too many archive entries.")
        cursor += entry_size

    if cursor != directory_end or actual_entry_count != entry_count:
        raise DocxArchiveError("DOCX archive entry count is inconsistent.")


def docx_archive_names(contents: bytes) -> set[str]:
    """Validate archive bounds before ZipFile builds its member list."""
    _preflight_docx_directory(contents)
    try:
        with zipfile.ZipFile(io.BytesIO(contents)) as archive:
            members = archive.filelist
            if len(members) > MAX_DOCX_ARCHIVE_ENTRIES:
                raise DocxArchiveError("DOCX contains too many archive entries.")
            if (
                sum(member.file_size for member in members)
                > MAX_DOCX_UNCOMPRESSED_BYTES
            ):
                raise DocxArchiveError("DOCX exceeds the decompression limit.")
            if any(
                member.file_size > 1_000_000
                and member.file_size / max(member.compress_size, 1)
                > MAX_DOCX_MEMBER_COMPRESSION_RATIO
                for member in members
            ):
                raise DocxArchiveError("DOCX compression ratio is unsafe.")
            return {member.filename for member in members}
    except DocxArchiveError:
        raise
    except (
        EOFError,
        OSError,
        ValueError,
        struct.error,
        zipfile.BadZipFile,
        zipfile.LargeZipFile,
    ) as exc:
        raise DocxArchiveError("DOCX archive is malformed.") from exc
