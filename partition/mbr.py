"""
MBR (Master Boot Record) partition table parser.

MBR is at sector 0. Signature 0x55AA at bytes 510-511.
4 primary partitions at offsets 0x1BE, 0x1CE, 0x1DE, 0x1EE (16 bytes each).

Partition types relevant to us:
  0x83 = Linux filesystem (likely ext2/3/4)
  0x8E = Linux LVM
"""
import struct
from typing import List, Optional

MBR_SIGNATURE = 0xAA55
MBR_SIZE = 512

# Partition entry format (16 bytes)
_PART_FMT  = "<BBBBBBBBII"
_PART_SIZE = struct.calcsize(_PART_FMT)  # 16

# Partition types that might be ext4
LINUX_FS_TYPES = {0x83, 0x8E}


def parse_mbr(data: bytes) -> Optional[List[dict]]:
    """
    Parse MBR partition table.
    Returns list of partition dicts, or None if not a valid MBR.
    """
    if len(data) < MBR_SIZE:
        return None
    sig = struct.unpack_from("<H", data, 510)[0]
    if sig != MBR_SIGNATURE:
        return None

    partitions = []
    for i in range(4):
        offset = 0x1BE + i * _PART_SIZE
        (
            status, chs_start_0, chs_start_1, chs_start_2,
            part_type, chs_end_0, chs_end_1, chs_end_2,
            lba_start, lba_count,
        ) = struct.unpack_from(_PART_FMT, data, offset)

        if lba_count == 0:
            continue

        partitions.append({
            "index":      i + 1,
            "type":       part_type,
            "type_str":   _type_str(part_type),
            "lba_start":  lba_start,
            "lba_count":  lba_count,
            "byte_start": lba_start * 512,
            "size_bytes": lba_count * 512,
            "bootable":   status == 0x80,
            "is_linux":   part_type in LINUX_FS_TYPES,
        })

    return partitions


def _type_str(t: int) -> str:
    types = {
        0x00: "Empty",
        0x05: "Extended",
        0x0F: "Extended (LBA)",
        0x82: "Linux Swap",
        0x83: "Linux Filesystem",
        0x8E: "Linux LVM",
        0xEE: "GPT Protective",
        0xEF: "EFI System",
        0xFB: "VMware VMFS",
    }
    return types.get(t, f"Unknown (0x{t:02X})")
