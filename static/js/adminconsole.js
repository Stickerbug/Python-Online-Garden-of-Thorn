const $ = (id) => document.getElementById(id);

const MAX_OUTPUT_ENTRIES = 500;
const MAX_HISTORY_ENTRIES = 100;
const HISTORY_STORAGE_KEY = 'gtn.adminconsole.history.v1';
let authenticated = false;
let historyItems = [];
let historyIndex = 0;
let historyDraft = '';
let completionItems = [];
let completionIndex = -1;
let completionAbort = null;
let completionLine = '';
let completionAppliedLine = '';
let completionCursor = 0;
let csrfToken = '';
let commandQueue = [];
let activeCommand = null;
let secretPrompt = null;

function loadHistory() {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(HISTORY_STORAGE_KEY) || '[]');
    historyItems = Array.isArray(parsed)
      ? parsed.filter((item) => typeof item === 'string' && item.trim()).slice(-MAX_HISTORY_ENTRIES)
      : [];
  } catch (_) {
    historyItems = [];
  }
  historyIndex = historyItems.length;
}

function saveHistory() {
  try {
    window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(historyItems.slice(-MAX_HISTORY_ENTRIES)));
  } catch (_) {}
}

function setConnectionState(state, activity = '') {
  const status = $('console-status');
  status.dataset.state = state;
  status.textContent = state;
  $('console-activity').textContent = activity || (state === 'running' ? 'running' : 'idle');
}

function updateQueueStatus() {
  const queued = commandQueue.length;
  const running = !!activeCommand;
  $('console-stop').disabled = !running;
  if (running) {
    setConnectionState('running', queued ? `1 running, ${queued} queued` : '1 running');
  } else if (authenticated) {
    setConnectionState('connected', queued ? `${queued} queued` : 'idle');
  }
}

function showLogin(show) {
  $('console-login').classList.toggle('hidden', !show);
  $('console-shell').classList.toggle('hidden', show);
  if (show) {
    setConnectionState('offline', 'authentication required');
    $('console-password').focus();
  } else {
    setConnectionState('connected');
    $('console-command').focus();
  }
}

async function api(path, options = {}) {
  const { headers: extraHeaders = {}, ...fetchOptions } = options;
  const headers = { 'Content-Type': 'application/json', ...extraHeaders };
  if (csrfToken && String(fetchOptions.method || 'GET').toUpperCase() !== 'GET') {
    headers['X-Admin-Console-CSRF'] = csrfToken;
  }
  const response = await fetch(path, {
    credentials: 'same-origin',
    headers,
    ...fetchOptions,
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

function redactCommand(line) {
  const command = String(line || '').trim();
  return command.replace(
    /^(\s*\/?account\s+password\s+(?:"[^"]+"|'[^']+'|\S+))(?:\s+.*)?$/i,
    '$1 ********',
  );
}

function safeHistoryCommand(line) {
  const command = String(line || '').trim();
  const passwordMatch = command.match(
    /^(\s*\/?account\s+password\s+(?:"[^"]+"|'[^']+'|\S+))(?:\s+.*)?$/i,
  );
  return passwordMatch ? passwordMatch[1] : command;
}

function rememberCommand(line) {
  const safe = safeHistoryCommand(line);
  if (!safe) return;
  if (historyItems[historyItems.length - 1] !== safe) {
    historyItems.push(safe);
  }
  historyItems = historyItems.slice(-MAX_HISTORY_ENTRIES);
  historyIndex = historyItems.length;
  historyDraft = '';
  saveHistory();
}

function quoteShellArg(value) {
  return `'${String(value || '').replace(/'/g, `'\"'\"'`)}'`;
}

function passwordPromptBase(line) {
  const match = String(line || '').trim().match(
    /^(\s*\/?account\s+password\s+(?:"[^"]+"|'[^']+'|\S+))\s*$/i,
  );
  return match ? match[1] : '';
}

function enterSecretPrompt(baseLine) {
  secretPrompt = { baseLine };
  const input = $('console-command');
  input.value = '';
  input.type = 'password';
  input.autocomplete = 'new-password';
  input.placeholder = '输入新密码（不会回显）';
  $('console-prompt').textContent = 'password>';
  $('console-command-form').classList.add('secret');
  hideCompletions();
  input.focus();
}

function leaveSecretPrompt() {
  secretPrompt = null;
  const input = $('console-command');
  input.value = '';
  input.type = 'text';
  input.autocomplete = 'off';
  input.placeholder = '';
  $('console-prompt').textContent = '>';
  $('console-command-form').classList.remove('secret');
  input.focus();
}

async function checkAuth() {
  try {
    const data = await api('/api/adminconsole/me');
    authenticated = !!data.authenticated;
    csrfToken = data.csrf_token || '';
    showLogin(!authenticated);
    if (authenticated) clearOutput();
  } catch (_) {
    authenticated = false;
    csrfToken = '';
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
    const auth = await api('/api/adminconsole/me');
    csrfToken = auth.csrf_token || '';
    authenticated = true;
    $('console-password').value = '';
    showLogin(false);
    clearOutput();
  } catch (err) {
    $('console-login-error').textContent = err.status === 429 ? '尝试次数过多，请稍后再试。' : '密码错误。';
  }
}

async function logout() {
  interruptActiveCommand();
  try {
    await api('/api/adminconsole/logout', { method: 'POST', body: '{}' });
  } catch (_) {}
  authenticated = false;
  csrfToken = '';
  commandQueue = [];
  leaveSecretPrompt();
  showLogin(true);
}

function enqueueCommand(line, displayLine = '') {
  const command = String(line || '').trim();
  if (!command) return;
  const visible = displayLine || redactCommand(command);
  appendEntry('command', visible, '>');
  rememberCommand(command);
  commandQueue.push({
    id: `cmd-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    line: command,
    displayLine: visible,
    queuedAt: performance.now(),
  });
  hideCompletions();
  updateQueueStatus();
  processCommandQueue();
}

function waitWithSignal(delay, signal) {
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(resolve, delay);
    signal.addEventListener('abort', () => {
      window.clearTimeout(timer);
      reject(new DOMException('Aborted', 'AbortError'));
    }, { once: true });
  });
}

async function waitForCommandJob(jobId, signal) {
  let delay = 250;
  while (true) {
    await waitWithSignal(delay, signal);
    const data = await api(`/api/adminconsole/jobs/${encodeURIComponent(jobId)}`, { signal });
    const state = data.status || 'queued';
    $('console-activity').textContent = `${jobId} ${state}`;
    if (state === 'done' || state === 'failed' || state === 'cancelled') {
      return {
        ...(data.result || { success: false, output: '后台任务没有返回结果。' }),
        request_id: data.request_id,
        elapsed_ms: data.elapsed_ms,
      };
    }
    delay = Math.min(1000, delay + 150);
  }
}

async function processCommandQueue() {
  if (activeCommand || !commandQueue.length || !authenticated) return;
  const command = commandQueue.shift();
  const controller = new AbortController();
  activeCommand = { ...command, controller, jobId: '' };
  updateQueueStatus();
  const started = performance.now();
  let requestFailed = false;
  try {
    let data = await api('/api/adminconsole/command', {
      method: 'POST',
      signal: controller.signal,
      body: JSON.stringify({ line: command.line, request_id: command.id }),
    });
    if (data.accepted && data.job_id) {
      activeCommand.jobId = data.job_id;
      data = await waitForCommandJob(data.job_id, controller.signal);
    }
    if (data.clear) {
      clearOutput();
    } else {
      const elapsed = Number.isFinite(Number(data.elapsed_ms))
        ? Number(data.elapsed_ms)
        : performance.now() - started;
      const trace = String(data.request_id || command.id).slice(-8);
      appendEntry(
        data.success ? 'ok' : 'err',
        data.output || (data.success ? 'OK' : 'ERR'),
        `${data.success ? '[OK]' : '[ERR]'} #${trace} ${Math.max(0, elapsed).toFixed(0)}ms`,
      );
    }
  } catch (err) {
    if (err.name === 'AbortError') {
      appendEntry('err', '已停止等待响应；若命令已经开始修改数据，服务端可能仍会完成该操作。', '[INTERRUPTED]');
      return;
    }
    if (err.status === 401 || err.status === 403) {
      appendEntry('err', '登录已失效，请重新登录。', '[ERR]');
      authenticated = false;
      csrfToken = '';
      commandQueue = [];
      showLogin(true);
      return;
    }
    if (err.status === 409) {
      appendEntry('err', err.message || '已有管理命令正在执行。', '[BUSY]');
      return;
    }
    requestFailed = true;
    setConnectionState('offline', 'request failed');
    appendEntry('err', err.message || '请求失败', '[ERR]');
  } finally {
    activeCommand = null;
    updateQueueStatus();
    if (authenticated) {
      if (requestFailed) {
        setConnectionState('offline', 'request failed');
      } else {
        setConnectionState('connected', commandQueue.length ? `${commandQueue.length} queued` : 'idle');
      }
      window.setTimeout(processCommandQueue, 0);
    }
  }
}

function interruptActiveCommand() {
  if (!activeCommand) return;
  if (activeCommand.jobId) {
    api(`/api/adminconsole/jobs/${encodeURIComponent(activeCommand.jobId)}/cancel`, {
      method: 'POST',
      body: '{}',
    }).catch(() => null);
  }
  activeCommand.controller.abort();
}

function hideCompletions() {
  completionItems = [];
  completionIndex = -1;
  completionLine = '';
  completionAppliedLine = '';
  completionCursor = 0;
  const box = $('console-completions');
  box.classList.add('hidden');
  box.innerHTML = '';
}

function completionValue(item) {
  return typeof item === 'string' ? item : String(item?.value || '');
}

function applyCompletion(value, options = {}) {
  const input = $('console-command');
  const raw = options.baseLine ?? completionLine ?? input.value;
  const cursor = options.baseCursor ?? completionCursor ?? raw.length;
  const before = raw.slice(0, cursor);
  const tokenMatch = before.match(/[^\s]*$/);
  const tokenStart = tokenMatch ? cursor - tokenMatch[0].length : cursor;
  const nextValue = `${raw.slice(0, tokenStart)}${value}${options.addSpace ? ' ' : ''}${raw.slice(cursor)}`;
  const nextCursor = tokenStart + value.length + (options.addSpace ? 1 : 0);
  input.value = nextValue;
  input.setSelectionRange(nextCursor, nextCursor);
  completionAppliedLine = nextValue;
  input.focus();
  if (!options.keepOpen) {
    hideCompletions();
  }
}

function activeCompletionValue() {
  if (!completionItems.length || completionIndex < 0) return '';
  return completionValue(completionItems[Math.max(0, Math.min(completionIndex, completionItems.length - 1))]);
}

function renderCompletions(items) {
  const box = $('console-completions');
  box.innerHTML = '';
  completionItems = items || [];
  completionIndex = completionItems.length ? 0 : -1;
  completionLine = $('console-command').value;
  completionCursor = $('console-command').selectionStart ?? completionLine.length;
  completionAppliedLine = '';
  if (!completionItems.length) {
    hideCompletions();
    return;
  }
  completionItems.slice(0, 80).forEach((item, index) => {
    const value = completionValue(item);
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `completion-item ${index === completionIndex ? 'active' : ''}`;
    const valueNode = document.createElement('span');
    valueNode.className = 'completion-value';
    valueNode.textContent = value;
    const detailNode = document.createElement('span');
    detailNode.className = 'completion-detail';
    detailNode.textContent = typeof item === 'object' ? String(item.detail || item.kind || '') : '';
    button.append(valueNode, detailNode);
    button.addEventListener('mousedown', (event) => {
      event.preventDefault();
      applyCompletion(value);
    });
    box.appendChild(button);
  });
  box.classList.remove('hidden');
}

async function refreshCompletions() {
  if (!authenticated || secretPrompt) return [];
  if (completionAbort) completionAbort.abort();
  completionAbort = new AbortController();
  const line = $('console-command').value;
  if (!line.trim()) {
    hideCompletions();
    return [];
  }
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

function scheduleCompletions(delay = 160) {
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
  if (secretPrompt) return;
  if (!completionStillOwnsInput()) {
    let items;
    if (!input.value.trim()) {
      if (completionAbort) completionAbort.abort();
      try {
        const response = await fetch('/api/adminconsole/complete?line=', {
          credentials: 'same-origin',
        });
        const data = response.ok ? await response.json() : {};
        items = data.items || [];
        renderCompletions(items);
      } catch (_) {
        items = [];
      }
    } else {
      items = await refreshCompletions();
    }
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

function moveHistory(delta) {
  if (!historyItems.length) return;
  const input = $('console-command');
  if (historyIndex === historyItems.length) {
    historyDraft = input.value;
  }
  historyIndex = Math.max(0, Math.min(historyItems.length, historyIndex + delta));
  input.value = historyIndex === historyItems.length
    ? historyDraft
    : (historyItems[historyIndex] || '');
  input.setSelectionRange(input.value.length, input.value.length);
  hideCompletions();
}

function searchHistory() {
  if (!historyItems.length) return;
  const input = $('console-command');
  const needle = input.value.trim().toLowerCase();
  const start = Math.min(historyIndex - 1, historyItems.length - 1);
  for (let index = start; index >= 0; index -= 1) {
    if (!needle || historyItems[index].toLowerCase().includes(needle)) {
      historyIndex = index;
      input.value = historyItems[index];
      input.setSelectionRange(input.value.length, input.value.length);
      hideCompletions();
      return;
    }
  }
}

function bindEvents() {
  $('console-login-form').addEventListener('submit', (event) => {
    event.preventDefault();
    login($('console-password').value);
  });

  $('console-logout').addEventListener('click', logout);
  $('console-clear').addEventListener('click', clearOutput);
  $('console-stop').addEventListener('click', interruptActiveCommand);

  $('console-command-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const input = $('console-command');
    if (secretPrompt) {
      const password = input.value;
      if (!password) return;
      const baseLine = secretPrompt.baseLine;
      leaveSecretPrompt();
      enqueueCommand(`${baseLine} ${quoteShellArg(password)}`, `${baseLine} ********`);
      return;
    }
    const line = input.value.trim();
    if (!line) return;
    const promptBase = passwordPromptBase(line);
    if (promptBase) {
      enterSecretPrompt(promptBase);
      return;
    }
    input.value = '';
    enqueueCommand(line);
  });

  $('console-command').addEventListener('input', () => {
    completionAppliedLine = '';
    historyIndex = historyItems.length;
    historyDraft = $('console-command').value;
    if (!$('console-command').value.trim() || secretPrompt) {
      hideCompletions();
      return;
    }
    scheduleCompletions(160);
  });

  $('console-command').addEventListener('focus', () => {
    if ($('console-command').value || !$('console-completions').classList.contains('hidden')) {
      scheduleCompletions(0);
    }
  });

  $('console-command').addEventListener('keydown', (event) => {
    const input = $('console-command');
    const control = event.ctrlKey || event.metaKey;
    if (control && event.key.toLowerCase() === 'c') {
      event.preventDefault();
      if (secretPrompt) {
        leaveSecretPrompt();
        appendEntry('info', '已取消密码输入。', '[CANCELLED]');
      } else if (activeCommand) {
        interruptActiveCommand();
      } else {
        input.value = '';
        hideCompletions();
      }
      return;
    }
    if (control && event.key.toLowerCase() === 'r' && !secretPrompt) {
      event.preventDefault();
      searchHistory();
      return;
    }
    if (event.key === 'Enter' && !event.isComposing) {
      event.preventDefault();
      $('console-command-form').requestSubmit();
      return;
    }
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
    if (event.key === 'ArrowUp' && !completionItems.length && !secretPrompt) {
      event.preventDefault();
      moveHistory(-1);
      return;
    }
    if (event.key === 'ArrowDown' && !completionItems.length && !secretPrompt) {
      event.preventDefault();
      moveHistory(1);
      return;
    }
    if (control && event.key.toLowerCase() === 'l') {
      event.preventDefault();
      clearOutput();
      return;
    }
    if (event.key === 'Escape') {
      if (secretPrompt) {
        leaveSecretPrompt();
        appendEntry('info', '已取消密码输入。', '[CANCELLED]');
      } else {
        hideCompletions();
      }
    }
  });

  window.addEventListener('offline', () => setConnectionState('offline', 'browser offline'));
  window.addEventListener('online', () => {
    if (authenticated && !activeCommand) setConnectionState('connected');
  });
}

loadHistory();
bindEvents();
checkAuth();
