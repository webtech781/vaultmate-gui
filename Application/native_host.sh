#!/bin/bash
# VaultMate Native Host Wrapper
# Uses the venv Python that has all required packages (cryptography, etc.)
VENV_PYTHON="/home/krishna/vaultmate-gui/Application/.venv/bin/python3"
NATIVE_HOST="/home/krishna/vaultmate-gui/Application/native_host.py"

if [ -f /.flatpak-info ]; then
    exec flatpak-spawn --host "$VENV_PYTHON" "$NATIVE_HOST" "$@"
else
    exec "$VENV_PYTHON" "$NATIVE_HOST" "$@"
fi
