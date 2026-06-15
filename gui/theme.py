"""
Theme configuration — dark modern color palette + ttk style setup.
"""
import tkinter as tk
from tkinter import ttk

# ── Palette ────────────────────────────────────────────────────────────── #
BG_DEEP     = "#0D1117"   # deepest background (window)
BG_PANEL    = "#161B22"   # panel / sidebar
BG_CARD     = "#1C2128"   # card / list area
BG_HOVER    = "#21262D"   # hover state
BG_SELECT   = "#1F6FEB"   # selection blue
BG_SELECT2  = "#388BFD"   # lighter selection accent

TEXT_PRI    = "#E6EDF3"   # primary text
TEXT_SEC    = "#8B949E"   # secondary / muted text
TEXT_ACCENT = "#58A6FF"   # hyperlink / accent
TEXT_GREEN  = "#3FB950"   # success / ext4 confirmed
TEXT_ORANGE = "#D29922"   # warning
TEXT_RED    = "#F85149"   # error

BORDER      = "#30363D"   # subtle borders
BORDER_MED  = "#484F58"   # medium emphasis border

FONT_MAIN   = ("Segoe UI", 10)
FONT_MONO   = ("Consolas", 9)
FONT_TITLE  = ("Segoe UI Semibold", 11)
FONT_SMALL  = ("Segoe UI", 9)
FONT_LARGE  = ("Segoe UI", 13, "bold")

# ── ttk Style Setup ────────────────────────────────────────────────────── #

def apply_theme(root: tk.Tk) -> None:
    """Apply dark theme to all ttk widgets."""
    style = ttk.Style(root)
    style.theme_use("clam")

    # ── Treeview (directory tree + file list) ──
    style.configure(
        "Ext4.Treeview",
        background=BG_CARD,
        foreground=TEXT_PRI,
        fieldbackground=BG_CARD,
        rowheight=22,
        font=FONT_MAIN,
        borderwidth=0,
        relief="flat",
    )
    style.configure(
        "Ext4.Treeview.Heading",
        background=BG_PANEL,
        foreground=TEXT_SEC,
        font=FONT_SMALL,
        relief="flat",
        borderwidth=0,
    )
    style.map(
        "Ext4.Treeview",
        background=[("selected", BG_SELECT)],
        foreground=[("selected", TEXT_PRI)],
    )
    style.map(
        "Ext4.Treeview.Heading",
        background=[("active", BG_HOVER)],
    )

    # ── Scrollbar ──
    style.configure(
        "Ext4.Vertical.TScrollbar",
        background=BG_PANEL,
        troughcolor=BG_DEEP,
        bordercolor=BG_PANEL,
        arrowcolor=TEXT_SEC,
        width=10,
    )
    style.map(
        "Ext4.Vertical.TScrollbar",
        background=[("active", BG_HOVER), ("pressed", BG_SELECT)],
    )
    style.configure(
        "Ext4.Horizontal.TScrollbar",
        background=BG_PANEL,
        troughcolor=BG_DEEP,
        bordercolor=BG_PANEL,
        arrowcolor=TEXT_SEC,
        width=10,
    )

    # ── PanedWindow separator ──
    style.configure(
        "TPanedwindow",
        background=BORDER,
    )

    # ── Separator ──
    style.configure(
        "TSeparator",
        background=BORDER,
    )

    # ── Button ──
    style.configure(
        "Ext4.TButton",
        background=BG_CARD,
        foreground=TEXT_PRI,
        font=FONT_MAIN,
        borderwidth=1,
        relief="flat",
        padding=(10, 4),
    )
    style.map(
        "Ext4.TButton",
        background=[("active", BG_HOVER), ("pressed", BG_SELECT)],
        foreground=[("active", TEXT_PRI)],
    )

    # ── Primary Button ──
    style.configure(
        "Primary.TButton",
        background=BG_SELECT,
        foreground="#FFFFFF",
        font=FONT_MAIN,
        borderwidth=0,
        relief="flat",
        padding=(12, 5),
    )
    style.map(
        "Primary.TButton",
        background=[("active", BG_SELECT2), ("pressed", "#1158C7")],
    )

    # ── Combobox ──
    style.configure(
        "Ext4.TCombobox",
        background=BG_CARD,
        foreground=TEXT_PRI,
        fieldbackground=BG_CARD,
        selectbackground=BG_SELECT,
        font=FONT_MAIN,
        arrowcolor=TEXT_SEC,
        bordercolor=BORDER,
    )
    style.map(
        "Ext4.TCombobox",
        fieldbackground=[("readonly", BG_CARD)],
        foreground=[("readonly", TEXT_PRI)],
    )

    # ── Label / Frame defaults ──
    style.configure("TLabel", background=BG_DEEP, foreground=TEXT_PRI, font=FONT_MAIN)
    style.configure("TFrame", background=BG_DEEP)

    # ── Notebook ──
    style.configure(
        "TNotebook",
        background=BG_PANEL,
        borderwidth=0,
    )
    style.configure(
        "TNotebook.Tab",
        background=BG_PANEL,
        foreground=TEXT_SEC,
        font=FONT_SMALL,
        padding=(10, 4),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", BG_CARD)],
        foreground=[("selected", TEXT_PRI)],
    )
