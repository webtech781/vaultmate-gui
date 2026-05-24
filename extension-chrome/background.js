// background.js - Forwards requests to the Python Native Host

// Keep service worker alive with a periodic alarm so it's ready for passkey interception
chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create('keepAlive', { periodInMinutes: 0.4 });
});
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'keepAlive') {
    // No-op: just keeps the service worker alive
  }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log("VaultMate: received message", request.action);

  if (request.action === "intercept_passkey" || request.action === "autofill_request" || request.action === "auto_save") {
    chrome.runtime.sendNativeMessage('com.vaultmate.passkey', request, (response) => {
      if (chrome.runtime.lastError) {
        const errMsg = chrome.runtime.lastError.message;
        console.error("VaultMate Native Messaging Error:", errMsg);
        sendResponse({ error: errMsg });
      } else {
        console.log("VaultMate: response from native host", response);
        sendResponse(response);
      }
    });
    // Keep message channel open for async response
    return true;
  }
});
