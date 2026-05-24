// content.js - Intercepts WebAuthn and manages Autofill/Auto-Save

// --- 1. WebAuthn Passkey Interception (Firefox Xray Vision) ---
if (typeof exportFunction !== 'undefined' && typeof cloneInto !== 'undefined' && window.wrappedJSObject && window.wrappedJSObject.navigator && window.wrappedJSObject.navigator.credentials) {
    
    const originalCreate = window.wrappedJSObject.navigator.credentials.create;
    const originalGet = window.wrappedJSObject.navigator.credentials.get;

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

    // Explicitly copy required WebAuthn properties across the Xray boundary
    function serializeOptions(optionsWrapper) {
        if (!optionsWrapper) return optionsWrapper;
        const options = optionsWrapper.wrappedJSObject || optionsWrapper;
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

    // Helper to deeply convert Base64url back to ArrayBuffers in response
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

    function interceptCreate(optionsWrapper) {
        const options = optionsWrapper ? (optionsWrapper.wrappedJSObject || optionsWrapper) : null;
        if (!options || !options.publicKey) {
            return originalCreate.call(window.wrappedJSObject.navigator.credentials, optionsWrapper);
        }

        const promiseFunc = function(resolve, reject) {
            chrome.runtime.sendMessage({
                action: "passkey_create",
                options: serializeOptions(options),
                url: window.location.href
            }, function(response) {
                if (!response || response.error) {
                    const errMsg = response ? response.error : "Native host crashed or disconnected";
                    alert("VaultMate Passkey Error: " + errMsg);
                    console.log("VaultMate Passkey error/fallback:", errMsg);
                    originalCreate.call(window.wrappedJSObject.navigator.credentials, options)
                        .then(resolve)
                        .catch(reject);
                } else {
                    const parsed = deserializeResponse(response.credential);
                    parsed.authenticatorAttachment = "platform";
                    parsed.getClientExtensionResults = function() { return new window.wrappedJSObject.Object(); };
                    
                    if (parsed.response) {
                        if (parsed.response.authenticatorData) {
                            parsed.response.getAuthenticatorData = function() { return parsed.response.authenticatorData; };
                        } else {
                            parsed.response.getAuthenticatorData = function() { return parsed.response.attestationObject; };
                        }
                        parsed.response.getPublicKey = function() { return null; };
                        parsed.response.getPublicKeyAlgorithm = function() { return -7; };
                        parsed.response.getTransports = function() { return new window.wrappedJSObject.Array("internal"); };
                    }
                    
                    // Clone the response into the page's context
                    const cloned = cloneInto(parsed, window.wrappedJSObject, { cloneFunctions: true });
                    resolve(cloned);
                }
            });
        };
        
        return new window.wrappedJSObject.Promise(exportFunction(promiseFunc, window.wrappedJSObject));
    }

    function interceptGet(optionsWrapper) {
        const options = optionsWrapper ? (optionsWrapper.wrappedJSObject || optionsWrapper) : null;
        if (!options || !options.publicKey) {
            return originalGet.call(window.wrappedJSObject.navigator.credentials, optionsWrapper);
        }

        const promiseFunc = function(resolve, reject) {
            chrome.runtime.sendMessage({
                action: "passkey_get",
                options: serializeOptions(options),
                url: window.location.href
            }, function(response) {
                if (!response || response.error) {
                    const errMsg = response ? response.error : "Native host crashed or disconnected";
                    alert("VaultMate Passkey Error: " + errMsg);
                    console.log("VaultMate Passkey error/fallback:", errMsg);
                    originalGet.call(window.wrappedJSObject.navigator.credentials, options)
                        .then(resolve)
                        .catch(reject);
                } else {
                    const parsed = deserializeResponse(response.credential);
                    parsed.authenticatorAttachment = "platform";
                    parsed.getClientExtensionResults = function() { return new window.wrappedJSObject.Object(); };
                    
                    if (parsed.response) {
                        parsed.response.getAuthenticatorData = function() { return parsed.response.authenticatorData; };
                    }
                    
                    // Clone the response into the page's context
                    const cloned = cloneInto(parsed, window.wrappedJSObject, { cloneFunctions: true });
                    resolve(cloned);
                }
            });
        };
        
        return new window.wrappedJSObject.Promise(exportFunction(promiseFunc, window.wrappedJSObject));
    }

    exportFunction(interceptCreate, window.wrappedJSObject.navigator.credentials, {defineAs: "create"});
    exportFunction(interceptGet, window.wrappedJSObject.navigator.credentials, {defineAs: "get"});
}

// --- 2. Autofill Logic ---
function attemptAutofill() {
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    if (passwordInputs.length > 0) {
        chrome.runtime.sendMessage({ action: "autofill_request", url: window.location.href }, (response) => {
            if (response && response.status === "success" && response.credentials.length > 0) {
                const cred = response.credentials[0]; // Take the first match
                
                // Find nearest text/email input for username
                passwordInputs.forEach(passInput => {
                    passInput.value = cred.password;
                    const form = passInput.closest('form');
                    if (form) {
                        const userInputs = form.querySelectorAll('input[type="text"], input[type="email"]');
                        if (userInputs.length > 0) {
                            userInputs[0].value = cred.username;
                        }
                    }
                });
            }
        });
    }
}

// Run autofill after page load
setTimeout(attemptAutofill, 1000);

// --- 3. Auto-Save Logic (Aggressive Capture) ---
function captureAndSave(formOrElement) {
    // Try to find the closest form, or just scan the whole document if no form
    const container = (formOrElement && formOrElement.closest) ? (formOrElement.closest('form') || document) : document;
    
    const passwordInputs = container.querySelectorAll('input[type="password"]');
    if (passwordInputs.length === 0) return;
    
    // Get the last password input (usually the actual password, avoiding hidden honeypots)
    const passwordInput = passwordInputs[passwordInputs.length - 1];
    
    if (passwordInput && passwordInput.value && passwordInput.value.length >= 3) {
        let username = "";
        const userInputs = container.querySelectorAll('input[type="text"], input[type="email"]');
        if (userInputs.length > 0) {
            // Find the text input closest to the password input
            username = userInputs[0].value;
        }
        
        chrome.runtime.sendMessage({
            action: "auto_save",
            url: window.location.href,
            name: document.title || window.location.hostname,
            username: username.trim(),
            password: passwordInput.value
        });
    }
}

// Intercept standard form submissions
document.addEventListener('submit', (e) => {
    captureAndSave(e.target);
}, true);

// Intercept button clicks that look like submit/login
document.addEventListener('click', (e) => {
    if (e.target.tagName === 'BUTTON' || (e.target.tagName === 'INPUT' && (e.target.type === 'submit' || e.target.type === 'button'))) {
        captureAndSave(e.target);
    }
}, true);

// Intercept 'Enter' key on password fields
document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.target.tagName === 'INPUT' && e.target.type === 'password') {
        captureAndSave(e.target);
    }
}, true);
