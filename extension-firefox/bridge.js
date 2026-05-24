// bridge.js
// Runs in the ISOLATED world and bridges messages between the MAIN world (content.js) and the background script.

// 1. Inject content.js into the MAIN world
const script = document.createElement('script');
script.src = chrome.runtime.getURL('content.js');
(document.head || document.documentElement).appendChild(script);
script.onload = () => script.remove();

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
            // Forward the response back to the MAIN world
            window.postMessage({
                type: "VAULTMATE_PASSKEY_RESPONSE",
                requestId: requestId,
                response: response
            }, "*");
        });
    }
});

// --- 2. Autofill Logic (Runs in ISOLATED world with DOM access) ---
function attemptAutofill() {
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    if (passwordInputs.length > 0) {
        chrome.runtime.sendMessage({ action: "autofill_request", url: window.location.href }, (response) => {
            if (response && response.status === "success" && response.credentials.length > 0) {
                const cred = response.credentials[0];
                
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
