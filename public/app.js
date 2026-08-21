document.addEventListener('DOMContentLoaded', () => {
  // Auth state
  let authToken = localStorage.getItem('wifi_share_token') || '';
  let userRole = '';
  let userPermissions = [];
  let detectedClientIp = '';
  let pollingInterval = null;

  // DOM Elements
  const loginOverlay = document.getElementById('loginOverlay');
  const loginFormCard = document.getElementById('loginFormCard');
  const requestIpCard = document.getElementById('requestIpCard');
  const waitingIpCard = document.getElementById('waitingIpCard');

  const loginForm = document.getElementById('loginForm');
  const loginPassword = document.getElementById('loginPassword');
  const loginError = document.getElementById('loginError');

  const showRequestIpBtn = document.getElementById('showRequestIpBtn');
  const cancelRequestBtn = document.getElementById('cancelRequestBtn');
  const requestIpForm = document.getElementById('requestIpForm');
  const deviceNameInput = document.getElementById('deviceNameInput');
  const clientIpDisplay = document.getElementById('clientIpDisplay');

  const waitingDeviceName = document.getElementById('waitingDeviceName');
  const waitingIpDisplay = document.getElementById('waitingIpDisplay');
  const cancelWaitingBtn = document.getElementById('cancelWaitingBtn');

  const appContainer = document.getElementById('appContainer');
  const roleBadge = document.getElementById('roleBadge');
  const roleText = document.getElementById('roleText');
  const logoutBtn = document.getElementById('logoutBtn');
  const manageKeysBtn = document.getElementById('manageKeysBtn');

  const pendingBellBtn = document.getElementById('pendingBellBtn');
  const pendingCountBadge = document.getElementById('pendingCountBadge');

  const networkIp = document.getElementById('networkIp');
  const copyIpBtn = document.getElementById('copyIpBtn');
  const showQrBtn = document.getElementById('showQrBtn');
  const qrModal = document.getElementById('qrModal');
  const closeQrBtn = document.getElementById('closeQrBtn');
  const modalUrlDisplay = document.getElementById('modalUrlDisplay');
  const copyModalUrlBtn = document.getElementById('copyModalUrlBtn');
  const qrcodeContainer = document.getElementById('qrcode');

  const keysModal = document.getElementById('keysModal');
  const closeKeysBtn = document.getElementById('closeKeysBtn');
  const pendingRequestsTbody = document.getElementById('pendingRequestsTbody');
  const approvedIpsTbody = document.getElementById('approvedIpsTbody');

  const generatePassForm = document.getElementById('generatePassForm');
  const keyLabel = document.getElementById('keyLabel');
  const keyDuration = document.getElementById('keyDuration');
  const keyPermission = document.getElementById('keyPermission');
  const generatedKeyBox = document.getElementById('generatedKeyBox');
  const generatedKeyCode = document.getElementById('generatedKeyCode');
  const copyGeneratedCodeBtn = document.getElementById('copyGeneratedCodeBtn');
  const activeKeysTbody = document.getElementById('activeKeysTbody');
  const changeAdminPassForm = document.getElementById('changeAdminPassForm');
  const newAdminPass = document.getElementById('newAdminPass');

  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const uploadProgress = document.getElementById('uploadProgress');
  const filesGrid = document.getElementById('filesGrid');
  const emptyState = document.getElementById('emptyState');
  const fileCountBadge = document.getElementById('fileCountBadge');
  const searchInput = document.getElementById('searchInput');
  const readOnlyBanner = document.getElementById('readOnlyBanner');

  const clipboardInput = document.getElementById('clipboardInput');
  const saveClipboardBtn = document.getElementById('saveClipboardBtn');
  const copyClipboardBtn = document.getElementById('copyClipboardBtn');
  const lastSyncTime = document.getElementById('lastSyncTime');

  let currentPrimaryUrl = '';
  let allFiles = [];

  // Helper fetch wrapper with Bearer token
  async function authFetch(url, options = {}) {
    options.headers = options.headers || {};
    if (authToken) {
      options.headers['Authorization'] = `Bearer ${authToken}`;
    }
    const response = await fetch(url, options);
    if (response.status === 401) {
      handleLogout();
    }
    return response;
  }

  // Initial Check
  checkAuth();

  async function checkAuth() {
    fetchServerInfo(); // Public IP info
    await checkIpRequestStatus(); // Check if this client IP is pending or approved

    if (!authToken) {
      showLoginScreen();
      return;
    }

    try {
      const res = await authFetch('/api/auth/status');
      if (res.ok) {
        const data = await res.json();
        userRole = data.role;
        userPermissions = data.permissions;
        showAppScreen();
      } else {
        showLoginScreen();
      }
    } catch (err) {
      showLoginScreen();
    }
  }

  // Check IP Request Status (Used on page load and guest polling)
  async function checkIpRequestStatus() {
    try {
      const res = await fetch('/api/access/request-status');
      if (!res.ok) return;
      const data = await res.json();
      detectedClientIp = data.client_ip || '';
      clientIpDisplay.textContent = detectedClientIp;

      if (data.status === 'approved' && data.token) {
        authToken = data.token;
        userRole = 'guest_ip';
        userPermissions = data.permissions;
        localStorage.setItem('wifi_share_token', authToken);
        stopPolling();
        showAppScreen();
        showToast('IP Access Approved! Logged in automatically.');
      } else if (data.status === 'pending') {
        waitingDeviceName.textContent = data.device_name || 'Device';
        waitingIpDisplay.textContent = detectedClientIp;
        showWaitingCard();
        startPolling();
      }
    } catch (err) {
      console.error('Error checking IP status:', err);
    }
  }

  function startPolling() {
    if (pollingInterval) return;
    pollingInterval = setInterval(checkIpRequestStatus, 2000);
  }

  function stopPolling() {
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }
  }

  // Login Form Submission (Password / Temp Passcode)
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    loginError.textContent = '';
    const password = loginPassword.value.trim();
    if (!password) return;

    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      });
      const data = await res.json();

      if (res.ok && data.status === 'success') {
        authToken = data.token;
        userRole = data.role;
        userPermissions = data.permissions;
        localStorage.setItem('wifi_share_token', authToken);
        loginPassword.value = '';
        stopPolling();
        showAppScreen();
        showToast(`Logged in as ${userRole.toUpperCase()}`);
      } else {
        loginError.textContent = data.error || 'Invalid password';
      }
    } catch (err) {
      loginError.textContent = 'Server connection error';
    }
  });

  // Request IP Access Button Handlers
  showRequestIpBtn.addEventListener('click', () => {
    loginFormCard.style.display = 'none';
    requestIpCard.style.display = 'block';
    waitingIpCard.style.display = 'none';
  });

  cancelRequestBtn.addEventListener('click', () => {
    requestIpCard.style.display = 'none';
    loginFormCard.style.display = 'block';
    waitingIpCard.style.display = 'none';
  });

  requestIpForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const device_name = deviceNameInput.value.trim();
    if (!device_name) return;

    try {
      const res = await fetch('/api/access/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_name })
      });
      const data = await res.json();
      if (res.ok && data.status === 'pending') {
        waitingDeviceName.textContent = device_name;
        waitingIpDisplay.textContent = data.client_ip;
        showWaitingCard();
        startPolling();
        showToast('Access request sent to Admin!');
      } else {
        showToast(data.error || 'Request failed', true);
      }
    } catch (err) {
      showToast('Error sending access request', true);
    }
  });

  cancelWaitingBtn.addEventListener('click', () => {
    stopPolling();
    waitingIpCard.style.display = 'none';
    loginFormCard.style.display = 'block';
  });

  function showLoginScreen() {
    loginOverlay.classList.add('active');
    appContainer.style.display = 'none';
  }

  function showWaitingCard() {
    loginOverlay.classList.add('active');
    appContainer.style.display = 'none';
    loginFormCard.style.display = 'none';
    requestIpCard.style.display = 'none';
    waitingIpCard.style.display = 'block';
  }

  function showAppScreen() {
    loginOverlay.classList.remove('active');
    appContainer.style.display = 'block';

    if (userRole === 'admin') {
      roleBadge.className = 'user-role-badge admin';
      roleText.textContent = '👑 Admin';
      manageKeysBtn.style.display = 'inline-flex';
      pendingBellBtn.style.display = 'inline-flex';
      loadPendingRequests();
    } else {
      roleBadge.className = 'user-role-badge guest';
      const isReadOnly = !userPermissions.includes('write');
      roleText.textContent = isReadOnly ? '👁️ Read-Only Guest' : '✏️ Read & Write Guest';
      manageKeysBtn.style.display = 'none';
      pendingBellBtn.style.display = 'none';
    }

    const isWriteAllowed = userPermissions.includes('write');
    document.querySelectorAll('.write-only').forEach(el => {
      el.style.display = isWriteAllowed ? '' : 'none';
    });
    readOnlyBanner.style.display = isWriteAllowed ? 'none' : 'block';
    clipboardInput.readOnly = !isWriteAllowed;

    loadFilesList();
    loadClipboardText();
  }

  // Logout Handler
  logoutBtn.addEventListener('click', handleLogout);
  function handleLogout() {
    stopPolling();
    if (authToken) {
      fetch('/api/logout', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${authToken}` }
      }).catch(() => {});
    }
    authToken = '';
    userRole = '';
    userPermissions = [];
    localStorage.removeItem('wifi_share_token');
    loginFormCard.style.display = 'block';
    requestIpCard.style.display = 'none';
    waitingIpCard.style.display = 'none';
    showLoginScreen();
  }

  // Auto-refresh files & clipboard & pending requests
  setInterval(() => {
    if (authToken) {
      loadFilesList(true);
      loadClipboardText(true);
      if (userRole === 'admin') {
        loadPendingRequests(true);
      }
    }
  }, 3000);

  // Tab Switching
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.getAttribute('data-tab');
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));

      btn.classList.add('active');
      document.getElementById(targetTab).classList.add('active');
    });
  });

  // Fetch Public Network Info
  async function fetchServerInfo() {
    try {
      const res = await fetch('/api/info');
      const data = await res.json();
      currentPrimaryUrl = data.primary_url;
      detectedClientIp = data.your_client_ip;
      clientIpDisplay.textContent = detectedClientIp;
      networkIp.textContent = `${data.primary_ip}:${data.port}`;
      modalUrlDisplay.textContent = currentPrimaryUrl;

      qrcodeContainer.innerHTML = '';
      if (window.QRCode) {
        new QRCode(qrcodeContainer, {
          text: currentPrimaryUrl,
          width: 180,
          height: 180,
          colorDark : "#0b0f19",
          colorLight : "#ffffff",
          correctLevel : QRCode.CorrectLevel.H
        });
      }
    } catch (err) {
      networkIp.textContent = 'Offline / Error';
    }
  }

  copyIpBtn.addEventListener('click', () => {
    if (currentPrimaryUrl) {
      navigator.clipboard.writeText(currentPrimaryUrl);
      showToast('Address copied to clipboard!');
    }
  });

  showQrBtn.addEventListener('click', () => qrModal.classList.add('active'));
  closeQrBtn.addEventListener('click', () => qrModal.classList.remove('active'));
  qrModal.addEventListener('click', (e) => { if (e.target === qrModal) qrModal.classList.remove('active'); });
  copyModalUrlBtn.addEventListener('click', () => {
    if (currentPrimaryUrl) {
      navigator.clipboard.writeText(currentPrimaryUrl);
      showToast('URL copied to clipboard!');
    }
  });

  // Manage Keys & Approvals Modal (Admin Only)
  manageKeysBtn.addEventListener('click', openManagerModal);
  pendingBellBtn.addEventListener('click', openManagerModal);

  function openManagerModal() {
    keysModal.classList.add('active');
    loadPendingRequests();
    loadApprovedIps();
    loadActiveKeys();
  }

  closeKeysBtn.addEventListener('click', () => keysModal.classList.remove('active'));
  keysModal.addEventListener('click', (e) => { if (e.target === keysModal) keysModal.classList.remove('active'); });

  // Load Pending IP Requests
  async function loadPendingRequests(isSilent = false) {
    if (userRole !== 'admin') return;
    try {
      const res = await authFetch('/api/access/pending');
      if (!res.ok) return;
      const data = await res.json();
      const list = data.pending_requests || [];
      pendingCountBadge.textContent = list.length;

      pendingRequestsTbody.innerHTML = '';
      if (list.length === 0) {
        pendingRequestsTbody.innerHTML = '<tr><td colspan="6" class="text-center" style="color: var(--text-muted);">No pending access requests</td></tr>';
        return;
      }

      list.forEach(item => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong>${escapeHtml(item.device_name)}</strong></td>
          <td><code>${escapeHtml(item.ip)}</code></td>
          <td>${item.requested_at_formatted}</td>
          <td>
            <select class="req-duration">
              <option value="15">15 Mins</option>
              <option value="30">30 Mins</option>
              <option value="60" selected>1 Hour</option>
              <option value="360">6 Hours</option>
              <option value="720">12 Hours</option>
              <option value="1440">24 Hours</option>
            </select>
          </td>
          <td>
            <select class="req-perm">
              <option value="read_only">👁️ Read Only</option>
              <option value="read_write" selected>✏️ Read & Write</option>
              <option value="full_access">⚡ Full Guest</option>
            </select>
          </td>
          <td>
            <div style="display: flex; gap: 4px;">
              <button class="btn btn-primary approve-btn" style="padding: 2px 8px; font-size: 0.75rem;">Approve</button>
              <button class="btn btn-danger reject-btn" style="padding: 2px 8px; font-size: 0.75rem;">Reject</button>
            </div>
          </td>
        `;

        const approveBtn = tr.querySelector('.approve-btn');
        const rejectBtn = tr.querySelector('.reject-btn');
        const durationSelect = tr.querySelector('.req-duration');
        const permSelect = tr.querySelector('.req-perm');

        approveBtn.addEventListener('click', () => approveIpRequest(item.ip, durationSelect.value, permSelect.value));
        rejectBtn.addEventListener('click', () => rejectIpRequest(item.ip));

        pendingRequestsTbody.appendChild(tr);
      });
    } catch (err) {
      if (!isSilent) console.error('Failed to load pending requests:', err);
    }
  }

  async function approveIpRequest(ip, duration_minutes, access_type) {
    try {
      const res = await authFetch('/api/access/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ip, duration_minutes: parseInt(duration_minutes), access_type })
      });
      const data = await res.json();
      if (res.ok) {
        showToast(`Approved IP ${ip} (${duration_minutes}m limit)`);
        loadPendingRequests();
        loadApprovedIps();
      } else {
        showToast(data.error || 'Approval failed', true);
      }
    } catch (err) {
      showToast('Error approving IP request', true);
    }
  }

  async function rejectIpRequest(ip) {
    try {
      const res = await authFetch('/api/access/reject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ip })
      });
      if (res.ok) {
        showToast(`Rejected request from ${ip}`);
        loadPendingRequests();
      }
    } catch (err) {
      showToast('Error rejecting request', true);
    }
  }

  // Load Active Approved IPs
  async function loadApprovedIps() {
    if (userRole !== 'admin') return;
    try {
      const res = await authFetch('/api/access/approved-ips');
      if (!res.ok) return;
      const data = await res.json();
      const list = data.approved_ips || [];

      approvedIpsTbody.innerHTML = '';
      if (list.length === 0) {
        approvedIpsTbody.innerHTML = '<tr><td colspan="5" class="text-center" style="color: var(--text-muted);">No active IP approvals</td></tr>';
        return;
      }

      list.forEach(item => {
        const tr = document.createElement('tr');
        const minutes = Math.floor(item.expires_in_seconds / 60);
        const seconds = item.expires_in_seconds % 60;
        const timeStr = `${minutes}m ${seconds}s`;

        tr.innerHTML = `
          <td><strong>${escapeHtml(item.device_name)}</strong></td>
          <td><code>${escapeHtml(item.ip)}</code></td>
          <td><span class="badge" style="font-size: 0.75rem;">${escapeHtml(item.permissions.join(', '))}</span></td>
          <td style="color: var(--accent-green); font-family: var(--font-mono);">${timeStr}</td>
          <td>
            <button class="btn btn-danger revoke-ip-btn" data-ip="${escapeHtml(item.ip)}" style="padding: 2px 8px; font-size: 0.75rem;">Revoke</button>
          </td>
        `;
        tr.querySelector('.revoke-ip-btn').addEventListener('click', () => revokeIpAccess(item.ip));
        approvedIpsTbody.appendChild(tr);
      });
    } catch (err) {
      console.error('Failed to load approved IPs:', err);
    }
  }

  async function revokeIpAccess(ip) {
    if (!confirm(`Revoke access for IP ${ip}?`)) return;
    try {
      const res = await authFetch(`/api/access/revoke-ip/${encodeURIComponent(ip)}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        showToast(`Revoked access for IP ${ip}`);
        loadApprovedIps();
      }
    } catch (err) {
      showToast('Error revoking IP access', true);
    }
  }

  // Generate Temporary Password Form
  generatePassForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const label = keyLabel.value.trim();
    const duration_minutes = parseInt(keyDuration.value);
    const access_type = keyPermission.value;

    try {
      const res = await authFetch('/api/passwords/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label, duration_minutes, access_type })
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        generatedKeyCode.textContent = data.code;
        generatedKeyBox.style.display = 'flex';
        showToast(`Generated key: ${data.code}`);
        keyLabel.value = '';
        loadActiveKeys();
      } else {
        showToast(data.error || 'Failed to generate passcode', true);
      }
    } catch (err) {
      showToast('Error generating passcode', true);
    }
  });

  copyGeneratedCodeBtn.addEventListener('click', () => {
    const code = generatedKeyCode.textContent;
    if (code && code !== '------') {
      navigator.clipboard.writeText(code);
      showToast('Passcode copied to clipboard!');
    }
  });

  // Load Active Temp Passwords Keys Table
  async function loadActiveKeys() {
    try {
      const res = await authFetch('/api/passwords/list');
      const data = await res.json();
      if (!res.ok) return;

      activeKeysTbody.innerHTML = '';
      if (!data.passwords || data.passwords.length === 0) {
        activeKeysTbody.innerHTML = '<tr><td colspan="5" class="text-center" style="color: var(--text-muted);">No active temporary passwords</td></tr>';
        return;
      }

      data.passwords.forEach(item => {
        const tr = document.createElement('tr');
        const minutes = Math.floor(item.expires_in_seconds / 60);
        const seconds = item.expires_in_seconds % 60;
        const timeStr = `${minutes}m ${seconds}s`;

        tr.innerHTML = `
          <td><code>${escapeHtml(item.code)}</code></td>
          <td>${escapeHtml(item.label)}</td>
          <td><span class="badge" style="font-size: 0.75rem;">${escapeHtml(item.permissions.join(', '))}</span></td>
          <td style="color: var(--accent-green); font-family: var(--font-mono);">${timeStr}</td>
          <td>
            <button class="btn btn-danger revoke-btn" data-code="${escapeHtml(item.code)}" style="padding: 2px 8px; font-size: 0.75rem;">Revoke</button>
          </td>
        `;
        tr.querySelector('.revoke-btn').addEventListener('click', () => revokeKey(item.code));
        activeKeysTbody.appendChild(tr);
      });
    } catch (err) {
      console.error('Failed to load active keys:', err);
    }
  }

  async function revokeKey(code) {
    if (!confirm(`Revoke password "${code}"?`)) return;
    try {
      const res = await authFetch(`/api/passwords/revoke/${encodeURIComponent(code)}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        showToast(`Revoked passcode ${code}`);
        loadActiveKeys();
      }
    } catch (err) {
      showToast('Failed to revoke passcode', true);
    }
  }

  // Change Admin Password Form
  changeAdminPassForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const new_password = newAdminPass.value.trim();
    if (!new_password) return;

    try {
      const res = await authFetch('/api/admin/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_password })
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        showToast('Admin password updated successfully!');
        newAdminPass.value = '';
      } else {
        showToast(data.error || 'Failed to update admin password', true);
      }
    } catch (err) {
      showToast('Error updating admin password', true);
    }
  });

  // Drag & Drop Upload
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, preventDefaults, false);
  });
  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, () => dropzone.classList.add('dragover'), false);
  });
  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, () => dropzone.classList.remove('dragover'), false);
  });

  dropzone.addEventListener('drop', (e) => {
    if (!userPermissions.includes('write')) return;
    handleFileUpload(e.dataTransfer.files);
  });

  fileInput.addEventListener('change', (e) => {
    handleFileUpload(e.target.files);
  });

  async function handleFileUpload(files) {
    if (!files || files.length === 0) return;
    if (!userPermissions.includes('write')) {
      showToast('Permission denied: You cannot upload files', true);
      return;
    }

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    uploadProgress.style.width = '30%';

    try {
      uploadProgress.style.width = '70%';
      const res = await authFetch('/api/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      uploadProgress.style.width = '100%';
      setTimeout(() => { uploadProgress.style.width = '0%'; }, 1000);

      if (res.ok && data.status === 'success') {
        showToast(`Uploaded ${files.length} file(s) successfully!`);
        loadFilesList();
        fileInput.value = '';
      } else {
        showToast(data.error || 'Upload failed', true);
      }
    } catch (err) {
      uploadProgress.style.width = '0%';
      showToast('Network error during upload', true);
    }
  }

  // Load Files List
  async function loadFilesList(isSilent = false) {
    try {
      const res = await authFetch('/api/files');
      if (!res.ok) return;
      const data = await res.json();
      if (!data.files) return;

      allFiles = data.files;
      renderFiles(allFiles);
    } catch (err) {
      if (!isSilent) console.error('Failed to load files list:', err);
    }
  }

  function renderFiles(files) {
    const query = searchInput.value.toLowerCase().trim();
    const filtered = files.filter(f => f.name.toLowerCase().includes(query));

    fileCountBadge.textContent = files.length;
    filesGrid.innerHTML = '';

    if (filtered.length === 0) {
      emptyState.style.display = 'block';
      return;
    }

    emptyState.style.display = 'none';

    const canDelete = userPermissions.includes('delete');

    filtered.forEach(file => {
      const card = document.createElement('div');
      card.className = 'file-card';

      const categoryIcons = {
        image: '🖼️', video: '🎬', audio: '🎵',
        document: '📄', archive: '📦', code: '💻', file: '📎'
      };
      const icon = categoryIcons[file.category] || '📎';

      card.innerHTML = `
        <div class="file-header">
          <div class="file-icon ${file.category}">${icon}</div>
          <div class="file-details">
            <div class="file-name" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</div>
            <div class="file-meta">${file.size_formatted} • ${file.mod_time_formatted}</div>
          </div>
        </div>
        <div class="file-actions">
          <a href="${file.url}?token=${encodeURIComponent(authToken)}" download class="btn btn-secondary" title="Download">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            Download
          </a>
          ${canDelete ? `
            <button class="btn btn-danger delete-btn" data-filename="${escapeHtml(file.name)}" title="Delete file">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
              Delete
            </button>
          ` : ''}
        </div>
      `;

      if (canDelete) {
        const deleteBtn = card.querySelector('.delete-btn');
        deleteBtn.addEventListener('click', () => deleteFile(file.name));
      }

      filesGrid.appendChild(card);
    });
  }

  // Delete File API Call
  async function deleteFile(filename) {
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) return;

    try {
      const res = await authFetch(`/api/files/${encodeURIComponent(filename)}`, {
        method: 'DELETE'
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        showToast(`Deleted ${filename}`);
        loadFilesList();
      } else {
        showToast(data.error || 'Failed to delete file', true);
      }
    } catch (err) {
      showToast('Network error during deletion', true);
    }
  }

  searchInput.addEventListener('input', () => renderFiles(allFiles));

  // Load Clipboard Text
  async function loadClipboardText(isSilent = false) {
    try {
      const res = await authFetch('/api/clipboard');
      if (!res.ok) return;
      const data = await res.json();
      
      if (document.activeElement !== clipboardInput && data.text !== undefined) {
        clipboardInput.value = data.text;
      }
      if (data.updated_at) {
        lastSyncTime.textContent = `Synced: ${data.updated_at}`;
      }
    } catch (err) {
      if (!isSilent) console.error('Failed to load clipboard text:', err);
    }
  }

  // Save Clipboard Text
  async function saveClipboardText() {
    if (!userPermissions.includes('write')) {
      showToast('Permission denied: Read-only access', true);
      return;
    }
    const text = clipboardInput.value;
    try {
      const res = await authFetch('/api/clipboard', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      const data = await res.json();
      if (res.ok) {
        showToast('Text synchronized across all devices!');
        if (data.clipboard && data.clipboard.updated_at) {
          lastSyncTime.textContent = `Synced: ${data.clipboard.updated_at}`;
        }
      }
    } catch (err) {
      showToast('Failed to sync text', true);
    }
  }

  saveClipboardBtn.addEventListener('click', saveClipboardText);

  copyClipboardBtn.addEventListener('click', () => {
    if (clipboardInput.value) {
      navigator.clipboard.writeText(clipboardInput.value);
      showToast('Clipboard text copied!');
    }
  });

  // Utilities
  function showToast(msg, isError = false) {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = 'toast';
    if (isError) toast.style.borderColor = 'var(--accent-red)';

    toast.innerHTML = `
      <span>${isError ? '⚠️' : '✅'}</span>
      <span>${escapeHtml(msg)}</span>
    `;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  function escapeHtml(str) {
    return str.replace(/[&<>"']/g, function(m) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m];
    });
  }
});
