"""Partition table parsers (MBR + GPT)."""
from .detector import detect_partitions, PartitionEntry

__all__ = ["detect_partitions", "PartitionEntry"]
