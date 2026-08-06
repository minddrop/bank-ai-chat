/**
 * App.js - Frontend Logic for Japanese Major Bank AI Portal & Core Banking System
 * Connects with Core Banking REST API, Control Plane Backend, RAG Engine, and FISC Audit Logger.
 */

let currentCustomers = [];
let selectedCustomer = null;
let activeTab = 'chat';

document.addEventListener('DOMContentLoaded', async () => {
  const savedMode = localStorage.getItem('bank_ai_view_mode') || 'dev';
  setViewMode(savedMode);
  await loadCustomers();
  await refreshAuditLogs();
});

function setViewMode(mode) {
  const chatLayout = document.getElementById('view-chat-layout');
  const devBtn = document.getElementById('mode-btn-dev');
  const userBtn = document.getElementById('mode-btn-user');
  const modeToggleGroup = document.getElementById('view-mode-toggle-group');

  if (!chatLayout || !devBtn || !userBtn) return;

  if (mode === 'user') {
    chatLayout.classList.add('mode-user-view');
    devBtn.classList.remove('active');
    userBtn.classList.add('active');
    localStorage.setItem('bank_ai_view_mode', 'user');
  } else {
    chatLayout.classList.remove('mode-user-view');
    userBtn.classList.remove('active');
    devBtn.classList.add('active');
    localStorage.setItem('bank_ai_view_mode', 'dev');
  }
}

function switchTab(tabName) {
  activeTab = tabName;
  const chatLayout = document.getElementById('view-chat-layout');
  const coreLayout = document.getElementById('view-core-layout');
  const chatTabBtn = document.getElementById('tab-btn-chat');
  const coreTabBtn = document.getElementById('tab-btn-core');
  const modeToggleGroup = document.getElementById('view-mode-toggle-group');

  if (tabName === 'core') {
    chatLayout.classList.add('hidden');
    coreLayout.classList.remove('hidden');
    chatTabBtn.classList.remove('active');
    coreTabBtn.classList.add('active');
    if (modeToggleGroup) modeToggleGroup.style.display = 'none';
    if (selectedCustomer) {
      renderCoreBankingView(selectedCustomer);
    }
  } else {
    coreLayout.classList.add('hidden');
    chatLayout.classList.remove('hidden');
    coreTabBtn.classList.remove('active');
    chatTabBtn.classList.add('active');
    if (modeToggleGroup) modeToggleGroup.style.display = 'flex';
  }
}

async function loadCustomers() {
  try {
    const res = await fetch('/api/core/customers');
    currentCustomers = await res.json();
    
    const dropdown = document.getElementById('customer-select');
    const coreDropdown = document.getElementById('core-customer-select');

    if (dropdown) dropdown.innerHTML = '';
    if (coreDropdown) coreDropdown.innerHTML = '';

    currentCustomers.forEach((c) => {
      if (dropdown) {
        const opt = document.createElement('option');
        opt.value = c.customer_id;
        opt.textContent = `${c.name_kanji} (${c.name_katakana})`;
        dropdown.appendChild(opt);
      }

      if (coreDropdown) {
        const optCore = document.createElement('option');
        optCore.value = c.customer_id;
        optCore.textContent = `${c.name_kanji} (${c.name_katakana})`;
        coreDropdown.appendChild(optCore);
      }
    });

    if (currentCustomers.length > 0) {
      selectedCustomer = currentCustomers[0];
      renderAccountCard(selectedCustomer);
      renderCoreBankingView(selectedCustomer);
    }
  } catch (err) {
    console.error('Error loading customers:', err);
  }
}

function onCustomerChange(custId) {
  const cust = currentCustomers.find(c => c.customer_id === custId);
  if (cust) {
    selectedCustomer = cust;
    // Sync both dropdowns
    const dropdown = document.getElementById('customer-select');
    const coreDropdown = document.getElementById('core-customer-select');
    if (dropdown) dropdown.value = custId;
    if (coreDropdown) coreDropdown.value = custId;

    renderAccountCard(cust);
    renderCoreBankingView(cust);
  }
}

function renderAccountCard(customer) {
  document.getElementById('acc-type').textContent = `${customer.branch_name} 口座一覧 (${customer.customer_tier} 会員)`;
  document.getElementById('acc-number').textContent = `${customer.branch_code}-${customer.account_number}`;
  document.getElementById('acc-branch').textContent = `${customer.branch_name} (${customer.branch_code})`;
  document.getElementById('acc-name').textContent = `${customer.name_kanji} (${customer.name_katakana})`;

  // Render Sub Accounts List & Balances
  const subAccountsList = document.getElementById('sub-accounts-list');
  if (subAccountsList) {
    subAccountsList.innerHTML = '';
    (customer.accounts || []).forEach(acc => {
      const accItem = document.createElement('div');
      accItem.className = 'sub-account-item';

      const curr = acc.currency || 'JPY';
      const isJPY = curr === 'JPY';
      const isNegative = acc.balance < 0;
      const formattedBalance = isJPY
        ? `${isNegative ? '-' : ''}¥${Math.abs(acc.balance).toLocaleString()}`
        : `${acc.balance.toLocaleString()} ${curr}`;

      accItem.innerHTML = `
        <div class="sub-acc-header">
          <span class="sub-acc-title">${escapeHtml(acc.account_type)}</span>
          <span class="sub-acc-rate">${acc.interest_rate ? '年' + acc.interest_rate : ''}</span>
        </div>
        <div class="sub-acc-balance ${isNegative ? 'negative-balance' : ''}">${formattedBalance}</div>
      `;
      subAccountsList.appendChild(accItem);
    });
  }

  // Render Transactions in sidebar
  const txnContainer = document.getElementById('txn-list-container');
  if (txnContainer) {
    txnContainer.innerHTML = '';
    const txns = customer.recent_transactions || [];

    const countBadge = document.getElementById('txn-count-badge');
    if (countBadge) countBadge.textContent = txns.length;

    txns.forEach(tx => {
      const li = document.createElement('li');
      li.className = 'txn-item';
      const isNeg = tx.amount < 0;
      const amountClass = isNeg ? 'txn-amount-neg' : 'txn-amount-pos';
      const amountText = isNeg ? `-¥${Math.abs(tx.amount).toLocaleString()}` : `+¥${tx.amount.toLocaleString()}`;
      const balAfter = tx.balance_after !== undefined ? `残高: ¥${tx.balance_after.toLocaleString()}` : '';

      li.innerHTML = `
        <div class="txn-left">
          <span class="txn-type">${escapeHtml(tx.type)}</span>
          <div class="txn-desc">${tx.date} - ${escapeHtml(tx.description)}</div>
        </div>
        <div class="txn-right">
          <div class="${amountClass}">${amountText}</div>
          ${balAfter ? `<div class="txn-bal-after">${balAfter}</div>` : ''}
        </div>
      `;
      txnContainer.appendChild(li);
    });
  }
}

function renderCoreBankingView(customer) {
  // Render Customer Profile Grid
  const profileGrid = document.getElementById('core-customer-profile');
  if (profileGrid) {
    profileGrid.innerHTML = `
      <div class="profile-stat-box">
        <div class="profile-stat-label">お名前 (漢字 / カタカナ)</div>
        <div class="profile-stat-value">${escapeHtml(customer.name_kanji)} (${escapeHtml(customer.name_katakana)})</div>
      </div>
      <div class="profile-stat-box">
        <div class="profile-stat-label">お客様ID / 口座番号</div>
        <div class="profile-stat-value">${customer.customer_id} / ${customer.branch_code}-${customer.account_number}</div>
      </div>
      <div class="profile-stat-box">
        <div class="profile-stat-label">お取扱店</div>
        <div class="profile-stat-value">${escapeHtml(customer.branch_name)} (店番: ${customer.branch_code})</div>
      </div>
      <div class="profile-stat-box">
        <div class="profile-stat-label">会員ステータス</div>
        <div class="profile-stat-value">${escapeHtml(customer.customer_tier)} (${escapeHtml(customer.happy_program_stage || '標準')})</div>
      </div>
      <div class="profile-stat-box">
        <div class="profile-stat-label">ダイレクトバンキング</div>
        <div class="profile-stat-value">${customer.direct_banking_status || 'ACTIVE'}</div>
      </div>
    `;
  }

  // Render Core Balance Cards
  const balanceGrid = document.getElementById('core-balance-cards');
  if (balanceGrid) {
    balanceGrid.innerHTML = '';
    (customer.accounts || []).forEach(acc => {
      const card = document.createElement('div');
      card.className = 'core-balance-card';

      const curr = acc.currency || 'JPY';
      const isJPY = curr === 'JPY';
      const formattedBalance = isJPY
        ? `¥${acc.balance.toLocaleString()}`
        : `${acc.balance.toLocaleString()} ${curr}`;

      card.innerHTML = `
        <div class="core-acc-type">${escapeHtml(acc.account_type)}</div>
        <div class="core-acc-balance">${formattedBalance}</div>
        <div class="core-acc-meta">
          <span>口座ID: ${acc.account_id}</span>
          <span>適用金利: ${acc.interest_rate || '0.02%'}</span>
        </div>
      `;
      balanceGrid.appendChild(card);
    });
  }

  // Render Transaction History Table
  renderCoreTransactionsTable(customer.recent_transactions || []);
}

function renderCoreTransactionsTable(txns) {
  const tbody = document.getElementById('core-txn-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';

  txns.forEach(tx => {
    const tr = document.createElement('tr');
    const isNeg = tx.amount < 0;
    const amountClass = isNeg ? 'tx-amount-minus' : 'tx-amount-plus';
    const curr = tx.currency || 'JPY';
    const isJPY = curr === 'JPY';
    const amountText = isJPY
      ? `${isNeg ? '-' : '+'}¥${Math.abs(tx.amount).toLocaleString()}`
      : `${tx.amount.toLocaleString()} ${curr}`;
    const balAfterText = isJPY
      ? `¥${tx.balance_after.toLocaleString()}`
      : `${tx.balance_after.toLocaleString()} ${curr}`;

    tr.innerHTML = `
      <td>${tx.transaction_id}</td>
      <td>${tx.date}</td>
      <td><span class="badge badge-tokyo">${escapeHtml(tx.type)}</span></td>
      <td>${escapeHtml(tx.description)}</td>
      <td class="${amountClass}">${amountText}</td>
      <td>${balAfterText}</td>
    `;
    tbody.appendChild(tr);
  });
}

function filterTransactions() {
  const input = document.getElementById('txn-search-input');
  if (!input || !selectedCustomer) return;
  const q = input.value.toLowerCase().trim();
  const txns = selectedCustomer.recent_transactions || [];

  if (!q) {
    renderCoreTransactionsTable(txns);
    return;
  }

  const filtered = txns.filter(tx => 
    (tx.description && tx.description.toLowerCase().includes(q)) ||
    (tx.type && tx.type.toLowerCase().includes(q)) ||
    (tx.date && tx.date.includes(q)) ||
    (tx.transaction_id && tx.transaction_id.toLowerCase().includes(q))
  );

  renderCoreTransactionsTable(filtered);
}

async function fetchAIExtractionPayload() {
  if (!selectedCustomer) return;
  const outEl = document.getElementById('api-extraction-output');
  outEl.textContent = 'API呼び出し実行中... (POST /api/core/extract-account-info)';

  try {
    const res = await fetch('/api/core/extract-account-info', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ customer_id: selectedCustomer.customer_id })
    });
    const data = await res.json();
    outEl.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    console.error('Extraction API error:', err);
    outEl.textContent = 'APIエラーが発生しました。接続を確認してください。';
  }
}

function sendPreset(text) {
  switchTab('chat');
  document.getElementById('user-input').value = text;
  handleChatSubmit(new Event('submit'));
}

async function handleChatSubmit(e) {
  if (e) e.preventDefault();
  const inputEl = document.getElementById('user-input');
  const text = inputEl.value.trim();
  if (!text) return;

  // Add User Message to UI
  appendMessage('user', text);
  inputEl.value = '';

  const sendBtn = document.getElementById('send-btn');
  sendBtn.disabled = true;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: 'SESS-' + Date.now(),
        customer_id: selectedCustomer ? selectedCustomer.customer_id : 'CUST-1001',
        message: text
      })
    });

    const data = await res.json();
    appendMessage('ai', data.reply);

    // Update Control Plane Inspector
    if (data.control_plane) {
      updateControlPlaneMonitor(data.control_plane);
    }

    // Refresh Audit Stream
    await refreshAuditLogs();

  } catch (err) {
    console.error('Chat error:', err);
    appendMessage('ai', '通信エラーが発生いたしました。サーバー接続をご確認ください。');
  } finally {
    sendBtn.disabled = false;
  }
}

function appendMessage(role, text) {
  const container = document.getElementById('chat-messages');
  const msgDiv = document.createElement('div');
  msgDiv.className = `message message-${role}`;

  const timeStr = new Date().toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });

  msgDiv.innerHTML = `
    <div class="avatar">${role === 'user' ? '客' : 'AI'}</div>
    <div class="message-body">
      <p>${escapeHtml(text)}</p>
      <span class="msg-time">${timeStr}</span>
    </div>
  `;

  container.appendChild(msgDiv);
  container.scrollTop = container.scrollHeight;
}

function updateControlPlaneMonitor(cp) {
  const inputEval = cp.input_guardrail || {};
  const outputEval = cp.output_guardrail || {};
  const ragContexts = cp.rag_contexts || [];

  // Input status indicator
  const inputInd = document.getElementById('input-status-indicator');
  if (inputEval.prompt_injection_blocked) {
    inputInd.textContent = 'BLOCKED (プロンプト注入)';
    inputInd.className = 'metric-status status-blocked';
  } else if (inputEval.pii_detected) {
    inputInd.textContent = 'PASSED (PII自動除去)';
    inputInd.className = 'metric-status status-ok';
  } else {
    inputInd.textContent = 'PASSED (安全)';
    inputInd.className = 'metric-status status-ok';
  }

  // Grounding score
  document.getElementById('grounding-score-display').textContent = `${(outputEval.grounding_score * 100).toFixed(0)}%`;

  // Input CP breakdown
  document.getElementById('input-cp-details').innerHTML = `
    <strong>[Sanitized Payload]</strong>: ${escapeHtml(inputEval.sanitized_prompt || '')}<br>
    <strong>[PII Redactions]</strong>: ${inputEval.pii_detected ? inputEval.pii_tokens_scrubbed.join(', ') : 'なし'}
  `;

  // RAG CP breakdown
  if (ragContexts.length > 0) {
    document.getElementById('rag-cp-details').innerHTML = ragContexts.map(r => `
      • <strong>[${r.category}] ${escapeHtml(r.question)}</strong> (スコア: ${r.relevance_score})
    `).join('<br>');
  } else {
    document.getElementById('rag-cp-details').innerHTML = '<span class="placeholder-text">勘定系DB (`data/bank_core.db`) 連携</span>';
  }

  // Output CP breakdown
  document.getElementById('output-cp-details').innerHTML = `
    <strong>[PII 漏洩検出]</strong>: ${outputEval.pii_leak_prevented ? '防止済' : '検出なし'}<br>
    <strong>[法的免責事項]</strong>: 自動付与済 (銀行法適合)
  `;
}

async function refreshAuditLogs() {
  try {
    const res = await fetch('/api/control-plane/logs');
    const logs = await res.json();
    const stream = document.getElementById('log-stream');
    if (!stream) return;
    stream.innerHTML = '';

    logs.slice(-10).reverse().forEach(log => {
      const entry = document.createElement('div');
      entry.className = 'log-entry';
      const time = log.timestamp ? log.timestamp.split('T')[1].split('.')[0] : '00:00:00';
      const model = log.llm_metadata?.model_id || 'bedrock-nova-lite';
      const sig = log.fisc_compliance?.tamper_proof_signature?.substring(0, 10) || '0x4f...';
      
      entry.innerHTML = `
        <span>[${time}] ${log.log_id}</span> | 
        <span class="log-model">${model}</span> | 
        <span class="log-sig">HASH: ${sig}</span>
      `;
      stream.appendChild(entry);
    });
  } catch (err) {
    console.error('Log stream error:', err);
  }
}

function escapeHtml(text) {
  if (!text) return '';
  return String(text).replace(/[&<>"']/g, function(m) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m];
  });
}
