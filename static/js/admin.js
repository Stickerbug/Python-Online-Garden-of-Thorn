const $ = (id) => document.getElementById(id);

let adminState = null;
let refreshTimer = null;
let registeredRefreshTimer = null;
let commandHistory = [];
let historyIndex = 0;
let completionState = null;
let registeredUsersState = null;
let registeredUsersSearchTimer = null;
const expandedRegisteredUsers = new Set();
const registeredUserDetails = new Map();

const STATUS_LABELS = {
  lobby: '大厅',
  in_game: '对局中',
  spectating: '观战中',
  reconnecting: '重连中',
  solo: '单人训练',
  tutorial: '新手教程',
};

const PHASE_LABELS = {
  action: '行动',
  draw: '抽牌',
  response: '响应',
  choice: '选择',
  playing: '进行中',
  draft: '选牌',
  event_select: '开局事件',
  game_over: '结束',
};

const EVENT_KIND_LABELS = {
  admin: '管理',
  player: '玩家',
  game: '对局',
  error: '错误',
  security: '安全',
};

function labelFrom(map, value) {
  return map[value] || value || '-';
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
  } catch {
    data = { success: false, error: text || response.statusText };
  }
  if (!response.ok) {
    const error = new Error(data.error || response.statusText);
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
}

function formatBytes(value) {
  if (value == null || Number.isNaN(Number(value))) return '-';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = Number(value);
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(index ? 1 : 0)} ${units[index]}`;
}

function formatUptime(seconds) {
  seconds = Math.max(0, Number(seconds) || 0);
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (d) return `${d}天 ${h}时 ${m}分`;
  if (h) return `${h}时 ${m}分 ${s}秒`;
  if (m) return `${m}分 ${s}秒`;
  return `${s}秒`;
}

function formatAdminTime(value) {
  if (!value) return '-';
  const date = value instanceof Date ? value : new Date(String(value));
  if (Number.isNaN(date.getTime())) return String(value);
  try {
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hourCycle: 'h23',
    }).formatToParts(date).reduce((acc, part) => {
      if (part.type !== 'literal') acc[part.type] = part.value;
      return acc;
    }, {});
    return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}:${parts.second}`;
  } catch {
    return String(value);
  }
}

function valueOrDash(value) {
  return value == null || value === '' ? '-' : value;
}

function formatPercent(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '0%';
  return `${n.toFixed(1).replace(/\.0$/, '')}%`;
}

function escapeHtml(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function showShell(authenticated) {
  $('admin-login').classList.toggle('hidden', authenticated);
  $('admin-shell').classList.toggle('hidden', !authenticated);
  if (authenticated) {
    loadStatus();
    loadRegisteredUsers();
    if (!refreshTimer) refreshTimer = setInterval(loadStatus, 1000);
    if (!registeredRefreshTimer) registeredRefreshTimer = setInterval(loadRegisteredUsers, 10000);
  } else {
    if (refreshTimer) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
    if (registeredRefreshTimer) {
      clearInterval(registeredRefreshTimer);
      registeredRefreshTimer = null;
    }
  }
}

async function checkAuth() {
  const data = await api('/api/admin/me');
  showShell(!!data.authenticated);
}

async function login(password) {
  $('admin-login-error').textContent = '';
  try {
    await api('/api/admin/login', {
      method: 'POST',
      body: JSON.stringify({ password }),
    });
    $('admin-password').value = '';
    appendTerminal('login', '管理员会话已开启。');
    showShell(true);
  } catch (error) {
    $('admin-login-error').textContent = error.status === 429 ? '尝试次数过多，请稍后再试。' : '密码错误。';
  }
}

async function logout() {
  try {
    await api('/api/admin/logout', { method: 'POST', body: '{}' });
  } catch {}
  showShell(false);
}

async function loadStatus() {
  try {
    adminState = await api('/api/admin/status');
    renderStatus(adminState);
  } catch (error) {
    if (error.status === 401) {
      showShell(false);
      return;
    }
    appendTerminal('status', `状态加载失败：${error.message}`, true);
  }
}

function renderStatus(data) {
  const metrics = data.metrics || {};
  const summary = data.summary || {};
  const process = metrics.process || {};
  const system = metrics.system || {};
  const disk = metrics.disk || {};

  const pcpu = process.cpu_percent == null ? '-' : `${Number(process.cpu_percent).toFixed(1)}%`;
  const scpu = system.cpu_percent == null ? '-' : `${Number(system.cpu_percent).toFixed(1)}%`;
  $('metric-cpu').textContent = pcpu;
  $('metric-cpu-sub').textContent = `进程 ${pcpu} / 系统 ${scpu}`;
  $('metric-memory').textContent = formatBytes(process.memory_rss);
  $('metric-memory-sub').textContent = system.memory_percent == null
    ? '系统内存不可用'
    : `${formatBytes(system.memory_used)} / ${formatBytes(system.memory_total)}（${system.memory_percent}%）`;
  $('metric-disk').textContent = disk.percent == null ? '-' : `${disk.percent}%`;
  $('metric-uptime').textContent = formatUptime(metrics.uptime_seconds);
  $('metric-clock').textContent = formatAdminTime(metrics.time);
  $('metric-online').textContent = summary.online_players || 0;
  $('metric-online-sub').textContent = `大厅 ${summary.lobby_players || 0} / 观战 ${summary.spectators || 0}`;
  $('metric-rooms').textContent = summary.rooms || 0;
  $('metric-history-sub').textContent = `历史 ${summary.history_count || 0}`;

  renderPlayers(data.players || []);
  renderRooms(data.rooms || []);
  renderEvents(data.events || []);
  renderHistory(data.history || []);
}

function renderPlayers(players) {
  $('players-count').textContent = players.length;
  if (!players.length) {
    $('players-table').innerHTML = '<div class="log-item">暂无在线玩家。</div>';
    return;
  }
  $('players-table').innerHTML = `
    <table>
      <thead><tr><th>昵称</th><th>状态</th><th>模式</th><th>房间</th><th>SID</th><th>操作</th></tr></thead>
      <tbody>
        ${players.map((p) => `
          <tr>
            <td>${escapeHtml(p.nickname)}</td>
            <td>${escapeHtml(labelFrom(STATUS_LABELS, p.status))}</td>
            <td>${escapeHtml(p.mode || '')}</td>
            <td>${escapeHtml(p.room_id ?? p.spectating_room ?? '-')}</td>
            <td><span class="muted">${escapeHtml(p.sid)}</span></td>
            <td><button class="row-action danger" data-kick="${escapeHtml(p.sid)}">踢出</button></td>
          </tr>`).join('')}
      </tbody>
    </table>`;
}

function registeredUsersQuery() {
  const params = new URLSearchParams();
  params.set('query', $('registered-users-search')?.value || '');
  params.set('sort', $('registered-users-sort')?.value || 'last_login_at');
  params.set('order', $('registered-users-order')?.value || 'desc');
  params.set('limit', '120');
  return params;
}

async function loadRegisteredUsers() {
  const panel = $('registered-users-panel');
  if (!panel) return;
  try {
    if (!registeredUsersState) {
      panel.innerHTML = '<div class="log-item">正在读取账号列表。</div>';
    }
    registeredUsersState = await api(`/api/admin/users?${registeredUsersQuery().toString()}`);
    renderRegisteredUsers(registeredUsersState);
  } catch (error) {
    panel.innerHTML = `<div class="log-item error">账号列表加载失败：${escapeHtml(error.message)}</div>`;
  }
}

function queueRegisteredUsersLoad() {
  clearTimeout(registeredUsersSearchTimer);
  registeredUsersSearchTimer = setTimeout(loadRegisteredUsers, 180);
}

function renderRegisteredUsers(data) {
  const users = data.users || [];
  $('registered-users-count').textContent = `${users.length}/${data.total || 0}`;
  if (!users.length) {
    $('registered-users-panel').innerHTML = '<div class="log-item">暂无注册玩家。</div>';
    return;
  }
  $('registered-users-panel').innerHTML = users.map(renderRegisteredUserCard).join('');
}

function renderOnlinePill(user) {
  if (!user.online) return '<span class="user-pill muted-pill">离线</span>';
  const status = labelFrom(STATUS_LABELS, user.online.status);
  const room = user.online.room_id ?? user.online.spectating_room;
  return `<span class="user-pill online-pill">${escapeHtml(status)}${room != null ? ` #${escapeHtml(room)}` : ''}</span>`;
}

function renderRegisteredUserCard(user) {
  const key = String(user.id);
  const expanded = expandedRegisteredUsers.has(key);
  const detail = registeredUserDetails.get(key);
  const winRate = formatPercent(user.win_rate);
  const detailsHtml = expanded ? renderRegisteredUserDetails(user, detail) : '';
  return `
    <article class="registered-user-card ${expanded ? 'expanded' : ''}">
      <button class="registered-user-main" type="button" data-user-toggle="${escapeHtml(key)}">
        <div class="user-avatar">${escapeHtml(String(user.username || '?').slice(0, 1).toUpperCase())}</div>
        <div class="user-main-text">
          <div class="user-title-row">
            <strong>${escapeHtml(user.username)}</strong>
            ${renderOnlinePill(user)}
          </div>
          <div class="user-meta-row">
            <span>ID ${escapeHtml(user.id)}</span>
            <span>上次登录 ${escapeHtml(formatAdminTime(user.last_login_at))}</span>
            <span>注册 ${escapeHtml(formatAdminTime(user.created_at))}</span>
          </div>
        </div>
        <div class="user-score-row" aria-label="账号战绩">
          <span><b>${escapeHtml(user.games_played || 0)}</b> 对局</span>
          <span><b>${escapeHtml(user.wins || 0)}</b> 胜</span>
          <span><b>${escapeHtml(user.losses || 0)}</b> 败</span>
          <span><b>${escapeHtml(user.draws || 0)}</b> 平</span>
          <span><b>${escapeHtml(winRate)}</b> 胜率</span>
        </div>
        <span class="expand-mark">${expanded ? '收起' : '详情'}</span>
      </button>
      ${detailsHtml}
    </article>`;
}

function renderRegisteredUserDetails(user, detail) {
  if (!detail) {
    return '<div class="registered-user-details"><div class="log-item">正在读取账号详情。</div></div>';
  }
  if (detail.error) {
    return `<div class="registered-user-details"><div class="log-item error">${escapeHtml(detail.error)}</div></div>`;
  }
  const matches = detail.matches || [];
  const online = (detail.user && detail.user.online) || user.online;
  return `
    <div class="registered-user-details">
      <div class="user-detail-grid">
        <div class="user-detail-block">
          <h3>账号数据</h3>
          <dl>
            <div><dt>用户名</dt><dd>${escapeHtml(user.username)}</dd></div>
            <div><dt>账号ID</dt><dd>${escapeHtml(user.id)}</dd></div>
            <div><dt>注册时间</dt><dd>${escapeHtml(formatAdminTime(user.created_at))}</dd></div>
            <div><dt>上次登录</dt><dd>${escapeHtml(formatAdminTime(user.last_login_at))}</dd></div>
            <div><dt>当前状态</dt><dd>${online ? `${escapeHtml(labelFrom(STATUS_LABELS, online.status))} ${online.room_id != null ? `#${escapeHtml(online.room_id)}` : ''}` : '离线'}</dd></div>
          </dl>
        </div>
        <div class="user-detail-block">
          <h3>最近对局</h3>
          ${matches.length ? `
            <div class="user-match-list">
              ${matches.map(renderUserMatch).join('')}
            </div>` : '<div class="empty-detail">暂无已保存对局。</div>'}
        </div>
      </div>
    </div>`;
}

function renderUserMatch(match) {
  const players = (match.players || []).join(' / ');
  const result = match.result === 'draw' ? '平局' : valueOrDash(match.winner_name);
  return `
    <div class="user-match-row">
      <time>${escapeHtml(formatAdminTime(match.ended_at || match.started_at))}</time>
      <div><b>${escapeHtml(match.mode || '-')}</b> · ${escapeHtml(players)}</div>
      <div class="muted">结果 ${escapeHtml(result)} · 回合 ${escapeHtml(valueOrDash(match.rounds))} · 时长 ${escapeHtml(formatUptime(match.duration_seconds || 0))}</div>
    </div>`;
}

async function toggleRegisteredUser(userId) {
  const key = String(userId);
  if (expandedRegisteredUsers.has(key)) {
    expandedRegisteredUsers.delete(key);
    renderRegisteredUsers(registeredUsersState || { users: [], total: 0 });
    return;
  }
  expandedRegisteredUsers.add(key);
  renderRegisteredUsers(registeredUsersState || { users: [], total: 0 });
  if (registeredUserDetails.has(key)) return;
  try {
    registeredUserDetails.set(key, await api(`/api/admin/users/${encodeURIComponent(key)}`));
  } catch (error) {
    registeredUserDetails.set(key, { error: `账号详情加载失败：${error.message}` });
  }
  renderRegisteredUsers(registeredUsersState || { users: [], total: 0 });
}

function renderRooms(rooms) {
  $('rooms-count').textContent = rooms.length;
  if (!rooms.length) {
    $('rooms-table').innerHTML = '<div class="log-item">暂无进行中的对局。</div>';
    return;
  }
  $('rooms-table').innerHTML = `
    <table>
      <thead><tr><th>ID</th><th>模式</th><th>阶段</th><th>回合</th><th>玩家</th><th>观战</th><th>操作</th></tr></thead>
      <tbody>
        ${rooms.map((r) => `
          <tr>
            <td>#${r.room_id}</td>
            <td>${escapeHtml(r.mode)}</td>
            <td>${escapeHtml(labelFrom(PHASE_LABELS, r.phase))}</td>
            <td>${escapeHtml(r.round)}</td>
            <td>${escapeHtml((r.players || []).join(' / '))}</td>
            <td>${escapeHtml(r.spectators)}</td>
            <td>
              <div class="row-actions">
                <button class="row-action" data-skip="${r.room_id}">跳过</button>
                <button class="row-action danger" data-end="${r.room_id}">结束</button>
              </div>
            </td>
          </tr>`).join('')}
      </tbody>
    </table>`;
}

function renderEvents(events) {
  $('events-list').innerHTML = events.length ? events.slice(0, 80).map((event) => `
    <div class="log-item">
      <time>${escapeHtml(formatAdminTime(event.time))} · ${escapeHtml(labelFrom(EVENT_KIND_LABELS, event.kind))}</time>
      ${escapeHtml(event.message)}
    </div>`).join('') : '<div class="log-item">暂无事件。</div>';
}

function renderHistory(history) {
  $('history-list').innerHTML = history.length ? history.slice(0, 80).map((item) => `
    <div class="log-item">
      <time>${escapeHtml(formatAdminTime(item.time))} · 房间 #${escapeHtml(item.room_id)} · ${escapeHtml(item.mode)}</time>
      ${escapeHtml((item.players || []).join(' / '))}<br>
      胜者=${escapeHtml(item.winner)} · 回合=${escapeHtml(item.round)} · 时长=${formatUptime(item.duration_seconds || 0)}
    </div>`).join('') : '<div class="log-item">暂无历史对局。</div>';
}

function appendTerminal(command, output, isError = false) {
  const line = document.createElement('div');
  line.className = 'terminal-line';
  line.innerHTML = `<div class="cmd">&gt; ${escapeHtml(command)}</div><div class="${isError ? 'error' : ''}">${escapeHtml(output || '')}</div>`;
  $('terminal-output').appendChild(line);
  $('terminal-output').scrollTop = $('terminal-output').scrollHeight;
}

async function runCommand(line) {
  if (!line.trim()) return;
  commandHistory.push(line);
  historyIndex = commandHistory.length;
  try {
    const result = await api('/api/admin/command', {
      method: 'POST',
      body: JSON.stringify({ line }),
    });
    if (result.clear) {
      $('terminal-output').innerHTML = '';
      return;
    }
    appendTerminal(line, result.output || '', !result.success);
    await loadStatus();
  } catch (error) {
    appendTerminal(line, error.message, true);
  }
}

async function updateSuggestions() {
  const input = $('terminal-input');
  try {
    const data = await api(`/api/admin/complete?line=${encodeURIComponent(input.value)}`);
    const items = data.items || [];
    const box = $('terminal-suggestions');
    if (!items.length) {
      box.classList.add('hidden');
      box.innerHTML = '';
      return;
    }
    box.classList.remove('hidden');
    box.innerHTML = items.map((item) => `<button type="button" data-suggestion="${escapeHtml(item)}">${escapeHtml(item)}</button>`).join('');
  } catch {
    $('terminal-suggestions').classList.add('hidden');
  }
}

function hideSuggestions() {
  const box = $('terminal-suggestions');
  if (box) {
    box.classList.add('hidden');
    box.innerHTML = '';
  }
  completionState = null;
}

function completedLineFromBase(baseLine, cursor, value) {
  const before = baseLine.slice(0, cursor);
  const after = baseLine.slice(cursor);
  let completedBefore;
  if (/\s$/.test(before)) {
    completedBefore = `${before}${value}`;
  } else {
    completedBefore = before.replace(/\S*$/, value);
  }
  const spacer = after && !/^\s/.test(after) ? ' ' : '';
  return {
    line: `${completedBefore} ${spacer}${after}`,
    cursor: completedBefore.length + 1,
  };
}

function renderSuggestions() {
  const box = $('terminal-suggestions');
  if (!box || !completionState || !completionState.items.length) {
    if (box) {
      box.classList.add('hidden');
      box.innerHTML = '';
    }
    return;
  }
  box.classList.remove('hidden');
  box.innerHTML = completionState.items.map((item, index) => (
    `<button type="button" class="${index === completionState.index ? 'active' : ''}" data-suggestion-index="${index}" data-suggestion="${escapeHtml(item)}">${escapeHtml(item)}</button>`
  )).join('');
}

function applyCompletionIndex(index) {
  if (!completionState || !completionState.items.length) return;
  const input = $('terminal-input');
  completionState.index = ((index % completionState.items.length) + completionState.items.length) % completionState.items.length;
  const next = completedLineFromBase(completionState.baseLine, completionState.baseCursor, completionState.items[completionState.index]);
  input.value = next.line;
  input.focus();
  input.setSelectionRange(next.cursor, next.cursor);
  completionState.appliedCursor = next.cursor;
  renderSuggestions();
}

async function startOrCycleCompletion() {
  if (completionState && completionState.items.length) {
    applyCompletionIndex(completionState.index + 1);
    return;
  }
  const input = $('terminal-input');
  const baseLine = input.value;
  const baseCursor = input.selectionStart == null ? baseLine.length : input.selectionStart;
  try {
    const data = await api(`/api/admin/complete?line=${encodeURIComponent(baseLine)}`);
    const items = data.items || [];
    if (!items.length) {
      hideSuggestions();
      return;
    }
    completionState = {
      items,
      index: -1,
      baseLine,
      baseCursor,
      appliedCursor: baseCursor,
    };
    applyCompletionIndex(0);
  } catch {
    hideSuggestions();
  }
}

function applySuggestion(value) {
  const input = $('terminal-input');
  const cursor = input.selectionStart == null ? input.value.length : input.selectionStart;
  const next = completedLineFromBase(input.value, cursor, value);
  input.value = next.line;
  input.focus();
  input.setSelectionRange(next.cursor, next.cursor);
  hideSuggestions();
}

function bindEvents() {
  $('admin-login-form').addEventListener('submit', (event) => {
    event.preventDefault();
    login($('admin-password').value);
  });
  $('admin-logout').addEventListener('click', logout);
  $('admin-refresh').addEventListener('click', loadStatus);
  $('registered-users-refresh')?.addEventListener('click', loadRegisteredUsers);
  $('registered-users-search')?.addEventListener('input', queueRegisteredUsersLoad);
  $('registered-users-sort')?.addEventListener('change', loadRegisteredUsers);
  $('registered-users-order')?.addEventListener('change', loadRegisteredUsers);

  document.querySelectorAll('.admin-tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.admin-tab').forEach((item) => item.classList.remove('active'));
      tab.classList.add('active');
      const target = tab.dataset.tab;
      $('admin-gui').classList.toggle('hidden', target !== 'gui');
      $('admin-terminal').classList.toggle('hidden', target !== 'terminal');
      if (target === 'terminal') $('terminal-input').focus();
    });
  });

  $('broadcast-send').addEventListener('click', async () => {
    const msg = $('broadcast-input').value.trim();
    if (!msg) return;
    await runCommand(`broadcast ${msg}`);
    $('broadcast-input').value = '';
  });

  document.addEventListener('click', async (event) => {
    const userToggle = event.target.closest && event.target.closest('[data-user-toggle]');
    const kickSid = event.target.dataset && event.target.dataset.kick;
    const skipRoom = event.target.dataset && event.target.dataset.skip;
    const endRoom = event.target.dataset && event.target.dataset.end;
    const suggestion = event.target.dataset && event.target.dataset.suggestion;
    const suggestionIndex = event.target.dataset && event.target.dataset.suggestionIndex;
    if (suggestionIndex != null && completionState) {
      applyCompletionIndex(Number(suggestionIndex));
      return;
    }
    if (suggestion) {
      applySuggestion(suggestion);
      return;
    }
    if (userToggle) {
      await toggleRegisteredUser(userToggle.dataset.userToggle);
      return;
    }
    if (kickSid) {
      await runCommand(`kick ${kickSid}`);
    } else if (skipRoom) {
      await runCommand(`skip ${skipRoom}`);
    } else if (endRoom) {
      const winner = window.prompt('输入 winner：0、1 或 draw', 'draw');
      if (winner != null) await runCommand(`endgame ${endRoom} ${winner}`);
    }
  });

  $('terminal-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const line = $('terminal-input').value;
    $('terminal-input').value = '';
    hideSuggestions();
    runCommand(line);
  });

  $('terminal-input').addEventListener('input', hideSuggestions);
  $('terminal-input').addEventListener('click', () => {
    if (completionState) {
      const input = $('terminal-input');
      if (input.selectionStart !== completionState.appliedCursor || input.selectionEnd !== completionState.appliedCursor) {
        hideSuggestions();
      }
    }
  });
  $('terminal-input').addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.isComposing) {
      event.preventDefault();
      const line = $('terminal-input').value;
      $('terminal-input').value = '';
      hideSuggestions();
      runCommand(line);
      return;
    }
    if (event.key === 'Tab') {
      event.preventDefault();
      startOrCycleCompletion();
      return;
    }
    if (!['Shift', 'Control', 'Alt', 'Meta'].includes(event.key)) hideSuggestions();
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      historyIndex = Math.max(0, historyIndex - 1);
      $('terminal-input').value = commandHistory[historyIndex] || '';
    } else if (event.key === 'ArrowDown') {
      event.preventDefault();
      historyIndex = Math.min(commandHistory.length, historyIndex + 1);
      $('terminal-input').value = commandHistory[historyIndex] || '';
    }
  });
  $('terminal-input').addEventListener('keyup', () => {
    if (completionState) {
      const input = $('terminal-input');
      if (input.selectionStart !== completionState.appliedCursor || input.selectionEnd !== completionState.appliedCursor) {
        hideSuggestions();
      }
    }
  });
}

bindEvents();
checkAuth().catch(() => showShell(false));
