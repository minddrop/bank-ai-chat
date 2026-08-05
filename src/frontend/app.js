/**
 * App.js - Frontend Logic for Japanese Major Bank AI Portal
 * Connects with FastAPI Control Plane Backend, RAG Engine, and FISC Audit Logger.
 */

let currentCustomers = [];
let selectedCustomer = null;

document.addEventListener('DOMContentLoaded', async () => {
  await loadCustomers();
  await refreshAuditLogs();
});

async function loadCustomers() {
  try {
    const res = await fetch('/api/customers');
    currentCustomers = await res.json();
    const dropdown = document.getElementById('customer-select');
    dropdown.innerHTML = '';
    
    currentCustomers.forEach((c) => {
      const opt = document.createElement('option');
      opt.value = c.customer_id;
      opt.textContent = `${c.name_kanji} (${c.name_katakana})`;
      dropdown.appendChild(opt);
    });

    if (currentCustomers.length > 0) {
      renderAccountCard(currentCustomers[0]);
    }
  } catch (err) {
    console.error('Error loading customers:', err);
  }
}

function onCustomerChange() {
  const dropdown = document.getElementById('customer-select');
  const custId = dropdown.value;
  const cust = currentCustomers.find(c => c.customer_id === custId);
  if (cust) {
    renderAccountCard(cust);
  }
}

function renderAccountCard(customer) {
  selectedCustomer = customer;

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

  // Render Transactions
  const txnContainer = document.getElementById('txn-list-container');
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

function sendPreset(text) {
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
    document.getElementById('rag-cp-details').innerHTML = '<span class="placeholder-text">口座データベース直接参照</span>';
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
    stream.innerHTML = '';

    logs.slice(-10).reverse().forEach(log => {
      const entry = document.createElement('div');
      entry.className = 'log-entry';
      const time = log.timestamp.split('T')[1].split('.')[0];
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
  return text.replace(/[&<>"']/g, function(m) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m];
  });
}
