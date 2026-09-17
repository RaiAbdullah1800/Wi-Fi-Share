document.addEventListener('DOMContentLoaded', () => {
  // Application State
  let activeDrops = [];
  let currentFilter = 'all';
  let unlockedDropsCache = {}; // { drop_id: unlockedData }
  let activePromptDropId = null;
  let serverPrimaryUrl = window.location.origin;
  let qrcodeInstance = null;

  // DOM References - Headers & Nav
  const networkIp = document.getElementById('networkIp');
  const openQrBtn = document.getElementById('openQrBtn');
  const tabBtnFiles = document.getElementById('tabBtnFiles');
  const tabBtnText = document.getElementById('tabBtnText');
  const filesTab = document.getElementById('files-tab');
  const textTab = document.getElementById('text-tab');

  // DOM References - File Drop Form
  const fileDropForm = document.getElementById('fileDropForm');
  const dropzone = document.getElementById('dropzone');
  const fileDropInput = document.getElementById('fileDropInput');
  const browseFilesBtn = document.getElementById('browseFilesBtn');
  const dropzoneTitle = document.getElementById('dropzoneTitle');
  const dropzoneSubtitle = document.getElementById('dropzoneSubtitle');
  const uploadProgressBar = document.getElementById('uploadProgressBar');
  const fileDropTitle = document.getElementById('fileDropTitle');
  const fileDropPassword = document.getElementById('fileDropPassword');
  const fileDropLifetime = document.getElementById('fileDropLifetime');
  const submitFileDropBtn = document.getElementById('submitFileDropBtn');

  // DOM References - Text Drop Form
  const textDropForm = document.getElementById('textDropForm');
  const textDropContent = document.getElementById('textDropContent');
  const textDropTitle = document.getElementById('textDropTitle');
  const textDropPassword = document.getElementById('textDropPassword');
  const textDropLifetime = document.getElementById('textDropLifetime');
  const textDropBurnAfterRead = document.getElementById('textDropBurnAfterRead');
  const charCountDisplay = document.getElementById('charCountDisplay');
  const lineCountDisplay = document.getElementById('lineCountDisplay');
  const submitTextDropBtn = document.getElementById('submitTextDropBtn');

  // DOM References - Feed & Filters
  const dropsGrid = document.getElementById('dropsGrid');
  const dropsEmptyState = document.getElementById('dropsEmptyState');
  const refreshDropsBtn = document.getElementById('refreshDropsBtn');
  const totalDropsCount = document.getElementById('totalDropsCount');
  const filesDropsCount = document.getElementById('filesDropsCount');
  const textDropsCount = document.getElementById('textDropsCount');
  const filterButtons = document.querySelectorAll('.filter-btn');

  // DOM References - Unlock Modal
  const unlockModal = document.getElementById('unlockModal');
  const closeUnlockModalBtn = document.getElementById('closeUnlockModalBtn');
  const cancelUnlockBtn = document.getElementById('cancelUnlockBtn');
  const unlockForm = document.getElementById('unlockForm');
  const unlockModalIcon = document.getElementById('unlockModalIcon');
  const unlockModalTitle = document.getElementById('unlockModalTitle');
  const unlockModalSubtitle = document.getElementById('unlockModalSubtitle');
  const unlockPassword = document.getElementById('unlockPassword');
  const unlockErrorBanner = document.getElementById('unlockErrorBanner');

  // DOM References - File Folder Modal
  const filesViewModal = document.getElementById('filesViewModal');
  const closeFilesViewBtn = document.getElementById('closeFilesViewBtn');
  const unlockedFolderTitle = document.getElementById('unlockedFolderTitle');
  const unlockedFolderMeta = document.getElementById('unlockedFolderMeta');
  const unlockedFolderTimer = document.getElementById('unlockedFolderTimer');
  const unlockedFilesList = document.getElementById('unlockedFilesList');
  const lockFolderNowBtn = document.getElementById('lockFolderNowBtn');

  // DOM References - Text View Modal
  const textViewModal = document.getElementById('textViewModal');
  const closeTextViewBtn = document.getElementById('closeTextViewBtn');
  const unlockedTextTitle = document.getElementById('unlockedTextTitle');
  const unlockedTextMeta = document.getElementById('unlockedTextMeta');
  const unlockedTextTimer = document.getElementById('unlockedTextTimer');
  const unlockedTextContent = document.getElementById('unlockedTextContent');
  const burnAlertBanner = document.getElementById('burnAlertBanner');
  const copyNoteContentBtn = document.getElementById('copyNoteContentBtn');

  // DOM References - QR Code Modal
  const qrModal = document.getElementById('qrModal');
  const closeQrBtn = document.getElementById('closeQrBtn');
  const qrcodeDiv = document.getElementById('qrcode');
  const modalUrlDisplay = document.getElementById('modalUrlDisplay');
  const copyUrlBtn = document.getElementById('copyUrlBtn');

  // --- 1. NETWORK INFO ---
  async function fetchServerInfo() {
    try {
      const res = await fetch('/api/info');
      if (res.ok) {
        const data = await res.json();
        const primaryIp = data.primary_ip || window.location.hostname;
        const port = data.port || window.location.port || 5000;
        serverPrimaryUrl = `http://${primaryIp}:${port}`;
        if (networkIp) networkIp.textContent = `${primaryIp}:${port}`;
        if (modalUrlDisplay) modalUrlDisplay.textContent = serverPrimaryUrl;
      }
    } catch (err) {
      if (networkIp) networkIp.textContent = window.location.host;
    }
  }

  fetchServerInfo();

  // --- 2. TAB SWITCHING ---
  function switchTab(target) {
    if (target === 'files') {
      tabBtnFiles.classList.add('active');
      tabBtnText.classList.remove('active');
      filesTab.classList.add('active');
      textTab.classList.remove('active');
    } else {
      tabBtnText.classList.add('active');
      tabBtnFiles.classList.remove('active');
      textTab.classList.add('active');
      filesTab.classList.remove('active');
      if (textDropContent) textDropContent.focus();
    }
  }

  if (tabBtnFiles) tabBtnFiles.addEventListener('click', () => switchTab('files'));
  if (tabBtnText) tabBtnText.addEventListener('click', () => switchTab('text'));

  // --- 3. FILE DROP UPLOADER LOGIC ---
  if (browseFilesBtn && fileDropInput) {
    browseFilesBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      fileDropInput.click();
    });
  }

  if (dropzone && fileDropInput) {
    dropzone.addEventListener('click', (e) => {
      if (e.target !== browseFilesBtn) {
        fileDropInput.click();
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
        fileDropInput.files = e.dataTransfer.files;
        updateDropzoneLabel();
      }
    });

    fileDropInput.addEventListener('change', updateDropzoneLabel);
  }

  function updateDropzoneLabel() {
    const files = fileDropInput.files;
    if (files && files.length > 0) {
      dropzoneTitle.textContent = `📁 ${files.length} file${files.length > 1 ? 's' : ''} selected`;
      const names = Array.from(files).map(f => f.name).join(', ');
      dropzoneSubtitle.textContent = names.length > 60 ? names.substring(0, 60) + '...' : names;
    } else {
      dropzoneTitle.textContent = 'Drag & Drop Files Here';
      dropzoneSubtitle.textContent = 'or click anywhere inside this box to browse files';
    }
  }

  if (fileDropForm) {
    fileDropForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const files = fileDropInput.files;
      const password = fileDropPassword.value.trim();
      const title = fileDropTitle.value.trim();
      const lifetime = fileDropLifetime.value;

      if (!files || files.length === 0) {
        showToast('Please select at least one file', true);
        return;
      }
      if (!password) {
        showToast('Please set an unlock password or PIN', true);
        return;
      }

      const formData = new FormData();
      formData.append('title', title);
      formData.append('password', password);
      formData.append('lifetime', lifetime);
      for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
      }

      try {
        submitFileDropBtn.disabled = true;
        submitFileDropBtn.textContent = 'Uploading files...';
        if (uploadProgressBar) uploadProgressBar.style.width = '60%';

        const res = await fetch('/api/drops/upload', {
          method: 'POST',
          body: formData
        });

        if (uploadProgressBar) uploadProgressBar.style.width = '100%';
        const data = await res.json();

        if (res.ok && data.status === 'success') {
          showToast(data.message || 'File drop created successfully!');
          fileDropForm.reset();
          updateDropzoneLabel();
          loadDrops();
        } else {
          showToast(data.error || 'Failed to create file drop', true);
        }
      } catch (err) {
        showToast('Network error while uploading files', true);
      } finally {
        submitFileDropBtn.disabled = false;
        submitFileDropBtn.textContent = '🚀 Create & Publish File Drop';
        setTimeout(() => {
          if (uploadProgressBar) uploadProgressBar.style.width = '0%';
        }, 600);
      }
    });
  }

  // --- 4. TEXT DROP LOGIC ---
  if (textDropContent) {
    textDropContent.addEventListener('input', updateTextCounters);

    // Support Tab key inside textarea
    textDropContent.addEventListener('keydown', (e) => {
      if (e.key === 'Tab') {
        e.preventDefault();
        const start = textDropContent.selectionStart;
        const end = textDropContent.selectionEnd;
        textDropContent.value = textDropContent.value.substring(0, start) + '  ' + textDropContent.value.substring(end);
        textDropContent.selectionStart = textDropContent.selectionEnd = start + 2;
        updateTextCounters();
      }
    });
  }

  function updateTextCounters() {
    const text = textDropContent ? textDropContent.value : '';
    const chars = text.length;
    const lines = text ? text.split('\n').length : 0;
    if (charCountDisplay) charCountDisplay.textContent = `${chars} char${chars !== 1 ? 's' : ''}`;
    if (lineCountDisplay) lineCountDisplay.textContent = `${lines} line${lines !== 1 ? 's' : ''}`;
  }

  if (textDropForm) {
    textDropForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const content = textDropContent.value.trim();
      const password = textDropPassword.value.trim();
      const title = textDropTitle.value.trim();
      const lifetime = textDropLifetime.value;
      const burnAfterRead = textDropBurnAfterRead.checked;

      if (!content) {
        showToast('Please enter or paste some text', true);
        return;
      }
      if (!password) {
        showToast('Please set an unlock password or PIN', true);
        return;
      }

      try {
        submitTextDropBtn.disabled = true;
        submitTextDropBtn.textContent = 'Locking note...';

        const res = await fetch('/api/drops/paste', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            content,
            password,
            title,
            lifetime: parseInt(lifetime),
            burn_after_read: burnAfterRead
          })
        });

        const data = await res.json();
        if (res.ok && data.status === 'success') {
          showToast(data.message || 'Locked text note created!');
          textDropForm.reset();
          updateTextCounters();
          loadDrops();
        } else {
          showToast(data.error || 'Failed to create text note', true);
        }
      } catch (err) {
        showToast('Network error creating text note', true);
      } finally {
        submitTextDropBtn.disabled = false;
        submitTextDropBtn.textContent = '🔒 Lock & Publish Text Note';
      }
    });
  }

  // --- 5. DROPS FEED & FILTERING ---
  async function loadDrops() {
    try {
      const res = await fetch('/api/drops');
      if (!res.ok) return;
      const data = await res.json();
      activeDrops = data.drops || [];
      updateCounts();
      renderDrops();
    } catch (err) {
      console.error('Error fetching drops:', err);
    }
  }

  function updateCounts() {
    const total = activeDrops.length;
    const filesCount = activeDrops.filter(d => d.drop_type === 'files').length;
    const textCount = activeDrops.filter(d => d.drop_type === 'text').length;

    if (totalDropsCount) totalDropsCount.textContent = total;
    if (filesDropsCount) filesDropsCount.textContent = filesCount;
    if (textDropsCount) textDropsCount.textContent = textCount;
  }

  filterButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      filterButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.dataset.filter;
      renderDrops();
    });
  });

  if (refreshDropsBtn) {
    refreshDropsBtn.addEventListener('click', () => {
      loadDrops();
      showToast('Drops refreshed!');
    });
  }

  function renderDrops() {
    if (!dropsGrid) return;
    dropsGrid.innerHTML = '';

    const filtered = activeDrops.filter(d => {
      if (currentFilter === 'files') return d.drop_type === 'files';
      if (currentFilter === 'text') return d.drop_type === 'text';
      return true;
    });

    if (filtered.length === 0) {
      if (dropsEmptyState) dropsEmptyState.style.display = 'block';
      return;
    }

    if (dropsEmptyState) dropsEmptyState.style.display = 'none';

    const now = Date.now() / 1000;

    filtered.forEach(drop => {
      const isUnlocked = !!unlockedDropsCache[drop.drop_id];
      const isFile = drop.drop_type === 'files';
      const remainingSecs = Math.max(0, Math.floor(drop.expires_at - now));
      const mins = Math.floor(remainingSecs / 60);
      const secs = remainingSecs % 60;
      const timeStr = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;

      const card = document.createElement('div');
      card.className = `drop-card type-${drop.drop_type}`;
      card.dataset.dropId = drop.drop_id;

      let metaText = '';
      if (isFile) {
        metaText = `📄 ${drop.file_count} file${drop.file_count !== 1 ? 's' : ''} • ${drop.total_size_formatted}`;
      } else {
        metaText = `📝 ${drop.char_count} chars • ${drop.line_count} lines`;
        if (drop.burn_after_read) {
          metaText += ' • 🔥 Burn on read';
        }
      }

      card.innerHTML = `
        <div class="drop-card-top">
          <span class="drop-type-badge ${isFile ? 'cyan' : 'purple'}">
            ${isFile ? '📦 File Drop' : '📝 Text Note'}
          </span>
          <span class="timer-badge ${mins < 5 ? 'warning' : ''}" id="timer-${drop.drop_id}">
            ⏱️ ${timeStr}
          </span>
        </div>

        <div>
          <div class="drop-card-title">${escapeHtml(drop.title)}</div>
          <div class="drop-card-meta">${metaText}</div>
          <div class="drop-card-meta" style="font-size: 0.75rem; opacity: 0.6; margin-top: 0.2rem;">
            Created at ${escapeHtml(drop.created_at_formatted)}
          </div>
        </div>

        <div class="drop-card-footer">
          <span>${isUnlocked ? '✅ Unlocked' : (drop.burn_after_read ? '🔥 Locked (Burn)' : '🔒 Password Locked')}</span>
          <span class="action">${isUnlocked ? 'Open ➔' : 'Click to Unlock ➔'}</span>
        </div>
      `;

      card.addEventListener('click', () => handleDropClick(drop.drop_id));
      dropsGrid.appendChild(card);
    });
  }

  // --- 6. LIVE TIMERS ---
  setInterval(() => {
    if (!activeDrops || activeDrops.length === 0) return;
    const now = Date.now() / 1000;

    activeDrops.forEach(drop => {
      const remainingSecs = Math.max(0, Math.floor(drop.expires_at - now));
      const mins = Math.floor(remainingSecs / 60);
      const secs = remainingSecs % 60;
      const timeStr = `⏱️ ${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;

      const badge = document.getElementById(`timer-${drop.drop_id}`);
      if (badge) {
        badge.textContent = timeStr;
        if (mins < 5) badge.classList.add('warning');
      }

      // If unlocked in files view modal
      if (unlockedFolderTimer && filesViewModal.classList.contains('active') && filesViewModal.dataset.dropId === drop.drop_id) {
        unlockedFolderTimer.textContent = timeStr;
      }
      // If unlocked in text view modal
      if (unlockedTextTimer && textViewModal.classList.contains('active') && textViewModal.dataset.dropId === drop.drop_id) {
        unlockedTextTimer.textContent = timeStr;
      }
    });
  }, 1000);

  // --- 7. HANDLE DROP CLICK & UNLOCK ---
  function handleDropClick(dropId) {
    if (unlockedDropsCache[dropId]) {
      const data = unlockedDropsCache[dropId];
      if (data.drop_type === 'files') {
        openFilesModal(data);
      } else {
        openTextModal(data);
      }
      return;
    }

    openUnlockModal(dropId);
  }

  function openUnlockModal(dropId) {
    activePromptDropId = dropId;
    const drop = activeDrops.find(d => d.drop_id === dropId);
    if (!drop) return;

    if (unlockModalTitle) unlockModalTitle.textContent = drop.title;
    if (unlockModalSubtitle) {
      unlockModalSubtitle.textContent = drop.drop_type === 'files'
        ? `Enter password to open folder (${drop.file_count} files)`
        : `Enter password to read note (${drop.char_count} chars)`;
    }
    if (unlockModalIcon) {
      unlockModalIcon.textContent = drop.drop_type === 'files' ? '📁' : '📝';
    }
    if (unlockPassword) unlockPassword.value = '';
    if (unlockErrorBanner) unlockErrorBanner.style.display = 'none';

    if (unlockModal) unlockModal.classList.add('active');
    setTimeout(() => {
      if (unlockPassword) unlockPassword.focus();
    }, 100);
  }

  function closeUnlockModal() {
    if (unlockModal) unlockModal.classList.remove('active');
    activePromptDropId = null;
  }

  if (closeUnlockModalBtn) closeUnlockModalBtn.addEventListener('click', closeUnlockModal);
  if (cancelUnlockBtn) cancelUnlockBtn.addEventListener('click', closeUnlockModal);

  if (unlockForm) {
    unlockForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const password = unlockPassword.value.trim();
      if (!activePromptDropId || !password) return;

      try {
        const res = await fetch('/api/drops/unlock', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ drop_id: activePromptDropId, password })
        });

        const data = await res.json();
        if (res.ok && data.status === 'success') {
          const unlocked = data.unlocked;
          const dropId = activePromptDropId;

          closeUnlockModal();

          if (unlocked.burn_after_read) {
            // Drop destroyed upon viewing: do not cache for re-entry, refresh feed
            loadDrops();
            openTextModal(unlocked);
            showToast('Note unlocked! Notice: Burn-after-read activated.', true);
          } else {
            unlockedDropsCache[dropId] = unlocked;
            renderDrops();
            showToast('Drop unlocked successfully!');
            if (unlocked.drop_type === 'files') {
              openFilesModal(unlocked);
            } else {
              openTextModal(unlocked);
            }
          }
        } else {
          if (unlockErrorBanner) {
            unlockErrorBanner.textContent = data.error || 'Incorrect password or PIN';
            unlockErrorBanner.style.display = 'block';
          }
        }
      } catch (err) {
        if (unlockErrorBanner) {
          unlockErrorBanner.textContent = 'Network error verifying password';
          unlockErrorBanner.style.display = 'block';
        }
      }
    });
  }

  // --- 8. MODAL: UNLOCKED FILES FOLDER ---
  function openFilesModal(unlocked) {
    if (!filesViewModal) return;
    filesViewModal.dataset.dropId = unlocked.drop_id;
    if (unlockedFolderTitle) unlockedFolderTitle.textContent = unlocked.title;
    if (unlockedFolderMeta) {
      const totalSize = unlocked.files.reduce((a, b) => a + b.size, 0);
      unlockedFolderMeta.textContent = `${unlocked.files.length} file(s) available for download`;
    }

    renderUnlockedFiles(unlocked.files);
    filesViewModal.classList.add('active');
  }

  function renderUnlockedFiles(files) {
    if (!unlockedFilesList) return;
    unlockedFilesList.innerHTML = '';

    files.forEach(f => {
      const row = document.createElement('div');
      row.className = 'file-row';
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
            ⬇️ Download
          </a>
        </div>
      `;

      unlockedFilesList.appendChild(row);
    });
  }

  if (closeFilesViewBtn) {
    closeFilesViewBtn.addEventListener('click', () => {
      filesViewModal.classList.remove('active');
    });
  }

  if (lockFolderNowBtn) {
    lockFolderNowBtn.addEventListener('click', () => {
      const dropId = filesViewModal.dataset.dropId;
      if (dropId && unlockedDropsCache[dropId]) {
        delete unlockedDropsCache[dropId];
        renderDrops();
        showToast('Folder locked');
      }
      filesViewModal.classList.remove('active');
    });
  }

  // --- 9. MODAL: UNLOCKED TEXT NOTE ---
  function openTextModal(unlocked) {
    if (!textViewModal) return;
    textViewModal.dataset.dropId = unlocked.drop_id;
    if (unlockedTextTitle) unlockedTextTitle.textContent = unlocked.title;
    if (unlockedTextMeta) {
      unlockedTextMeta.textContent = `${unlocked.char_count} chars • ${unlocked.line_count} lines`;
    }
    if (unlockedTextContent) {
      unlockedTextContent.textContent = unlocked.content;
    }

    if (burnAlertBanner) {
      burnAlertBanner.style.display = unlocked.burn_after_read ? 'block' : 'none';
    }

    textViewModal.classList.add('active');
  }

  if (closeTextViewBtn) {
    closeTextViewBtn.addEventListener('click', () => {
      textViewModal.classList.remove('active');
    });
  }

  if (copyNoteContentBtn) {
    copyNoteContentBtn.addEventListener('click', async () => {
      if (!unlockedTextContent) return;
      const text = unlockedTextContent.textContent;
      try {
        await navigator.clipboard.writeText(text);
        copyNoteContentBtn.textContent = '✅ Copied!';
        showToast('Text copied to clipboard!');
        setTimeout(() => {
          copyNoteContentBtn.textContent = '📋 Copy Text';
        }, 2000);
      } catch (err) {
        showToast('Failed to copy text', true);
      }
    });
  }

  // --- 10. QR CODE MODAL ---
  if (openQrBtn) {
    openQrBtn.addEventListener('click', () => {
      if (modalUrlDisplay) modalUrlDisplay.textContent = serverPrimaryUrl;

      if (qrcodeDiv) {
        qrcodeDiv.innerHTML = '';
        if (typeof QRCode !== 'undefined') {
          qrcodeInstance = new QRCode(qrcodeDiv, {
            text: serverPrimaryUrl,
            width: 200,
            height: 200,
            colorDark: '#000000',
            colorLight: '#ffffff',
            correctLevel: QRCode.CorrectLevel.M
          });
        } else {
          qrcodeDiv.innerHTML = `<p style="color: #333; padding: 1rem; text-align: center;">Open:<br><strong>${serverPrimaryUrl}</strong></p>`;
        }
      }

      if (qrModal) qrModal.classList.add('active');
    });
  }

  if (closeQrBtn) {
    closeQrBtn.addEventListener('click', () => {
      if (qrModal) qrModal.classList.remove('active');
    });
  }

  if (copyUrlBtn) {
    copyUrlBtn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(serverPrimaryUrl);
        copyUrlBtn.textContent = 'Copied!';
        showToast('Address copied to clipboard!');
        setTimeout(() => {
          copyUrlBtn.textContent = 'Copy Link';
        }, 2000);
      } catch (err) {
        showToast('Could not copy link', true);
      }
    });
  }

  // Close modals on clicking overlay outside card
  document.querySelectorAll('.modal-overlay').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.classList.remove('active');
      }
    });
  });

  // --- UTILITIES ---
  function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext)) return '🖼️';
    if (['mp4', 'mkv', 'avi', 'mov', 'webm'].includes(ext)) return '🎬';
    if (['mp3', 'wav', 'flac', 'm4a'].includes(ext)) return '🎵';
    if (['pdf'].includes(ext)) return '📕';
    if (['zip', 'tar', 'gz', '7z', 'rar'].includes(ext)) return '📦';
    if (['py', 'js', 'html', 'css', 'json', 'c', 'cpp', 'rs', 'go', 'sh'].includes(ext)) return '💻';
    if (['txt', 'md', 'doc', 'docx'].includes(ext)) return '📄';
    return '📁';
  }

  function showToast(msg, isError = false) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${isError ? 'error' : ''}`;

    toast.innerHTML = `
      <span>${isError ? '⚠️' : '✅'}</span>
      <span>${escapeHtml(msg)}</span>
    `;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      setTimeout(() => toast.remove(), 300);
    }, 3200);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, function(m) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m];
    });
  }

  // Initial Load
  loadDrops();
});
