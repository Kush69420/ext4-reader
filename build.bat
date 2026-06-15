@echo off
REM Build ext4 Reader into a standalone Windows .exe using PyInstaller
REM Run this script on Windows with Python + PyInstaller installed.
REM   pip install pyinstaller
REM   build.bat

echo Building ext4 Reader...

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "ext4Reader" ^
    --icon NONE ^
    --add-data "ext4;ext4" ^
    --add-data "partition;partition" ^
    --add-data "gui;gui" ^
    main.py

echo.
echo Done! Executable is in: dist\ext4Reader.exe
echo NOTE: Run as Administrator to access physical drives.
pause
