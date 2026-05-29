#!/bin/bash
# VaultMate Native Host Wrapper - uses venv Python with all required packages
VENV_PYTHON="/home/kali/.Vaultmate/Application/.venv/bin/python3"
NATIVE_HOST="/home/kali/.Vaultmate/Application/native_host.py"
if [ -f /.flatpak-info ]; then
    exec flatpak-spawn --host "$VENV_PYTHON" "$NATIVE_HOST" "$@"
else
    exec "$VENV_PYTHON" "$NATIVE_HOST" "$@"
fi
