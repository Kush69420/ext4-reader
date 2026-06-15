"""
File list panel — right pane showing files in the current directory.
"""
import datetime
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Optional

from gui.theme import (
    BG_DEEP, BG_CARD, BG_PANEL, BG_HOVER, BG_SELECT, BORDER,
    TEXT_PRI, TEXT_SEC, TEXT_ACCENT, TEXT_GREEN, TEXT_ORANGE, TEXT_RED,
    FONT_MAIN, FONT_SMALL, FONT_TITLE, FONT_MONO,
)
from ext4.inode import FileType
from ext4.directory import DirEntry


def _fmt_size(n: int) -> str:
    for unit, divisor in [("TB", 2**40), ("GB", 2**30), ("MB", 2**20), ("KB", 2**10)]:
        if n >= divisor:
            return f"{n / divisor:.1f} {unit}"
    return f"{n} B"


def _fmt_time(ts: int) -> str:
    try:
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "—"


# File-type icons
_FT_ICONS = {
    "FILE":     "📄",
    "DIR":      "📁",
    "SYMLINK":  "🔗",
    "SOCKET":   "🔌",
    "BLOCKDEV": "💾",
    "CHARDEV":  "⌨",
    "FIFO":     "⇌",
    "UNKNOWN":  "❓",
}

_COLS = ("Name", "Size", "Modified", "Permissions", "UID", "GID")
_COL_WIDTHS = (280, 80, 160, 110, 50, 50)


class FilePanel(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_DEEP, **kwargs)
        self._volume = None
        self._current_inode: Optional[int] = None
        self._entries: List[tuple] = []  # (entry, inode_obj)
        self._build()

    def _build(self):
        # ── Toolbar ──
        toolbar = tk.Frame(self, bg=BG_PANEL, height=36)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        self._path_var = tk.StringVar(value="/")
        tk.Label(
            toolbar, textvariable=self._path_var,
            bg=BG_PANEL, fg=TEXT_ACCENT,
            font=FONT_MONO, anchor="w",
        ).pack(side="left", padx=10, pady=6)

        self._extract_btn = self._mk_btn(
            toolbar, "⬇  Extract…", self._extract_selected
        )
        self._extract_btn.pack(side="right", padx=6, pady=4)
        self._extract_btn.config(state="disabled")

        self._extract_all_btn = self._mk_btn(
            toolbar, "⬇  Extract All", self._extract_all
        )
        self._extract_all_btn.pack(side="right", padx=2, pady=4)
        self._extract_all_btn.config(state="disabled")

        # ── Separator ──
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # ── File list ──
        container = tk.Frame(self, bg=BG_DEEP)
        container.pack(fill="both", expand=True)

        vsb = ttk.Scrollbar(container, orient="vertical",
                             style="Ext4.Vertical.TScrollbar")
        hsb = ttk.Scrollbar(container, orient="horizontal",
                             style="Ext4.Horizontal.TScrollbar")

        self.tree = ttk.Treeview(
            container,
            style="Ext4.Treeview",
            columns=_COLS,
            show="headings",
            selectmode="extended",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
        )
        for col, width in zip(_COLS, _COL_WIDTHS):
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=width, minwidth=40, anchor="w")

        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        hsb.pack(side="bottom", fill="x")
        vsb.pack(side="right",  fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._on_dclick)

        # ── Status bar ──
        self._status_var = tk.StringVar(value="No filesystem loaded.")
        status = tk.Frame(self, bg=BG_PANEL, height=24)
        status.pack(fill="x", side="bottom")
        status.pack_propagate(False)
        tk.Label(
            status, textvariable=self._status_var,
            bg=BG_PANEL, fg=TEXT_SEC,
            font=FONT_SMALL, anchor="w",
        ).pack(side="left", padx=10, pady=3)

        # ── Properties popup ──
        self._prop_popup: Optional[tk.Toplevel] = None

    # ------------------------------------------------------------------ #

    def _mk_btn(self, parent, text, cmd):
        b = tk.Button(
            parent, text=text, command=cmd,
            bg=BG_CARD, fg=TEXT_PRI,
            activebackground=BG_HOVER, activeforeground=TEXT_PRI,
            font=FONT_SMALL, relief="flat", bd=0,
            padx=8, pady=3, cursor="hand2",
        )
        b.bind("<Enter>", lambda e: b.config(bg=BG_HOVER))
        b.bind("<Leave>", lambda e: b.config(bg=BG_CARD))
        return b

    # ------------------------------------------------------------------ #

    def set_volume(self, volume) -> None:
        self._volume = volume
        self._extract_all_btn.config(state="normal")

    def load_directory(self, inode_num: int, path: str = "/") -> None:
        """Populate file list from a directory inode."""
        if self._volume is None:
            return

        self._current_inode = inode_num
        self._path_var.set(path)
        self.tree.delete(*self.tree.get_children())
        self._entries = []
        self._extract_btn.config(state="disabled")

        try:
            dir_entries = self._volume.list_dir(inode_num)
        except Exception as e:
            self._status_var.set(f"Error reading directory: {e}")
            return

        # Sort: dirs first, then files, alphabetically
        dir_entries = sorted(
            dir_entries,
            key=lambda e: (0 if e.file_type.name == "DIR" else 1, e.name.lower()),
        )

        rows_inserted = 0
        for entry in dir_entries:
            if not entry.is_valid:
                continue
            try:
                inode = self._volume.read_inode(entry.inode)
            except Exception:
                inode = None

            icon = _FT_ICONS.get(entry.file_type.name, "❓")
            size_str = _fmt_size(inode.size) if inode else "—"
            mtime_str = _fmt_time(inode.mtime) if inode else "—"
            mode_str = inode.mode_str if inode else "—"
            uid = str(inode.uid) if inode else "—"
            gid = str(inode.gid) if inode else "—"

            name_display = f"{icon}  {entry.name}"

            iid = self.tree.insert(
                "", "end",
                values=(name_display, size_str, mtime_str, mode_str, uid, gid),
            )
            self._entries.append((entry, inode, iid))
            rows_inserted += 1

        self._status_var.set(
            f"{rows_inserted} item{'s' if rows_inserted != 1 else ''}  ·  {path}"
        )

    def clear(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self._entries = []
        self._current_inode = None
        self._path_var.set("/")
        self._status_var.set("No filesystem loaded.")
        self._extract_btn.config(state="disabled")
        self._extract_all_btn.config(state="disabled")

    # ------------------------------------------------------------------ #

    def _on_select(self, event):
        sel = self.tree.selection()
        self._extract_btn.config(
            state="normal" if sel else "disabled"
        )

    def _on_dclick(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        for entry, inode, stored_iid in self._entries:
            if stored_iid == iid:
                if inode and inode.is_file:
                    self._show_properties(entry, inode)
                return

    # ------------------------------------------------------------------ #

    def _sort_by(self, col: str):
        """Simple column sort."""
        items = [(self.tree.set(iid, col), iid)
                 for iid in self.tree.get_children("")]
        items.sort(key=lambda x: x[0].lower())
        for i, (_, iid) in enumerate(items):
            self.tree.move(iid, "", i)

    # ------------------------------------------------------------------ #

    def _selected_entries(self):
        sel = self.tree.selection()
        result = []
        for entry, inode, stored_iid in self._entries:
            if stored_iid in sel:
                result.append((entry, inode))
        return result

    def _extract_selected(self):
        selected = self._selected_entries()
        if not selected:
            return
        if len(selected) == 1 and selected[0][1] and selected[0][1].is_file:
            entry, inode = selected[0]
            dest = filedialog.asksaveasfilename(
                title="Save File As",
                initialfile=entry.name,
            )
            if dest:
                self._extract_files([(entry, inode)], os.path.dirname(dest),
                                    single_name=os.path.basename(dest))
        else:
            dest_dir = filedialog.askdirectory(title="Extract To…")
            if dest_dir:
                self._extract_files(selected, dest_dir)

    def _extract_all(self):
        dest_dir = filedialog.askdirectory(title="Extract All Files To…")
        if not dest_dir:
            return
        all_items = [(e, ino) for e, ino, _ in self._entries
                     if e.is_valid and ino and ino.is_file]
        self._extract_files(all_items, dest_dir)

    def _extract_files(self, items, dest_dir: str, single_name: str = None):
        """Extract files in a background thread to avoid freezing the GUI."""
        def _worker():
            errors = []
            for i, (entry, inode) in enumerate(items):
                try:
                    if inode is None or not inode.is_file:
                        continue
                    fname = single_name if single_name and len(items) == 1 else entry.name
                    dest_path = os.path.join(dest_dir, fname)
                    data = self._volume.read_file_data(entry.inode)
                    with open(dest_path, "wb") as f:
                        f.write(data)
                    self._status_var.set(
                        f"Extracting {i+1}/{len(items)}: {entry.name}…"
                    )
                except Exception as e:
                    errors.append(f"{entry.name}: {e}")

            if errors:
                messagebox.showerror("Extraction Errors",
                    "\n".join(errors[:10]) +
                    (f"\n…and {len(errors)-10} more." if len(errors) > 10 else ""))
            else:
                self._status_var.set(
                    f"✓ Extracted {len(items)} file(s) to {dest_dir}"
                )

        threading.Thread(target=_worker, daemon=True).start()

    # ------------------------------------------------------------------ #

    def _show_properties(self, entry: DirEntry, inode):
        """Show a properties popup for the selected file."""
        if self._prop_popup and self._prop_popup.winfo_exists():
            self._prop_popup.destroy()

        win = tk.Toplevel(self)
        win.title(f"Properties — {entry.name}")
        win.configure(bg=BG_DEEP)
        win.geometry("380x340")
        win.resizable(False, False)
        self._prop_popup = win

        tk.Label(win, text=f"📄  {entry.name}", bg=BG_DEEP, fg=TEXT_ACCENT,
                 font=FONT_TITLE).pack(pady=(16, 4), padx=16, anchor="w")

        tk.Frame(win, bg=BORDER, height=1).pack(fill="x")

        grid = tk.Frame(win, bg=BG_DEEP)
        grid.pack(fill="both", expand=True, padx=16, pady=10)

        def row(label, value, r):
            tk.Label(grid, text=label + ":", bg=BG_DEEP, fg=TEXT_SEC,
                     font=FONT_SMALL, anchor="e", width=14).grid(
                         row=r, column=0, sticky="e", pady=2)
            tk.Label(grid, text=value, bg=BG_DEEP, fg=TEXT_PRI,
                     font=FONT_MONO, anchor="w").grid(
                         row=r, column=1, sticky="w", padx=8, pady=2)

        row("Inode",       str(entry.inode), 0)
        row("Size",        _fmt_size(inode.size), 1)
        row("Permissions", inode.mode_str, 2)
        row("UID / GID",   f"{inode.uid} / {inode.gid}", 3)
        row("Modified",    _fmt_time(inode.mtime), 4)
        row("Accessed",    _fmt_time(inode.atime), 5)
        row("Changed",     _fmt_time(inode.ctime), 6)
        if inode.crtime:
            row("Created", _fmt_time(inode.crtime), 7)
        row("Hard Links",  str(inode.links_count), 8)

        tk.Button(
            win, text="Close", command=win.destroy,
            bg=BG_CARD, fg=TEXT_PRI, relief="flat",
            padx=12, pady=4, font=FONT_SMALL, cursor="hand2",
        ).pack(pady=8)
