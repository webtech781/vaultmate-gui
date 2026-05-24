// bridge.js
// Runs in the ISOLATED world and bridges messages between the MAIN world (content.js) and the background script.

// 1. (Content.js is now injected natively by Manifest V3 in the MAIN world to prevent race conditions)

// 2. Listen for messages from the injected MAIN world script
window.addEventListener("message", (event) => {
    // We only accept messages from ourselves
    if (event.source !== window) return;

    if (event.data && event.data.type === "VAULTMATE_PASSKEY_REQUEST") {
        const requestId = event.data.requestId;
        
        // Forward the request to the background script
        chrome.runtime.sendMessage({
            action: "intercept_passkey",
            operation: event.data.operation,
            options: event.data.options,
            url: window.location.href
        }, (response) => {
            // Check for messaging errors (e.g. background script crashed or native host failed)
            if (chrome.runtime.lastError) {
                console.error("VaultMate bridge error:", chrome.runtime.lastError.message);
                window.postMessage({
                    type: "VAULTMATE_PASSKEY_RESPONSE",
                    requestId: requestId,
                    response: { error: chrome.runtime.lastError.message }
                }, "*");
                return;
            }
            // Forward the response back to the MAIN world
            window.postMessage({
                type: "VAULTMATE_PASSKEY_RESPONSE",
                requestId: requestId,
                response: response || { error: "No response from VaultMate host" }
            }, "*");
        });
    }
});

// --- 2. Autofill Logic (Runs in ISOLATED world with DOM access) ---

// Fires native input/change events so React/Vue/Angular sites detect value changes
function setNativeValue(el, value) {
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    nativeInputValueSetter.call(el, value);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
}

function attemptAutofill() {
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    if (passwordInputs.length > 0) {
        chrome.runtime.sendMessage({ action: "autofill_request", url: window.location.href }, (response) => {
            if (chrome.runtime.lastError) return;
            if (response && response.status === "success" && response.credentials && response.credentials.length > 0) {
                const cred = response.credentials[0];
                
                passwordInputs.forEach(passInput => {
                    setNativeValue(passInput, cred.password);
                    const form = passInput.closest('form');
                    if (form) {
                        const userInputs = form.querySelectorAll('input[type="text"], input[type="email"]');
                        if (userInputs.length > 0) {
                            setNativeValue(userInputs[0], cred.username);
                        }
                    }
                });
            }
        });
    }
}

setTimeout(attemptAutofill, 1000);

// --- 3. Auto-Save Logic ---
function captureAndSave(formOrElement) {
    const container = (formOrElement && formOrElement.closest) ? (formOrElement.closest('form') || document) : document;
    
    const passwordInputs = container.querySelectorAll('input[type="password"]');
    if (passwordInputs.length === 0) return;
    
    const passwordInput = passwordInputs[passwordInputs.length - 1];
    
    if (passwordInput && passwordInput.value && passwordInput.value.length >= 3) {
        let username = "";
        const userInputs = container.querySelectorAll('input[type="text"], input[type="email"]');
        if (userInputs.length > 0) {
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

document.addEventListener('submit', (e) => {
    captureAndSave(e.target);
}, true);

document.addEventListener('click', (e) => {
    if (e.target.tagName === 'BUTTON' || (e.target.tagName === 'INPUT' && (e.target.type === 'submit' || e.target.type === 'button'))) {
        captureAndSave(e.target);
    }
}, true);

document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.target.tagName === 'INPUT' && e.target.type === 'password') {
        captureAndSave(e.target);
    }
}, true);
