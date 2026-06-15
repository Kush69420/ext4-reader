"""
ext4 Inode parser.

Reference: https://ext4.wiki.kernel.org/index.php/Ext4_Disk_Layout#Inode_Table
"""
import struct
import stat
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional

# Inode struct — first 128 bytes (always present)
_INODE_FMT = "<"
_INODE_FMT += "H"    # 0   i_mode
_INODE_FMT += "H"    # 2   i_uid (lo)
_INODE_FMT += "I"    # 4   i_size_lo
_INODE_FMT += "I"    # 8   i_atime
_INODE_FMT += "I"    # 12  i_ctime
_INODE_FMT += "I"    # 16  i_mtime
_INODE_FMT += "I"    # 20  i_dtime
_INODE_FMT += "H"    # 24  i_gid (lo)
_INODE_FMT += "H"    # 26  i_links_count
_INODE_FMT += "I"    # 28  i_blocks_lo  (512-byte blocks)
_INODE_FMT += "I"    # 32  i_flags
_INODE_FMT += "I"    # 36  i_osd1
_INODE_FMT += "60s"  # 40  i_block[15]  (extent tree or block map)
_INODE_FMT += "I"    # 100 i_generation
_INODE_FMT += "I"    # 104 i_file_acl_lo
_INODE_FMT += "I"    # 108 i_size_high
_INODE_FMT += "I"    # 112 i_obso_faddr
_INODE_FMT += "H"    # 116 l_i_blocks_high
_INODE_FMT += "H"    # 118 l_i_file_acl_high
_INODE_FMT += "H"    # 120 l_i_uid_high
_INODE_FMT += "H"    # 122 l_i_gid_high
_INODE_FMT += "H"    # 124 l_i_checksum_lo
_INODE_FMT += "H"    # 126 l_i_reserved

_INODE_SIZE_BASE = struct.calcsize(_INODE_FMT)  # 128

# Extended inode fields (present when inode_size > 128)
_INODE_EXT_FMT = "<"
_INODE_EXT_FMT += "H"   # 128 i_extra_isize
_INODE_EXT_FMT += "H"   # 130 i_checksum_hi
_INODE_EXT_FMT += "I"   # 132 i_ctime_extra
_INODE_EXT_FMT += "I"   # 136 i_mtime_extra
_INODE_EXT_FMT += "I"   # 140 i_atime_extra
_INODE_EXT_FMT += "I"   # 144 i_crtime
_INODE_EXT_FMT += "I"   # 148 i_crtime_extra
_INODE_EXT_FMT += "I"   # 152 i_version_hi

_INODE_EXT_SIZE = struct.calcsize(_INODE_EXT_FMT)  # 24

# i_flags
INODE_FLAG_EXTENTS   = 0x00080000
INODE_FLAG_INLINE    = 0x10000000

# i_mode type bits
S_IFMT   = 0xF000
S_IFSOCK = 0xC000
S_IFLNK  = 0xA000
S_IFREG  = 0x8000
S_IFBLK  = 0x6000
S_IFDIR  = 0x4000
S_IFCHR  = 0x2000
S_IFIFO  = 0x1000


class FileType(IntEnum):
    UNKNOWN  = 0
    FILE     = 1
    DIR      = 2
    CHARDEV  = 3
    BLOCKDEV = 4
    FIFO     = 5
    SOCKET   = 6
    SYMLINK  = 7

    @classmethod
    def from_mode(cls, mode: int) -> "FileType":
        t = mode & S_IFMT
        mapping = {
            S_IFREG:  cls.FILE,
            S_IFDIR:  cls.DIR,
            S_IFLNK:  cls.SYMLINK,
            S_IFSOCK: cls.SOCKET,
            S_IFBLK:  cls.BLOCKDEV,
            S_IFCHR:  cls.CHARDEV,
            S_IFIFO:  cls.FIFO,
        }
        return mapping.get(t, cls.UNKNOWN)

    @property
    def icon(self) -> str:
        icons = {
            FileType.FILE:     "📄",
            FileType.DIR:      "📁",
            FileType.SYMLINK:  "🔗",
            FileType.SOCKET:   "🔌",
            FileType.BLOCKDEV: "💾",
            FileType.CHARDEV:  "⌨",
            FileType.FIFO:     "⇌",
            FileType.UNKNOWN:  "❓",
        }
        return icons.get(self, "❓")


@dataclass
class Inode:
    mode:           int
    uid:            int
    gid:            int
    size:           int
    atime:          int
    ctime:          int
    mtime:          int
    dtime:          int
    links_count:    int
    flags:          int
    block_data:     bytes   # raw 60 bytes of i_block[] — extent tree or block map
    file_acl:       int
    crtime:         Optional[int]  # creation time (ext4 only, may be None)

    @classmethod
    def parse(cls, data: bytes) -> "Inode":
        if len(data) < _INODE_SIZE_BASE:
            raise ValueError(f"Inode data too short: {len(data)}")
        (
            mode, uid_lo, size_lo, atime, ctime, mtime, dtime,
            gid_lo, links_count, blocks_lo, flags, osd1,
            block_data, generation, file_acl_lo, size_high,
            obso_faddr, blocks_high, file_acl_high,
            uid_high, gid_high, checksum_lo, reserved,
        ) = struct.unpack_from(_INODE_FMT, data, 0)

        uid  = uid_lo  | (uid_high  << 16)
        gid  = gid_lo  | (gid_high  << 16)
        size = size_lo | (size_high << 32)
        file_acl = file_acl_lo | (file_acl_high << 32)

        crtime = None
        if len(data) >= _INODE_SIZE_BASE + _INODE_EXT_SIZE:
            try:
                (
                    extra_isize, checksum_hi,
                    ctime_extra, mtime_extra, atime_extra,
                    crtime_val, crtime_extra_val, version_hi,
                ) = struct.unpack_from(_INODE_EXT_FMT, data, _INODE_SIZE_BASE)
                crtime = crtime_val
            except struct.error:
                pass

        return cls(
            mode=mode,
            uid=uid,
            gid=gid,
            size=size,
            atime=atime,
            ctime=ctime,
            mtime=mtime,
            dtime=dtime,
            links_count=links_count,
            flags=flags,
            block_data=block_data,
            file_acl=file_acl,
            crtime=crtime,
        )

    @property
    def file_type(self) -> FileType:
        return FileType.from_mode(self.mode)

    @property
    def is_dir(self) -> bool:
        return self.file_type == FileType.DIR

    @property
    def is_file(self) -> bool:
        return self.file_type == FileType.FILE

    @property
    def is_symlink(self) -> bool:
        return self.file_type == FileType.SYMLINK

    @property
    def uses_extents(self) -> bool:
        return bool(self.flags & INODE_FLAG_EXTENTS)

    @property
    def mode_str(self) -> str:
        """Human-readable mode string like 'drwxr-xr-x'."""
        return stat.filemode(self.mode)
