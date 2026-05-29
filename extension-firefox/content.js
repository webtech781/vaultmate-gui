// content.js - Intercepts WebAuthn and manages Premium Autofill Picker / Auto-Save

let vaultmateEnabled = true;
let activeConditionalRequest = null;
let activeInputEl = null;

// Fetch local enabled status from storage
chrome.storage.local.get({ enabled: true }, (res) => {
    vaultmateEnabled = res.enabled !== false;
});

// Watch for storage changes in real-time
chrome.storage.onChanged.addListener((changes, area) => {
    if (area === 'local' && changes.enabled) {
        vaultmateEnabled = changes.enabled.newValue !== false;
    }
});

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
        if (!vaultmateEnabled) {
            return originalCreate.call(window.wrappedJSObject.navigator.credentials, optionsWrapper);
        }

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
        if (!vaultmateEnabled) {
            return originalGet.call(window.wrappedJSObject.navigator.credentials, optionsWrapper);
        }

        const options = optionsWrapper ? (optionsWrapper.wrappedJSObject || optionsWrapper) : null;
        if (!options || !options.publicKey) {
            return originalGet.call(window.wrappedJSObject.navigator.credentials, optionsWrapper);
        }

        // Custom conditional WebAuthn interception to allow choosing standard accounts or passkeys from VaultMate
        if (options && options.mediation === 'conditional') {
            const promiseFunc = function(resolve, reject) {
                activeConditionalRequest = {
                    options: serializeOptions(options),
                    resolve: resolve,
                    reject: reject
                };
            };
            return new window.wrappedJSObject.Promise(exportFunction(promiseFunc, window.wrappedJSObject));
        }

        const promiseFunc = function(resolve, reject) {
            chrome.runtime.sendMessage({
                action: "passkey_get",
                options: serializeOptions(options),
                url: window.location.href
            }, function(response) {
                if (!response || response.error) {
                    const errMsg = response ? response.error : "Native host crashed or disconnected";
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

// --- 2. Advanced Autofill Picker & Caching ---

function getCleanServiceName(hostname) {
    if (!hostname) return "Unknown Service";
    let clean = hostname.split(':')[0].toLowerCase();
    const subdomainsToRemove = ['www.', 'm.', 'login.', 'signin.', 'accounts.', 'sso.', 'auth.', 'web.', 'app.'];
    for (const sub of subdomainsToRemove) {
        if (clean.startsWith(sub)) {
            clean = clean.substring(sub.length);
        }
    }
    const parts = clean.split('.');
    let domainName = parts[0];
    const commonTlds = ['com', 'co', 'org', 'net', 'gov', 'edu', 'ac'];
    if (parts.length > 2 && commonTlds.includes(parts[1])) {
        domainName = parts[0];
    } else if (parts.length > 1 && !commonTlds.includes(parts[0])) {
        domainName = parts[0];
    }
    
    const brandMap = {
        'reddit': 'Reddit',
        'github': 'GitHub',
        'google': 'Google',
        'facebook': 'Facebook',
        'twitter': 'Twitter',
        'x': 'X (Twitter)',
        'linkedin': 'LinkedIn',
        'microsoft': 'Microsoft',
        'stackoverflow': 'Stack Overflow',
        'netflix': 'Netflix',
        'amazon': 'Amazon',
        'apple': 'Apple',
        'spotify': 'Spotify',
        'discord': 'Discord',
        'zoom': 'Zoom',
        'dropbox': 'Dropbox',
        'steam': 'Steam',
        'twitch': 'Twitch',
        'slack': 'Slack',
        'figma': 'Figma',
        'gitlab': 'GitLab',
        'bitbucket': 'BitBucket',
        'trello': 'Trello',
        'atlassian': 'Atlassian',
        'adobe': 'Adobe',
        'salesforce': 'Salesforce',
        'paypal': 'PayPal',
        'stripe': 'Stripe'
    };
    
    if (brandMap[domainName]) {
        return brandMap[domainName];
    }
    return domainName.charAt(0).toUpperCase() + domainName.slice(1);
}

function getCleanLoginUrl(urlStr) {
    try {
        const parsed = new URL(urlStr);
        const path = parsed.pathname.toLowerCase();
        const isLoginPath = path.includes('login') || 
                            path.includes('signin') || 
                            path.includes('signup') || 
                            path.includes('register') || 
                            path.includes('oauth') || 
                            path.includes('auth') || 
                            path.includes('session');
        if (isLoginPath) {
            return parsed.origin + parsed.pathname;
        } else {
            return parsed.origin;
        }
    } catch (e) {
        return urlStr;
    }
}

function queryAllShadow(selector, root = document) {
    let elements = Array.from(root.querySelectorAll(selector));
    const walk = (node) => {
        if (node.shadowRoot) {
            elements = elements.concat(Array.from(node.shadowRoot.querySelectorAll(selector)));
            node.shadowRoot.querySelectorAll('*').forEach(walk);
        }
    };
    root.querySelectorAll('*').forEach(walk);
    return elements;
}

function findUsernameInput(passwordInput) {
    if (!passwordInput) return null;

    // Helper to check if an element is visible in the viewport/DOM
    const isVisible = (el) => {
        if (!el) return false;
        const style = window.getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
        if (el.offsetWidth === 0 || el.offsetHeight === 0) return false;
        return true;
    };

    // Helper to score how likely an input is to be the username input
    const getUsernameScore = (el) => {
        if (!isVisible(el)) return -100;
        if (el.disabled || el.readOnly) return -100;

        let score = 0;
        const type = (el.type || '').toLowerCase();
        const name = (el.name || '').toLowerCase();
        const id = (el.id || '').toLowerCase();
        const placeholder = (el.placeholder || '').toLowerCase();
        const autocomplete = (el.getAttribute('autocomplete') || '').toLowerCase();

        // Must be a valid input type for username
        if (type === 'text' || type === 'email' || type === 'username' || type === '') {
            score += 10;
        } else {
            return -100;
        }

        // Email type is very strong indicator
        if (type === 'email') score += 15;

        // Specific keywords in name, id, autocomplete, or placeholder
        if (name.includes('username') || name.includes('email') || name.includes('login') || name.includes('usr')) score += 30;
        if (id.includes('username') || id.includes('email') || id.includes('login') || id.includes('usr')) score += 30;
        if (autocomplete.includes('username') || autocomplete.includes('email')) score += 40;
        if (placeholder.includes('username') || placeholder.includes('email') || placeholder.includes('login') || placeholder.includes('phone') || placeholder.includes('identifier')) score += 25;

        return score;
    };

    // 1. Walk up parent elements looking for candidate inputs in the same subtree/form
    let current = passwordInput.parentElement;
    let levels = 0;
    while (current && current !== document.body && levels < 4) {
        const inputs = queryAllShadow('input', current);
        let bestCandidate = null;
        let bestScore = -1;

        inputs.forEach(input => {
            if (input === passwordInput) return;
            const score = getUsernameScore(input);
            if (score > bestScore) {
                bestScore = score;
                bestCandidate = input;
            }
        });

        if (bestCandidate && bestScore >= 10) {
            return bestCandidate;
        }

        if (current.tagName === 'FORM') break;
        current = current.parentElement;
        levels++;
    }

    // 2. Fallback: Search all inputs in the document order before the password input
    const allInputs = queryAllShadow('input', document);
    const index = allInputs.indexOf(passwordInput);
    if (index > 0) {
        let bestCandidate = null;
        let bestScore = -1;

        for (let i = index - 1; i >= 0; i--) {
            const input = allInputs[i];
            const score = getUsernameScore(input);
            if (score > bestScore) {
                bestScore = score;
                bestCandidate = input;
            }
        }

        if (bestCandidate && bestScore >= 0) {
            return bestCandidate;
        }
    }

    return null;
}

function setNativeValue(el, value) {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(el, value);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    el.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true }));
    el.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
}

function findLoginInputs(anchor) {
    const container = (anchor && anchor.closest) ? (anchor.closest('form') || document) : document;
    const passInputs = queryAllShadow('input[type="password"]', container);
    const allInputs = queryAllShadow('input', container);
    const userInputs = [];
    allInputs.forEach(input => {
        const type = input.type ? input.type.toLowerCase() : 'text';
        if (type === 'text' || type === 'email' || type === 'username' || type === '' || input.name === 'username' || input.name === 'email') {
            userInputs.push(input);
        }
    });
    return { passInputs, userInputs };
}

let pickerEl = null;
let cachedCreds = null;
let cacheUrl = null;

function removePickerEl() {
    if (pickerEl) {
        pickerEl.remove();
        pickerEl = null;
    }
}

function createPickerStyles() {
    if (document.getElementById('vaultmate-styles')) return;
    const style = document.createElement('style');
    style.id = 'vaultmate-styles';
    style.textContent = `
        #vaultmate-picker {
            position: fixed;
            z-index: 2147483647;
            background: rgba(20, 21, 26, 0.95);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.65), inset 0 1px 0 rgba(255,255,255,0.1);
            min-width: 290px;
            max-width: 380px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            overflow: hidden;
            animation: vm-fadein 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        }
        @keyframes vm-fadein {
            from { opacity: 0; transform: translateY(-8px) scale(0.98); }
            to   { opacity: 1; transform: translateY(0) scale(1); }
        }
        #vaultmate-picker .vm-header {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            background: rgba(255,255,255,0.02);
        }
        #vaultmate-picker .vm-logo {
            font-size: 16px;
        }
        #vaultmate-picker .vm-title {
            font-size: 11px;
            font-weight: 700;
            color: rgba(255, 255, 255, 0.5);
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        #vaultmate-picker .vm-item {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 12px 16px;
            cursor: pointer;
            transition: all 0.15s ease;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        }
        #vaultmate-picker .vm-item:last-child {
            border-bottom: none;
        }
        #vaultmate-picker .vm-item:hover {
            background: rgba(255, 255, 255, 0.05);
            transform: translateX(4px);
        }
        #vaultmate-picker .vm-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: linear-gradient(135deg, #6366f1, #a855f7);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 15px;
            color: white;
            font-weight: 700;
            flex-shrink: 0;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }
        #vaultmate-picker .vm-info {
            flex: 1;
            min-width: 0;
        }
        #vaultmate-picker .vm-name {
            font-size: 13.5px;
            font-weight: 600;
            color: #ffffff;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        #vaultmate-picker .vm-user {
            font-size: 11px;
            color: rgba(255, 255, 255, 0.45);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            margin-top: 1px;
        }
        #vaultmate-picker .vm-fill-badge {
            font-size: 10px;
            color: #a855f7;
            background: rgba(168, 85, 247, 0.15);
            border: 1px solid rgba(168, 85, 247, 0.25);
            padding: 3px 9px;
            border-radius: 20px;
            font-weight: 600;
            flex-shrink: 0;
            transition: all 0.2s ease;
        }
        #vaultmate-picker .vm-item:hover .vm-fill-badge {
            background: linear-gradient(135deg, #6366f1, #a855f7);
            color: white;
            border-color: transparent;
            box-shadow: 0 2px 8px rgba(168, 85, 247, 0.4);
        }
    `;
    document.head.appendChild(style);
}

function showPicker(anchorEl, credentials, showAll = false) {
    activeInputEl = anchorEl;
    
    // Filter credentials: show only standard credentials for standard username/password interactions
    const displayCreds = showAll ? credentials : credentials.filter(c => c.type !== 'passkey');
    if (displayCreds.length === 0) {
        removePickerEl();
        return;
    }

    removePickerEl();
    createPickerStyles();

    const picker = document.createElement('div');
    picker.id = 'vaultmate-picker';

    // Header
    const header = document.createElement('div');
    header.className = 'vm-header';
    header.style.justifyContent = 'space-between';
    header.style.width = '100%';

    const logoContainer = document.createElement('div');
    logoContainer.style.display = 'flex';
    logoContainer.style.alignItems = 'center';
    logoContainer.style.gap = '10px';

    const logoSpan = document.createElement('span');
    logoSpan.className = 'vm-logo';
    logoSpan.textContent = '🔐';

    const titleSpan = document.createElement('span');
    titleSpan.className = 'vm-title';
    titleSpan.textContent = 'VaultMate — Saved Credentials';

    logoContainer.appendChild(logoSpan);
    logoContainer.appendChild(titleSpan);

    const closeBtn = document.createElement('button');
    closeBtn.id = 'vm-picker-close';
    closeBtn.style.background = 'none';
    closeBtn.style.border = 'none';
    closeBtn.style.color = 'rgba(255, 255, 255, 0.4)';
    closeBtn.style.fontSize = '18px';
    closeBtn.style.cursor = 'pointer';
    closeBtn.style.padding = '0 4px';
    closeBtn.style.display = 'flex';
    closeBtn.style.alignItems = 'center';
    closeBtn.style.justifyContent = 'center';
    closeBtn.style.transition = 'color 0.15s';
    closeBtn.style.lineHeight = '1';
    closeBtn.style.marginLeft = 'auto';
    closeBtn.textContent = '×';

    closeBtn.addEventListener('mousedown', (e) => {
        e.preventDefault();
        e.stopPropagation();
        removePickerEl();
    });
    closeBtn.addEventListener('mouseenter', () => { closeBtn.style.color = '#ffffff'; });
    closeBtn.addEventListener('mouseleave', () => { closeBtn.style.color = 'rgba(255, 255, 255, 0.4)'; });

    header.appendChild(logoContainer);
    header.appendChild(closeBtn);
    picker.appendChild(header);

    // Items
    displayCreds.forEach(cred => {
        const item = document.createElement('div');
        item.className = 'vm-item';

        if (cred.type === 'passkey') {
            const avatar = document.createElement('div');
            avatar.className = 'vm-avatar';
            avatar.style.background = 'linear-gradient(135deg, #a855f7, #ec4899)';
            avatar.style.fontSize = '14px';
            avatar.textContent = '🔑';

            const info = document.createElement('div');
            info.className = 'vm-info';

            const name = document.createElement('div');
            name.className = 'vm-name';
            name.style.fontFamily = "'Outfit', sans-serif";
            name.textContent = cred.username;

            const user = document.createElement('div');
            user.className = 'vm-user';
            user.textContent = 'Passkey Account';

            info.appendChild(name);
            info.appendChild(user);

            const badge = document.createElement('div');
            badge.className = 'vm-fill-badge';
            badge.style.color = '#ec4899';
            badge.style.background = 'rgba(236, 72, 153, 0.15)';
            badge.style.border = '1px solid rgba(236, 72, 153, 0.25)';
            badge.textContent = 'Use Passkey';

            item.appendChild(avatar);
            item.appendChild(info);
            item.appendChild(badge);
            
            item.addEventListener('mousedown', (e) => {
                e.preventDefault(); // prevent blur
                removePickerEl();
                
                // Trigger WebAuthn conditional response by requesting signature from native host
                if (activeConditionalRequest) {
                    chrome.runtime.sendMessage({
                        action: "passkey_get_by_id",
                        passkey_id: cred.id,
                        options: activeConditionalRequest.options,
                        url: window.location.href
                    }, (response) => {
                        if (response && !response.error) {
                            const parsed = deserializeResponse(response.credential);
                            parsed.authenticatorAttachment = "platform";
                            parsed.getClientExtensionResults = function() { return new window.wrappedJSObject.Object(); };
                            if (parsed.response) {
                                parsed.response.getAuthenticatorData = function() { return parsed.response.authenticatorData; };
                            }
                            const cloned = cloneInto(parsed, window.wrappedJSObject, { cloneFunctions: true });
                            activeConditionalRequest.resolve(cloned);
                            activeConditionalRequest = null;
                        } else {
                            console.error("[VaultMate] Passkey resolve error:", response ? response.error : "No response");
                        }
                    });
                } else {
                    // Fallback
                    const passkeyBtn = document.querySelector('[data-signin-label="Sign in with a passkey"]') || document.querySelector('button[type="submit"]');
                    if (passkeyBtn) passkeyBtn.click();
                }
            });
        } else {
            const initial = (cred.username || cred.name || '?')[0].toUpperCase();

            const avatar = document.createElement('div');
            avatar.className = 'vm-avatar';
            avatar.textContent = initial;

            const info = document.createElement('div');
            info.className = 'vm-info';

            const name = document.createElement('div');
            name.className = 'vm-name';
            name.textContent = cred.name || cred.username;

            const user = document.createElement('div');
            user.className = 'vm-user';
            user.textContent = cred.username;

            info.appendChild(name);
            info.appendChild(user);

            const badge = document.createElement('div');
            badge.className = 'vm-fill-badge';
            badge.textContent = 'Fill';

            item.appendChild(avatar);
            item.appendChild(info);
            item.appendChild(badge);

            item.addEventListener('mousedown', (e) => {
                e.preventDefault(); // prevent blur
                fillCredential(anchorEl, cred);
                removePickerEl();
            });
        }
        picker.appendChild(item);
    });

    document.body.appendChild(picker);
    pickerEl = picker;

    positionPicker(anchorEl, picker);
}

function positionPicker(anchorEl, picker) {
    const rect = anchorEl.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const pickerH = picker.offsetHeight || 200;
    const pickerW = picker.offsetWidth || 300;

    let top = rect.bottom + 6;
    let left = rect.left;

    if (top + pickerH > vh - 20) top = rect.top - pickerH - 6;
    if (left + pickerW > vw - 12) left = vw - pickerW - 12;
    if (left < 6) left = 6;

    picker.style.top = `${top}px`;
    picker.style.left = `${left}px`;
}


function fillCredential(anchorEl, cred) {
    const { passInputs, userInputs } = findLoginInputs(anchorEl);

    if (userInputs.length > 0) {
        const target = anchorEl.type === 'password' ? userInputs[0] : anchorEl;
        setNativeValue(target, cred.username);
        if (anchorEl.type === 'password') setNativeValue(userInputs[0], cred.username);
    }
    if (passInputs.length > 0) {
        setNativeValue(passInputs[passInputs.length - 1], cred.password);
    }
}

function fetchAndShowPicker(inputEl) {
    if (!vaultmateEnabled) return;
    const url = window.location.href;

    const showAll = activeConditionalRequest !== null;

    if (cachedCreds !== null && cacheUrl === url) {
        if (cachedCreds.length > 0) showPicker(inputEl, cachedCreds, showAll);
        return;
    }

    chrome.runtime.sendMessage({ action: "autofill_request", url }, (response) => {
        if (chrome.runtime.lastError) return;
        if (response && response.status === "success" && response.credentials && response.credentials.length > 0) {
            cachedCreds = response.credentials;
            cacheUrl = url;
            showPicker(inputEl, cachedCreds, showAll);
        } else {
            cachedCreds = [];
            cacheUrl = url;
        }
    });
}

// --- 3. Event Listeners ---

document.addEventListener('focusin', (e) => {
    if (!vaultmateEnabled) return;
    const el = e.target;
    if (!el || el.tagName !== 'INPUT') return;
    const type = el.type ? el.type.toLowerCase() : 'text';
    if (type === 'password' || type === 'text' || type === 'email') {
        fetchAndShowPicker(el);
    }
}, true);

document.addEventListener('mousedown', (e) => {
    if (pickerEl && !pickerEl.contains(e.target) && e.target !== activeInputEl) {
        removePickerEl();
    }
}, true);

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') removePickerEl();
}, true);

// --- 4. Robust Auto-Save Capture ---

// Dynamically capture keystrokes and write them to storage *before* submission occurs
document.addEventListener('input', (e) => {
    if (!vaultmateEnabled) return;
    const el = e.target;
    if (el && el.tagName === 'INPUT') {
        const type = el.type ? el.type.toLowerCase() : 'text';
        if (type === 'password' || type === 'text' || type === 'email' || type === 'username') {
            const container = el.closest('form') || document;
            const passwordInputs = queryAllShadow('input[type="password"]', container);
            if (passwordInputs.length > 0) {
                const passwordInput = passwordInputs[passwordInputs.length - 1];
                if (passwordInput && passwordInput.value && passwordInput.value.length >= 3) {
                    let username = "";
                    const userInput = findUsernameInput(passwordInput);
                    if (userInput) username = userInput.value;

                    const pending = {
                        url: getCleanLoginUrl(window.location.href),
                        name: getCleanServiceName(window.location.hostname),
                        username: username.trim(),
                        password: passwordInput.value,
                        timestamp: Date.now(),
                        submitted: false
                    };

                    // Commits to storage continuously as they type, avoiding navigation race conditions
                    chrome.storage.local.set({ pending_auto_save: pending });
                }
            }
        }
    }
}, true);

function captureAndSave(formOrElement) {
    if (!vaultmateEnabled) return;
    
    // Capture the login URL and title immediately and synchronously
    const currentUrl = getCleanLoginUrl(window.location.href);
    const currentTitle = getCleanServiceName(window.location.hostname);

    const container = (formOrElement && formOrElement.closest) ? (formOrElement.closest('form') || document) : document;
    const passwordInputs = queryAllShadow('input[type="password"]', container);
    if (passwordInputs.length === 0) return;

    const passwordInput = passwordInputs[passwordInputs.length - 1];
    if (passwordInput && passwordInput.value && passwordInput.value.length >= 3) {
        let username = "";
        const userInput = findUsernameInput(passwordInput);
        if (userInput) username = userInput.value;

        // Retrieve existing pending data from storage to preserve the correct login URL
        chrome.storage.local.get("pending_auto_save", (result) => {
            let loginUrl = currentUrl;
            let loginName = currentTitle;
            if (result && result.pending_auto_save && result.pending_auto_save.url) {
                loginUrl = result.pending_auto_save.url;
                loginName = result.pending_auto_save.name;
            }

            const pending = {
                url: loginUrl,
                name: loginName,
                username: username.trim(),
                password: passwordInput.value,
                timestamp: Date.now(),
                submitted: true
            };

            // Flag as submitted and write immediately to storage
            chrome.storage.local.set({ pending_auto_save: pending });
        });

        cachedCreds = null;
    }
}

document.addEventListener('submit', (e) => { captureAndSave(e.target); }, true);

document.addEventListener('click', (e) => {
    if (!vaultmateEnabled) return;
    // Resolve any nested click targets (like icons or spans inside buttons)
    const btn = e.target.closest('button') || e.target.closest('input[type="submit"]') || e.target.closest('input[type="button"]');
    if (btn) {
        captureAndSave(btn);
    }
}, true);

document.addEventListener('keydown', (e) => {
    if (!vaultmateEnabled) return;
    if (e.key === 'Enter' && e.target.tagName === 'INPUT') {
        const type = e.target.type ? e.target.type.toLowerCase() : 'text';
        if (type === 'password' || type === 'text' || type === 'email') {
            captureAndSave(e.target);
        }
    }
}, true);

// Hide picker when window loses focus (e.g. user clicks inside a Google Sign-In iframe!)
window.addEventListener('blur', () => {
    removePickerEl();
});

function showSavePrompt(pending) {
    const inject = () => {
        if (document.getElementById('vaultmate-save-prompt')) return;
        
        // Inject styles if not present
        if (!document.getElementById('vaultmate-prompt-styles')) {
            const style = document.createElement('style');
            style.id = 'vaultmate-prompt-styles';
            style.textContent = `
                #vaultmate-save-prompt {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 2147483647;
                    background: rgba(20, 21, 28, 0.96);
                    backdrop-filter: blur(12px);
                    -webkit-backdrop-filter: blur(12px);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 16px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.1);
                    width: 320px;
                    padding: 16px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    color: #ffffff;
                    animation: vm-slidein 0.3s cubic-bezier(0.16, 1, 0.3, 1);
                }
                @keyframes vm-slidein {
                    from { opacity: 0; transform: translateY(-20px) scale(0.95); }
                    to   { opacity: 1; transform: translateY(0) scale(1); }
                }
                #vaultmate-save-prompt .vm-prompt-header {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    margin-bottom: 8px;
                }
                #vaultmate-save-prompt .vm-prompt-logo {
                    font-size: 18px;
                }
                #vaultmate-save-prompt .vm-prompt-title {
                    font-size: 11px;
                    font-weight: 700;
                    text-transform: uppercase;
                    color: rgba(255,255,255,0.5);
                    letter-spacing: 1px;
                }
                #vaultmate-save-prompt .vm-prompt-body {
                    font-size: 12.5px;
                    line-height: 1.5;
                    color: #cbd5e1;
                    margin-bottom: 12px;
                }
                #vaultmate-save-prompt .vm-prompt-details {
                    background: rgba(255,255,255,0.03);
                    border-radius: 8px;
                    padding: 8px 10px;
                    margin-bottom: 14px;
                    border: 1px solid rgba(255,255,255,0.04);
                    font-size: 11px;
                }
                #vaultmate-save-prompt .vm-prompt-detail-item {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 4px;
                }
                #vaultmate-save-prompt .vm-prompt-detail-item:last-child {
                    margin-bottom: 0;
                }
                #vaultmate-save-prompt .vm-prompt-detail-label {
                    color: #94a3b8;
                }
                #vaultmate-save-prompt .vm-prompt-detail-val {
                    font-weight: 600;
                    color: #ffffff;
                    max-width: 140px;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                }
                #vaultmate-save-prompt .vm-prompt-actions {
                    display: flex;
                    gap: 10px;
                }
                #vaultmate-save-prompt .vm-prompt-btn {
                    flex: 1;
                    padding: 8px 12px;
                    border-radius: 8px;
                    border: none;
                    font-size: 12px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    text-align: center;
                }
                #vaultmate-save-prompt .vm-prompt-btn-save {
                    background: linear-gradient(135deg, #6366f1, #a855f7);
                    color: #ffffff;
                    box-shadow: 0 4px 12px rgba(168, 85, 247, 0.3);
                }
                #vaultmate-save-prompt .vm-prompt-btn-save:hover {
                    transform: translateY(-1px);
                    box-shadow: 0 6px 16px rgba(168, 85, 247, 0.45);
                }
                #vaultmate-save-prompt .vm-prompt-btn-cancel {
                    background: transparent;
                    color: #cbd5e1;
                    border: 1px solid rgba(255,255,255,0.15);
                }
                #vaultmate-save-prompt .vm-prompt-btn-cancel:hover {
                    background: rgba(255,255,255,0.05);
                    color: #ffffff;
                    border-color: rgba(255,255,255,0.25);
                }
            `;
            document.head.appendChild(style);
        }

        const container = document.createElement('div');
        container.id = 'vaultmate-save-prompt';

        // Header
        const prHeader = document.createElement('div');
        prHeader.className = 'vm-prompt-header';

        const prLogo = document.createElement('span');
        prLogo.className = 'vm-prompt-logo';
        prLogo.textContent = '🔐';

        const prTitle = document.createElement('span');
        prTitle.className = 'vm-prompt-title';
        prTitle.textContent = 'VaultMate';

        prHeader.appendChild(prLogo);
        prHeader.appendChild(prTitle);

        // Body
        const prBody = document.createElement('div');
        prBody.className = 'vm-prompt-body';
        prBody.textContent = 'Would you like to store this username & password into VaultMate?';

        // Details
        const prDetails = document.createElement('div');
        prDetails.className = 'vm-prompt-details';

        // Service row
        const svcRow = document.createElement('div');
        svcRow.className = 'vm-prompt-detail-item';
        const svcLbl = document.createElement('span');
        svcLbl.className = 'vm-prompt-detail-label';
        svcLbl.textContent = 'Service';
        const svcVal = document.createElement('span');
        svcVal.className = 'vm-prompt-detail-val';
        svcVal.textContent = pending.name;
        svcRow.appendChild(svcLbl);
        svcRow.appendChild(svcVal);

        // Username row
        const usrRow = document.createElement('div');
        usrRow.className = 'vm-prompt-detail-item';
        const usrLbl = document.createElement('span');
        usrLbl.className = 'vm-prompt-detail-label';
        usrLbl.textContent = 'Username';
        const usrVal = document.createElement('span');
        usrVal.className = 'vm-prompt-detail-val';
        usrVal.textContent = pending.username;
        usrRow.appendChild(usrLbl);
        usrRow.appendChild(usrVal);

        prDetails.appendChild(svcRow);
        prDetails.appendChild(usrRow);

        // Actions
        const prActions = document.createElement('div');
        prActions.className = 'vm-prompt-actions';

        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'vm-prompt-btn vm-prompt-btn-cancel';
        cancelBtn.id = 'vm-prompt-btn-no';
        cancelBtn.textContent = 'No, thanks';

        const saveBtn = document.createElement('button');
        saveBtn.className = 'vm-prompt-btn vm-prompt-btn-save';
        saveBtn.id = 'vm-prompt-btn-yes';
        saveBtn.textContent = 'Save';

        prActions.appendChild(cancelBtn);
        prActions.appendChild(saveBtn);

        container.appendChild(prHeader);
        container.appendChild(prBody);
        container.appendChild(prDetails);
        container.appendChild(prActions);

        document.body.appendChild(container);

        // Save handler
        document.getElementById('vm-prompt-btn-yes').addEventListener('click', () => {
            chrome.runtime.sendMessage({
                action: "auto_save_confirm",
                url: pending.url,
                name: pending.name,
                username: pending.username,
                password: pending.password
            });
            container.remove();
            chrome.storage.local.remove("pending_auto_save");
        });

        // Dismiss handler
        document.getElementById('vm-prompt-btn-no').addEventListener('click', () => {
            container.remove();
            chrome.storage.local.remove("pending_auto_save");
        });
    };

    if (document.body) {
        inject();
    } else {
        document.addEventListener('DOMContentLoaded', inject);
    }
}

// 5. On page load, check for any pending auto-saves that were submitted
chrome.storage.local.get("pending_auto_save", (result) => {
    if (result && result.pending_auto_save) {
        const pending = result.pending_auto_save;
        // Verify it was submitted, and captured recently (within last 60 seconds)
        if (pending.submitted && Date.now() - pending.timestamp < 60000) {
            showSavePrompt(pending);
        } else if (Date.now() - pending.timestamp >= 60000) {
            // Discard stale credentials
            chrome.storage.local.remove("pending_auto_save");
        }
    }
});
