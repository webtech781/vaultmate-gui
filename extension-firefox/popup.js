// popup.js - Manages the extension popup connection status and enabling toggle

document.addEventListener('DOMContentLoaded', () => {
  const statusBadge = document.getElementById('status-badge');
  const statusPulse = document.getElementById('status-pulse');
  const connectionTitle = document.getElementById('connection-title');
  const connectionDesc = document.getElementById('connection-desc');
  const userWrapper = document.getElementById('connection-user-wrapper');
  const activeUserName = document.getElementById('active-user-name');
  
  const shieldToggle = document.getElementById('shield-toggle');
  const retryBtn = document.getElementById('retry-btn');

  // Load and apply the toggle state
  chrome.storage.local.get({ enabled: true }, (result) => {
    shieldToggle.checked = result.enabled !== false;
  });

  // Watch for changes to the toggle
  shieldToggle.addEventListener('change', () => {
    chrome.storage.local.set({ enabled: shieldToggle.checked });
  });

  // Ping the native host to check connection status
  function checkConnection() {
    // Set to checking / loading state first
    statusBadge.textContent = "Checking...";
    statusBadge.className = "badge status-locked";
    statusPulse.className = "pulse-dot pulse-yellow";
    connectionTitle.textContent = "Connecting...";
    connectionDesc.textContent = "Querying VaultMate connection status...";
    userWrapper.classList.add('hidden');

    chrome.runtime.sendMessage({ action: "ping" }, (response) => {
      if (chrome.runtime.lastError || !response || response.error) {
        // Disconnected state
        statusBadge.textContent = "Offline";
        statusBadge.className = "badge status-disconnected";
        statusPulse.className = "pulse-dot pulse-red";
        connectionTitle.textContent = "Disconnected";
        connectionDesc.textContent = response && response.error 
          ? "Ensure VaultMate desktop app is running." 
          : "Could not establish connection to the desktop application.";
        userWrapper.classList.add('hidden');
      } else {
        if (response.unlocked) {
          // Connected & Unlocked
          statusBadge.textContent = "Connected";
          statusBadge.className = "badge status-connected";
          statusPulse.className = "pulse-dot pulse-green";
          connectionTitle.textContent = "Active & Unlocked";
          connectionDesc.textContent = "Autofill and passkey interceptors are active.";
          if (response.username) {
            activeUserName.textContent = response.username;
            userWrapper.classList.remove('hidden');
          } else {
            userWrapper.classList.add('hidden');
          }
        } else {
          // Connected but Locked
          statusBadge.textContent = "Locked";
          statusBadge.className = "badge status-locked";
          statusPulse.className = "pulse-dot pulse-yellow";
          connectionTitle.textContent = "Vault Locked";
          connectionDesc.textContent = "Please log in to the VaultMate desktop application to unlock.";
          userWrapper.classList.add('hidden');
        }
      }
    });
  }

  // Click handler for Retry
  retryBtn.addEventListener('click', (e) => {
    e.preventDefault();
    checkConnection();
  });

  // Initial connection check
  checkConnection();
});
