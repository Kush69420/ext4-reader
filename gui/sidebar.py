"""
Sidebar panel — disk/image selector + volume info + partition list.
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Callable, Optional, List

from gui.theme import (
    BG_DEEP, BG_PANEL, BG_CARD, BG_HOVER, BG_SELECT,
    TEXT_PRI, TEXT_SEC, TEXT_ACCENT, TEXT_GREEN, TEXT_ORANGE, TEXT_RED,
    BORDER, FONT_MAIN, FONT_SMALL, FONT_TITLE, FONT_LARGE, FONT_MONO,
)
from partition import detect_partitions, PartitionEntry


class Sidebar(tk.Frame):
    def __init__(self, parent, on_partition_open: Callable, **kwargs):
        super().__init__(parent, bg=BG_PANEL, **kwargs)
        self._on_partition_open = on_partition_open
        self._stream = None
        self._partitions: List[PartitionEntry] = []
        self._build()

    def _build(self):
        # ── Logo / Title ──
        title_frame = tk.Frame(self, bg=BG_PANEL)
        title_frame.pack(fill="x", padx=14, pady=(16, 4))

        tk.Label(
            title_frame,
            text="⬡  ext4 Reader",
            bg=BG_PANEL,
            fg=TEXT_ACCENT,
            font=FONT_LARGE,
        ).pack(anchor="w")

        tk.Label(
            title_frame,
            text="for Windows",
            bg=BG_PANEL,
            fg=TEXT_SEC,
            font=FONT_SMALL,
        ).pack(anchor="w")

        self._sep()

        # ── Open buttons ──
        btn_frame = tk.Frame(self, bg=BG_PANEL)
        btn_frame.pack(fill="x", padx=12, pady=6)

        self._btn(btn_frame, "📂  Open Image File…", self._open_image).pack(fill="x", pady=2)
        self._btn(btn_frame, "💽  Open Physical Disk…", self._open_disk).pack(fill="x", pady=2)

        self._sep()

        # ── Partition list label ──
        tk.Label(
            self, text="PARTITIONS",
            bg=BG_PANEL, fg=TEXT_SEC,
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w", padx=14, pady=(8, 2))

        # ── Partition listbox ──
        list_frame = tk.Frame(self, bg=BG_PANEL)
        list_frame.pack(fill="both", padx=8, pady=2)

        sb = tk.Scrollbar(list_frame, orient="vertical", bg=BG_PANEL, troughcolor=BG_DEEP,
                          width=8, borderwidth=0, highlightthickness=0)
        self._part_list = tk.Listbox(
            list_frame,
            bg=BG_CARD,
            fg=TEXT_PRI,
            selectbackground=BG_SELECT,
            selectforeground=TEXT_PRI,
            font=FONT_SMALL,
            borderwidth=0,
            highlightthickness=0,
            yscrollcommand=sb.set,
            activestyle="none",
            cursor="hand2",
        )
        sb.config(command=self._part_list.yview)
        self._part_list.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._part_list.bind("<Double-1>", self._on_partition_dclick)
        self._part_list.bind("<Return>", self._on_partition_dclick)

        # ── Open partition button ──
        self._open_part_btn = self._btn(
            self, "⮕  Open Selected Partition", self._open_selected_partition,
            primary=True,
        )
        self._open_part_btn.pack(fill="x", padx=12, pady=4)
        self._open_part_btn.config(state="disabled")

        self._sep()

        # ── Volume info area ──
        tk.Label(
            self, text="VOLUME INFO",
            bg=BG_PANEL, fg=TEXT_SEC,
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w", padx=14, pady=(8, 2))

        self._info_frame = tk.Frame(self, bg=BG_PANEL)
        self._info_frame.pack(fill="x", padx=14, pady=(0, 8))

        self._info_labels = {}

    # ------------------------------------------------------------------ #

    def _sep(self):
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=0, pady=4)

    def _btn(self, parent, text, cmd, primary=False):
        bg  = BG_SELECT if primary else BG_CARD
        afg = "#FFFFFF" if primary else TEXT_PRI
        b = tk.Button(
            parent, text=text, command=cmd,
            bg=bg, fg=afg, activebackground=BG_HOVER,
            activeforeground=TEXT_PRI,
            font=FONT_SMALL, relief="flat",
            bd=0, padx=10, pady=5,
            cursor="hand2",
        )
        b.bind("<Enter>", lambda e: b.config(bg="#2D7DD2" if primary else BG_HOVER))
        b.bind("<Leave>", lambda e: b.config(bg=bg))
        return b

    # ------------------------------------------------------------------ #

    def _open_image(self):
        path = filedialog.askopenfilename(
            title="Open Disk Image",
            filetypes=[
                ("Disk Images", "*.img *.iso *.dd *.raw *.bin *.vhd *.vmdk *.qcow2"),
                ("All files", "*.*"),
            ]
        )
        if path:
            self._load_stream(open(path, "rb"), path)

    def _open_disk(self):
        if sys.platform == "win32":
            self._open_disk_windows()
        else:
            self._open_disk_linux()

    def _open_disk_windows(self):
        # Enumerate \\.\PhysicalDriveN
        drives = []
        for i in range(16):
            path = f"\\\\.\\PhysicalDrive{i}"
            try:
                f = open(path, "rb")
                f.read(1)
                f.seek(0)
                drives.append((f"PhysicalDrive{i}", path))
                f.close()
            except (PermissionError, FileNotFoundError, OSError):
                if i > 3:
                    break
                continue

        if not drives:
            messagebox.showerror(
                "No Drives Found",
                "No physical drives found.\n"
                "Try running as Administrator, or open a disk image instead.",
            )
            return

        win = tk.Toplevel(self)
        win.title("Select Physical Drive")
        win.configure(bg=BG_DEEP)
        win.geometry("360x260")
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="Select a physical disk:", bg=BG_DEEP, fg=TEXT_PRI,
                 font=FONT_TITLE).pack(pady=(14, 4))

        lb = tk.Listbox(win, bg=BG_CARD, fg=TEXT_PRI, selectbackground=BG_SELECT,
                        font=FONT_MAIN, borderwidth=0, highlightthickness=0)
        for name, _ in drives:
            lb.insert("end", name)
        lb.pack(fill="both", expand=True, padx=16, pady=6)

        def confirm():
            sel = lb.curselection()
            if not sel:
                return
            _, path = drives[sel[0]]
            try:
                stream = open(path, "rb")
                self._load_stream(stream, path)
                win.destroy()
            except PermissionError:
                messagebox.showerror("Permission Denied",
                    "Cannot open drive.\nRun as Administrator.")

        tk.Button(win, text="Open", command=confirm,
                  bg=BG_SELECT, fg="#FFF", relief="flat", padx=12, pady=5,
                  font=FONT_MAIN, cursor="hand2").pack(pady=6)

    def _open_disk_linux(self):
        path = filedialog.askopenfilename(
            title="Open Block Device",
            initialdir="/dev",
            filetypes=[("Block Devices", "*"), ("All files", "*.*")],
        )
        if path:
            try:
                self._load_stream(open(path, "rb"), path)
            except PermissionError:
                messagebox.showerror("Permission Denied",
                    f"Cannot open {path}.\nTry: sudo chmod o+r {path}")

    def _load_stream(self, stream, label: str):
        if self._stream:
            try:
                self._stream.close()
            except Exception:
                pass
        self._stream = stream
        self._partitions = []
        self._part_list.delete(0, "end")
        self._open_part_btn.config(state="disabled")
        self._clear_info()

        try:
            parts = detect_partitions(stream)
        except Exception as e:
            messagebox.showerror("Read Error", f"Failed to read partition table:\n{e}")
            return

        self._partitions = parts
        for p in parts:
            color = TEXT_GREEN if p.is_ext4 else TEXT_SEC
            display = f"  {'✓' if p.is_ext4 else '○'}  {p.label}"
            self._part_list.insert("end", display)
            # Color the item
            idx = self._part_list.size() - 1
            self._part_list.itemconfig(idx, fg=color)

        if parts:
            self._open_part_btn.config(state="normal")
            # Auto-select first ext4 partition
            for i, p in enumerate(parts):
                if p.is_ext4:
                    self._part_list.selection_set(i)
                    break
            else:
                self._part_list.selection_set(0)

    def _on_partition_dclick(self, event=None):
        self._open_selected_partition()

    def _open_selected_partition(self):
        sel = self._part_list.curselection()
        if not sel or not self._partitions:
            return
        part = self._partitions[sel[0]]
        if not part.is_ext4:
            if not messagebox.askyesno("Not ext4",
                "This partition was not identified as ext4.\n"
                "Try to open it anyway?"):
                return
        self._on_partition_open(self._stream, part)

    # ------------------------------------------------------------------ #

    def update_volume_info(self, info: dict):
        """Called from app.py after a volume is opened."""
        self._clear_info()
        for i, (k, v) in enumerate(info.items()):
            tk.Label(
                self._info_frame, text=f"{k}:",
                bg=BG_PANEL, fg=TEXT_SEC, font=FONT_SMALL,
                anchor="w",
            ).grid(row=i, column=0, sticky="w", pady=1)
            tk.Label(
                self._info_frame, text=v,
                bg=BG_PANEL, fg=TEXT_PRI, font=FONT_SMALL,
                anchor="w", wraplength=160, justify="left",
            ).grid(row=i, column=1, sticky="w", padx=(6, 0), pady=1)

    def _clear_info(self):
        for w in self._info_frame.winfo_children():
            w.destroy()
