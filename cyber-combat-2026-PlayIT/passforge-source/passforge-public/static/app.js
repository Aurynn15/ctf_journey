


const state = {
  token: localStorage.getItem('pf_token') || '',
  username: localStorage.getItem('pf_username') || '',
  vaults: [],
  activeVault: null, 
  entries: [],
  activeDetailEntry: null
};


const API_BASE = '';


const el = {
  authView: document.getElementById('auth-view'),
  dashboardView: document.getElementById('dashboard-view'),
  loginForm: document.getElementById('login-form'),
  registerForm: document.getElementById('register-form'),
  tabLogin: document.getElementById('tab-login'),
  tabRegister: document.getElementById('tab-register'),
  btnGotoRecover: document.getElementById('btn-goto-recover'),
  
  userDisplayName: document.getElementById('user-display-name'),
  userDisplayEmail: document.getElementById('user-display-email'),
  btnLogout: document.getElementById('btn-logout'),
  
  vaultList: document.getElementById('vault-list'),
  btnNewVault: document.getElementById('btn-new-vault'),
  btnOpenDirectory: document.getElementById('btn-open-directory'),
  btnOpenImport: document.getElementById('btn-open-import'),
  btnExportVault: document.getElementById('btn-export-vault'),
  
  activeVaultName: document.getElementById('active-vault-name'),
  activeVaultBadge: document.getElementById('active-vault-badge'),
  activeVaultHandle: document.getElementById('active-vault-handle'),
  btnNewEntry: document.getElementById('btn-new-entry'),
  
  vaultEmptyState: document.getElementById('vault-empty-state'),
  entriesContainer: document.getElementById('entries-container'),
  entriesList: document.getElementById('entries-list'),
  vaultEntriesSearch: document.getElementById('vault-entries-search'),
  
  
  dialogCreateVault: document.getElementById('dialog-create-vault'),
  formCreateVault: document.getElementById('form-create-vault'),
  vaultNameInput: document.getElementById('vault-name'),
  vaultHandleInput: document.getElementById('vault-handle-input'),
  
  dialogCreateEntry: document.getElementById('dialog-create-entry'),
  formCreateEntry: document.getElementById('form-create-entry'),
  btnGeneratePassword: document.getElementById('btn-generate-password'),
  entryTitle: document.getElementById('entry-title'),
  entryLogin: document.getElementById('entry-login'),
  entrySecret: document.getElementById('entry-secret'),
  entryNote: document.getElementById('entry-note'),
  
  dialogDetailEntry: document.getElementById('dialog-detail-entry'),
  detailTitle: document.getElementById('detail-title'),
  detailLogin: document.getElementById('detail-login'),
  detailSecret: document.getElementById('detail-secret'),
  detailNote: document.getElementById('detail-note'),
  detailVaultHandle: document.getElementById('detail-vault-handle'),
  detailId: document.getElementById('detail-id'),
  btnRevealDetail: document.getElementById('btn-reveal-detail'),
  
  dialogDirectory: document.getElementById('dialog-directory'),
  directorySearchInput: document.getElementById('directory-search-input'),
  btnDirectorySearchSubmit: document.getElementById('btn-directory-search-submit'),
  directoryResults: document.getElementById('directory-results'),
  
  dialogImport: document.getElementById('dialog-import'),
  formImportCsv: document.getElementById('form-import-csv'),
  csvPayload: document.getElementById('csv-payload'),
  
  dialogRecovery: document.getElementById('dialog-recovery'),
  formRecoveryRequest: document.getElementById('form-recovery-request'),
  formRecoveryConfirm: document.getElementById('form-recovery-confirm'),
  recoverRequestUsername: document.getElementById('recover-request-username'),
  recoverActiveUser: document.getElementById('recover-active-user'),
  recoverToken: document.getElementById('recover-token'),
  recoverNewPassword: document.getElementById('recover-new-password'),
  btnBackToRequest: document.getElementById('btn-back-to-request'),
  toastContainer: document.getElementById('toast-container')
};


function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  let icon = '';
  if (type === 'success') {
    icon = `<svg class="w-5 h-5 text-success" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"></path></svg>`;
  } else if (type === 'error') {
    icon = `<svg class="w-5 h-5 text-danger" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"></path></svg>`;
  } else {
    icon = `<svg class="w-5 h-5 text-gold-accent" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 111.063.852l-.708 2.836a.75.75 0 001.063.852l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"></path></svg>`;
  }

  toast.innerHTML = `
    ${icon}
    <span class="flex-grow">${message}</span>
  `;
  
  el.toastContainer.appendChild(toast);
  
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-10px)';
    setTimeout(() => toast.remove(), 150);
  }, 4000);
}


async function apiFetch(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };
  
  if (state.token) {
    headers['Authorization'] = `Bearer ${state.token}`;
  }
  
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });
  
  if (response.status === 401) {
    
    handleLogout();
    throw new Error('Unauthorized');
  }
  
  return response;
}



function setupDialogBackdropDismiss(dialog) {
  if (!('closedBy' in HTMLDialogElement.prototype)) {
    dialog.addEventListener('click', (event) => {
      if (event.target !== dialog) return;
      const rect = dialog.getBoundingClientRect();
      const isDialogContent = (
        rect.top <= event.clientY &&
        event.clientY <= rect.top + rect.height &&
        rect.left <= event.clientX &&
        event.clientX <= rect.left + rect.width
      );
      if (isDialogContent) return;
      dialog.close();
    });
  }
}


function generateSecurePassword(length = 20) {
  const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?';
  const array = new Uint32Array(length);
  crypto.getRandomValues(array);
  let password = '';
  for (let i = 0; i < length; i++) {
    password += chars[array[i] % chars.length];
  }
  return password;
}


function initApp() {
  
  document.querySelectorAll('dialog').forEach(setupDialogBackdropDismiss);
  
  if (state.token) {
    checkSession();
  } else {
    showAuthView();
  }
}


function showAuthView() {
  el.authView.classList.remove('hidden');
  el.dashboardView.classList.add('hidden');
  el.loginForm.reset();
  el.registerForm.reset();
}

async function checkSession() {
  try {
    const res = await apiFetch('/api/me');
    if (res.ok) {
      const data = await res.json();
      state.username = data.username;
      localStorage.setItem('pf_username', data.username);
      
      el.userDisplayName.textContent = data.username;
      el.userDisplayEmail.textContent = data.email;
      
      el.authView.classList.add('hidden');
      el.dashboardView.classList.remove('hidden');
      
      showToast(`Welcome back, ${data.username}`, 'success');
      loadVaults();
    } else {
      handleLogout();
    }
  } catch (err) {
    console.error('Session validation error:', err);
    handleLogout();
  }
}

function handleLogout() {
  state.token = '';
  state.username = '';
  state.vaults = [];
  state.activeVault = null;
  state.entries = [];
  localStorage.removeItem('pf_token');
  localStorage.removeItem('pf_username');
  
  
  document.cookie = 'pf_session=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;';
  
  showAuthView();
}


el.tabLogin.addEventListener('click', () => {
  el.tabLogin.className = 'flex-1 pb-3 text-sm font-medium border-b-2 border-gold-accent text-white tab-btn';
  el.tabRegister.className = 'flex-1 pb-3 text-sm font-medium border-b-2 border-transparent text-muted tab-btn';
  el.loginForm.classList.remove('hidden');
  el.registerForm.classList.add('hidden');
});

el.tabRegister.addEventListener('click', () => {
  el.tabRegister.className = 'flex-1 pb-3 text-sm font-medium border-b-2 border-gold-accent text-white tab-btn';
  el.tabLogin.className = 'flex-1 pb-3 text-sm font-medium border-b-2 border-transparent text-muted tab-btn';
  el.registerForm.classList.remove('hidden');
  el.loginForm.classList.add('hidden');
});


el.loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = document.getElementById('login-username').value;
  const password = document.getElementById('login-password').value;
  
  try {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      state.token = data.token;
      state.username = data.username;
      localStorage.setItem('pf_token', data.token);
      localStorage.setItem('pf_username', data.username);
      
      checkSession();
    } else {
      showToast(data.status || 'Invalid login credentials', 'error');
    }
  } catch (err) {
    showToast('Network error during login authentication', 'error');
  }
});

el.registerForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = el.registerForm.querySelector('#register-username').value;
  const email = el.registerForm.querySelector('#register-email').value;
  const password = el.registerForm.querySelector('#register-password').value;
  
  try {
    const res = await fetch('/api/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password })
    });
    
    const data = await res.json();
    if (res.status === 200 && data.status === 'ok') {
      state.token = data.token;
      state.username = data.username;
      localStorage.setItem('pf_token', data.token);
      localStorage.setItem('pf_username', data.username);
      
      checkSession();
    } else {
      showToast(data.status || 'Failed to initialize account', 'error');
    }
  } catch (err) {
    showToast('Network error during account registration', 'error');
  }
});

el.btnLogout.addEventListener('click', handleLogout);


el.btnGotoRecover.addEventListener('click', () => {
  el.formRecoveryRequest.classList.remove('hidden');
  el.formRecoveryConfirm.classList.add('hidden');
  el.dialogRecovery.showModal();
});

document.querySelectorAll('.btn-back-to-auth').forEach(btn => {
  btn.addEventListener('click', () => {
    el.dialogRecovery.close();
  });
});

el.formRecoveryRequest.addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = el.recoverRequestUsername.value;
  
  try {
    const res = await fetch('/api/recover/request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username })
    });
    
    if (res.ok) {
      el.recoverActiveUser.textContent = username;
      el.formRecoveryRequest.classList.add('hidden');
      el.formRecoveryConfirm.classList.remove('hidden');

      
      showToast('Recovery sequence initiated', 'success');
    } else {
      showToast('Error request recovery', 'error');
    }
  } catch (err) {
    showToast('Network error during recovery request', 'error');
  }
});

el.btnBackToRequest.addEventListener('click', () => {
  el.formRecoveryRequest.classList.remove('hidden');
  el.formRecoveryConfirm.classList.add('hidden');
});

el.formRecoveryConfirm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = el.recoverActiveUser.textContent;
  const token = el.recoverToken.value;
  const new_password = el.recoverNewPassword.value;
  
  try {
    const res = await fetch('/api/recover/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, token, new_password })
    });
    
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      showToast('Account recovery successful. Master key rotated.', 'success');
      el.dialogRecovery.close();
      
      
      const loginRes = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password: new_password })
      });
      const loginData = await loginRes.json();
      if (loginRes.ok && loginData.status === 'ok') {
        state.token = loginData.token;
        state.username = loginData.username;
        localStorage.setItem('pf_token', loginData.token);
        localStorage.setItem('pf_username', loginData.username);
        checkSession();
      }
    } else {
      showToast(data.status || 'Invalid recovery token validation', 'error');
    }
  } catch (err) {
    showToast('Network error during recovery confirmation', 'error');
  }
});


async function loadVaults() {
  try {
    const res = await apiFetch('/api/vaults');
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      state.vaults = data.items;
      renderVaults();
    }
  } catch (err) {
    console.error('Failed to load vaults:', err);
  }
}

function renderVaults() {
  el.vaultList.innerHTML = '';
  if (state.vaults.length === 0) {
    el.vaultList.innerHTML = '<p class="text-xs text-muted text-center py-4">No vaults available</p>';
    return;
  }
  
  state.vaults.forEach(vault => {
    const button = document.createElement('button');
    const isActive = state.activeVault && state.activeVault.handle === vault.handle;
    button.className = `sidebar-item ${isActive ? 'active' : ''}`;
    button.innerHTML = `
      <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 9.776c.112-.017.227-.026.344-.026h15.812c.117 0 .232.009.344.026m-16.5 0a2.25 2.25 0 00-1.883 2.542l.857 6a2.25 2.25 0 002.227 1.932H19.05a2.25 2.25 0 002.227-1.932l.857-6a2.25 2.25 0 00-1.883-2.542m-16.5 0V6A2.25 2.25 0 016 3.75h3.879a1.5 1.5 0 011.06.44l2.122 2.12a1.5 1.5 0 001.06.44H18A2.25 2.25 0 0120.25 9v.776"></path>
      </svg>
      <span>${vault.name}</span>
      <span class="badge badge-${vault.role === 'owner' ? 'gold' : 'gray'}">${vault.role}</span>
    `;
    
    button.addEventListener('click', () => selectVault(vault));
    el.vaultList.appendChild(button);
  });
}

function selectVault(vault) {
  state.activeVault = vault;
  renderVaults();
  
  el.activeVaultName.textContent = vault.name;
  el.activeVaultHandle.textContent = vault.handle;
  el.activeVaultBadge.textContent = vault.role;
  el.activeVaultBadge.className = `badge badge-${vault.role === 'owner' ? 'gold' : 'gray'}`;
  el.activeVaultBadge.classList.remove('hidden');
  
  el.vaultEmptyState.classList.add('hidden');
  el.entriesContainer.classList.remove('hidden');
  el.btnNewEntry.classList.remove('hidden');
  
  loadEntries(vault.handle);
}


async function loadEntries(handle) {
  try {
    const res = await apiFetch(`/api/vaults/${handle}/entries`);
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      state.entries = data.items;
      renderEntries();
    }
  } catch (err) {
    showToast('Failed to retrieve vault entries', 'error');
  }
}

function renderEntries() {
  const tbody = el.entriesList.querySelector('tbody');
  tbody.innerHTML = '';
  const query = el.vaultEntriesSearch.value.toLowerCase();

  const filtered = state.entries.filter(entry =>
    entry.title.toLowerCase().includes(query) ||
    entry.login.toLowerCase().includes(query) ||
    entry.note.toLowerCase().includes(query)
  );

  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr class="empty-row">
        <td colspan="3">No matching credentials found in this vault.</td>
      </tr>
    `;
    return;
  }

  filtered.forEach(entry => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${entry.title}</strong></td>
      <td><span class="text-muted">${entry.login}</span></td>
      <td>
        <div class="flex items-center gap-2">
          <button class="row-action btn-copy-secret" title="Copy password" aria-label="Copy password">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H5.25M16.5 5.25h.008v.008H16.5V5.25zm0 2.25h.008v.008H16.5V7.5zm0 2.25h.008v.008H16.5V9.75zm0 2.25h.008v.008H16.5v-.008zm1.5-4.875L20.25 9.75M16.5 5.25v4.5m0-4.5h4.5m-9 9h9M10.5 15h9"></path>
            </svg>
          </button>
          <button class="row-action btn-view-entry" title="View details" aria-label="View details">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z"></path>
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
            </svg>
          </button>
        </div>
      </td>
    `;

    tr.querySelector('.btn-copy-secret').addEventListener('click', (e) => {
      e.stopPropagation();
      navigator.clipboard.writeText(entry.secret);
      showToast('Password copied to clipboard', 'success');
    });

    tr.querySelector('.btn-view-entry').addEventListener('click', (e) => {
      e.stopPropagation();
      viewEntryDetail(entry.id);
    });

    tr.addEventListener('click', () => viewEntryDetail(entry.id));
    tbody.appendChild(tr);
  });
}

el.vaultEntriesSearch.addEventListener('input', renderEntries);


el.btnNewVault.addEventListener('click', () => {
  el.formCreateVault.reset();
  el.dialogCreateVault.showModal();
});

el.formCreateVault.addEventListener('submit', async (e) => {
  e.preventDefault();
  const name = el.vaultNameInput.value;
  const handle = el.vaultHandleInput.value || undefined;
  
  try {
    const res = await apiFetch('/api/vaults', {
      method: 'POST',
      body: JSON.stringify({ name, handle })
    });
    
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      showToast(`Vault "${name}" successfully initialized`, 'success');
      el.dialogCreateVault.close();
      await loadVaults();
      
      
      const newVault = state.vaults.find(v => v.handle === data.handle);
      if (newVault) selectVault(newVault);
    } else {
      showToast(data.status || 'Failed to initialize vault', 'error');
    }
  } catch (err) {
    showToast('Network error while creating vault', 'error');
  }
});


el.btnNewEntry.addEventListener('click', () => {
  el.formCreateEntry.reset();
  el.dialogCreateEntry.showModal();
});

el.btnGeneratePassword.addEventListener('click', () => {
  const generated = generateSecurePassword();
  el.entrySecret.value = generated;
  showToast('Generated strong cryptographically random master secret', 'info');
});

el.formCreateEntry.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!state.activeVault) return;
  
  const title = el.entryTitle.value;
  const login = el.entryLogin.value;
  const secret = el.entrySecret.value;
  const note = el.entryNote.value;
  
  try {
    const res = await apiFetch(`/api/vaults/${state.activeVault.handle}/entries`, {
      method: 'POST',
      body: JSON.stringify({ title, login, secret, note })
    });
    
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      showToast(`Entry "${title}" added to vault`, 'success');
      el.dialogCreateEntry.close();
      loadEntries(state.activeVault.handle);
    } else {
      showToast(data.status || 'Failed to save entry', 'error');
    }
  } catch (err) {
    showToast('Network error while saving entry', 'error');
  }
});


async function viewEntryDetail(entryId) {
  if (!state.activeVault) return;
  
  try {
    const res = await apiFetch(`/api/entries/${entryId}?vault=${state.activeVault.handle}`);
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      const entry = data.entry;
      state.activeDetailEntry = entry;
      
      el.detailTitle.textContent = entry.title;
      el.detailLogin.textContent = entry.login;
      el.detailSecret.textContent = '••••••••••••••••';
      el.detailSecret.classList.add('password-masked');
      
      el.detailNote.textContent = entry.note || 'No secure notes provided.';
      el.detailVaultHandle.textContent = entry.vault_handle;
      el.detailId.textContent = entry.id;
      
      
      el.btnRevealDetail.querySelector('svg').style.color = '';
      
      el.dialogDetailEntry.showModal();
    } else {
      showToast('Failed to retrieve entry credentials', 'error');
    }
  } catch (err) {
    showToast('Network error retrieving details', 'error');
  }
}


el.btnRevealDetail.addEventListener('click', () => {
  if (!state.activeDetailEntry) return;
  
  const isMasked = el.detailSecret.classList.contains('password-masked');
  if (isMasked) {
    el.detailSecret.textContent = state.activeDetailEntry.secret;
    el.detailSecret.classList.remove('password-masked');
    el.btnRevealDetail.querySelector('svg').style.color = 'var(--color-gold)';
  } else {
    el.detailSecret.textContent = '••••••••••••••••';
    el.detailSecret.classList.add('password-masked');
    el.btnRevealDetail.querySelector('svg').style.color = '';
  }
});


document.querySelectorAll('.btn-copy').forEach(btn => {
  btn.addEventListener('click', () => {
    const targetId = btn.getAttribute('data-target');
    let text = '';
    
    if (targetId === 'detail-login') {
      text = state.activeDetailEntry ? state.activeDetailEntry.login : '';
    } else if (targetId === 'detail-secret') {
      text = state.activeDetailEntry ? state.activeDetailEntry.secret : '';
    }
    
    if (text) {
      navigator.clipboard.writeText(text);
      showToast('Copied to clipboard', 'success');
    }
  });
});


el.btnOpenDirectory.addEventListener('click', () => {
  el.directorySearchInput.value = '';
  el.directoryResults.innerHTML = `
    <tr>
      <td colspan="3" class="p-8 text-center text-muted text-sm">Type a search query above to query the directory database.</td>
    </tr>
  `;
  el.dialogDirectory.showModal();
});

async function performDirectorySearch() {
  const query = el.directorySearchInput.value;
  
  try {
    const res = await apiFetch(`/api/directory/search?q=${encodeURIComponent(query)}`);
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      el.directoryResults.innerHTML = '';
      if (data.items.length === 0) {
        el.directoryResults.innerHTML = `
          <tr>
            <td colspan="3" class="p-8 text-center text-muted text-sm">No matching users found in the system.</td>
          </tr>
        `;
        return;
      }
      
      data.items.forEach(item => {
        const tr = document.createElement('tr');
        tr.className = 'cursor-pointer hover:bg-white/[0.02]';
        tr.innerHTML = `
          <td class="p-3 font-medium text-white">${item.username}</td>
          <td class="p-3 text-muted">${item.email}</td>
          <td class="p-3 font-mono text-gold-accent text-xs">${item.vault_handle}</td>
        `;
        
        tr.addEventListener('click', () => {
          navigator.clipboard.writeText(item.vault_handle);
          showToast(`Vault handle "${item.vault_handle}" copied`, 'success');
        });
        
        el.directoryResults.appendChild(tr);
      });
    }
  } catch (err) {
    showToast('Failed to perform directory search', 'error');
  }
}

el.btnDirectorySearchSubmit.addEventListener('click', performDirectorySearch);
el.directorySearchInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') performDirectorySearch();
});


el.btnExportVault.addEventListener('click', () => {
  if (!state.activeVault) {
    showToast('Select a vault to export first', 'info');
    return;
  }
  
  const handle = state.activeVault.handle;
  const exportUrl = `${API_BASE}/api/export?vault=${handle}`;
  
  
  apiFetch(exportUrl)
    .then(res => {
      if (!res.ok) throw new Error('Export failure');
      return res.blob();
    })
    .then(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `passforge_export_${handle}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      showToast('Vault CSV backup file generated successfully', 'success');
    })
    .catch(err => {
      showToast('Failed to export vault credentials', 'error');
    });
});


el.btnOpenImport.addEventListener('click', () => {
  el.csvPayload.value = '';
  el.dialogImport.showModal();
});

el.formImportCsv.addEventListener('submit', async (e) => {
  e.preventDefault();
  const rawCsv = el.csvPayload.value;
  
  try {
    const res = await apiFetch('/api/import', {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain' },
      body: rawCsv
    });
    
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      showToast(`Import completed. Added ${data.imported} new records.`, 'success');
      el.dialogImport.close();
      loadVaults();
      if (state.activeVault) {
        loadEntries(state.activeVault.handle);
      }
    } else {
      showToast(data.status || 'Error importing CSV data', 'error');
    }
  } catch (err) {
    showToast('Network error during import sequence', 'error');
  }
});


document.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
    return;
  }
  if (e.key === '/') {
    e.preventDefault();
    if (el.dialogDirectory.open) {
      el.directorySearchInput.focus();
    } else if (!el.authView.classList.contains('hidden')) {
      
    } else if (state.activeVault) {
      el.vaultEntriesSearch.focus();
    }
  }
});


initApp();
