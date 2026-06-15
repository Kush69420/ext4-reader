"""
Main application window.
"""
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, BinaryIO

from gui.theme import (
    apply_theme,
    BG_DEEP, BG_PANEL, BG_CARD, BORDER,
    TEXT_PRI, TEXT_SEC, TEXT_ACCENT,
    FONT_MAIN, FONT_TITLE,
)
from gui.sidebar import Sidebar
from gui.tree_panel import TreePanel
from gui.file_panel import FilePanel
from ext4 import Ext4Volume
from partition import PartitionEntry

ROOT_INODE = 2


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ext4 Reader for Windows")
        self.geometry("1200x720")
        self.minsize(900, 560)
        self.configure(bg=BG_DEEP)

        # Apply dark theme
        apply_theme(self)

        # State
        self._volume: Optional[Ext4Volume] = None
        self._current_path: str = "/"
        self._path_stack: list = []   # breadcrumb inode stack
        self._stream: Optional[BinaryIO] = None

        self._build_ui()
        self._center()

    # ------------------------------------------------------------------ #
    #  UI construction                                                     #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        # ── Title bar strip ──
        top_bar = tk.Frame(self, bg=BG_PANEL, height=40)
        top_bar.pack(fill="x", side="top")
        top_bar.pack_propagate(False)

        tk.Label(
            top_bar,
            text="  ⬡  ext4 Reader",
            bg=BG_PANEL, fg=TEXT_ACCENT,
            font=("Segoe UI Semibold", 12),
        ).pack(side="left", padx=6, pady=8)

        self._volume_label = tk.Label(
            top_bar,
            text="",
            bg=BG_PANEL, fg=TEXT_SEC,
            font=FONT_MAIN,
        )
        self._volume_label.pack(side="left", padx=20, pady=8)

        # Help button
        tk.Button(
            top_bar, text="?",
            bg=BG_PANEL, fg=TEXT_SEC,
            relief="flat", bd=0, padx=8, pady=4,
            font=FONT_MAIN, cursor="hand2",
            command=self._show_help,
        ).pack(side="right", padx=8)

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # ── Main body: sidebar | paned content ──
        body = tk.Frame(self, bg=BG_DEEP)
        body.pack(fill="both", expand=True)

        # Sidebar (fixed width)
        self._sidebar = Sidebar(body, on_partition_open=self._open_partition)
        self._sidebar.pack(side="left", fill="y")

        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")

        # PanedWindow for tree + file list
        paned = ttk.PanedWindow(body, orient="horizontal")
        paned.pack(side="left", fill="both", expand=True)

        self._tree_panel = TreePanel(paned, on_dir_select=self._on_dir_select)
        self._file_panel = FilePanel(paned)

        paned.add(self._tree_panel, weight=1)
        paned.add(self._file_panel, weight=3)

        # Set initial sash position after window renders
        self.after(100, lambda: paned.sashpos(0, 260))

    # ------------------------------------------------------------------ #
    #  Event handlers                                                      #
    # ------------------------------------------------------------------ #

    def _open_partition(self, stream: BinaryIO, part: PartitionEntry):
        """Called by sidebar when user selects a partition to open."""
        def _load():
            try:
                volume = Ext4Volume(stream, partition_offset=part.byte_start)
                self.after(0, lambda: self._on_volume_loaded(volume, part))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror(
                    "ext4 Error",
                    f"Failed to mount partition:\n\n{e}\n\n"
                    "Make sure the partition is a valid ext4 filesystem.",
                ))

        self._volume_label.config(text="Loading…")
        threading.Thread(target=_load, daemon=True).start()

    def _on_volume_loaded(self, volume: Ext4Volume, part: PartitionEntry):
        self._volume = volume
        self._current_path = "/"
        self._path_stack = [ROOT_INODE]

        label = part.label
        self._volume_label.config(
            text=f"  Mounted: {label}  ·  Block size: {volume.block_size} B"
        )

        # Update sidebar info
        self._sidebar.update_volume_info(volume.info)

        # Load tree
        self._tree_panel.load_volume(volume)

        # Load root directory in file panel
        self._file_panel.set_volume(volume)
        self._file_panel.load_directory(ROOT_INODE, "/")

    def _on_dir_select(self, inode_num: int):
        """Called when user clicks a directory in the tree."""
        if self._volume is None:
            return
        # Rebuild path from tree selection (simplified — just use inode)
        self._file_panel.load_directory(inode_num, self._inode_path(inode_num))

    def _inode_path(self, inode_num: int) -> str:
        """Reconstruct path for the currently focused tree node.

        Names are stored in values[1] of each node (set by tree_panel.py),
        so we don't need to parse or strip the display text at all.
        """
        tree = self._tree_panel.tree
        node = tree.focus()
        if not node:
            return "/"
        parts = []
        current = node
        while current:
            values = tree.item(current, "values")
            # values = (inode_str, name) — root has empty name
            name = values[1] if len(values) >= 2 else ""
            if name:
                parts.append(name)
            current = tree.parent(current)
        parts.reverse()
        return "/" + "/".join(parts) if parts else "/"

    # ------------------------------------------------------------------ #

    def _show_help(self):
        win = tk.Toplevel(self)
        win.title("About ext4 Reader")
        win.configure(bg=BG_DEEP)
        win.geometry("420x320")
        win.resizable(False, False)
        win.grab_set()

        tk.Label(
            win, text="⬡  ext4 Reader for Windows",
            bg=BG_DEEP, fg=TEXT_ACCENT,
            font=("Segoe UI Semibold", 13),
        ).pack(pady=(20, 6))

        info = (
            "A pure-Python ext4 filesystem explorer.\n\n"
            "Features:\n"
            "  • Open disk images (.img, .dd, .raw, .bin)\n"
            "  • Open physical drives (run as Admin on Windows)\n"
            "  • Auto-detect MBR and GPT partition tables\n"
            "  • Browse ext4 directory trees\n"
            "  • Extract files and folders\n"
            "  • View file metadata and permissions\n\n"
            "Supports: extents, block maps, symlinks,\n"
            "32-bit & 64-bit block groups."
        )

        tk.Label(
            win, text=info,
            bg=BG_DEEP, fg=TEXT_PRI,
            font=FONT_MAIN,
            justify="left",
        ).pack(padx=24, pady=4, anchor="w")

        tk.Button(
            win, text="Close", command=win.destroy,
            bg=BG_CARD, fg=TEXT_PRI, relief="flat",
            padx=12, pady=4, font=FONT_MAIN, cursor="hand2",
        ).pack(pady=10)

    # ------------------------------------------------------------------ #

    def _center(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
