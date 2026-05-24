// VaultMate Passkey Injector
(function() {
    if (!window.navigator || !window.navigator.credentials) return;

    const originalCreate = window.navigator.credentials.create.bind(window.navigator.credentials);
    const originalGet = window.navigator.credentials.get.bind(window.navigator.credentials);

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

    // Helper to deeply convert ArrayBuffers in options to Base64url for messaging
    function serializeOptions(options) {
        return JSON.parse(JSON.stringify(options, (key, value) => {
            // Check if it's an arraybuffer or view
            if (value instanceof ArrayBuffer) {
                return { __type: 'ArrayBuffer', data: bufferToBase64url(value) };
            }
            if (ArrayBuffer.isView(value)) {
                return { __type: 'ArrayBuffer', data: bufferToBase64url(value.buffer) };
            }
            return value;
        }));
    }

    // Helper to deeply convert Base64url back to ArrayBuffers in response
    function deserializeResponse(response) {
        return JSON.parse(JSON.stringify(response), (key, value) => {
            if (value && typeof value === 'object' && value.__type === 'ArrayBuffer') {
                return base64urlToBuffer(value.data);
            }
            return value;
        });
    }

    window.navigator.credentials.create = async function(options) {
        if (!options.publicKey) return originalCreate(options);

        return new Promise((resolve, reject) => {
            const requestId = Math.random().toString(36).substring(7);
            
            const handleResponse = (event) => {
                if (event.source !== window || !event.data || event.data.type !== 'VAULTMATE_PASSKEY_CREATE_RES') return;
                if (event.data.requestId !== requestId) return;
                
                window.removeEventListener('message', handleResponse);
                
                if (event.data.error) {
                    console.log("VaultMate Passkey error/fallback:", event.data.error);
                    originalCreate(options).then(resolve).catch(reject);
                } else {
                    const parsed = deserializeResponse(event.data.credential);
                    resolve(parsed);
                }
            };
            
            window.addEventListener('message', handleResponse);
            
            window.postMessage({
                type: 'VAULTMATE_PASSKEY_CREATE_REQ',
                requestId: requestId,
                options: serializeOptions(options)
            }, '*');
        });
    };

    window.navigator.credentials.get = async function(options) {
        if (!options.publicKey) return originalGet(options);

        return new Promise((resolve, reject) => {
            const requestId = Math.random().toString(36).substring(7);
            
            const handleResponse = (event) => {
                if (event.source !== window || !event.data || event.data.type !== 'VAULTMATE_PASSKEY_GET_RES') return;
                if (event.data.requestId !== requestId) return;
                
                window.removeEventListener('message', handleResponse);
                
                if (event.data.error) {
                    console.log("VaultMate Passkey error/fallback:", event.data.error);
                    originalGet(options).then(resolve).catch(reject);
                } else {
                    const parsed = deserializeResponse(event.data.credential);
                    resolve(parsed);
                }
            };
            
            window.addEventListener('message', handleResponse);
            
            window.postMessage({
                type: 'VAULTMATE_PASSKEY_GET_REQ',
                requestId: requestId,
                options: serializeOptions(options)
            }, '*');
        });
    };
})();
