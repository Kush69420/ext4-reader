"""
ext4 Superblock parser.

Reference: https://ext4.wiki.kernel.org/index.php/Ext4_Disk_Layout#The_Super_Block
Superblock is always at byte offset 1024 from the start of the partition.
"""
import struct
from dataclasses import dataclass
from typing import Optional

# Magic number for ext2/3/4
EXT4_MAGIC = 0xEF53

# Superblock format (up to byte 204, sufficient for our purposes)
# Full superblock is 1024 bytes but we only need the first portion
_SB_FMT = "<"
_SB_FMT += "I"   # 0   s_inodes_count
_SB_FMT += "I"   # 4   s_blocks_count_lo
_SB_FMT += "I"   # 8   s_r_blocks_count_lo
_SB_FMT += "I"   # 12  s_free_blocks_count_lo
_SB_FMT += "I"   # 16  s_free_inodes_count
_SB_FMT += "I"   # 20  s_first_data_block
_SB_FMT += "I"   # 24  s_log_block_size
_SB_FMT += "I"   # 28  s_log_cluster_size
_SB_FMT += "I"   # 32  s_blocks_per_group
_SB_FMT += "I"   # 36  s_clusters_per_group
_SB_FMT += "I"   # 40  s_inodes_per_group
_SB_FMT += "I"   # 44  s_mtime
_SB_FMT += "I"   # 48  s_wtime
_SB_FMT += "H"   # 52  s_mnt_count
_SB_FMT += "H"   # 54  s_max_mnt_count
_SB_FMT += "H"   # 56  s_magic
_SB_FMT += "H"   # 58  s_state
_SB_FMT += "H"   # 60  s_errors
_SB_FMT += "H"   # 62  s_minor_rev_level
_SB_FMT += "I"   # 64  s_lastcheck
_SB_FMT += "I"   # 68  s_checkinterval
_SB_FMT += "I"   # 72  s_creator_os
_SB_FMT += "I"   # 76  s_rev_level
_SB_FMT += "H"   # 80  s_def_resuid
_SB_FMT += "H"   # 82  s_def_resgid
# EXT4_DYNAMIC_REV fields start at byte 84
_SB_FMT += "I"   # 84  s_first_ino
_SB_FMT += "H"   # 88  s_inode_size
_SB_FMT += "H"   # 90  s_block_group_nr
_SB_FMT += "I"   # 92  s_feature_compat
_SB_FMT += "I"   # 96  s_feature_incompat
_SB_FMT += "I"   # 100 s_feature_ro_compat
_SB_FMT += "16s" # 104 s_uuid
_SB_FMT += "16s" # 120 s_volume_name
_SB_FMT += "64s" # 136 s_last_mounted
_SB_FMT += "I"   # 200 s_algorithm_usage_bitmap
_SB_FMT += "B"   # 204 s_prealloc_blocks
_SB_FMT += "B"   # 205 s_prealloc_dir_blocks
_SB_FMT += "H"   # 206 s_reserved_gdt_blocks
_SB_FMT += "16s" # 208 s_journal_uuid
_SB_FMT += "I"   # 224 s_journal_inum
_SB_FMT += "I"   # 228 s_journal_dev
_SB_FMT += "I"   # 232 s_last_orphan
_SB_FMT += "16s" # 236 s_hash_seed (4x uint32 but treat as bytes)
_SB_FMT += "B"   # 252 s_def_hash_version
_SB_FMT += "B"   # 253 s_jnl_backup_type
_SB_FMT += "H"   # 254 s_desc_size  (64-bit BG descriptor size)
_SB_FMT += "I"   # 256 s_default_mount_opts
_SB_FMT += "I"   # 260 s_first_meta_bg
_SB_FMT += "I"   # 264 s_mkfs_time
# skip rest for now

_SB_SIZE = struct.calcsize(_SB_FMT)

# Feature flags
FEAT_INCOMPAT_64BIT      = 0x0080
FEAT_INCOMPAT_EXTENTS    = 0x0040
FEAT_INCOMPAT_FILETYPE   = 0x0002
FEAT_INCOMPAT_HTREE      = 0x0004   # dir_index
FEAT_COMPAT_DIR_INDEX    = 0x0020

# State flags
FS_STATE_CLEAN  = 0x0001
FS_STATE_ERRORS = 0x0002


@dataclass
class Superblock:
    inodes_count:         int
    blocks_count:         int
    free_blocks_count:    int
    free_inodes_count:    int
    first_data_block:     int
    block_size:           int          # computed: 1024 << s_log_block_size
    blocks_per_group:     int
    inodes_per_group:     int
    magic:                int
    state:                int
    inode_size:           int
    desc_size:            int          # block group descriptor size (32 or 64)
    feature_incompat:     int
    feature_compat:       int
    feature_ro_compat:    int
    uuid:                 bytes
    volume_name:          str
    last_mounted:         str
    mtime:                int
    wtime:                int
    # derived
    is_64bit:             bool
    has_extents:          bool
    has_filetype:         bool

    @classmethod
    def parse(cls, data: bytes) -> "Superblock":
        if len(data) < _SB_SIZE:
            raise ValueError(f"Superblock data too short: {len(data)} < {_SB_SIZE}")
        fields = struct.unpack_from(_SB_FMT, data)
        (
            inodes_count, blocks_count_lo, r_blocks_lo, free_blocks_lo,
            free_inodes_count, first_data_block, log_block_size, log_cluster_size,
            blocks_per_group, clusters_per_group, inodes_per_group,
            mtime, wtime, mnt_count, max_mnt_count, magic, state, errors,
            minor_rev, lastcheck, checkinterval, creator_os, rev_level,
            def_resuid, def_resgid, first_ino, inode_size, block_group_nr,
            feature_compat, feature_incompat, feature_ro_compat,
            uuid, volume_name_raw, last_mounted_raw,
            algo_usage_bitmap, prealloc_blocks, prealloc_dir_blocks,
            reserved_gdt_blocks, journal_uuid, journal_inum, journal_dev,
            last_orphan, hash_seed, def_hash_version, jnl_backup_type, desc_size,
            default_mount_opts, first_meta_bg, mkfs_time,
        ) = fields

        if magic != EXT4_MAGIC:
            raise ValueError(f"Invalid ext4 magic: 0x{magic:04X} (expected 0x{EXT4_MAGIC:04X})")

        block_size = 1024 << log_block_size

        is_64bit = bool(feature_incompat & FEAT_INCOMPAT_64BIT)
        # desc_size is only valid if 64bit feature is set
        effective_desc_size = desc_size if is_64bit and desc_size >= 64 else 32

        volume_name = volume_name_raw.rstrip(b"\x00").decode("utf-8", errors="replace")
        last_mounted = last_mounted_raw.rstrip(b"\x00").decode("utf-8", errors="replace")

        return cls(
            inodes_count=inodes_count,
            blocks_count=blocks_count_lo,
            free_blocks_count=free_blocks_lo,
            free_inodes_count=free_inodes_count,
            first_data_block=first_data_block,
            block_size=block_size,
            blocks_per_group=blocks_per_group,
            inodes_per_group=inodes_per_group,
            magic=magic,
            state=state,
            inode_size=inode_size,
            desc_size=effective_desc_size,
            feature_incompat=feature_incompat,
            feature_compat=feature_compat,
            feature_ro_compat=feature_ro_compat,
            uuid=uuid,
            volume_name=volume_name,
            last_mounted=last_mounted,
            mtime=mtime,
            wtime=wtime,
            is_64bit=is_64bit,
            has_extents=bool(feature_incompat & FEAT_INCOMPAT_EXTENTS),
            has_filetype=bool(feature_incompat & FEAT_INCOMPAT_FILETYPE),
        )

    @property
    def uuid_str(self) -> str:
        u = self.uuid
        return (f"{u[0:4].hex()}-{u[4:6].hex()}-{u[6:8].hex()}-"
                f"{u[8:10].hex()}-{u[10:16].hex()}")

    @property
    def state_str(self) -> str:
        if self.state == FS_STATE_CLEAN:
            return "Clean"
        elif self.state == FS_STATE_ERRORS:
            return "Errors detected"
        return f"Unknown (0x{self.state:04X})"
