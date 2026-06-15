"""
Block Group Descriptor parser.

Supports both 32-byte (classic) and 64-byte (64bit feature) descriptors.
Reference: https://ext4.wiki.kernel.org/index.php/Ext4_Disk_Layout#Block_Group_Descriptors
"""
import struct
from dataclasses import dataclass

# 32-byte descriptor
# 32-byte block group descriptor
# Fields: bb_lo, ib_lo, it_lo, free_blocks_lo, free_inodes_lo,
#         used_dirs_lo, flags, exclude_bitmap_lo, bb_csum, ib_csum,
#         itable_unused_lo, checksum
_BGD32_FMT = "<IIIHHHHIHHHh"
_BGD32_SIZE = struct.calcsize(_BGD32_FMT)  # 32 bytes

# 64-byte descriptor — only the extra 32 bytes (hi words)
_BGD64_EXTRA_FMT = "<IIIHHIH"
# (bg_block_bitmap_hi, bg_inode_bitmap_hi, bg_inode_table_hi,
#  bg_free_blocks_count_hi, bg_free_inodes_count_hi,
#  bg_used_dirs_count_hi, bg_itable_unused_hi)
_BGD64_EXTRA_SIZE = struct.calcsize(_BGD64_EXTRA_FMT)


@dataclass
class BlockGroupDescriptor:
    block_bitmap:        int   # block number of block usage bitmap
    inode_bitmap:        int   # block number of inode usage bitmap
    inode_table:         int   # block number of inode table
    free_blocks_count:   int
    free_inodes_count:   int
    used_dirs_count:     int
    flags:               int
    itable_unused:       int
    checksum:            int

    @classmethod
    def parse(cls, data: bytes, desc_size: int = 32) -> "BlockGroupDescriptor":
        if len(data) < desc_size:
            raise ValueError(f"BGD data too short: {len(data)} < {desc_size}")

        (
            bb_lo, ib_lo, it_lo,
            free_blocks_lo, free_inodes_lo,
            used_dirs_lo, flags,
            exclude_bitmap_lo,
            block_bitmap_csum_lo,
            inode_bitmap_csum_lo,
            itable_unused_lo,
            checksum,
        ) = struct.unpack_from(_BGD32_FMT, data, 0)

        block_bitmap = bb_lo
        inode_bitmap = ib_lo
        inode_table  = it_lo
        free_blocks  = free_blocks_lo
        free_inodes  = free_inodes_lo
        used_dirs    = used_dirs_lo
        itable_unused = itable_unused_lo

        if desc_size >= 64:
            (
                bb_hi, ib_hi, it_hi,
                free_blocks_hi, free_inodes_hi,
                used_dirs_hi, itable_unused_hi,
            ) = struct.unpack_from(_BGD64_EXTRA_FMT, data, 32)
            block_bitmap |= bb_hi << 32
            inode_bitmap |= ib_hi << 32
            inode_table  |= it_hi << 32
            free_blocks  |= free_blocks_hi << 16
            free_inodes  |= free_inodes_hi << 16
            used_dirs    |= used_dirs_hi << 16
            itable_unused |= itable_unused_hi << 16

        return cls(
            block_bitmap=block_bitmap,
            inode_bitmap=inode_bitmap,
            inode_table=inode_table,
            free_blocks_count=free_blocks,
            free_inodes_count=free_inodes,
            used_dirs_count=used_dirs,
            flags=flags,
            itable_unused=itable_unused,
            checksum=checksum,
        )
