"""
ext4 Reader — Entry point.
"""
import sys
import os

# Ensure package root is on sys.path when run as a script
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from gui.app import App


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
