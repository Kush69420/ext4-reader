"""
ext4 Extent Tree parser.

Extents replace the old block-map scheme.
Every modern ext4 filesystem uses extents (INCOMPAT_EXTENTS flag).

Tree structure:
  i_block[0..14] (60 bytes) contains the root node.
  Root node header: ext4_extent_header
    If depth == 0: contains leaf nodes (ext4_extent)
    If depth  > 0: contains index nodes (ext4_extent_idx)

Reference: https://ext4.wiki.kernel.org/index.php/Ext4_Disk_Layout#Extent_Tree
"""
import struct
from typing import Iterator, IO, List, Tuple

# Extent header (12 bytes)
_EH_FMT  = "<HHHHI"
_EH_SIZE = struct.calcsize(_EH_FMT)  # 12
EXT4_EXT_MAGIC = 0xF30A

# Leaf extent (12 bytes)
_EXT_FMT  = "<IHHHI"
_EXT_SIZE = struct.calcsize(_EXT_FMT)  # 12

# Index node (12 bytes)
_IDX_FMT  = "<IIIH2x"
_IDX_SIZE = struct.calcsize(_IDX_FMT)  # 12


def _parse_header(data: bytes, offset: int) -> Tuple[int, int, int, int, int]:
    """Returns (magic, entries, max, depth, generation)."""
    return struct.unpack_from(_EH_FMT, data, offset)


def _parse_leaf(data: bytes, offset: int) -> Tuple[int, int, int]:
    """Returns (logical_block, length, physical_block)."""
    ee_block, ee_len, ee_start_hi, ee_start_lo = struct.unpack_from(_EXT_FMT, data, offset)[:4]
    # ee_start is a 48-bit block number
    phys = (ee_start_hi << 32) | ee_start_lo
    # High bit of ee_len signals uninitialized extent (kernel uses it)
    length = ee_len & 0x7FFF
    return ee_block, length, phys


def _parse_index(data: bytes, offset: int) -> Tuple[int, int]:
    """Returns (logical_block, leaf_physical_block)."""
    ei_block, ei_leaf_lo, ei_leaf_hi, _ = struct.unpack_from(_IDX_FMT, data, offset)
    leaf = (ei_leaf_hi << 32) | ei_leaf_lo
    return ei_block, leaf


def iter_extents(block_data: bytes, read_block_fn) -> Iterator[Tuple[int, int, int]]:
    """
    Walk the extent tree rooted at block_data (60 bytes from inode).
    Yields (logical_block, physical_block, length) tuples.

    read_block_fn(block_num) -> bytes
    """
    yield from _walk_node(block_data, 0, read_block_fn)


def _walk_node(data: bytes, offset: int, read_block_fn) -> Iterator[Tuple[int, int, int]]:
    magic, entries, max_entries, depth, generation = _parse_header(data, offset)
    if magic != EXT4_EXT_MAGIC:
        raise ValueError(f"Bad extent magic 0x{magic:04X} at offset {offset}")

    hdr_offset = offset + _EH_SIZE

    if depth == 0:
        # Leaf node — entries are ext4_extent
        for i in range(entries):
            lblock, length, pblock = _parse_leaf(data, hdr_offset + i * _EXT_SIZE)
            yield lblock, pblock, length
    else:
        # Index node — entries are ext4_extent_idx
        for i in range(entries):
            _, leaf_block = _parse_index(data, hdr_offset + i * _IDX_SIZE)
            child_data = read_block_fn(leaf_block)
            yield from _walk_node(child_data, 0, read_block_fn)


def collect_blocks(block_data: bytes, read_block_fn) -> List[int]:
    """
    Return ordered list of physical block numbers for a file.
    Holes (sparse files) are represented as block number 0.
    """
    extents = sorted(iter_extents(block_data, read_block_fn), key=lambda x: x[0])
    if not extents:
        return []

    # Find total logical block span
    last = extents[-1]
    total = last[0] + last[2]
    blocks: List[int] = [0] * total

    for lblock, pblock, length in extents:
        for i in range(length):
            if lblock + i < total:
                blocks[lblock + i] = pblock + i

    return blocks
