/**
 * User App.js - Customer Direct Banking Web Application Logic
 * Separated from Control Plane Simulator for end-to-end customer UX testing.
 */

let allCustomers = [];
let currentCustomer = null;
let activeScreen = 'dashboard';

document.addEventListener('DOMContentLoaded', async () => {
  await fetchCustomers();
});

async function fetchCustomers() {
  try {
    const res = await fetch('/api/core/customers');
    allCustomers = await res.json();
    renderPresetLoginButtons();

    // Check if session exists in localStorage
    const savedCustId = localStorage.getItem('user_portal_customer_id');
    if (savedCustId) {
      const found = allCustomers.find(c => c.customer_id === savedCustId);
      if (found) {
        loginAsCustomer(found);
        return;
      }
    }

    // Default to first customer if no session
    if (allCustomers.length > 0) {
      renderPresetDefaultForm(allCustomers[0]);
    }
  } catch (err) {
    console.error('Failed to fetch customers:', err);
  }
}

function renderPresetLoginButtons() {
  const container = document.getElementById('preset-login-buttons');
  if (!container) return;
  container.innerHTML = '';

  allCustomers.forEach(c => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'preset-btn';
    btn.onclick = () => loginAsCustomer(c);
    btn.innerHTML = `
      <span><strong>${c.name_kanji}</strong> (${c.customer_tier})</span>
      <span>${c.branch_code}-${c.account_number}</span>
    `;
    container.appendChild(btn);
  });
}

function renderPresetDefaultForm(customer) {
  document.getElementById('input-branch').value = customer.branch_code;
  document.getElementById('input-account').value = customer.account_number;
}

async function handleLoginSubmit(event) {
  event.preventDefault();

  if (allCustomers.length === 0) {
    await fetchCustomers();
  }

  const branch = document.getElementById('input-branch').value.trim();
  const account = document.getElementById('input-account').value.trim();

  let found = allCustomers.find(c => c.branch_code === branch && c.account_number === account);
  if (!found) {
    found = allCustomers.find(c => c.account_number.includes(account) || c.branch_code.includes(branch));
  }
  if (!found && allCustomers.length > 0) {
    found = allCustomers[0];
  }

  if (found) {
    loginAsCustomer(found);
  } else {
    // Hardcoded fallback customer if API is offline
    loginAsCustomer({
      customer_id: "CUST-1001",
      name_kanji: "山田 太郎",
      name_katakana: "ヤマダ タロウ",
      branch_code: "001",
      branch_name: "本店営業部",
      account_number: "1234567",
      customer_tier: "SUPER_VIP",
      happy_program_stage: "スーパーVIP",
      accounts: [
        { account_type: "普通預金", account_type_code: "SAVINGS", balance: 2450000, currency: "JPY" },
        { account_type: "定期預金", account_type_code: "TIME_DEPOSIT", balance: 5000000, currency: "JPY" }
      ],
      recent_transactions: [
        { transaction_id: "TXN-90850", date: "2026-08-04", type: "振込入金", amount: 15000, currency: "JPY", description: "フリコミ スズキ イチロウ", balance_after: 2450000 }
      ]
    });
  }
}

async function loginAsCustomer(customer) {
  // If accounts array is missing, fetch full detailed profile
  if (!customer.accounts || customer.accounts.length === 0) {
    try {
      const res = await fetch(`/api/core/customers/${customer.customer_id}`);
      if (res.ok) {
        customer = await res.json();
      }
    } catch (e) {
      console.warn('Could not fetch full profile:', e);
    }
  }

  currentCustomer = customer;
  localStorage.setItem('user_portal_customer_id', customer.customer_id);

  // Update UI Elements
  document.getElementById('user-display-name').textContent = `${customer.name_kanji} 様`;
  document.getElementById('user-display-tier').textContent = customer.customer_tier || 'REGULAR';
  document.getElementById('chat-greeting-name').textContent = customer.name_kanji;

  // Render Screens
  renderDashboard(customer);
  renderTransactionsTable(customer);

  // Switch to Main App View
  document.getElementById('screen-login').classList.add('hidden');
  document.getElementById('screen-main-app').classList.remove('hidden');

  navigateTo('dashboard');
}

function handleLogout() {
  localStorage.removeItem('user_portal_customer_id');
  currentCustomer = null;
  document.getElementById('screen-main-app').classList.add('hidden');
  document.getElementById('screen-login').classList.remove('hidden');
}

function navigateTo(screenId, presetPrompt = null) {
  activeScreen = screenId;
  const screens = ['dashboard', 'transactions', 'chat'];
  
  screens.forEach(s => {
    const el = document.getElementById(`subscreen-${s}`);
    const btn = document.getElementById(`nav-btn-${s}`);
    if (el) {
      if (s === screenId) {
        el.classList.remove('hidden');
      } else {
        el.classList.add('hidden');
      }
    }
    if (btn) {
      if (s === screenId) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    }
  });

  if (screenId === 'chat' && presetPrompt) {
    sendChatPrompt(presetPrompt);
  }
}

function renderDashboard(cust) {
  document.getElementById('dash-welcome-name').textContent = cust.name_kanji;
  document.getElementById('dash-branch-info').textContent = `${cust.branch_name} (${cust.branch_code})`;

  // Extract balances
  let savingsBal = 0;
  let timeBal = 0;
  let usdBal = 0;

  (cust.accounts || []).forEach(acc => {
    if (acc.account_type_code === 'SAVINGS' || acc.account_type.includes('普通')) {
      savingsBal = acc.balance;
      document.getElementById('dash-savings-acc').textContent = `口座: ${cust.branch_code}-${cust.account_number}`;
    } else if (acc.account_type_code === 'TIME_DEPOSIT' || acc.account_type.includes('定期')) {
      timeBal = acc.balance;
    } else if (acc.account_type_code === 'FOREIGN_USD' || acc.account_type.includes('外貨')) {
      usdBal = acc.balance;
    }
  });

  document.getElementById('dash-savings-balance').textContent = savingsBal.toLocaleString();
  document.getElementById('dash-time-balance').textContent = timeBal.toLocaleString();
  document.getElementById('dash-usd-balance').textContent = usdBal.toFixed(2);

  // Loyalty Stage
  const stage = cust.happy_program_stage || cust.customer_tier || 'SUPER_VIP';
  document.getElementById('dash-stage-badge').textContent = stage;
  document.getElementById('dash-free-transfers').textContent = (stage.includes('VIP') || stage === 'SUPER_VIP') ? '3' : '1';
  document.getElementById('dash-free-atm').textContent = (stage.includes('VIP') || stage === 'SUPER_VIP') ? '7' : '3';

  // Render recent 5 transactions
  const dashTable = document.getElementById('dash-txn-rows');
  dashTable.innerHTML = '';

  const txns = (cust.recent_transactions || []).slice(0, 5);
  txns.forEach(tx => {
    const tr = document.createElement('tr');
    const isDeposit = tx.amount > 0;
    const amtClass = isDeposit ? 'amount-positive' : 'amount-negative';
    const amtPrefix = isDeposit ? '+' : '';
    const badgeClass = isDeposit ? 'type-deposit' : 'type-withdrawal';

    tr.innerHTML = `
      <td>${tx.date}</td>
      <td><span class="txn-type-badge ${badgeClass}">${tx.type}</span></td>
      <td>${tx.description}</td>
      <td class="${amtClass}">${amtPrefix}${tx.amount.toLocaleString()} 円</td>
      <td>${tx.balance_after.toLocaleString()} 円</td>
    `;
    dashTable.appendChild(tr);
  });
}

function renderTransactionsTable(cust) {
  const table = document.getElementById('full-txn-rows');
  if (!table) return;
  table.innerHTML = '';

  const txns = cust.recent_transactions || [];
  txns.forEach(tx => {
    const tr = document.createElement('tr');
    const isDeposit = tx.amount > 0;
    const amtClass = isDeposit ? 'amount-positive' : 'amount-negative';
    const amtPrefix = isDeposit ? '+' : '';
    const badgeClass = isDeposit ? 'type-deposit' : 'type-withdrawal';

    tr.innerHTML = `
      <td>${tx.transaction_id}</td>
      <td>${tx.date}</td>
      <td><span class="txn-type-badge ${badgeClass}">${tx.type}</span></td>
      <td>${tx.description}</td>
      <td class="${amtClass}">${amtPrefix}${tx.amount.toLocaleString()} 円</td>
      <td>${tx.balance_after.toLocaleString()} 円</td>
    `;
    table.appendChild(tr);
  });
}

function onTxnSearchInput() {
  const keyword = document.getElementById('txn-search-keyword').value.toLowerCase();
  const rows = document.querySelectorAll('#full-txn-rows tr');

  rows.forEach(tr => {
    const text = tr.textContent.toLowerCase();
    if (text.includes(keyword)) {
      tr.style.display = '';
    } else {
      tr.style.display = 'none';
    }
  });
}

function exportTxnCSV() {
  if (!currentCustomer) return;
  let csv = 'Transaction ID,Date,Type,Description,Amount,Balance After\n';
  (currentCustomer.recent_transactions || []).forEach(tx => {
    csv += `"${tx.transaction_id}","${tx.date}","${tx.type}","${tx.description}",${tx.amount},${tx.balance_after}\n`;
  });

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `transactions_${currentCustomer.customer_id}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

/* ==========================================================================
   Full Dedicated AI Chat Logic
   ========================================================================== */

function handleUserChatSubmit(event) {
  event.preventDefault();
  const inputEl = document.getElementById('user-chat-input');
  const message = inputEl.value.trim();
  if (!message) return;

  sendChatPrompt(message);
  inputEl.value = '';
}

async function sendChatPrompt(promptText) {
  if (!currentCustomer) return;

  // Append User Message to UI
  appendChatMessage('user', promptText);

  // Append streaming AI message container
  const aiMsgDiv = appendChatMessage('ai', '');
  const pTag = aiMsgDiv.querySelector('.msg-bubble p');
  let fullAiText = '';

  try {
    const res = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: `SESS-USER-${Date.now()}`,
        customer_id: currentCustomer.customer_id,
        message: promptText
      })
    });

    if (!res.ok) {
      throw new Error(`SSE stream failed with status ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop();

      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith('data: ')) continue;
        try {
          const event = JSON.parse(line.slice(6));
          if (event.type === 'content_chunk') {
            fullAiText += event.delta;
            pTag.innerHTML = fullAiText.replace(/\n/g, '<br>');
            const container = document.getElementById('user-chat-messages');
            if (container) container.scrollTop = container.scrollHeight;
          } else if (event.type === 'step_up_required') {
            renderUserStepUpActionWidget(aiMsgDiv, event.payload);
          }
        } catch (err) {
          console.debug('SSE parse skip:', err);
        }
      }
    }

  } catch (err) {
    console.warn('SSE stream error, falling back to /api/chat:', err);
    try {
      const fallbackRes = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: `SESS-USER-${Date.now()}`,
          customer_id: currentCustomer.customer_id,
          message: promptText
        })
      });
      const data = await fallbackRes.json();
      pTag.innerHTML = (data.reply || '').replace(/\n/g, '<br>');
      if (data.status === 'STEP_UP_REQUIRED' && data.step_up) {
        renderUserStepUpActionWidget(aiMsgDiv, data.step_up);
      }
    } catch (fallbackErr) {
      console.error('Chat API Error:', fallbackErr);
      pTag.textContent = '通信エラーが発生いたしました。サーバー接続をご確認ください。';
    }
  }
}

function renderUserStepUpActionWidget(msgDiv, payload) {
  if (!msgDiv || !payload) return;
  const bubble = msgDiv.querySelector('.msg-bubble');
  if (!bubble || bubble.querySelector('.step-up-action-card')) return;

  const card = document.createElement('div');
  card.className = 'step-up-action-card';
  card.innerHTML = `
    <div class="step-up-header">
      <span class="step-up-badge">要・多要素認証 (Step-Up MFA)</span>
      <span class="step-up-action">${payload.target_action || '重要取引'}</span>
    </div>
    <p class="step-up-text">${payload.message}</p>
    <a href="${payload.redirect_url}" target="_blank" rel="noopener noreferrer" class="step-up-redirect-btn">
      🔒 公式インターネットバンキング取引画面へ進む
    </a>
  `;
  bubble.appendChild(card);
}

function appendChatMessage(sender, text) {
  const container = document.getElementById('user-chat-messages');
  if (!container) return null;

  const msgDiv = document.createElement('div');
  msgDiv.className = `chat-message msg-${sender}`;

  const avatarText = sender === 'ai' ? 'AI' : 'お客様';
  const now = new Date().toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });

  // Format linebreaks into clean HTML paragraphs
  const formattedText = text.replace(/\n/g, '<br>');

  msgDiv.innerHTML = `
    <div class="msg-avatar">${avatarText}</div>
    <div class="msg-bubble">
      <p>${formattedText}</p>
      <span class="time-stamp">${now}</span>
    </div>
  `;

  container.appendChild(msgDiv);
  container.scrollTop = container.scrollHeight;
  return msgDiv;
}

function appendChatLoading() {
  const container = document.getElementById('user-chat-messages');
  if (!container) return null;

  const loadingId = `loading-${Date.now()}`;
  const msgDiv = document.createElement('div');
  msgDiv.className = 'chat-message msg-ai';
  msgDiv.id = loadingId;

  msgDiv.innerHTML = `
    <div class="msg-avatar">AI</div>
    <div class="msg-bubble">
      <p><em>AIが回答を作成中でございます...</em></p>
    </div>
  `;

  container.appendChild(msgDiv);
  container.scrollTop = container.scrollHeight;
  return loadingId;
}

function removeChatLoading(loadingId) {
  if (!loadingId) return;
  const el = document.getElementById(loadingId);
  if (el) el.remove();
}

function clearChatMessages() {
  const container = document.getElementById('user-chat-messages');
  if (!container) return;
  container.innerHTML = `
    <div class="chat-message msg-ai">
      <div class="msg-avatar">AI</div>
      <div class="msg-bubble">
        <p>チャット履歴を消去いたしました。</p>
        <p>お口座の残高確認やお振込手数料についてお気軽にご質問ください。</p>
      </div>
    </div>
  `;
}
