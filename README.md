# VaultMate GUI & Browser Extension Combo (V2)

VaultMate has evolved into a powerful, offline-first password manager with an integrated browser extension, bringing you cross-platform security with built-in Passkey interception!

## 📁 Project Structure

This repository is split into two distinct, interconnected components:

### 1. `Application/`
The core desktop password manager built with Python, CustomTkinter, and SQLite.
- **Offline First**: All data is stored locally in `vaultmate.db`.
- **Bank-Level Encryption**: Passwords are mathematically encrypted via `cryptography.fernet`.
- **OS Biometrics**: Unlocks seamlessly using your Operating System's credentials (macOS Keychain, Windows Hello, etc.).
- **Native Host**: Acts as a secure backend to process requests from the browser extension.

👉 [View Application Documentation](Application/README.md)

### 2. `extension/`
A custom Chrome/Edge browser extension that bridges your web browser with the VaultMate application.
- **Passkey Interception**: Injects a script into websites to intercept WebAuthn Passkey requests.
- **Native Messaging**: Communicates directly with the VaultMate desktop application to fulfill biometric passkey requests from the web.

👉 [View Extension Documentation](extension/README.md)

## 🚀 Quick Start

1. **Install the Application**: Navigate to `Application/`, setup your python virtual environment, and install `requirements.txt`.
2. **Load the Extension**: Navigate to `chrome://extensions/` in your browser, turn on Developer Mode, and Load Unpacked the `extension/` directory.
3. **Link Them**: Copy the loaded Extension ID, paste it into `Application/install_host.sh`, and run the script to link the browser to your VaultMate desktop app!

---

## 🚀 Upcoming Features

- **Encrypted Cloud Sync**: Seamlessly sync your encrypted vault across devices using Google Drive and Dropbox (currently VaultMate is 100% offline for maximum security).

## 🛠️ Support & Contributions

Have a feature request, bug, or question?
👉 Open an issue on GitHub

## 📄 License

This project is licensed under the MIT License. See the LICENSE file for more information.
