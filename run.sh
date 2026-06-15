#!/usr/bin/env bash
# Quick smoke test — launch the app on Linux for UI testing before Windows deployment.
# Requires: python3 with tkinter  (apt install python3-tk)

cd "$(dirname "$0")"
python3 main.py
