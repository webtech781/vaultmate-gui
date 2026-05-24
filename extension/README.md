# VaultMate Browser Extension

This directory contains the companion browser extension for VaultMate. It allows VaultMate to bridge the gap between your desktop application and your web browser.

## Overview

Modern websites use a web standard called **WebAuthn** to request "Passkeys". Because desktop applications do not run inside the browser, they cannot intercept these requests natively. 

This extension solves that problem by:
1. **Intercepting Requests**: The `content.js` script injects itself into webpages and intercepts calls to `navigator.credentials.get` and `navigator.credentials.create`.
2. **Forwarding to Desktop**: The `background.js` service worker receives the intercepted passkey request and forwards it to the VaultMate desktop application via Chrome's Native Messaging API.

## Installation (Developer Mode)

To use this extension, you must load it into your browser manually:

1. Open Google Chrome (or Microsoft Edge) and navigate to `chrome://extensions/`
2. Enable **Developer mode** (usually a toggle in the top right corner).
3. Click **Load unpacked**.
4. Select this `extension` directory.
5. The extension will appear in your list. **Copy the Extension ID** (e.g., `abcdefghijklmnopqrstuvwxyz123456`).

## Connecting to VaultMate

For this extension to work, your browser needs to know how to communicate with the VaultMate Python app.

1. Take the **Extension ID** you copied.
2. Open the **VaultMate Application** and log into your vault.
3. On the Dashboard, click the **"🧩 Setup Browser Extension"** button.
4. Paste your Extension ID into the box and click **Link**.

The application will handle all the complex cross-platform setup for you. Once completed, anytime a website asks for a Passkey, this extension will securely forward the request directly to your VaultMate application!
