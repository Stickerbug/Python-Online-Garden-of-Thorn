const $ = (id) => document.getElementById(id);

const MAX_OUTPUT_ENTRIES = 500;
let authenticated = false;
let historyItems = [];
let historyIndex = 0;
let completionItems = [];
let completionIndex = -1;
let completionAbort = null;
let completionLine = '';
let completionAppliedLine = '';

function showLogin(show) {
  $('console-login').classList.toggle('hidden', !show);
  $('console-shell').classList.toggle('hidden', show);
  if (show) {
    $('console-password').focus();
  } else {
    $('console-command').focus();
  }
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (_) {
    data = { success: false, error: text || response.statusText };
  }
  if (!response.ok) {
    const err = new Error(data.error || response.statusText);
    err.status = response.status;
    err.data = data;
    throw err;
  }
  return data;
}

function appendColoredText(parent, text) {
  const pattern = /(\/?(?:help|player|account|game|lobby|moderation|content|data|server)\b|\[(?:error|warning|security|admin|deploy|player|perf)\]|错误|失败|警告|参数错误|未知命令|ID:[A-Z0-9-]+|#[0-9]+|\b\d+(?:\.\d+)?(?:ms|秒|%)?\b|\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})/gi;
  let last = 0;
  for (const match of text.matchAll(pattern)) {
    if (match.index > last) {
      parent.appendChild(document.createTextNode(text.slice(last, match.index)));
    }
    const value = match[0];
    const span = document.createElement('span');
    const lower = value.toLowerCase();
    span.className = 'console-token';
    if (lower.startsWith('/') || /^(help|player|account|game|lobby|moderation|data|server)\b/i.test(value)) {
      span.classList.add('command');
    } else if (/error|错误|失败|参数错误|未知命令/i.test(value)) {
      span.classList.add('error');
    } else if (/warning|警告/i.test(value)) {
      span.classList.add('warning');
    } else if (/^#\d+/.test(value)) {
      span.classList.add('room');
    } else if (/^ID:/i.test(value)) {
      span.classList.add('id');
    } else if (/^\d/.test(value)) {
      span.classList.add('number');
    } else {
      span.classList.add('time');
    }
    span.textContent = value;
    parent.appendChild(span);
    last = match.index + value.length;
  }
  if (last < text.length) {
    parent.appendChild(document.createTextNode(text.slice(last)));
  }
}

function appendEntry(kind, text, prefix = '') {
  const output = $('console-output');
  const entry = document.createElement('div');
  entry.className = `console-entry ${kind}`;
  if (prefix) {
    const prefixSpan = document.createElement('span');
    prefixSpan.className = 'entry-prefix';
    prefixSpan.textContent = prefix;
    entry.appendChild(prefixSpan);
    entry.appendChild(document.createTextNode(' '));
  }
  appendColoredText(entry, String(text || ''));
  output.appendChild(entry);
  while (output.children.length > MAX_OUTPUT_ENTRIES) {
    output.removeChild(output.firstElementChild);
  }
  output.scrollTop = output.scrollHeight;
}

function clearOutput() {
  $('console-output').innerHTML = '';
  appendEntry('info', 'GTN 管理控制台已就绪。输入 help 查看命令。', '[INFO]');
}

async function checkAuth() {
  try {
    const data = await api('/api/adminconsole/me');
    authenticated = !!data.authenticated;
    showLogin(!authenticated);
    if (authenticated) clearOutput();
  } catch (_) {
    authenticated = false;
    showLogin(true);
  }
}

async function login(password) {
  $('console-login-error').textContent = '';
  try {
    await api('/api/adminconsole/login', {
      method: 'POST',
      body: JSON.stringify({ password }),
    });
    authenticated = true;
    showLogin(false);
    clearOutput();
  } catch (err) {
    $('console-login-error').textContent = err.status === 429 ? '尝试次数过多，请稍后再试。' : '密码错误。';
  }
}

async function logout() {
  try {
    await api('/api/adminconsole/logout', { method: 'POST', body: '{}' });
  } catch (_) {}
  authenticated = false;
  showLogin(true);
}

async function runCommand(line) {
  const command = String(line || '').trim();
  if (!command) return;
  appendEntry('command', command, '>');
  historyItems.push(command);
  historyItems = historyItems.slice(-100);
  historyIndex = historyItems.length;
  hideCompletions();
  try {
    const data = await api('/api/adminconsole/command', {
      method: 'POST',
      body: JSON.stringify({ line: command }),
    });
    if (data.clear) {
      clearOutput();
      return;
    }
    appendEntry(data.success ? 'ok' : 'err', data.output || (data.success ? 'OK' : 'ERR'), data.success ? '[OK]' : '[ERR]');
  } catch (err) {
    if (err.status === 401) {
      appendEntry('err', '登录已失效，请重新登录。', '[ERR]');
      authenticated = false;
      showLogin(true);
      return;
    }
    appendEntry('err', err.message || '请求失败', '[ERR]');
  }
}

function hideCompletions() {
  completionItems = [];
  completionIndex = -1;
  completionLine = '';
  completionAppliedLine = '';
  const box = $('console-completions');
  box.classList.add('hidden');
  box.innerHTML = '';
}

function applyCompletion(value, options = {}) {
  const input = $('console-command');
  const raw = options.baseLine ?? completionLine ?? input.value;
  const trailing = raw.endsWith(' ');
  const parts = raw.split(/\s+/);
  if (trailing || !parts.length) {
    parts.push(value);
  } else {
    parts[parts.length - 1] = value;
  }
  const nextValue = parts.filter(Boolean).join(' ') + (options.addSpace ? ' ' : '');
  input.value = nextValue;
  completionAppliedLine = nextValue;
  input.focus();
  if (!options.keepOpen) {
    hideCompletions();
  }
}

function activeCompletionValue() {
  if (!completionItems.length || completionIndex < 0) return '';
  return completionItems[Math.max(0, Math.min(completionIndex, completionItems.length - 1))];
}

function renderCompletions(items) {
  const box = $('console-completions');
  box.innerHTML = '';
  completionItems = items || [];
  completionIndex = completionItems.length ? 0 : -1;
  completionLine = $('console-command').value;
  completionAppliedLine = '';
  if (!completionItems.length) {
    hideCompletions();
    return;
  }
  completionItems.slice(0, 80).forEach((item, index) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `completion-item ${index === completionIndex ? 'active' : ''}`;
    button.textContent = item;
    button.addEventListener('mousedown', (event) => {
      event.preventDefault();
      applyCompletion(item);
    });
    box.appendChild(button);
  });
  box.classList.remove('hidden');
}

async function refreshCompletions() {
  if (!authenticated) return;
  if (completionAbort) completionAbort.abort();
  completionAbort = new AbortController();
  const line = $('console-command').value;
  try {
    const response = await fetch(`/api/adminconsole/complete?line=${encodeURIComponent(line)}`, {
      credentials: 'same-origin',
      signal: completionAbort.signal,
    });
    if (!response.ok) return;
    const data = await response.json();
    renderCompletions(data.items || []);
    return data.items || [];
  } catch (err) {
    if (err.name !== 'AbortError') hideCompletions();
  }
  return [];
}

function moveCompletion(delta) {
  if (!completionItems.length) return;
  completionIndex = (completionIndex + delta + completionItems.length) % completionItems.length;
  [...$('console-completions').children].forEach((child, index) => {
    child.classList.toggle('active', index === completionIndex);
    if (index === completionIndex) child.scrollIntoView({ block: 'nearest' });
  });
}

function scheduleCompletions(delay = 80) {
  window.clearTimeout($('console-command')._completeTimer);
  $('console-command')._completeTimer = window.setTimeout(refreshCompletions, delay);
}

function completionStillOwnsInput() {
  const value = $('console-command').value;
  if (!completionItems.length || $('console-completions').classList.contains('hidden')) return false;
  if (completionAppliedLine) return value === completionAppliedLine;
  return value === completionLine;
}

async function tabComplete(delta = 1) {
  const input = $('console-command');
  if (!completionStillOwnsInput()) {
    const items = await refreshCompletions();
    if (!items.length) return;
    completionIndex = delta < 0 ? items.length - 1 : 0;
    moveCompletion(0);
    applyCompletion(activeCompletionValue(), { keepOpen: true, baseLine: completionLine });
    return;
  }
  if (!completionAppliedLine) {
    applyCompletion(activeCompletionValue(), { keepOpen: true, baseLine: completionLine });
    return;
  }
  moveCompletion(delta);
  applyCompletion(activeCompletionValue(), { keepOpen: true, baseLine: completionLine });
  input.focus();
}

function bindEvents() {
  $('console-login-form').addEventListener('submit', (event) => {
    event.preventDefault();
    login($('console-password').value);
  });

  $('console-logout').addEventListener('click', logout);
  $('console-clear').addEventListener('click', clearOutput);

  $('console-command-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const input = $('console-command');
    const line = input.value;
    input.value = '';
    runCommand(line);
  });

  $('console-command').addEventListener('input', () => {
    completionAppliedLine = '';
    scheduleCompletions(80);
  });

  $('console-command').addEventListener('focus', () => {
    if ($('console-command').value || !$('console-completions').classList.contains('hidden')) {
      scheduleCompletions(0);
    }
  });

  $('console-command').addEventListener('keydown', (event) => {
    const input = $('console-command');
    if (event.key === 'Tab') {
      event.preventDefault();
      tabComplete(event.shiftKey ? -1 : 1);
      return;
    }
    if (event.key === 'ArrowDown' && completionItems.length) {
      event.preventDefault();
      moveCompletion(1);
      return;
    }
    if (event.key === 'ArrowUp' && completionItems.length) {
      event.preventDefault();
      moveCompletion(-1);
      return;
    }
    if (event.key === 'ArrowUp' && !input.value && historyItems.length) {
      event.preventDefault();
      historyIndex = Math.max(0, historyIndex - 1);
      input.value = historyItems[historyIndex] || '';
      return;
    }
    if (event.key === 'ArrowDown' && !completionItems.length && historyItems.length) {
      event.preventDefault();
      historyIndex = Math.min(historyItems.length, historyIndex + 1);
      input.value = historyItems[historyIndex] || '';
      return;
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'l') {
      event.preventDefault();
      clearOutput();
    }
    if (event.key === 'Escape') hideCompletions();
  });
}

bindEvents();
checkAuth();
