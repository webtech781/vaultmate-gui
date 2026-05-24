// background.js - Forwards requests to the Python Native Host

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log("Sending request to VaultMate Native Host...", request.action);
  
  chrome.runtime.sendNativeMessage('com.vaultmate.passkey', request, (response) => {
    if (chrome.runtime.lastError) {
      console.error("Native Messaging Error: ", chrome.runtime.lastError.message);
      sendResponse({ error: "VaultMate application is not running or not installed correctly." });
    } else {
      console.log("Received response from VaultMate:", response);
      sendResponse(response);
    }
  });
  
  // Return true to indicate we wish to send a response asynchronously
  return true;
});
