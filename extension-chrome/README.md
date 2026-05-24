# VaultMate Browser Extension

This directory contains the companion Manifest V3 browser extension for VaultMate. It allows VaultMate to bridge the gap between your desktop application and your web browser seamlessly.

## Overview

Modern websites use a web standard called **WebAuthn** to request "Passkeys". Because desktop applications do not run inside the browser, they cannot intercept these requests natively. 

This extension solves that problem utilizing a unified Manifest V3 bridging architecture:
1. **The Interceptor (`content.js`)**: Runs directly in the website's `MAIN` world to completely override `navigator.credentials.create` and `navigator.credentials.get` transparently.
2. **The Bridge (`bridge.js`)**: Runs in the browser's secure `ISOLATED` world. It listens for `window.postMessage` events from `content.js` and securely forwards the passkey data payload out of the page boundary.
3. **The Service Worker (`background.js`)**: Receives the bridged data and forwards it to the VaultMate Python Native Messaging Host on your desktop for cryptographic signing.

## Installation (Developer Mode)

To use this extension, you must load it into your browser manually:

1. Open Google Chrome, Edge, or Brave and navigate to `chrome://extensions/` (or `about:debugging` in Firefox).
2. Enable **Developer mode**.
3. Click **Load unpacked** (or "Load Temporary Add-on").
4. Select this `extension` directory.
5. If using Chromium, the extension will generate a random ID. **Copy the Extension ID** (e.g., `abcdefghijklmnopqrstuvwxyz123456`).

## Connecting to VaultMate

For this extension to work, your browser needs to know how to communicate with the VaultMate Python app.

1. Take the **Extension ID** you copied (Firefox users skip this step).
2. Open the **VaultMate Application** and log into your vault.
3. On the sidebar, click the **"Browser Integrations"** button.
4. Paste your Extension ID into the box and click **Install**.

The application will handle all the complex cross-platform setup for you, including standard directories and Flatpak sandbox configurations. Once completed, anytime a website asks for a Passkey, this extension will securely forward the request directly to your VaultMate application!
