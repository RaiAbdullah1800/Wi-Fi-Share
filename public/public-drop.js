document.addEventListener('DOMContentLoaded', () => {
  let publicSharesData = [];
  let currentUnlockShareId = null;
  let publicTimerInterval = null;

  // DOM Elements
  const networkIp = document.getElementById('networkIp');
  const dropzone = document.getElementById('dropzone');
  const publicDropFileInput = document.getElementById('publicDropFileInput');
  const browseFilesBtn = document.getElementById('browseFilesBtn');
  const dropzoneTitle = document.getElementById('dropzoneTitle');
  const dropzoneSubtitle = document.getElementById('dropzoneSubtitle');
  const uploadProgress = document.getElementById('uploadProgress');

  const publicUploadForm = document.getElementById('publicUploadForm');
  const publicDropTitle = document.getElementById('publicDropTitle');
  const publicDropPassword = document.getElementById('publicDropPassword');

  const refreshPublicListBtn = document.getElementById('refreshPublicListBtn');
  const publicDropsGrid = document.getElementById('publicDropsGrid');
  const publicEmptyState = document.getElementById('publicEmptyState');

  const publicUnlockModal = document.getElementById('publicUnlockModal');
  const closePublicUnlockBtn = document.getElementById('closePublicUnlockBtn');
  const publicUnlockForm = document.getElementById('publicUnlockForm');
  const unlockDropTitle = document.getElementById('unlockDropTitle');
  const unlockDropMeta = document.getElementById('unlockDropMeta');
  const unlockDropPassword = document.getElementById('unlockDropPassword');
  const unlockDropError = document.getElementById('unlockDropError');
  const unlockedFilesContainer = document.getElementById('unlockedFilesContainer');
  const unlockedFilesList = document.getElementById('unlockedFilesList');

  // Fetch Server Info
  async function fetchServerInfo() {
    try {
      const res = await fetch('/api/info');
      if (res.ok) {
        const data = await res.json();
        if (networkIp) networkIp.textContent = `${data.primary_ip}:${data.port}`;
      }
    } catch (err) {
      if (networkIp) networkIp.textContent = 'Disconnected';
    }
  }

  fetchServerInfo();

  // Dropzone File Select Handling
  if (browseFilesBtn && publicDropFileInput) {
    browseFilesBtn.addEventListener('click', () => publicDropFileInput.click());
  }

  if (dropzone && publicDropFileInput) {
    dropzone.addEventListener('click', (e) => {
      if (e.target !== browseFilesBtn) {
        publicDropFileInput.click();
      }
    });

    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
      dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        publicDropFileInput.files = e.dataTransfer.files;
        updateDropzoneLabel();
      }
    });

    publicDropFileInput.addEventListener('change', updateDropzoneLabel);
  }

  function updateDropzoneLabel() {
    const files = publicDropFileInput.files;
    if (files && files.length > 0) {
      if (dropzoneTitle) dropzoneTitle.textContent = `📁 ${files.length} file(s) selected`;
      if (dropzoneSubtitle) {
        const names = Array.from(files).map(f => f.name).join(', ');
        dropzoneSubtitle.textContent = names.length > 60 ? names.substring(0, 60) + '...' : names;
      }
    } else {
      if (dropzoneTitle) dropzoneTitle.textContent = 'Drag & Drop Files Here';
      if (dropzoneSubtitle) dropzoneSubtitle.textContent = 'or click to browse files from your computer / phone';
    }
  }

  // Handle Public Drop Upload
  if (publicUploadForm) {
    publicUploadForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const title = publicDropTitle.value.trim();
      const password = publicDropPassword.value.trim();
      const files = publicDropFileInput.files;

      if (!password) {
        showToast('Please set a password for the public share drop', true);
        return;
      }
      if (!files || files.length === 0) {
        showToast('Please select at least one file to upload', true);
        return;
      }

      const formData = new FormData();
      formData.append('title', title);
      formData.append('password', password);
      for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
      }

      try {
        if (uploadProgress) uploadProgress.style.width = '50%';
        showToast('Uploading public drop...');

        const res = await fetch('/api/public/create', {
          method: 'POST',
          body: formData
        });

        if (uploadProgress) uploadProgress.style.width = '100%';

        const data = await res.json();
        if (res.ok && data.status === 'success') {
          showToast(data.message || 'Public drop created successfully!');
          publicUploadForm.reset();
          updateDropzoneLabel();
          loadPublicShares();
        } else {
          showToast(data.error || 'Failed to create public drop', true);
        }
      } catch (err) {
        showToast('Network error during public drop creation', true);
      } finally {
        setTimeout(() => {
          if (uploadProgress) uploadProgress.style.width = '0%';
        }, 600);
      }
    });
  }

  // Fetch Public Shares List
  async function loadPublicShares() {
    try {
      const res = await fetch('/api/public/list');
      if (!res.ok) return;
      const data = await res.json();
      publicSharesData = data.public_shares || [];
      renderPublicShares();
    } catch (err) {
      console.error('Error fetching public shares:', err);
    }
  }

  if (refreshPublicListBtn) {
    refreshPublicListBtn.addEventListener('click', () => {
      loadPublicShares();
      showToast('Public drops list refreshed!');
    });
  }

  function renderPublicShares() {
    if (!publicDropsGrid) return;
    publicDropsGrid.innerHTML = '';

    if (publicSharesData.length === 0) {
      if (publicEmptyState) publicEmptyState.style.display = 'block';
      return;
    }

    if (publicEmptyState) publicEmptyState.style.display = 'none';

    publicSharesData.forEach(share => {
      const card = document.createElement('div');
      card.className = 'public-drop-card';
      card.dataset.shareId = share.share_id;

      const remainingSecs = Math.max(0, Math.floor(share.expires_at - (Date.now() / 1000)));
      const mins = Math.floor(remainingSecs / 60);
      const secs = remainingSecs % 60;
      const timeStr = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;

      card.innerHTML = `
        <div class="public-drop-header">
          <div class="public-drop-icon">📦</div>
          <span class="timer-badge ${mins < 5 ? 'warning' : ''}" id="timer-${share.share_id}">
            ⏱️ ${timeStr}
          </span>
        </div>
        <div>
          <div class="public-drop-title">${escapeHtml(share.title)}</div>
          <div class="public-drop-info">
            📄 ${share.file_count} file(s) • ${share.total_size_formatted}
          </div>
          <div class="public-drop-info" style="margin-top: 0.2rem; font-size: 0.78rem; opacity: 0.7;">
            Created at ${escapeHtml(share.created_at_formatted)}
          </div>
        </div>
        <button class="btn btn-primary cyan w-full unlock-drop-btn" data-share-id="${share.share_id}">
          🔓 Unlock & View Files
        </button>
      `;

      publicDropsGrid.appendChild(card);
    });

    document.querySelectorAll('.unlock-drop-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const sId = e.currentTarget.getAttribute('data-share-id');
        openUnlockModal(sId);
      });
    });
  }

  function updatePublicShareTimers() {
    if (!publicSharesData || publicSharesData.length === 0) return;
    const nowSecs = Date.now() / 1000;

    publicSharesData.forEach(share => {
      const remainingSecs = Math.max(0, Math.floor(share.expires_at - nowSecs));
      const badge = document.getElementById(`timer-${share.share_id}`);
      if (badge) {
        const mins = Math.floor(remainingSecs / 60);
        const secs = remainingSecs % 60;
        badge.textContent = `⏱️ ${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        if (mins < 5) badge.classList.add('warning');
      }
    });
  }

  if (!publicTimerInterval) {
    publicTimerInterval = setInterval(() => {
      updatePublicShareTimers();
    }, 1000);
  }

  function openUnlockModal(shareId) {
    currentUnlockShareId = shareId;
    const share = publicSharesData.find(s => s.share_id === shareId);
    if (share) {
      if (unlockDropTitle) unlockDropTitle.textContent = `📦 ${share.title}`;
      if (unlockDropMeta) unlockDropMeta.textContent = `${share.file_count} File(s) • Protected Drop`;
    }
    if (unlockDropPassword) unlockDropPassword.value = '';
    if (unlockDropError) unlockDropError.style.display = 'none';
    if (unlockedFilesContainer) unlockedFilesContainer.style.display = 'none';
    if (unlockedFilesList) unlockedFilesList.innerHTML = '';
    if (publicUnlockModal) publicUnlockModal.classList.add('active');
  }

  if (closePublicUnlockBtn) {
    closePublicUnlockBtn.addEventListener('click', () => {
      publicUnlockModal.classList.remove('active');
    });
  }

  // Handle Unlock Form Submission
  if (publicUnlockForm) {
    publicUnlockForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const password = unlockDropPassword.value.trim();
      if (!currentUnlockShareId || !password) return;

      try {
        const res = await fetch('/api/public/unlock', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ share_id: currentUnlockShareId, password })
        });
        const data = await res.json();
        if (res.ok && data.status === 'success') {
          if (unlockDropError) unlockDropError.style.display = 'none';
          renderUnlockedFiles(data.unlocked.files);
        } else {
          if (unlockDropError) {
            unlockDropError.textContent = data.error || 'Invalid password';
            unlockDropError.style.display = 'block';
          }
        }
      } catch (err) {
        if (unlockDropError) {
          unlockDropError.textContent = 'Network error verifying password';
          unlockDropError.style.display = 'block';
        }
      }
    });
  }

  function renderUnlockedFiles(files) {
    if (!unlockedFilesList || !unlockedFilesContainer) return;
    unlockedFilesList.innerHTML = '';

    files.forEach(f => {
      const item = document.createElement('div');
      item.className = 'unlocked-file-item';
      item.innerHTML = `
        <div style="display: flex; align-items: center; gap: 0.5rem;">
          <span>📄</span>
          <div>
            <div class="unlocked-file-name">${escapeHtml(f.name)}</div>
            <div style="font-size: 0.78rem; color: var(--text-muted);">${f.size_formatted}</div>
          </div>
        </div>
        <a href="${f.download_url}" download class="btn btn-primary cyan" style="padding: 0.4rem 0.8rem; font-size: 0.82rem;">
          ⬇️ Download
        </a>
      `;
      unlockedFilesList.appendChild(item);
    });

    unlockedFilesContainer.style.display = 'block';
  }

  loadPublicShares();

  // Utilities
  function showToast(msg, isError = false) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
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
