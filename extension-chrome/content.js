// content.js - Runs in the MAIN world to intercept WebAuthn passkeys natively
// Uses Object.defineProperty on the CredentialsContainer prototype for reliable
// override in Brave/Chrome where direct assignment is silently ignored.

(function() {
    if (!navigator.credentials) return;

    // Get the prototype so we override at the right level
    const credProto = Object.getPrototypeOf(navigator.credentials);
    const originalCreate = credProto.create ? credProto.create.bind(navigator.credentials) : navigator.credentials.create.bind(navigator.credentials);
    const originalGet = credProto.get ? credProto.get.bind(navigator.credentials) : navigator.credentials.get.bind(navigator.credentials);

    // Helpers to convert ArrayBuffer to Base64url and back
    function bufferToBase64url(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
    }

    function base64urlToBuffer(base64url) {
        const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
        const binary = atob(base64.padEnd(base64.length + (4 - base64.length % 4) % 4, '='));
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }
        return bytes.buffer;
    }

    function serializeBuffer(val) {
        if (!val) return null;
        if (val.byteLength !== undefined) {
            let bytes;
            if (val.buffer) {
                bytes = new Uint8Array(val.buffer, val.byteOffset, val.byteLength);
            } else {
                bytes = new Uint8Array(val);
            }
            return { __type: 'ArrayBuffer', data: bufferToBase64url(bytes) };
        }
        return null;
    }

    function serializeOptions(options) {
        if (!options) return options;
        const res = {};
        if (options.publicKey) {
            res.publicKey = {};
            const pk = options.publicKey;
            if (pk.rp) res.publicKey.rp = { id: pk.rp.id, name: pk.rp.name };
            if (pk.user) res.publicKey.user = { id: serializeBuffer(pk.user.id), name: pk.user.name, displayName: pk.user.displayName };
            if (pk.challenge) res.publicKey.challenge = serializeBuffer(pk.challenge);
            if (pk.rpId) res.publicKey.rpId = pk.rpId;
            if (pk.allowCredentials) res.publicKey.allowCredentials = pk.allowCredentials.map(c => ({ type: c.type, id: serializeBuffer(c.id) }));
            if (pk.userVerification) res.publicKey.userVerification = pk.userVerification;
            if (pk.timeout) res.publicKey.timeout = pk.timeout;
        }
        return res;
    }

    function deserializeResponse(val) {
        if (!val) return val;
        if (typeof val === 'object') {
            if (val.__type === 'ArrayBuffer') {
                return base64urlToBuffer(val.data);
            }
            if (Array.isArray(val)) {
                return val.map(deserializeResponse);
            }
            const res = {};
            for (let k in val) {
                res[k] = deserializeResponse(val[k]);
            }
            return res;
        }
        return val;
    }

    function sendToBridge(operation, options) {
        return new Promise((resolve, reject) => {
            const requestId = Math.random().toString(36).substring(7);
            
            const listener = (event) => {
                if (event.source !== window) return;
                if (event.data && event.data.type === "VAULTMATE_PASSKEY_RESPONSE" && event.data.requestId === requestId) {
                    window.removeEventListener("message", listener);
                    if (!event.data.response || event.data.response.error) {
                        reject(new Error(event.data.response ? event.data.response.error : "VaultMate bridge disconnected"));
                    } else {
                        resolve(event.data.response);
                    }
                }
            };
            
            window.addEventListener("message", listener);
            window.postMessage({
                type: "VAULTMATE_PASSKEY_REQUEST",
                requestId: requestId,
                operation: operation,
                options: serializeOptions(options)
            }, "*");
        });
    }

    const vaultmateCreate = async function(options) {
        if (!options || !options.publicKey) {
            return originalCreate(options);
        }
        console.log("[VaultMate] Intercepting credentials.create for:", options.publicKey.rp && options.publicKey.rp.id);
        try {
            const response = await sendToBridge("passkey_create", options);
            const parsed = deserializeResponse(response.credential);
            parsed.authenticatorAttachment = "platform";
            parsed.getClientExtensionResults = function() { return {}; };
            
            if (parsed.response) {
                if (parsed.response.authenticatorData) {
                    parsed.response.getAuthenticatorData = function() { return parsed.response.authenticatorData; };
                } else {
                    parsed.response.getAuthenticatorData = function() { return parsed.response.attestationObject; };
                }
                parsed.response.getPublicKey = function() { return null; };
                parsed.response.getPublicKeyAlgorithm = function() { return -7; };
                parsed.response.getTransports = function() { return ["internal"]; };
            }
            return parsed;
        } catch (err) {
            console.error("[VaultMate] Passkey create error:", err.message);
            return originalCreate(options);
        }
    };

    const vaultmateGet = async function(options) {
        if (!options || !options.publicKey) {
            // Pass through conditional UI / non-passkey calls
            return originalGet(options);
        }
        console.log("[VaultMate] Intercepting credentials.get for:", options.publicKey.rpId);
        try {
            const response = await sendToBridge("passkey_get", options);
            const parsed = deserializeResponse(response.credential);
            parsed.authenticatorAttachment = "platform";
            parsed.getClientExtensionResults = function() { return {}; };
            
            if (parsed.response) {
                parsed.response.getAuthenticatorData = function() { return parsed.response.authenticatorData; };
                parsed.response.getUserHandle = function() { return parsed.response.userHandle || null; };
            }
            return parsed;
        } catch (err) {
            console.error("[VaultMate] Passkey get error:", err.message);
            return originalGet(options);
        }
    };

    // Override at prototype level — direct assignment is silently ignored in Brave/Chrome
    try {
        Object.defineProperty(credProto, 'create', {
            value: vaultmateCreate,
            writable: true,
            configurable: true
        });
        Object.defineProperty(credProto, 'get', {
            value: vaultmateGet,
            writable: true,
            configurable: true
        });
        console.log("[VaultMate] WebAuthn override installed on CredentialsContainer prototype");
    } catch (e) {
        // Fallback to direct assignment
        console.warn("[VaultMate] Prototype override failed, using direct assignment:", e.message);
        navigator.credentials.create = vaultmateCreate;
        navigator.credentials.get = vaultmateGet;
    }
})();
