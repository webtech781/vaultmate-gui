# -*- mode: python ; coding: utf-8 -*-
# VaultMate PyInstaller Spec File
# Builds a single-folder distribution on all platforms.
# Run: pyinstaller vaultmate.spec

import sys
import os

block_cipher = None

# Collect all customtkinter theme/image assets
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

customtkinter_datas = collect_data_files('customtkinter')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # Application icons & images
        ('icon16.png',  '.'),
        ('icon32.png',  '.'),
        ('icon48.png',  '.'),
        ('icon128.png', '.'),
        ('icon256.png', '.'),
        ('icon_app.png', '.'),
        ('vaultmate.ico', '.'),
        # CustomTkinter theme assets
        *customtkinter_datas,
    ],
    hiddenimports=[
        'customtkinter',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'cryptography.hazmat.primitives.hashes',
        'bcrypt',
        'keyring',
        'keyring.backends',
        'keyring.backends.SecretService',
        'keyring.backends.Windows',
        'keyring.backends.macOS',
        'keyring.backends.fail',
        'fido2',
        'fido2.cose',
        'fido2.webauthn',
        'fido2.cbor',
        'cbor2',
        'dotenv',
        'sqlite3',
        'database',
        'crypto_utils',
        'extension_installer',
        'browser_profiles',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'test_fido', 'test_fido2', 'test_native', 'test_native2', 'test_passkey',
        'matplotlib', 'numpy', 'pandas', 'scipy', 'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VaultMate',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # No terminal window on Windows/macOS
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Windows: embed the icon into the .exe
    icon='vaultmate.ico' if sys.platform == 'win32' else (
        'icon256.png' if sys.platform != 'darwin' else 'icon256.png'
    ),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VaultMate',
)

# macOS: wrap everything in a .app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='VaultMate.app',
        icon='icon256.png',
        bundle_identifier='com.vaultmate.app',
        info_plist={
            'CFBundleName': 'VaultMate',
            'CFBundleDisplayName': 'VaultMate',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSHighResolutionCapable': True,
            'NSRequiresAquaSystemAppearance': False,  # Enable dark mode
        },
    )
