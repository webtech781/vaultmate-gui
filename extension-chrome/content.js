// content.js - Runs in the MAIN world to intercept WebAuthn passkeys natively

(function() {
if (navigator.credentials && navigator.credentials.create) {
    const originalCreate = navigator.credentials.create;
    const originalGet = navigator.credentials.get;

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
                        reject(event.data.response ? event.data.response.error : "Bridge disconnected");
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

    navigator.credentials.create = async function(options) {
        if (!options || !options.publicKey) {
            return originalCreate.call(navigator.credentials, options);
        }

        try {
            const response = await sendToBridge("passkey_create", options);
            const parsed = deserializeResponse(response.credential);
            parsed.authenticatorAttachment = "platform";
            parsed.getClientExtensionResults = function() { return {}; };
            
            if (parsed.response) {
                parsed.response.getAuthenticatorData = function() { return parsed.response.attestationObject; };
                parsed.response.getPublicKey = function() { return null; };
                parsed.response.getPublicKeyAlgorithm = function() { return 0; };
                parsed.response.getTransports = function() { return ["internal"]; };
            }
            return parsed;
        } catch (err) {
            console.log("VaultMate Passkey error/fallback:", err);
            return originalCreate.call(navigator.credentials, options);
        }
    };

    navigator.credentials.get = async function(options) {
        if (!options || !options.publicKey) {
            return originalGet.call(navigator.credentials, options);
        }

        try {
            const response = await sendToBridge("passkey_get", options);
            const parsed = deserializeResponse(response.credential);
            parsed.authenticatorAttachment = "platform";
            parsed.getClientExtensionResults = function() { return {}; };
            
            if (parsed.response) {
                parsed.response.getAuthenticatorData = function() { return parsed.response.authenticatorData; };
            }
            return parsed;
        } catch (err) {
            console.log("VaultMate Passkey error/fallback:", err);
            return originalGet.call(navigator.credentials, options);
        }
    };
}
})();
