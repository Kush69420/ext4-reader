"""
ext4 Directory Entry parser.

Supports both classic linear dir entries and hash-tree (htree/dir_index) dirs.
We read the raw directory data block-by-block and scan linearly regardless of
whether an htree index exists — this avoids needing to implement the full htree
lookup (which is only needed for performance on very large dirs, not correctness).

Reference:
  https://ext4.wiki.kernel.org/index.php/Ext4_Disk_Layout#Linear_.28Classic.29_Directories
  https://ext4.wiki.kernel.org/index.php/Ext4_Disk_Layout#Hash_Tree_Directories
"""
import struct
from dataclasses import dataclass
from typing import Iterator, List

from .inode import FileType

# Classic directory entry header (8 bytes)
_DIRENT_FMT  = "<IHBb"
_DIRENT_SIZE = struct.calcsize(_DIRENT_FMT)  # 8

# file_type values in dir entries (when INCOMPAT_FILETYPE is set)
_DTYPE_MAP = {
    0: FileType.UNKNOWN,
    1: FileType.FILE,
    2: FileType.DIR,
    3: FileType.CHARDEV,
    4: FileType.BLOCKDEV,
    5: FileType.FIFO,
    6: FileType.SOCKET,
    7: FileType.SYMLINK,
}


@dataclass
class DirEntry:
    inode:     int       # 0 = deleted / unused
    name:      str
    file_type: FileType
    rec_len:   int       # total length of this record (for advancing)

    @property
    def is_valid(self) -> bool:
        return self.inode != 0 and self.name not in ("", ".", "..")

    @property
    def is_dot(self) -> bool:
        return self.name in (".", "..")


def parse_dir_block(data: bytes, has_filetype: bool = True) -> Iterator[DirEntry]:
    """
    Parse all directory entries from a single block of raw directory data.
    """
    offset = 0
    size = len(data)

    while offset < size - _DIRENT_SIZE:
        inode, rec_len, name_len, file_type_raw = struct.unpack_from(_DIRENT_FMT, data, offset)

        if rec_len == 0:
            break   # should not happen, but guard against infinite loop

        name_len = name_len & 0xFF  # ensure positive
        if name_len > 0 and offset + _DIRENT_SIZE + name_len <= size:
            raw_name = data[offset + _DIRENT_SIZE: offset + _DIRENT_SIZE + name_len]
            try:
                name = raw_name.decode("utf-8", errors="replace")
            except Exception:
                name = raw_name.decode("latin-1", errors="replace")

            if has_filetype:
                ftype = _DTYPE_MAP.get(file_type_raw & 0x7F, FileType.UNKNOWN)
            else:
                ftype = FileType.UNKNOWN  # will be resolved from inode later

            yield DirEntry(
                inode=inode,
                name=name,
                file_type=ftype,
                rec_len=rec_len,
            )

        offset += rec_len
