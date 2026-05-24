# VaultMate Desktop Application

This directory contains the core VaultMate Password Manager desktop application. It is a secure, cross-platform GUI application built with Python and CustomTkinter, designed to manage your passwords and cryptographic passkeys locally without relying on cloud storage.

## Features

- **Offline First**: All data is stored locally in an SQLite database (`vaultmate.db`).
- **OS Keychain Integration**: Automatically unlock your vault using your system's built-in biometrics or PIN (Windows Hello, macOS TouchID, Linux Secret Service).
- **Strong Encryption**: Passwords and Passkey data are mathematically encrypted using `cryptography.fernet` and a key derived from your Master Password using `PBKDF2HMAC`.
- **Modern UI**: A sleek, intuitive interface built with CustomTkinter that now supports Web Passwords, App Passwords, and Passkeys seamlessly on one dashboard.

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

VaultMate acts as a Native Messaging Host for the companion Browser Extension. This enables the browser to forward WebAuthn Passkey challenges directly to this local Python application, where they are cryptographically signed using your Master Password.

To enable this:
1. Load the `extension/` folder in Chrome or Firefox Developer Mode.
2. If using Chrome, copy the generated Extension ID.
3. Open the VaultMate application and log in.
4. Click the **"Browser Integrations"** button on the sidebar.
5. Paste your Extension ID (if using Chrome) and click Install. The app will automatically handle the cross-platform setup (Windows Registry, macOS/Linux config files, and Flatpak sandbox directories) behind the scenes!
