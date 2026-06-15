# ext4 Reader for Windows

A pure-Python ext4 filesystem explorer that runs on **Windows** (and Linux) with **zero runtime dependencies** beyond a standard Python installation.

## Features

- 📂 **Open disk images** — `.img`, `.dd`, `.raw`, `.bin`, `.iso`, and more
- 💽 **Open physical drives** on Windows (`\\.\PhysicalDriveN`, requires Admin)
- 🗂️ **Auto-detect partitions** — MBR and GPT supported
- ✅ **ext4 validation** — automatically identifies ext4 partitions by magic number
- 📁 **Browse directory tree** — lazy-loaded, handles arbitrarily deep trees
- 📄 **Extract files** — single file or bulk extract with background thread
- 🔗 **Symlink display** — shows link targets
- 🔍 **File properties** — permissions, UID/GID, timestamps, inode number
- 🌑 **Dark theme** — GitHub-style dark UI

## What's Supported

| ext4 Feature | Status |
|---|---|
| Extent tree (extents) | ✅ Full support incl. multi-level |
| Legacy block maps | ✅ Direct + single/double/triple indirect |
| 64-bit block groups | ✅ |
| Inline data | ✅ |
| Symlinks (short + long) | ✅ |
| MBR partition table | ✅ |
| GPT partition table | ✅ |
| Bare image (no partition table) | ✅ |
| htree / dir_index dirs | ✅ (linear scan, no htree index needed) |

## Running on Linux (test/dev)

```bash
# Requires python3-tk
sudo apt install python3-tk   # Debian/Ubuntu
python3 main.py
```

## Building for Windows

On a Windows machine with Python 3.10+ installed:

```bat
pip install pyinstaller
build.bat
```

Output: `dist\ext4Reader.exe` — a single portable executable.

> **Note**: Opening physical drives requires running as Administrator.
> Opening disk image files works without admin.

## Usage

1. Launch `ext4Reader.exe`
2. Click **Open Image File…** to open a `.img` / `.dd` disk image, OR
3. Click **Open Physical Disk…** (Admin required) to select a drive
4. Partitions are listed — ext4 ones are highlighted in green with ✓
5. Double-click or click **Open Selected Partition**
6. Browse the directory tree on the left
7. Click files in the right panel — use **Extract…** to copy them out

## Project Structure

```
ext4 reader/
├── main.py             Entry point
├── ext4/
│   ├── superblock.py   Superblock parser
│   ├── block_group.py  Block Group Descriptor
│   ├── inode.py        Inode parser
│   ├── extent.py       Extent tree traversal
│   ├── directory.py    Directory entry parser
│   └── volume.py       Main Ext4Volume class
├── partition/
│   ├── mbr.py          MBR partition table
│   ├── gpt.py          GPT partition table
│   └── detector.py     Auto-detect + ext4 validation
├── gui/
│   ├── theme.py        Dark theme + ttk styles
│   ├── app.py          Main window
│   ├── sidebar.py      Disk selector + volume info
│   ├── tree_panel.py   Directory tree widget
│   └── file_panel.py   File list + extract
├── requirements.txt    No runtime deps!
└── build.bat           Windows PyInstaller build
```

## License

MIT
