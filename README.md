# 🔐 VaultMate — Password & Passkey Manager

> **Offline-first. Encrypted. Browser-integrated. No cloud. No hardware required.**

[![GitHub Release](https://img.shields.io/github/v/release/webtech781/vaultmate-gui?style=for-the-badge&logo=github&color=007AFF)](https://github.com/webtech781/vaultmate-gui/releases/latest)
[![Linux](https://img.shields.io/badge/Linux-x86__64-FCC624?style=for-the-badge&logo=linux&logoColor=black)](https://github.com/webtech781/vaultmate-gui/releases/latest)
[![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D4?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/webtech781/vaultmate-gui/releases/latest)
[![macOS](https://img.shields.io/badge/macOS-12%2B-000000?style=for-the-badge&logo=apple&logoColor=white)](https://github.com/webtech781/vaultmate-gui/releases/latest)
[![Firefox](https://img.shields.io/badge/Firefox-Fully%20Tested%20✅-FF7139?style=for-the-badge&logo=firefox&logoColor=white)](https://github.com/webtech781/vaultmate-gui/tree/main/extension-firefox)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

VaultMate is a powerful, open-source password manager and **software passkey authenticator** that runs entirely on your local machine. It pairs a Python desktop GUI with a browser extension, giving you secure credential autofill and passkey interception directly in your browser — without ever sending your data anywhere.

---

## ⬇️ Download & Install

> **No Python needed. No command line required.** Just download and run.

### 🪟 Windows — One-Click Installer

**[⬇️ Download VaultMate-Setup-windows.exe](https://github.com/webtech781/vaultmate-gui/releases/latest/download/VaultMate-Setup-v1.3.0-windows.exe)**

1. Download `VaultMate-Setup-*.exe`
2. Run it — click **Next → Install → Finish**
3. VaultMate appears on your **Desktop** and **Start Menu** automatically

> Installs to `Program Files`, adds to Add/Remove Programs, creates shortcuts.

### 🍎 macOS — DMG Package

**[⬇️ Download VaultMate-macOS.dmg](https://github.com/webtech781/vaultmate-gui/releases/latest)**

1. Download `VaultMate-*-macOS-*.dmg`
2. Open the `.dmg` file
3. **Drag VaultMate → Applications** (single drag-and-drop, done!)
4. First launch: **Right-click → Open** (bypasses Gatekeeper on unnotarized builds)

### 🐧 Linux — Portable Bundle

**[⬇️ Download VaultMate-linux-x86_64.tar.gz](https://github.com/webtech781/vaultmate-gui/releases/latest)**

```bash
tar -xzf VaultMate-*-linux-x86_64.tar.gz
cd VaultMate && ./VaultMate
```

> **If the app doesn't launch**, install the Tk system library first:
> ```bash
> sudo dnf install python3-tkinter   # Fedora/RHEL
> sudo apt install python3-tk        # Ubuntu/Debian
> ```

---

## ✅ Browser Extension Setup

> [!IMPORTANT]
> **Fully tested and verified on Mozilla Firefox.**
> Firefox is the recommended browser for the best VaultMate experience.

### 🦊 Firefox (Recommended — Fully Tested ✅)

1. Download or clone this repository
2. Open Firefox → `about:debugging#/runtime/this-firefox`
3. Click **"Load Temporary Add-on…"**
4. Navigate to `extension-firefox/` and select `manifest.json`
5. The VaultMate 🔐 icon will appear in your toolbar

> [!TIP]
> For a permanent install (survives browser restarts), package the extension:
> ```bash
> cd extension-firefox
> zip -r VaultMate-firefox.xpi .
> ```
> Then install via `about:addons` → ⚙️ → "Install Add-on From File"

### 🌐 Chrome / Brave / Edge

1. Go to `chrome://extensions/`
2. Enable **Developer Mode** (toggle, top-right)
3. Click **"Load unpacked"** → select the `extension-chrome/` folder
4. Copy the **Extension ID** shown on the card (you'll need it in Step 3 below)

---

## 🔗 Link the Extension to the Desktop App

After loading the extension in your browser:

1. Open **VaultMate** and log in
2. Click **"Browser Integrations"** in the sidebar
3. Click **"Add +"**, select your browser
4. For **Chrome/Brave/Edge**: paste the Extension ID you copied
5. Click **"Install"** — VaultMate auto-registers the Native Messaging Host

> VaultMate will now intercept login forms and passkey prompts in your browser.

---

## 🛡️ Who Is This For?

> [!NOTE]
> ### 💡 No Hardware? No Problem.
>
> Most passkey solutions require a hardware security key (YubiKey, FIDO2 token) or a platform authenticator (Apple Touch ID, Windows Hello). **VaultMate eliminates this requirement entirely.**
>
> VaultMate implements passkeys **100% in software**, meaning:
> - ✅ Works on any Linux machine, even without a fingerprint reader
> - ✅ Works on virtual machines and cloud desktops
> - ✅ Works on older hardware with no biometric sensor
> - ✅ Works in air-gapped or restricted enterprise environments
> - ✅ No YubiKey, no Touch ID, no Windows Hello required
>
> Your passkeys are secured by your **Master Password** and stored encrypted locally.

---

## 🖥️ Use Case: Environments Without Touch ID / Hardware Keys

> [!IMPORTANT]
> ### Bypass the "Touch Your Security Key" Wall
>
> When you encounter a dialog like **"Touch your security key to continue"** on a site like GitHub, the browser is waiting for hardware that may not exist on your machine. This is the exact scenario VaultMate was built to solve.
>
> **VaultMate intercepts the WebAuthn flow at the JavaScript level** and substitutes its own software-based passkey authenticator. The website receives a valid, cryptographically signed WebAuthn response — it never knows the difference.
>
> **Perfect for:**
> - 🐧 Linux desktops without fingerprint readers
> - 🖥️ Virtual machines (VMware, VirtualBox, cloud VMs)
> - 🏢 Enterprise workstations locked down from hardware security keys
> - 💻 Older laptops with no biometric sensors
> - 🧑‍💻 Developers testing WebAuthn flows locally without hardware

---

## 📁 Project Structure

```
vaultmate-gui/
├── Application/               # Core desktop app (Python + CustomTkinter)
│   ├── main.py                # Main GUI application
│   ├── native_host.py         # Native messaging backend (handles WebAuthn)
│   ├── native_host.sh         # Shell launcher for native messaging
│   ├── database.py            # SQLite-based encrypted vault
│   ├── crypto_utils.py        # Encryption & PBKDF2 key derivation
│   ├── browser_profiles.py    # Auto-detects installed browsers & profiles
│   ├── extension_installer.py # Registers the native host automatically
│   ├── vaultmate.spec         # PyInstaller build spec (all platforms)
│   ├── build_linux.sh         # Linux build script → .tar.gz
│   ├── build_macos.sh         # macOS build script → .dmg
│   ├── build_windows.bat      # Windows build script → .zip
│   └── requirements.txt       # Python dependencies
│
├── extension-firefox/         # Firefox extension (MV2, fully tested ✅)
├── extension-chrome/          # Chrome/Brave/Edge extension (MV3)
│
├── .github/workflows/
│   └── release.yml            # GitHub Actions: auto-build & release on tags
│
├── PRD.md                     # Product Requirements Document
├── LICENSE                    # MIT License
└── README.md                  # This file
```

---

## 🔨 Build From Source

If you want to build the executables yourself:

### Prerequisites

- Python 3.10+ with `pip`
- Linux: `python3-tkinter` system package
- macOS: Xcode Command Line Tools + `brew install create-dmg`
- Windows: Python from python.org (not Microsoft Store)

### Build

```bash
# Clone the repo
git clone https://github.com/webtech781/vaultmate-gui.git
cd vaultmate-gui/Application

# Linux
bash build_linux.sh

# macOS
bash build_macos.sh

# Windows (PowerShell or CMD)
build_windows.bat
```

### Automated Releases via GitHub Actions

Push a version tag to trigger a full cross-platform build automatically:

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions will build Linux, Windows, and macOS packages and attach them to a GitHub Release automatically.

---

## 🔑 Features

| Feature | Description |
|---|---|
| 🔐 **Password Autofill** | Detects login forms and fills credentials automatically |
| 🛡️ **Passkey Interception** | Intercepts WebAuthn `navigator.credentials.create/get` calls |
| 💾 **Offline Vault** | All data stored locally in an encrypted SQLite database |
| 🔒 **PBKDF2 Encryption** | Master password derives an AES key via PBKDF2HMAC (100,000 iterations) |
| 🌐 **Cross-Browser** | Works with Firefox, Chrome, Brave, and Edge |
| 🖥️ **Cross-Platform** | Windows, macOS, Linux — pre-built executables, no Python needed |
| 🖥️ **Native Host** | Handles Windows Registry, macOS plist, Linux config, and Flatpak sandboxes |
| 👁️ **Password Visibility Toggle** | Reveal/hide passwords with one click |
| 🔍 **Quick Search** | Instant fuzzy search across all credentials |
| 💻 **No Hardware Required** | Software-based passkeys — no YubiKey or Touch ID needed |

---

## 🛡️ Security Model

- **No cloud sync** — your vault never leaves your machine
- **No telemetry** — zero data collection
- **Encrypted at rest** — SQLite database encrypted with `cryptography.fernet`
- **Key derivation** — your Master Password is processed through `PBKDF2HMAC` with a unique salt; the raw password is never stored
- **Passkeys in software** — WebAuthn private keys are stored encrypted in the vault and used to sign challenges locally via the native host

---

## 🚀 Upcoming Features

- **Encrypted Cloud Sync**: Optionally sync your encrypted vault via Google Drive / Dropbox
- **Firefox Add-on Store**: Publish to AMO (addons.mozilla.org) for permanent installs
- **NSIS Installer for Windows**: Proper Windows installer with Start Menu shortcut

---

## 📄 Documentation

- [Application README](Application/README.md) — Desktop app details and native host setup
- [PRD.md](PRD.md) — Full product requirements, architecture, and threat model

---

## 🛠️ Support & Contributions

Have a bug, question, or feature request? **Open an issue on GitHub.**

Contributions are welcome — please fork, branch, and submit a pull request.

---

## 📄 License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.
