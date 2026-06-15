"""
Ext4Volume — main reader class tying all components together.

Usage:
    with open("disk.img", "rb") as f:
        vol = Ext4Volume(f, partition_offset_bytes=0)
        entries = vol.list_dir(vol.ROOT_INODE)
        data = vol.read_file(inode_num)
"""
import struct
from typing import IO, Iterator, List, Optional, BinaryIO

from .superblock import Superblock
from .block_group import BlockGroupDescriptor
from .inode import Inode, FileType
from .extent import collect_blocks, iter_extents
from .directory import DirEntry, parse_dir_block

ROOT_INODE = 2
SUPERBLOCK_OFFSET = 1024  # always 1024 bytes from partition start


class Ext4Volume:
    def __init__(self, stream: BinaryIO, partition_offset: int = 0):
        """
        stream: readable binary stream (file or device)
        partition_offset: byte offset to start of ext4 partition within stream
        """
        self.stream = stream
        self.partition_offset = partition_offset
        self._parse_superblock()
        self._parse_block_groups()

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _seek(self, byte_offset: int) -> None:
        self.stream.seek(self.partition_offset + byte_offset)

    def _read(self, n: int) -> bytes:
        data = self.stream.read(n)
        if len(data) < n:
            # Pad with zeros on short reads (sparse images, end of device, etc.)
            data += b"\x00" * (n - len(data))
        return data

    def _read_block(self, block_num: int) -> bytes:
        self._seek(block_num * self.block_size)
        return self._read(self.block_size)

    def _read_blocks(self, block_nums: List[int]) -> bytes:
        out = bytearray()
        for bn in block_nums:
            if bn == 0:
                out += b"\x00" * self.block_size  # sparse hole
            else:
                out += self._read_block(bn)
        return bytes(out)

    # ------------------------------------------------------------------ #
    #  Superblock                                                          #
    # ------------------------------------------------------------------ #

    def _parse_superblock(self) -> None:
        self._seek(SUPERBLOCK_OFFSET)
        raw = self._read(1024)
        self.sb = Superblock.parse(raw)
        self.block_size = self.sb.block_size

    # ------------------------------------------------------------------ #
    #  Block Group Descriptors                                             #
    # ------------------------------------------------------------------ #

    def _parse_block_groups(self) -> None:
        # BGD table starts at the first block after the superblock block
        # For 1K block size: block 0 is boot, block 1 is superblock, block 2 is BGD
        # For 4K block size: block 0 contains superblock, block 1 is BGD
        if self.block_size == 1024:
            bgd_start_block = 2
        else:
            bgd_start_block = 1

        num_groups = (
            (self.sb.blocks_count + self.sb.blocks_per_group - 1)
            // self.sb.blocks_per_group
        )

        self.block_groups: List[BlockGroupDescriptor] = []
        desc_size = self.sb.desc_size

        for i in range(num_groups):
            byte_offset = bgd_start_block * self.block_size + i * desc_size
            self._seek(byte_offset)
            raw = self._read(desc_size)
            bgd = BlockGroupDescriptor.parse(raw, desc_size)
            self.block_groups.append(bgd)

    # ------------------------------------------------------------------ #
    #  Inode access                                                        #
    # ------------------------------------------------------------------ #

    def read_inode(self, inode_num: int) -> Inode:
        """Read and parse inode by number (1-based)."""
        if inode_num < 1:
            raise ValueError(f"Invalid inode number: {inode_num}")
        group_idx = (inode_num - 1) // self.sb.inodes_per_group
        local_idx  = (inode_num - 1) %  self.sb.inodes_per_group
        bgd = self.block_groups[group_idx]
        byte_offset = bgd.inode_table * self.block_size + local_idx * self.sb.inode_size
        self._seek(byte_offset)
        raw = self._read(self.sb.inode_size)
        return Inode.parse(raw)

    # ------------------------------------------------------------------ #
    #  Block iteration                                                     #
    # ------------------------------------------------------------------ #

    def _iter_inode_blocks(self, inode: Inode) -> Iterator[bytes]:
        """Yield each data block of an inode."""
        if inode.uses_extents:
            block_list = collect_blocks(inode.block_data, self._read_block)
            for bn in block_list:
                if bn == 0:
                    yield b"\x00" * self.block_size
                else:
                    yield self._read_block(bn)
        else:
            # Old-style block map (12 direct + 1 indirect + 1 double + 1 triple)
            yield from self._iter_blockmap_blocks(inode)

    def _iter_blockmap_blocks(self, inode: Inode) -> Iterator[bytes]:
        """Legacy indirect block map traversal."""
        ptrs = struct.unpack_from("<15I", inode.block_data)
        ptr_size = self.block_size // 4
        num_blocks = (inode.size + self.block_size - 1) // self.block_size

        yielded = 0

        # Direct blocks
        for i in range(12):
            if yielded >= num_blocks:
                return
            bn = ptrs[i]
            if bn == 0:
                yield b"\x00" * self.block_size
            else:
                yield self._read_block(bn)
            yielded += 1

        # Single indirect
        if yielded < num_blocks and ptrs[12]:
            indirect = self._read_block(ptrs[12])
            for i in range(ptr_size):
                if yielded >= num_blocks:
                    break
                bn = struct.unpack_from("<I", indirect, i * 4)[0]
                if bn == 0:
                    yield b"\x00" * self.block_size
                else:
                    yield self._read_block(bn)
                yielded += 1

        # Double indirect
        if yielded < num_blocks and ptrs[13]:
            dbl = self._read_block(ptrs[13])
            for i in range(ptr_size):
                if yielded >= num_blocks:
                    break
                bn1 = struct.unpack_from("<I", dbl, i * 4)[0]
                if not bn1:
                    continue
                indirect = self._read_block(bn1)
                for j in range(ptr_size):
                    if yielded >= num_blocks:
                        break
                    bn = struct.unpack_from("<I", indirect, j * 4)[0]
                    if bn == 0:
                        yield b"\x00" * self.block_size
                    else:
                        yield self._read_block(bn)
                    yielded += 1

        # Triple indirect (rarely needed but let's be complete)
        if yielded < num_blocks and ptrs[14]:
            tpl = self._read_block(ptrs[14])
            for i in range(ptr_size):
                if yielded >= num_blocks:
                    break
                bn2 = struct.unpack_from("<I", tpl, i * 4)[0]
                if not bn2:
                    continue
                dbl = self._read_block(bn2)
                for j in range(ptr_size):
                    if yielded >= num_blocks:
                        break
                    bn1 = struct.unpack_from("<I", dbl, j * 4)[0]
                    if not bn1:
                        continue
                    indirect = self._read_block(bn1)
                    for k in range(ptr_size):
                        if yielded >= num_blocks:
                            break
                        bn = struct.unpack_from("<I", indirect, k * 4)[0]
                        if bn == 0:
                            yield b"\x00" * self.block_size
                        else:
                            yield self._read_block(bn)
                        yielded += 1

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def list_dir(self, inode_num: int) -> List[DirEntry]:
        """Return list of directory entries for the given inode."""
        inode = self.read_inode(inode_num)
        if not inode.is_dir:
            raise ValueError(f"Inode {inode_num} is not a directory")
        entries = []
        for block_data in self._iter_inode_blocks(inode):
            for entry in parse_dir_block(block_data, self.sb.has_filetype):
                entries.append(entry)
        return entries

    def read_file_data(self, inode_num: int, max_bytes: Optional[int] = None) -> bytes:
        """Read and return file contents for the given inode."""
        inode = self.read_inode(inode_num)
        if inode.is_dir:
            raise ValueError(f"Inode {inode_num} is a directory")

        # Inline data (tiny files stored inside the inode itself)
        if inode.flags & 0x10000000:  # EXT4_INLINE_DATA_FL
            return inode.block_data[:inode.size]

        buf = bytearray()
        limit = max_bytes if max_bytes is not None else inode.size
        for block_data in self._iter_inode_blocks(inode):
            remaining = limit - len(buf)
            if remaining <= 0:
                break
            buf += block_data[:remaining]

        return bytes(buf[:inode.size] if max_bytes is None else buf)

    def read_symlink(self, inode_num: int) -> str:
        """Return the target of a symlink."""
        inode = self.read_inode(inode_num)
        # Short symlinks are stored directly in block_data
        if inode.size <= 60:
            return inode.block_data[:inode.size].decode("utf-8", errors="replace").rstrip("\x00")
        data = self.read_file_data(inode_num)
        return data.decode("utf-8", errors="replace")

    def walk(self, inode_num: int = ROOT_INODE, path: str = "/") -> Iterator:
        """
        Recursively walk the directory tree.
        Yields (path, DirEntry, Inode) tuples.
        """
        try:
            entries = self.list_dir(inode_num)
        except Exception:
            return
        for entry in entries:
            if not entry.is_valid:
                continue
            child_path = path.rstrip("/") + "/" + entry.name
            try:
                child_inode = self.read_inode(entry.inode)
            except Exception:
                continue
            yield child_path, entry, child_inode
            if child_inode.is_dir:
                yield from self.walk(entry.inode, child_path)

    @property
    def info(self) -> dict:
        """Return a dict of volume metadata for display."""
        return {
            "Volume Name":    self.sb.volume_name or "(none)",
            "UUID":           self.sb.uuid_str,
            "Block Size":     f"{self.block_size} bytes",
            "Total Blocks":   f"{self.sb.blocks_count:,}",
            "Free Blocks":    f"{self.sb.free_blocks_count:,}",
            "Total Inodes":   f"{self.sb.inodes_count:,}",
            "Free Inodes":    f"{self.sb.free_inodes_count:,}",
            "State":          self.sb.state_str,
            "Last Mounted":   self.sb.last_mounted or "(none)",
            "64-bit":         "Yes" if self.sb.is_64bit else "No",
            "Extents":        "Yes" if self.sb.has_extents else "No",
        }
