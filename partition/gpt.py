"""
GPT (GUID Partition Table) parser.

GPT Header is at LBA 1. Partition entries start at LBA 2 by default.
Each partition has a 16-byte GUID type.

Reference: https://en.wikipedia.org/wiki/GUID_Partition_Table
"""
import struct
import uuid
from typing import List, Optional

GPT_HEADER_SIGNATURE = b"EFI PART"
GPT_HEADER_OFFSET = 512  # LBA 1

# GPT Header (92 bytes minimum)
_HDR_FMT = "<8sIIIIQQQQ16sQIII"
_HDR_SIZE = struct.calcsize(_HDR_FMT)

# Partition entry (128 bytes)
_ENTRY_FMT = "<16s16sQQQ72s"
_ENTRY_SIZE = struct.calcsize(_ENTRY_FMT)  # 128

# Linux Data partition type GUID
LINUX_DATA_GUID = uuid.UUID("0FC63DAF-8483-4772-8E79-3D69D8477DE4")
LINUX_LVM_GUID  = uuid.UUID("E6D6D379-F507-44C2-A23C-238F2A3DF928")
LINUX_SWAP_GUID = uuid.UUID("0657FD6D-A4AB-43C4-84E5-0933C84B4F4F")

LINUX_GUIDS = {LINUX_DATA_GUID, LINUX_LVM_GUID}


def _le_guid(b: bytes) -> uuid.UUID:
    """Parse a mixed-endian GPT GUID (first three fields are LE, last two are BE)."""
    # GPT stores GUIDs with the first three components in little-endian
    p1 = struct.unpack_from("<IHH", b, 0)
    p2 = b[8:16]
    return uuid.UUID(fields=(p1[0], p1[1], p1[2],
                              p2[0], p2[1],
                              int.from_bytes(p2[2:], "big")))


def parse_gpt(stream, sector_size: int = 512) -> Optional[List[dict]]:
    """
    Parse GPT from a binary stream.
    Returns list of partition dicts, or None if not a valid GPT.
    """
    stream.seek(GPT_HEADER_OFFSET)
    hdr_data = stream.read(_HDR_SIZE)
    if len(hdr_data) < _HDR_SIZE:
        return None

    (
        sig, revision, hdr_size, crc32_hdr, reserved,
        my_lba, alternate_lba, first_usable, last_usable,
        disk_guid_raw, part_entry_lba, num_part_entries,
        part_entry_size, crc32_entries,
    ) = struct.unpack_from(_HDR_FMT, hdr_data)

    if sig != GPT_HEADER_SIGNATURE:
        return None

    # Read partition entries
    stream.seek(part_entry_lba * sector_size)
    partitions = []

    for i in range(num_part_entries):
        entry_data = stream.read(part_entry_size)
        if len(entry_data) < _ENTRY_SIZE:
            break

        type_guid_raw, part_guid_raw, lba_start, lba_end, attr_flags, name_raw = \
            struct.unpack_from(_ENTRY_FMT, entry_data)

        if lba_start == 0 and lba_end == 0:
            continue  # unused entry

        type_guid = _le_guid(type_guid_raw)
        part_guid = _le_guid(part_guid_raw)

        name = name_raw.decode("utf-16-le", errors="replace").rstrip("\x00")
        lba_count = lba_end - lba_start + 1

        partitions.append({
            "index":      i + 1,
            "type_guid":  str(type_guid).upper(),
            "part_guid":  str(part_guid).upper(),
            "name":       name,
            "lba_start":  lba_start,
            "lba_count":  lba_count,
            "byte_start": lba_start * sector_size,
            "size_bytes": lba_count * sector_size,
            "is_linux":   type_guid in LINUX_GUIDS,
        })

    return partitions if partitions else None
