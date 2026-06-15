"""
Partition auto-detector.

Given a binary stream (disk image or physical device):
1. Tries GPT first (more modern)
2. Falls back to MBR
3. Falls back to treating entire stream as bare ext4 (no partition table)
4. Validates each candidate by checking ext4 magic in superblock
"""
import struct
from dataclasses import dataclass
from typing import BinaryIO, List, Optional

from .mbr import parse_mbr
from .gpt import parse_gpt

EXT4_MAGIC        = 0xEF53
SUPERBLOCK_OFFSET = 1024   # from partition start
MAGIC_OFFSET_IN_SB = 56    # offset of s_magic within the superblock


@dataclass
class PartitionEntry:
    index:       int
    label:       str          # human-readable label
    byte_start:  int          # byte offset within stream
    size_bytes:  int
    table_type:  str          # "GPT", "MBR", "RAW"
    is_ext4:     bool = False

    @property
    def size_str(self) -> str:
        n = self.size_bytes
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024 or unit == "TB":
                return f"{n:.1f} {unit}" if unit != "B" else f"{n} {unit}"
            n /= 1024
        return str(self.size_bytes)


def _is_ext4(stream: BinaryIO, byte_start: int) -> bool:
    try:
        stream.seek(byte_start + SUPERBLOCK_OFFSET + MAGIC_OFFSET_IN_SB)
        magic_bytes = stream.read(2)
        if len(magic_bytes) < 2:
            return False
        magic = struct.unpack_from("<H", magic_bytes)[0]
        return magic == EXT4_MAGIC
    except Exception:
        return False


def detect_partitions(stream: BinaryIO, sector_size: int = 512) -> List[PartitionEntry]:
    """
    Detect all partitions in a stream and flag which ones are ext4.
    Returns a list of PartitionEntry objects.
    """
    results: List[PartitionEntry] = []

    # --- Try GPT ---
    gpt_parts = parse_gpt(stream, sector_size)
    if gpt_parts:
        for p in gpt_parts:
            name = p.get("name") or f"Partition {p['index']}"
            label = f"[GPT] {name} ({_size_str(p['size_bytes'])})"
            is_ext4 = _is_ext4(stream, p["byte_start"])
            results.append(PartitionEntry(
                index=p["index"],
                label=label,
                byte_start=p["byte_start"],
                size_bytes=p["size_bytes"],
                table_type="GPT",
                is_ext4=is_ext4,
            ))
        if results:
            return results

    # --- Try MBR ---
    stream.seek(0)
    mbr_data = stream.read(512)
    mbr_parts = parse_mbr(mbr_data)
    if mbr_parts:
        for p in mbr_parts:
            label = f"[MBR #{p['index']}] {p['type_str']} ({_size_str(p['size_bytes'])})"
            is_ext4 = _is_ext4(stream, p["byte_start"])
            results.append(PartitionEntry(
                index=p["index"],
                label=label,
                byte_start=p["byte_start"],
                size_bytes=p["size_bytes"],
                table_type="MBR",
                is_ext4=is_ext4,
            ))
        if results:
            return results

    # --- Bare image (no partition table) ---
    stream.seek(0, 2)
    total_size = stream.tell()
    is_ext4 = _is_ext4(stream, 0)
    results.append(PartitionEntry(
        index=0,
        label=f"[RAW] Bare filesystem ({_size_str(total_size)})",
        byte_start=0,
        size_bytes=total_size,
        table_type="RAW",
        is_ext4=is_ext4,
    ))
    return results


def _size_str(n: int) -> str:
    for unit, divisor in [("TB", 2**40), ("GB", 2**30), ("MB", 2**20), ("KB", 2**10)]:
        if n >= divisor:
            return f"{n / divisor:.1f} {unit}"
    return f"{n} B"
