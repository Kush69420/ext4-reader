"""
Directory tree panel — left pane showing the folder hierarchy.
"""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from gui.theme import (
    BG_DEEP, BG_CARD, BG_PANEL, BG_SELECT, BORDER,
    TEXT_PRI, TEXT_SEC, TEXT_ACCENT,
    FONT_MAIN, FONT_SMALL, FONT_TITLE,
)

# Sentinel for lazy-load placeholder
_PLACEHOLDER = "__placeholder__"


class TreePanel(tk.Frame):
    def __init__(self, parent, on_dir_select: Callable, **kwargs):
        super().__init__(parent, bg=BG_DEEP, **kwargs)
        self._on_dir_select = on_dir_select
        self._volume = None
        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=BG_PANEL, height=32)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(
            hdr, text="  Directory Tree",
            bg=BG_PANEL, fg=TEXT_SEC,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=6, pady=6)

        # Tree + scrollbar
        container = tk.Frame(self, bg=BG_DEEP)
        container.pack(fill="both", expand=True)

        vsb = ttk.Scrollbar(container, orient="vertical",
                             style="Ext4.Vertical.TScrollbar")
        hsb = ttk.Scrollbar(container, orient="horizontal",
                             style="Ext4.Horizontal.TScrollbar")

        self.tree = ttk.Treeview(
            container,
            style="Ext4.Treeview",
            show="tree",
            selectmode="browse",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
        )
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        hsb.pack(side="bottom", fill="x")
        vsb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.bind("<<TreeviewOpen>>", self._on_open)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def load_volume(self, volume) -> None:
        """Initialize the tree with the root directory."""
        self._volume = volume
        self.tree.delete(*self.tree.get_children())

        # Root node
        root_id = self.tree.insert(
            "", "end",
            text="  📁  /",
            values=("2",),   # inode 2 = root
            open=False,
        )
        # Add placeholder so expand arrow shows
        self.tree.insert(root_id, "end", text=_PLACEHOLDER, values=("",))

    def clear(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self._volume = None

    # ------------------------------------------------------------------ #

    def _on_open(self, event):
        """Lazy-load children when a node is expanded."""
        node = self.tree.focus()
        children = self.tree.get_children(node)

        if len(children) == 1:
            placeholder_text = self.tree.item(children[0], "text")
            if placeholder_text == _PLACEHOLDER:
                self.tree.delete(children[0])
                self._populate(node)

    def _populate(self, node: str) -> None:
        """Read directory contents and insert subdirectories."""
        if self._volume is None:
            return
        values = self.tree.item(node, "values")
        if not values:
            return
        inode_num = int(values[0]) if values[0] else 2

        try:
            entries = self._volume.list_dir(inode_num)
        except Exception as e:
            self.tree.insert(node, "end", text=f"  ⚠ {e}", values=("",))
            return

        dirs = sorted(
            [e for e in entries if e.file_type.name == "DIR" and e.is_valid],
            key=lambda e: e.name.lower(),
        )

        if not dirs:
            # Empty dir — no children to add
            return

        for entry in dirs:
            child_id = self.tree.insert(
                node, "end",
                text=f"  📁  {entry.name}",
                values=(str(entry.inode),),
            )
            # Check if this subdir has further children
            try:
                sub_entries = self._volume.list_dir(entry.inode)
                has_dirs = any(
                    e.file_type.name == "DIR" and e.is_valid
                    for e in sub_entries
                )
                if has_dirs:
                    self.tree.insert(child_id, "end", text=_PLACEHOLDER, values=("",))
            except Exception:
                pass

    def _on_select(self, event):
        node = self.tree.focus()
        if not node:
            return
        values = self.tree.item(node, "values")
        if not values or not values[0]:
            return
        inode_num = int(values[0])
        if self._on_dir_select:
            self._on_dir_select(inode_num)
