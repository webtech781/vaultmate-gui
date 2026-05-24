# VaultMate Desktop Application

This directory contains the core VaultMate Password Manager desktop application. It is a secure, cross-platform GUI application built with Python and CustomTkinter, designed to manage your passwords locally without relying on cloud storage.

## Features

- **Offline First**: All data is stored locally in an SQLite database (`vaultmate.db`).
- **OS Keychain Integration**: Automatically unlock your vault using your system's built-in biometrics or PIN (Windows Hello, macOS TouchID, Linux Secret Service).
- **Strong Encryption**: Passwords are mathematically encrypted using `cryptography.fernet` and a key derived from your Master Password using `PBKDF2HMAC`.
- **Modern UI**: A sleek, intuitive interface built with CustomTkinter.

## Prerequisites

- Python 3.8+
- System packages for Tkinter (e.g., `python3-tk` on Linux/Fedora).

## Setup & Installation

1. Create a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```

## Native Messaging (Browser Extension Support)

VaultMate supports acting as a Native Messaging Host for the companion Browser Extension. This allows VaultMate to intercept Passkey requests from your browser!

To enable this:
1. Load the `extension/` folder in Chrome Developer Mode and copy its Extension ID.
2. Open the VaultMate application and log in.
3. Click the **"🧩 Setup Browser Extension"** button on the dashboard.
4. Paste your Extension ID and click Link. The app will automatically handle the cross-platform setup (Windows Registry, macOS/Linux config files) behind the scenes!
