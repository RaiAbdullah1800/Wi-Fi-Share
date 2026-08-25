document.addEventListener('DOMContentLoaded', () => {
  let publicSharesData = [];
  let unlockedShares = {}; // Cache unlocked folder data: { share_id: { token, title, files, expires_at } }
  let activePromptShareId = null;
  let currentOpenShareId = null;
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
  const publicFoldersGrid = document.getElementById('publicFoldersGrid');
  const publicEmptyState = document.getElementById('publicEmptyState');

  // View Containers
  const publicFoldersView = document.getElementById('publicFoldersView');
  const folderExplorerView = document.getElementById('folderExplorerView');
  const backToFoldersBtn = document.getElementById('backToFoldersBtn');
  const explorerFolderName = document.getElementById('explorerFolderName');
  const explorerTimerBadge = document.getElementById('explorerTimerBadge');
  const lockFolderBtn = document.getElementById('lockFolderBtn');
  const explorerHeaderTitle = document.getElementById('explorerHeaderTitle');
  const explorerHeaderMeta = document.getElementById('explorerHeaderMeta');
  const explorerFilesList = document.getElementById('explorerFilesList');

  // Password Prompt Modal Elements
  const folderPasswordModal = document.getElementById('folderPasswordModal');
  const closePasswordModalBtn = document.getElementById('closePasswordModalBtn');
  const cancelPasswordBtn = document.getElementById('cancelPasswordBtn');
  const folderPasswordForm = document.getElementById('folderPasswordForm');
  const promptFolderTitle = document.getElementById('promptFolderTitle');
  const promptFolderPassword = document.getElementById('promptFolderPassword');
  const promptFolderError = document.getElementById('promptFolderError');

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

  // Dropzone Handlers
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

  // Handle Upload Form Submit
  if (publicUploadForm) {
    publicUploadForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const title = publicDropTitle.value.trim();
      const password = publicDropPassword.value.trim();
      const files = publicDropFileInput.files;

      if (!password) {
        showToast('Please set a password for the public folder', true);
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
        showToast('Uploading public folder...');

        const res = await fetch('/api/public/create', {
          method: 'POST',
          body: formData
        });

        if (uploadProgress) uploadProgress.style.width = '100%';

        const data = await res.json();
        if (res.ok && data.status === 'success') {
          showToast(data.message || 'Public folder created successfully!');
          publicUploadForm.reset();
          updateDropzoneLabel();
          loadPublicShares();
        } else {
          showToast(data.error || 'Failed to create public drop', true);
        }
      } catch (err) {
        showToast('Network error during folder creation', true);
      } finally {
        setTimeout(() => {
          if (uploadProgress) uploadProgress.style.width = '0%';
        }, 600);
      }
    });
  }

  // Load Active Public Folders
  async function loadPublicShares() {
    try {
      const res = await fetch('/api/public/list');
      if (!res.ok) return;
      const data = await res.json();
      publicSharesData = data.public_shares || [];
      renderPublicFolders();
    } catch (err) {
      console.error('Error fetching public shares:', err);
    }
  }

  if (refreshPublicListBtn) {
    refreshPublicListBtn.addEventListener('click', () => {
      loadPublicShares();
      showToast('Folders list refreshed!');
    });
  }

  // Render Folders Grid
  function renderPublicFolders() {
    if (!publicFoldersGrid) return;
    publicFoldersGrid.innerHTML = '';

    if (publicSharesData.length === 0) {
      if (publicEmptyState) publicEmptyState.style.display = 'block';
      return;
    }

    if (publicEmptyState) publicEmptyState.style.display = 'none';

    publicSharesData.forEach(share => {
      const isUnlocked = !!unlockedShares[share.share_id];
      const card = document.createElement('div');
      card.className = 'public-folder-card';
      card.dataset.shareId = share.share_id;

      const remainingSecs = Math.max(0, Math.floor(share.expires_at - (Date.now() / 1000)));
      const mins = Math.floor(remainingSecs / 60);
      const secs = remainingSecs % 60;
      const timeStr = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;

      card.innerHTML = `
        <div class="folder-card-top">
          <div class="folder-big-icon">${isUnlocked ? '📂' : '📁'}</div>
          <span class="timer-badge ${mins < 5 ? 'warning' : ''}" id="timer-${share.share_id}">
            ⏱️ ${timeStr}
          </span>
        </div>
        <div>
          <div class="folder-title-text">${escapeHtml(share.title)}</div>
          <div class="folder-sub-text">
            📄 ${share.file_count} file(s) • ${share.total_size_formatted}
          </div>
          <div class="folder-sub-text" style="margin-top: 0.2rem; opacity: 0.6;">
            Created at ${escapeHtml(share.created_at_formatted)}
          </div>
        </div>
        <div class="folder-action-bar">
          <span>${isUnlocked ? '✅ Unlocked' : '🔒 Password Protected'}</span>
          <span>${isUnlocked ? 'Open Folder ➔' : 'Click to Open ➔'}</span>
        </div>
      `;

      card.addEventListener('click', () => {
        handleFolderClick(share.share_id);
      });

      publicFoldersGrid.appendChild(card);
    });
  }

  // Update Countdown Timers
  function updatePublicShareTimers() {
    if (!publicSharesData || publicSharesData.length === 0) return;
    const nowSecs = Date.now() / 1000;

    publicSharesData.forEach(share => {
      const remainingSecs = Math.max(0, Math.floor(share.expires_at - nowSecs));
      const badge = document.getElementById(`timer-${share.share_id}`);
      const mins = Math.floor(remainingSecs / 60);
      const secs = remainingSecs % 60;
      const timeStr = `⏱️ ${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;

      if (badge) {
        badge.textContent = timeStr;
        if (mins < 5) badge.classList.add('warning');
      }

      if (currentOpenShareId === share.share_id && explorerTimerBadge) {
        explorerTimerBadge.textContent = timeStr;
      }
    });
  }

  if (!publicTimerInterval) {
    publicTimerInterval = setInterval(() => {
      updatePublicShareTimers();
    }, 1000);
  }

  // Handle Clicking a Folder Card
  function handleFolderClick(shareId) {
    if (unlockedShares[shareId]) {
      // Already unlocked -> Open Explorer directly!
      openFolderExplorer(shareId);
    } else {
      // Open Password Prompt Modal
      openPasswordModal(shareId);
    }
  }

  // Open Password Modal
  function openPasswordModal(shareId) {
    activePromptShareId = shareId;
    const share = publicSharesData.find(s => s.share_id === shareId);

    if (share && promptFolderTitle) {
      promptFolderTitle.textContent = `📁 ${share.title}`;
    }
    if (promptFolderPassword) promptFolderPassword.value = '';
    if (promptFolderError) promptFolderError.style.display = 'none';

    if (folderPasswordModal) folderPasswordModal.classList.add('active');
    setTimeout(() => {
      if (promptFolderPassword) promptFolderPassword.focus();
    }, 100);
  }

  function closePasswordModal() {
    if (folderPasswordModal) folderPasswordModal.classList.remove('active');
    activePromptShareId = null;
  }

  if (closePasswordModalBtn) closePasswordModalBtn.addEventListener('click', closePasswordModal);
  if (cancelPasswordBtn) cancelPasswordBtn.addEventListener('click', closePasswordModal);

  // Handle Password Submit
  if (folderPasswordForm) {
    folderPasswordForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const password = promptFolderPassword.value.trim();
      if (!activePromptShareId || !password) return;

      try {
        const res = await fetch('/api/public/unlock', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ share_id: activePromptShareId, password })
        });
        const data = await res.json();
        if (res.ok && data.status === 'success') {
          // Store in memory
          const sId = activePromptShareId;
          unlockedShares[sId] = data.unlocked;
          closePasswordModal();
          renderPublicFolders();
          openFolderExplorer(sId);
          showToast('Folder unlocked successfully!');
        } else {
          if (promptFolderError) {
            promptFolderError.textContent = data.error || 'Invalid folder password';
            promptFolderError.style.display = 'block';
          }
        }
      } catch (err) {
        if (promptFolderError) {
          promptFolderError.textContent = 'Network error verifying password';
          promptFolderError.style.display = 'block';
        }
      }
    });
  }

  // Open Folder Explorer View
  function openFolderExplorer(shareId) {
    const unlocked = unlockedShares[shareId];
    if (!unlocked) return;

    currentOpenShareId = shareId;

    if (explorerFolderName) explorerFolderName.textContent = `📁 ${unlocked.title}`;
    if (explorerHeaderTitle) explorerHeaderTitle.textContent = `📁 ${unlocked.title}`;
    if (explorerHeaderMeta) {
      const totalSize = unlocked.files.reduce((acc, f) => acc + f.size, 0);
      explorerHeaderMeta.textContent = `${unlocked.files.length} File(s) • Unlocked Folder Access`;
    }

    renderExplorerFiles(unlocked.files);

    if (publicFoldersView) publicFoldersView.style.display = 'none';
    if (folderExplorerView) folderExplorerView.style.display = 'block';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function renderExplorerFiles(files) {
    if (!explorerFilesList) return;
    explorerFilesList.innerHTML = '';

    if (files.length === 0) {
      explorerFilesList.innerHTML = `<div class="empty-state"><h3>No files in this folder</h3></div>`;
      return;
    }

    files.forEach(f => {
      const row = document.createElement('div');
      row.className = 'explorer-file-row';
      const icon = getFileIcon(f.name);

      row.innerHTML = `
        <div class="file-row-left">
          <span class="file-row-icon">${icon}</span>
          <div>
            <div class="file-row-title">${escapeHtml(f.name)}</div>
            <div class="file-row-size">${f.size_formatted}</div>
          </div>
        </div>
        <div>
          <a href="${f.download_url}" download class="btn btn-primary cyan" style="padding: 0.5rem 1rem; font-size: 0.85rem;">
            ⬇️ Download File
          </a>
        </div>
      `;

      explorerFilesList.appendChild(row);
    });
  }

  // Back to Folders List View
  if (backToFoldersBtn) {
    backToFoldersBtn.addEventListener('click', () => {
      currentOpenShareId = null;
      if (folderExplorerView) folderExplorerView.style.display = 'none';
      if (publicFoldersView) publicFoldersView.style.display = 'block';
    });
  }

  // Re-lock Folder
  if (lockFolderBtn) {
    lockFolderBtn.addEventListener('click', () => {
      if (currentOpenShareId) {
        delete unlockedShares[currentOpenShareId];
        currentOpenShareId = null;
        renderPublicFolders();
        if (folderExplorerView) folderExplorerView.style.display = 'none';
        if (publicFoldersView) publicFoldersView.style.display = 'block';
        showToast('Folder locked');
      }
    });
  }

  function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext)) return '🖼️';
    if (['mp4', 'mkv', 'avi', 'mov', 'webm'].includes(ext)) return '🎬';
    if (['mp3', 'wav', 'flac', 'm4a'].includes(ext)) return '🎵';
    if (['pdf'].includes(ext)) return '📕';
    if (['zip', 'tar', 'gz', '7z', 'rar'].includes(ext)) return '📦';
    if (['py', 'js', 'html', 'css', 'json', 'c', 'cpp'].includes(ext)) return '💻';
    if (['txt', 'md', 'doc', 'docx'].includes(ext)) return '📄';
    return '📁';
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
