/**
 * AI Agent Sandbox — Main Application Logic
 * Handles SSE streaming, UI updates, tool listing, trace visualization, and LLM providers.
 */

let conversationId = null;
let isStreaming = false;

// Dynamically determine the base API URL to support local development and direct file loading
const API_BASE = (window.location.protocol === 'file:' || window.location.hostname === '')
  ? 'https://ai-agent-plat.onrender.com'
  : '';


// ─── Init ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadTools();
  autoResize(document.getElementById('query-input'));
  initLLMConfig();
});

function autoResize(el) {
  el.addEventListener('input', () => {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  });
}

// ─── LLM Configuration ────────────────────────────────
function initLLMConfig() {
  const providerSelect = document.getElementById('llm-provider');
  const keyInput = document.getElementById('llm-key');
  const modelInput = document.getElementById('llm-model');

  // Load from localStorage
  const savedProvider = localStorage.getItem('af_llm_provider') || 'pollinations';
  const savedKey = localStorage.getItem('af_llm_key') || '';
  const savedModel = localStorage.getItem('af_llm_model') || '';

  providerSelect.value = savedProvider;
  keyInput.value = savedKey;
  modelInput.value = savedModel;
  
  onProviderChange();

  // Save on modifications
  providerSelect.addEventListener('change', (e) => {
    localStorage.setItem('af_llm_provider', e.target.value);
  });
  keyInput.addEventListener('input', (e) => {
    localStorage.setItem('af_llm_key', e.target.value);
  });
  modelInput.addEventListener('input', (e) => {
    localStorage.setItem('af_llm_model', e.target.value);
  });
}

function onProviderChange() {
  const provider = document.getElementById('llm-provider').value;
  const keyGroup = document.getElementById('api-key-group');
  if (provider === 'pollinations') {
    keyGroup.style.display = 'none';
  } else {
    keyGroup.style.display = 'block';
  }
}

// ─── Tools ─────────────────────────────────────────────
async function loadTools() {
  try {
    const resp = await fetch(`${API_BASE}/api/tools`);
    const tools = await resp.json();
    const container = document.getElementById('tool-list');
    const icons = { blockchain: '🔗', math: '🧮', code: '💻' };
    container.innerHTML = tools.map((t, idx) => `
      <div class="tool-card" data-idx="${idx}">
        <div class="tool-icon ${t.category}">${icons[t.category] || '🔧'}</div>
        <div>
          <div class="tool-name">${t.name}</div>
          <div class="tool-desc">${t.description.substring(0, 60)}...</div>
        </div>
      </div>
    `).join('');

    // Dynamically attach event listeners to avoid escaping/quote syntax issues
    container.querySelectorAll('.tool-card').forEach(card => {
      card.addEventListener('click', () => {
        const idx = parseInt(card.getAttribute('data-idx'), 10);
        const tool = tools[idx];
        if (tool) {
          sendQuery(tool.examples[0] || tool.name);
        }
      });
    });
  } catch (e) {
    console.error('Failed to load tools:', e);
  }
}

// ─── Submit Query ──────────────────────────────────────
function sendQuery(query) {
  const input = document.getElementById('query-input');
  input.value = query;
  submitQuery();
}

async function submitQuery() {
  const input = document.getElementById('query-input');
  const query = input.value.trim();
  if (!query || isStreaming) return;

  // Hide welcome
  const welcome = document.getElementById('welcome');
  if (welcome) welcome.style.display = 'none';

  // Add user message
  addMessage('user', query);
  input.value = '';
  input.style.height = 'auto';

  // Start streaming
  isStreaming = true;
  document.getElementById('send-btn').disabled = true;

  const msgContainer = createAgentMessage();
  const stepsContainer = msgContainer.querySelector('.reasoning-steps');
  const finalContainer = msgContainer.querySelector('.final-answer');
  const headerInfo = msgContainer.querySelector('.reasoning-header-info');

  // Show thinking indicator in header, steps are collapsed by default
  headerInfo.textContent = ' · Thinking...';
  stepsContainer.innerHTML = `<div class="thinking"><div class="thinking-dots"><span></span><span></span><span></span></div>Agent is reasoning...</div>`;

  let stepCount = 0;
  let totalLatency = 0;

  // Load LLM configuration parameters from fields
  const provider = document.getElementById('llm-provider').value;
  const key = document.getElementById('llm-key').value.trim() || null;
  const model = document.getElementById('llm-model').value.trim() || null;

  try {
    const resp = await fetch(`${API_BASE}/api/agent/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        conversation_id: conversationId,
        max_steps: 10,
        llm_config: {
          provider: provider,
          api_key: key,
          model: model
        }
      }),
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));
          conversationId = data.conversation_id || conversationId;

          if (data.step) {
            stepCount++;
            totalLatency += data.step.latency_ms || 0;

            // Remove thinking indicator
            const thinking = stepsContainer.querySelector('.thinking');
            if (thinking) thinking.remove();

            if (data.step.step_type === 'final_answer') {
              finalContainer.innerHTML = renderContent(data.step.content);
              headerInfo.textContent = `${stepCount} steps · ${totalLatency.toFixed(0)}ms`;
            } else {
              stepsContainer.appendChild(createStepElement(data.step));
            }

            scrollToBottom();
          }

          if (data.summary) {
            updateTracePanel(conversationId);
            updateContextStats(conversationId);
          }
        }
      }
    }
  } catch (e) {
    finalContainer.innerHTML = `<div class="error-msg" style="color:var(--red);">Error: ${escapeHtml(e.message)}. Make sure the backend is running.</div>`;
  }

  isStreaming = false;
  document.getElementById('send-btn').disabled = false;
  document.getElementById('query-input').focus();
}

// ─── Message Elements ──────────────────────────────────
function addMessage(role, content) {
  const messages = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = `message message-${role}`;
  div.innerHTML = `<div class="message-content">${renderContent(content)}</div>`;
  messages.appendChild(div);
  scrollToBottom();
}

// Make toggleTrace, onProviderChange, and toggleDrawer accessible globally
function toggleDrawer() {
  const drawer = document.getElementById('tool-drawer');
  drawer.classList.toggle('collapsed');
}

window.toggleTrace = toggleTrace;
window.onProviderChange = onProviderChange;
window.sendQuery = sendQuery;
window.submitQuery = submitQuery;
window.newChat = newChat;
window.toggleDrawer = toggleDrawer;

function createAgentMessage() {
  const messages = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = 'message message-agent';
  div.innerHTML = `
    <div class="reasoning-container">
      <div class="reasoning-header" onclick="this.parentElement.querySelector('.reasoning-steps').classList.toggle('expanded'); this.querySelector('.reasoning-toggle').style.transform = this.parentElement.querySelector('.reasoning-steps').classList.contains('expanded') ? 'rotate(180deg)' : '';">
        <div class="reasoning-header-left">
          <span>🧠</span> <span>Agent Reasoning</span>
          <span class="reasoning-header-info" style="color:var(--text-muted);font-size:11px;"></span>
        </div>
        <span class="reasoning-toggle">▼</span>
      </div>
      <div class="reasoning-steps"></div>
      <div class="final-answer"></div>
    </div>
  `;
  messages.appendChild(div);
  return div;
}

function createStepElement(step) {
  const div = document.createElement('div');
  div.className = `step step-${step.step_type}`;

  const icons = { thought: '💭', action: '⚡', observation: '👁️', final_answer: '✅', error: '❌' };

  div.innerHTML = `
    <div class="step-icon">${icons[step.step_type] || '•'}</div>
    <div class="step-content">
      <div class="step-label">${step.step_type}</div>
      <div class="step-text">${renderContent(step.content)}</div>
      <div class="step-meta">
        <span>⏱ ${step.latency_ms?.toFixed(1) || 0}ms</span>
        <span>📝 ${step.tokens_used || 0} tokens</span>
        <span>#${step.step_number}</span>
      </div>
    </div>
  `;
  return div;
}

// ─── Trace Panel ───────────────────────────────────────
function toggleTrace() {
  document.getElementById('trace-panel').classList.toggle('open');
  if (conversationId) updateTracePanel(conversationId);
}

async function updateTracePanel(convId) {
  try {
    const resp = await fetch(`${API_BASE}/api/traces/${convId}`);
    const data = await resp.json();

    // Stats
    const stats = data.summary || {};
    document.getElementById('trace-stats').innerHTML = `
      <div class="stat-card"><div class="stat-value">${stats.total_steps || 0}</div><div class="stat-label">Steps</div></div>
      <div class="stat-card"><div class="stat-value">${(stats.total_latency_ms || 0).toFixed(0)}ms</div><div class="stat-label">Latency</div></div>
      <div class="stat-card"><div class="stat-value">${stats.total_tokens || 0}</div><div class="stat-label">Tokens</div></div>
      <div class="stat-card"><div class="stat-value">${Object.keys(stats.step_breakdown || {}).length}</div><div class="stat-label">Step Types</div></div>
    `;

    // Waterfall
    const wf = data.waterfall || {};
    const maxMs = Math.max(...(wf.spans || []).map(s => s.start_ms + s.duration_ms), 1);
    document.getElementById('trace-waterfall').innerHTML = (wf.spans || []).map(s => {
      const left = (s.start_ms / maxMs * 100).toFixed(1);
      const width = Math.max((s.duration_ms / maxMs * 100), 2).toFixed(1);
      return `
        <div class="waterfall-bar">
          <div class="waterfall-label">${s.type}</div>
          <div class="waterfall-track">
            <div class="waterfall-fill ${s.type}" style="left:${left}%;width:${width}%;"></div>
          </div>
          <div class="waterfall-time">${s.duration_ms.toFixed(0)}ms</div>
        </div>
      `;
    }).join('');
  } catch (e) {
    console.error('Trace update failed:', e);
  }
}

async function updateContextStats(convId) {
  try {
    const resp = await fetch(`${API_BASE}/api/context/${convId}`);
    const data = await resp.json();
    const s = data.stats;
    document.getElementById('context-stats').innerHTML = `
      <div style="margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px;">
          <span>Tokens</span><span>${s.tokens}/${s.max_tokens}</span>
        </div>
        <div style="height:4px;background:var(--border);border-radius:2px;overflow:hidden;">
          <div style="height:100%;width:${s.usage_pct}%;background:linear-gradient(90deg,var(--accent),var(--cyan));border-radius:2px;transition:width 0.5s;"></div>
        </div>
      </div>
      <div style="font-size:11px;color:var(--text-muted);">Messages: ${s.messages} · ${s.usage_pct}% used</div>
    `;
  } catch (e) {}
}

// ─── Utilities ─────────────────────────────────────────
function newChat() {
  conversationId = null;
  document.getElementById('messages').innerHTML = `
    <div class="welcome" id="welcome">
      <div class="welcome-icon">🔮</div>
      <h2>Welcome to the AI Agent Sandbox</h2>
      <p>An AI agent orchestration platform with real-time reasoning visualization, tool adapters, and blockchain integration.</p>
      <div class="welcome-cards">
        <div class="welcome-card" onclick="sendQuery('What is the price of Bitcoin?')"><div class="card-icon">₿</div><h4>Crypto Prices</h4><p>Real-time cryptocurrency data</p></div>
        <div class="welcome-card" onclick="sendQuery('Show me the crypto market overview')"><div class="card-icon">📊</div><h4>Market Overview</h4><p>Top coins & market trends</p></div>
        <div class="welcome-card" onclick="sendQuery('Show mining statistics')"><div class="card-icon">⛏️</div><h4>Mining Stats</h4><p>Hashrate, difficulty & pools</p></div>
        <div class="welcome-card" onclick="sendQuery('Calculate sqrt(144) * 2**10')"><div class="card-icon">🧮</div><h4>Math Engine</h4><p>Evaluate complex expressions</p></div>
      </div>
    </div>
  `;
  document.getElementById('context-stats').innerHTML = '<div style="font-size:12px;color:var(--text-muted);">No active conversation</div>';
}

function scrollToBottom() {
  const messages = document.getElementById('messages');
  messages.scrollTop = messages.scrollHeight;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function renderContent(content) {
  if (!content) return '';

  const trimmed = content.trim();

  // If content is a JSON object or array, format it cleanly in a pre block
  if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
    try {
      const parsed = JSON.parse(trimmed);
      return `<pre class="json-renderer"><code>${escapeHtml(JSON.stringify(parsed, null, 2))}</code></pre>`;
    } catch (e) {
      // fallback to markdown parsing if JSON fails to parse
    }
  }

  // Escape HTML to prevent XSS before parsing markdown tags
  let escaped = content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

  const lines = escaped.split('\n');
  let result = [];
  let inTable = false;
  let tableRows = [];
  let inList = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Check for Markdown Table Row
    const isTableRow = line.startsWith('|') && line.endsWith('|') && line.split('|').length > 2;

    if (isTableRow) {
      if (inList) {
        result.push('</ul>');
        inList = false;
      }

      // Skip table header alignment formatting line (e.g. |:---|:---:|)
      const isSeparator = /^\|[\s:\-|]+$/.test(line);
      if (isSeparator) {
        continue;
      }

      const cols = line.split('|').slice(1, -1).map(c => c.trim());
      tableRows.push(cols);
      inTable = true;
      continue;
    } else {
      if (inTable && tableRows.length > 0) {
        result.push(renderTableHtml(tableRows));
        tableRows = [];
        inTable = false;
      }
    }

    // Check for List Item
    const isListItem = /^[*\-+]\s+(.*)/.test(line);
    if (isListItem) {
      if (!inList) {
        result.push('<ul>');
        inList = true;
      }
      const match = line.match(/^[*\-+]\s+(.*)/);
      result.push(`<li>${parseInlineMarkdown(match[1])}</li>`);
      continue;
    } else {
      if (inList) {
        result.push('</ul>');
        inList = false;
      }
    }

    // Normal line
    if (line === '') {
      result.push('<div class="spacer" style="height: 8px;"></div>');
    } else {
      result.push(parseInlineMarkdown(line) + '<br>');
    }
  }

  if (inTable && tableRows.length > 0) {
    result.push(renderTableHtml(tableRows));
  }
  if (inList) {
    result.push('</ul>');
  }

  // Join lines and clean up trailing breaks next to list elements or table tags
  return result.join('\n')
    .replace(/<br>\n(<ul>|<table>)/g, '\n$1')
    .replace(/(<\/ul>|<\/table>)\n<br>/g, '$1\n');
}

function renderTableHtml(rows) {
  let tableHtml = '<div style="overflow-x:auto;"><table class="markdown-table">';
  // Header row
  tableHtml += '<thead><tr>' + rows[0].map(c => `<th>${parseInlineMarkdown(c)}</th>`).join('') + '</tr></thead>';
  if (rows.length > 1) {
    tableHtml += '<tbody>';
    for (let r = 1; r < rows.length; r++) {
      tableHtml += '<tr>' + rows[r].map(c => `<td>${parseInlineMarkdown(c)}</td>`).join('') + '</tr>';
    }
    tableHtml += '</tbody>';
  }
  tableHtml += '</table></div>';
  return tableHtml;
}

function parseInlineMarkdown(text) {
  // Bold: **text**
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  // Monospace backticks: `code`
  text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
  return text;
}
