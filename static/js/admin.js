const $ = (id) => document.getElementById(id);

let adminState = null;
let refreshTimer = null;
let registeredRefreshTimer = null;
let commandHistory = [];
let historyIndex = 0;
let completionState = null;
let registeredUsersState = null;
let registeredUsersSearchTimer = null;
let replaySearchTimer = null;
const expandedRegisteredUsers = new Set();
const registeredUserDetails = new Map();
let replayState = { items: [], offset: 0, hasMore: false, loading: false };
let replayTimeline = [];
let replayFrameIndex = 0;
let replaySpeed = 1;
let replayTimer = null;
let replayData = null;
let gameChatTimer = null;
let gameChatSignature = '';

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

function formatNumber(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '-';
  return n.toLocaleString('zh-CN');
}

function escapeHtml(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function gameChatChannelLabel(entry = {}) {
  const channel = entry.chat_channel || entry.channel || '';
  if (!channel || channel === 'public') return '';
  if (channel === 'team') return '队伍';
  if (channel === 'enemy') return '敌方';
  if (channel === 'private') return `私聊→${entry.chat_target_name || entry.targetName || '?'}`;
  return channel;
}

function gameChatRolePrefix(entry = {}) {
  if (entry.console_player || entry.special_role === 'console') return '控制台';
  if (entry.is_admin_player || entry.admin || entry.isAdminPlayer) return '管理员';
  if (entry.special_role === 'chief_designer') return '总设计师';
  if (entry.special_role === 'right_angle_person') return '直角人';
  return entry.special_role_label || '';
}

function gameChatDisplayName(entry = {}) {
  if (entry.system) return '[系统]';
  const spectator = entry.is_spectator ? '[观战]' : '';
  const prefix = gameChatRolePrefix(entry);
  const name = entry.nickname || entry.display_nick || '?';
  return `${spectator}${prefix ? `[${prefix}]` : ''}${name}`;
}

function renderGameChatEntry(entry = {}) {
  if (entry.type === 'time') {
    return `<div class="chat-time-separator">${escapeHtml(entry.display_time || '')}</div>`;
  }
  const channelLabel = gameChatChannelLabel(entry);
  const channel = entry.chat_channel || entry.channel || 'public';
  const roleColor = entry.special_role_color || (entry.is_admin_player ? 'admin' : '');
  const nameClasses = [
    'chat-nick',
    entry.system ? 'system-name' : '',
    (entry.is_admin_player || entry.console_player || roleColor === 'admin') ? 'admin-name' : '',
    roleColor === 'bloom' ? 'bloom-name' : '',
    roleColor === 'guard' ? 'guard-name' : '',
  ].filter(Boolean).join(' ');
  const nick = gameChatDisplayName(entry);
  const repeatCount = Number(entry.repeat_count || entry.repeatCount || 1);
  const repeatHtml = repeatCount > 1 ? `<span class="chat-repeat-count"> ×${repeatCount}</span>` : '';
  return `
    <div class="log-entry log-chat">
      ${channelLabel ? `<span class="chat-channel chat-channel-${escapeHtml(channel)}">[${escapeHtml(channelLabel)}] </span>` : ''}
      <span class="${nameClasses}">${escapeHtml(entry.system ? `${nick} ` : `${nick}: `)}</span>${escapeHtml(entry.text || '')}${repeatHtml}
    </div>
  `;
}

function renderGameChat(data = {}) {
  const log = $('admin-game-chat-log');
  if (!log) return;
  const items = Array.isArray(data.items) ? data.items : [];
  const signature = JSON.stringify(items.map((entry) => [
    entry && entry.type,
    entry && entry.id,
    entry && entry.time,
    entry && entry.nickname,
    entry && entry.text,
    entry && entry.repeat_count,
    entry && entry.display_time,
    entry && entry.chat_channel,
    entry && entry.system,
    entry && entry.scope,
    entry && entry.room_id,
  ]));
  if (signature === gameChatSignature) return;
  gameChatSignature = signature;
  log.innerHTML = items.map(renderGameChatEntry).join('');
  log.scrollTop = log.scrollHeight;
  const count = $('admin-game-chat-count');
  if (count) count.textContent = `${items.length}/${data.total_cached ?? items.length}`;
}

async function loadGameChat() {
  if (!$('admin-game-chat-log')) return;
  try {
    const data = await api('/api/admin/game-chat?limit=300');
    renderGameChat(data);
  } catch (err) {
    const log = $('admin-game-chat-log');
    if (log) log.innerHTML = `<div class="empty-detail">聊天读取失败：${escapeHtml(err.message || '')}</div>`;
  }
}

async function sendGameChatMessage(text) {
  const message = String(text || '').trim();
  if (!message) return;
  await api('/api/admin/game-chat/send', {
    method: 'POST',
    body: JSON.stringify({ text: message }),
  });
  gameChatSignature = '';
  await loadGameChat();
}

function showShell(authenticated) {
  $('admin-login').classList.toggle('hidden', authenticated);
  $('admin-shell').classList.toggle('hidden', !authenticated);
  if (authenticated) {
    loadStatus();
    loadRegisteredUsers();
    loadStorageSummary();
    resetAndLoadReplays();
    loadGameChat();
    if (!refreshTimer) refreshTimer = setInterval(loadStatus, 1000);
    if (!registeredRefreshTimer) registeredRefreshTimer = setInterval(loadRegisteredUsers, 10000);
    if (!gameChatTimer) gameChatTimer = setInterval(loadGameChat, 3000);
  } else {
    if (refreshTimer) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
    if (registeredRefreshTimer) {
      clearInterval(registeredRefreshTimer);
      registeredRefreshTimer = null;
    }
    if (gameChatTimer) {
      clearInterval(gameChatTimer);
      gameChatTimer = null;
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
  const profile = metrics.server_profile || {};

  const pcpu = process.cpu_percent == null ? '-' : `${Number(process.cpu_percent).toFixed(1)}%`;
  const scpu = system.cpu_percent == null ? '-' : `${Number(system.cpu_percent).toFixed(1)}%`;
  const loadavg = Array.isArray(metrics.loadavg) ? metrics.loadavg.map(v => Number(v).toFixed(2)).join(' / ') : '-';
  $('metric-cpu').textContent = scpu;
  $('metric-cpu-sub').textContent = `${system.cpu_count || profile.cpu_target || 2} 核；进程 ${pcpu}；负载 ${loadavg}`;
  $('metric-memory').textContent = system.memory_total
    ? `${formatBytes(system.memory_used)} / ${formatBytes(system.memory_total)}`
    : formatBytes(process.memory_rss);
  $('metric-memory-sub').textContent = system.memory_percent == null
    ? `进程 ${formatBytes(process.memory_rss)}`
    : `已用 ${system.memory_percent}%；可用 ${formatBytes(system.memory_available)}；进程 ${formatBytes(process.memory_rss)}`;
  $('metric-disk').textContent = disk.total ? `${formatBytes(disk.used)} / ${formatBytes(disk.total)}` : '-';
  const diskSub = $('metric-disk-sub');
  if (diskSub) diskSub.textContent = `已用 ${disk.percent ?? '-'}%；剩余 ${formatBytes(disk.free)}；${profile.disk_target || '40G'} 云盘`;
  $('metric-uptime').textContent = formatUptime(metrics.uptime_seconds);
  $('metric-clock').textContent = formatAdminTime(metrics.time);
  $('metric-online').textContent = summary.online_players || 0;
  $('metric-online-sub').textContent = `大厅 ${summary.lobby_players || 0} / 观战 ${summary.spectators || 0}`;
  $('metric-rooms').textContent = summary.rooms || 0;
  $('metric-history-sub').textContent = `历史 ${summary.history_count || 0}`;
  renderServerResources(metrics);
  renderResourceHistory(metrics.resource_history || {});

  renderPlayers(data.players || []);
  renderRooms(data.rooms || []);
  renderEvents(data.events || []);
  renderHistory(data.history || []);
}

function resourceCard(title, main, sub) {
  return `
    <article class="server-resource-card">
      <span>${escapeHtml(title)}</span>
      <strong>${escapeHtml(main)}</strong>
      <small>${escapeHtml(sub || '')}</small>
    </article>`;
}

function renderServerResources(metrics) {
  const grid = $('server-resource-grid');
  if (!grid) return;
  const profile = metrics.server_profile || {};
  const system = metrics.system || {};
  const process = metrics.process || {};
  const network = metrics.network || {};
  const storage = metrics.storage_breakdown || {};
  const database = storage.database || {};
  const dirs = Array.isArray(storage.directories) ? storage.directories : [];
  const dirCards = dirs.map((item) => resourceCard(
    item.label || item.path || '目录',
    formatBytes(item.bytes),
    `${item.path || ''}${item.files != null ? ` · ${formatNumber(item.files)} 个文件` : ''}${item.truncated ? ' · 已截断统计' : ''}`,
  ));
  const dbFiles = (database.files || []).map(file => `${file.name} ${formatBytes(file.bytes)}`).join(' / ');
  const cards = [
    resourceCard('服务器规格', `${profile.cpu_target || system.cpu_count || '-'} / ${profile.memory_target || formatBytes(system.memory_total)} / ${profile.disk_target || '-'}`, `${profile.provider || 'Aliyun'} · ${profile.os || 'Ubuntu 22.04'}`),
    resourceCard('数据库文件', formatBytes(database.bytes), `${database.path || ''}${dbFiles ? ` · ${dbFiles}` : ''}`),
    resourceCard('Python 进程', `PID ${process.pid || '-'}`, `RSS ${formatBytes(process.memory_rss)} · VMS ${formatBytes(process.memory_vms)} · 线程 ${process.threads ?? '-'}`),
    resourceCard('网络累计', `${formatBytes(network.bytes_recv)} 入 / ${formatBytes(network.bytes_sent)} 出`, '服务器启动后系统网络计数器累计值'),
    resourceCard('Socket.IO', `${metrics.socket?.latency?.avg_ms ?? '-'} ms`, `RTT p95 ${metrics.socket?.latency?.p95_ms ?? '-'} ms · 操作 p95 ${metrics.socket?.actions?.p95_ms ?? '-'} ms · 广播 p95 ${metrics.socket?.broadcasts?.p95_ms ?? '-'} ms`),
    resourceCard('R2 健康', `${metrics.r2?.mod_count ?? '-'} 个社区模组`, `Index 平均 ${metrics.r2?.index_avg_ms ?? '-'} ms · 错误 ${metrics.r2?.index_errors ?? 0} · 上传失败 ${metrics.r2?.upload_failures ?? 0}`),
    ...dirCards,
  ];
  grid.innerHTML = cards.join('');
  const label = $('server-profile-label');
  if (label) label.textContent = `${profile.provider || 'Aliyun'} · ${profile.os || 'Ubuntu 22.04'}`;
}

function chartPolyline(samples, key, color, width = 320, height = 110) {
  if (!samples.length) return '';
  const maxX = Math.max(1, samples.length - 1);
  const points = samples.map((sample, i) => {
    const value = Math.max(0, Math.min(100, Number(sample[key]) || 0));
    const x = (i / maxX) * width;
    const y = height - (value / 100) * height;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  return `<polyline points="${points}" fill="none" stroke="${color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />`;
}

function renderResourceHistory(history) {
  const grid = $('resource-history-grid');
  if (!grid) return;
  const windows = history.windows || {};
  const config = [
    ['5m', '最近 5 分钟'],
    ['15m', '最近 15 分钟'],
    ['60m', '最近 60 分钟'],
  ];
  grid.innerHTML = config.map(([key, label]) => {
    const samples = Array.isArray(windows[key]) ? windows[key] : [];
    const latest = samples[samples.length - 1] || {};
    return `
      <article class="resource-chart-card">
        <h3>${label}</h3>
        <svg class="resource-chart" viewBox="0 0 320 110" preserveAspectRatio="none" aria-label="${label}">
          <line x1="0" y1="55" x2="320" y2="55" stroke="rgba(98,112,128,0.18)" />
          ${chartPolyline(samples, 'cpu', '#2980b9')}
          ${chartPolyline(samples, 'memory', '#1abc9c')}
          ${chartPolyline(samples, 'disk', '#c0392b')}
        </svg>
        <div class="resource-chart-legend">
          <span><i class="legend-dot" style="background:#2980b9"></i>CPU ${latest.cpu ?? '-'}%</span>
          <span><i class="legend-dot" style="background:#1abc9c"></i>内存 ${latest.memory ?? '-'}%</span>
          <span><i class="legend-dot" style="background:#c0392b"></i>磁盘 ${latest.disk ?? '-'}%</span>
          <span>${samples.length} 点</span>
        </div>
      </article>`;
  }).join('');
}

function renderPlayers(players) {
  $('players-count').textContent = players.length;
  if (!players.length) {
    $('players-table').innerHTML = '<div class="log-item">暂无在线玩家。</div>';
    return;
  }
  $('players-table').innerHTML = `
    <table>
      <thead><tr><th>昵称</th><th>ID</th><th>状态</th><th>入口</th><th>模式</th><th>房间</th><th>SID</th><th>操作</th></tr></thead>
      <tbody>
        ${players.map((p) => `
          <tr>
            <td>${escapeHtml(p.nickname)}</td>
            <td><span class="muted">${escapeHtml(p.player_id || '-')}</span></td>
            <td>${escapeHtml(labelFrom(STATUS_LABELS, p.status))}</td>
            <td>${p.beta_mode ? '<span class="pill warn">内测</span>' : '<span class="muted">正式</span>'}</td>
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
            <span>ID:${escapeHtml(user.player_id || '-')}</span>
            <span>注册顺序：${escapeHtml(user.id)}</span>
            <span>上次下线 ${escapeHtml(formatAdminTime(user.last_login_at))}</span>
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
            <div><dt>ID</dt><dd>${escapeHtml(user.player_id || '-')}</dd></div>
            <div><dt>注册顺序</dt><dd>${escapeHtml(user.id)}</dd></div>
            <div><dt>注册时间</dt><dd>${escapeHtml(formatAdminTime(user.created_at))}</dd></div>
            <div><dt>上次下线</dt><dd>${escapeHtml(formatAdminTime(user.last_login_at))}</dd></div>
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

async function loadStorageSummary() {
  const grid = $('storage-summary-grid');
  if (!grid) return;
  try {
    const data = await api('/api/admin/storage/summary');
    renderStorageSummary(data);
    loadCommunityStorage();
  } catch (error) {
    grid.innerHTML = `<div class="log-item error">存储统计加载失败：${escapeHtml(error.message)}</div>`;
  }
}

function storageCard(title, main, sub) {
  return `
    <article class="metric-card storage-card">
      <span>${escapeHtml(title)}</span>
      <strong>${escapeHtml(main)}</strong>
      <small>${escapeHtml(sub || '')}</small>
    </article>`;
}

function renderStorageSummary(data) {
  const db = data.db || {};
  const replays = data.replays || {};
  const mods = data.mod_blobs || {};
  const cards = data.card_snapshots || {};
  $('storage-summary-grid').innerHTML = [
    storageCard('SQLite 文件', formatBytes(db.total_file_bytes), `DB ${formatBytes(db.db_file_bytes)} / WAL ${formatBytes(db.wal_file_bytes)} / SHM ${formatBytes(db.shm_file_bytes)}`),
    storageCard('回放数据', formatBytes(replays.bytes), `${replays.count || 0} 条；三个月外 ${replays.old_count || 0} 条 / ${formatBytes(replays.old_bytes)}`),
    storageCard('社区模组快照', formatBytes(mods.community_bytes), `${mods.community_count || 0} 个；孤儿 ${mods.orphan_count || 0} 个 / ${formatBytes(mods.orphan_bytes)}`),
    storageCard('官方卡牌快照', formatBytes(cards.bytes), `${cards.count || 0} 个；孤儿 ${cards.orphan_count || 0} 个 / ${formatBytes(cards.orphan_bytes)}`),
  ].join('');
  $('storage-last-result').textContent = `保留 ${replays.retention_days || 90} 天`;
}

async function runStorageAction(action) {
  const resultBox = $('storage-result');
  const write = (data) => {
    resultBox.textContent = JSON.stringify(data, null, 2);
    $('storage-last-result').textContent = '已完成';
  };
  try {
    let data;
    if (action === 'refresh') {
      await loadStorageSummary();
      return;
    }
    if (action === 'clean-old' && !window.confirm('确认删除三个月外回放和不再引用的快照？')) return;
    if (action === 'clean-orphans' && !window.confirm('确认删除不再被回放引用的孤儿快照？')) return;
    if (action === 'vacuum' && !window.confirm('确认执行 VACUUM？执行期间数据库会短暂锁定。')) return;
    if (action === 'dry-clean-old' || action === 'clean-old') {
      data = await api('/api/admin/storage/cleanup-old', {
        method: 'POST',
        body: JSON.stringify({ dry_run: action === 'dry-clean-old' }),
      });
    } else if (action === 'dry-clean-orphans' || action === 'clean-orphans') {
      data = await api('/api/admin/storage/cleanup-orphans', {
        method: 'POST',
        body: JSON.stringify({ dry_run: action === 'dry-clean-orphans' }),
      });
    } else if (action === 'vacuum') {
      data = await api('/api/admin/storage/vacuum', {
        method: 'POST',
        body: JSON.stringify({ confirm: true }),
      });
    }
    write(data || {});
    await loadStorageSummary();
  } catch (error) {
    resultBox.textContent = `失败：${error.message}`;
  }
}

async function loadCommunityStorage() {
  const table = $('community-storage-table');
  if (!table) return;
  try {
    const data = await api('/api/admin/community-mods/storage');
    const objects = data.objects || [];
    $('community-storage-count').textContent = `${objects.length} 个对象`;
    if (!objects.length) {
      table.innerHTML = '<div class="log-item">暂无 R2 社区模组对象。</div>';
      return;
    }
    table.innerHTML = `
      <table>
        <thead><tr><th>Key</th><th>大小</th><th>修改时间</th><th>类型</th><th>操作</th></tr></thead>
        <tbody>
          ${objects.map((obj) => `
            <tr>
              <td><span class="muted">${escapeHtml(obj.key)}</span></td>
              <td>${formatBytes(obj.size)}</td>
              <td>${escapeHtml(formatAdminTime(obj.last_modified))}</td>
              <td>${obj.is_index ? '索引' : (obj.is_trash ? '回收站' : '文件')}</td>
              <td>
                ${obj.is_index ? '<span class="muted">不可删除</span>' : `<button class="row-action danger" data-r2-delete="${escapeHtml(obj.key)}">彻底删除</button>`}
              </td>
            </tr>`).join('')}
        </tbody>
      </table>`;
  } catch (error) {
    table.innerHTML = `<div class="log-item error">社区模组仓库加载失败：${escapeHtml(error.message)}</div>`;
  }
}

async function deleteCommunityStorageObject(key) {
  if (!key) return;
  if (!window.confirm(`确认彻底删除 R2 对象？\n${key}`)) return;
  try {
    await api('/api/admin/community-mods/storage/delete', {
      method: 'POST',
      body: JSON.stringify({ key }),
    });
    await loadCommunityStorage();
  } catch (error) {
    window.alert(`删除失败：${error.message}`);
  }
}

function replayQuery(offset = 0) {
  const params = new URLSearchParams();
  params.set('limit', '50');
  params.set('offset', String(offset));
  const player = $('replay-search-player')?.value || '';
  const mode = $('replay-filter-mode')?.value || '';
  const modSource = $('replay-filter-mod-source')?.value || '';
  if (player) params.set('player', player);
  if (mode) params.set('mode', mode);
  if (modSource) params.set('mod_source', modSource);
  return params.toString();
}

async function resetAndLoadReplays() {
  replayState = { items: [], offset: 0, hasMore: false, loading: false };
  await loadReplays(false);
}

async function loadReplays(append = true) {
  if (replayState.loading) return;
  replayState.loading = true;
  const table = $('replay-table');
  if (table && !append) table.innerHTML = '<div class="log-item">正在读取回放。</div>';
  try {
    const data = await api(`/api/replays?${replayQuery(append ? replayState.offset : 0)}`);
    const items = data.items || [];
    replayState.items = append ? replayState.items.concat(items) : items;
    replayState.offset = data.next_offset || replayState.items.length;
    replayState.hasMore = !!data.has_more;
    renderReplays();
  } catch (error) {
    if (table) table.innerHTML = `<div class="log-item error">回放列表加载失败：${escapeHtml(error.message)}</div>`;
  } finally {
    replayState.loading = false;
  }
}

function formatDurationMs(ms) {
  return formatUptime(Math.round((Number(ms) || 0) / 1000));
}

function renderReplays() {
  $('replay-count-label').textContent = `${replayState.items.length}${replayState.hasMore ? '+' : ''}`;
  $('replay-load-more').classList.toggle('hidden', !replayState.hasMore);
  if (!replayState.items.length) {
    $('replay-table').innerHTML = '<div class="log-item">暂无三个月内回放。</div>';
    return;
  }
  $('replay-table').innerHTML = `
    <table>
      <thead><tr><th>时间</th><th>模式</th><th>玩家</th><th>胜者</th><th>回合</th><th>时长</th><th>模组</th><th>大小</th><th>操作</th></tr></thead>
      <tbody>
        ${replayState.items.map((item) => `
          <tr>
            <td>${escapeHtml(formatAdminTime(item.created_at))}</td>
            <td>${escapeHtml(item.mode || '-')}</td>
            <td>${escapeHtml((item.players || []).join(' / '))}</td>
            <td>${escapeHtml(item.winner_name || '-')}</td>
            <td>${escapeHtml(item.round_num ?? '-')}</td>
            <td>${escapeHtml(formatDurationMs(item.duration_ms))}</td>
            <td>${escapeHtml(item.mod_source === 'community' ? (item.community_mod_name || '社区模组') : '官方')}</td>
            <td>${escapeHtml(formatBytes(item.replay_size))}</td>
            <td><button class="row-action" data-replay-view="${escapeHtml(item.id)}">查看回放</button></td>
          </tr>`).join('')}
      </tbody>
    </table>`;
}

async function openReplayViewer(replayId) {
  pauseReplay();
  const viewer = $('replay-viewer');
  viewer.classList.remove('hidden');
  $('replay-frame').textContent = '正在生成时间线。';
  try {
    const data = await api(`/api/replays/${encodeURIComponent(replayId)}/timeline`);
    replayTimeline = data.timeline || [];
    replayFrameIndex = 0;
    const meta = (data.replay && data.replay.meta) || {};
    $('replay-viewer-title').textContent = `${meta.mode || '-'} · ${(meta.players || []).join(' / ')}`;
    const progress = $('replay-progress');
    progress.max = String(Math.max(0, replayTimeline.length - 1));
    progress.value = '0';
    renderReplayFrame();
  } catch (error) {
    $('replay-frame').textContent = `回放加载失败：${error.message}`;
  }
}

function renderReplayFrame() {
  const frame = replayTimeline[replayFrameIndex] || null;
  $('replay-progress').value = String(replayFrameIndex);
  $('replay-frame').textContent = frame ? JSON.stringify(frame, null, 2) : '暂无时间线数据。';
}

function pauseReplay() {
  if (replayTimer) {
    clearTimeout(replayTimer);
    replayTimer = null;
  }
}

function nextReplayFrame() {
  replayFrameIndex = Math.min(replayTimeline.length - 1, replayFrameIndex + 1);
  renderReplayFrame();
}

function prevReplayFrame() {
  replayFrameIndex = Math.max(0, replayFrameIndex - 1);
  renderReplayFrame();
}

function playReplay() {
  pauseReplay();
  if (!replayTimeline.length || replayFrameIndex >= replayTimeline.length - 1) return;
  const current = replayTimeline[replayFrameIndex] || {};
  const next = replayTimeline[replayFrameIndex + 1] || {};
  const delay = replaySpeed === 'instant' ? 0 : Math.max(80, ((Number(next.t) || 0) - (Number(current.t) || 0)) / Number(replaySpeed || 1));
  replayTimer = setTimeout(() => {
    nextReplayFrame();
    playReplay();
  }, delay);
}

function replayFrameState(frame) {
  return frame && frame.state && typeof frame.state === 'object' ? frame.state : {};
}

function replayPerspective(frame) {
  const state = replayFrameState(frame);
  if (Array.isArray(state.perspectives) && state.perspectives.length) return state.perspectives[0] || {};
  return state || {};
}

function replayNames(frame) {
  const state = replayFrameState(frame);
  const perspective = replayPerspective(frame);
  if (Array.isArray(state.player_names)) return state.player_names;
  if (Array.isArray(perspective.player_names)) return perspective.player_names;
  return [];
}

function replayName(frame, playerId, fallback) {
  const names = replayNames(frame);
  const id = Number(playerId);
  return Number.isInteger(id) && names[id] ? names[id] : fallback;
}

function replayMs(ms) {
  const total = Math.max(0, Math.round((Number(ms) || 0) / 1000));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
}

function replayBar(label, cur, max, color) {
  const safeMax = Math.max(1, Number(max || 1));
  const safeCur = Number(cur || 0);
  const pct = Math.max(0, Math.min(100, (safeCur / safeMax) * 100));
  return `
    <div class="admin-replay-bar">
      <span style="color:${color}">${label}</span>
      <div class="admin-replay-bar-track"><div class="admin-replay-bar-fill" style="width:${pct}%;background:${color}"></div></div>
      <span>${escapeHtml(safeCur)}/${escapeHtml(safeMax)}</span>
    </div>`;
}

function replayCardId(card) {
  if (!card) return '?';
  return card.def_id || card.id || card.card_id || (card.card_instance && card.card_instance.def_id) || '?';
}

function replayChipRow(cards, hiddenCount = 0) {
  const chips = [];
  (Array.isArray(cards) ? cards : []).slice(0, 18).forEach((card) => {
    const id = replayCardId(card);
    chips.push(`<span class="admin-replay-chip" title="${escapeHtml(id)}">${escapeHtml(id)}</span>`);
  });
  const count = Math.max(0, Number(hiddenCount || 0));
  for (let i = 0; i < Math.min(count, 12); i += 1) chips.push('<span class="admin-replay-chip">?</span>');
  if (count > 12) chips.push(`<span class="admin-replay-chip">+${count - 12}</span>`);
  return chips.length ? chips.join('') : '<span class="admin-replay-chip">无</span>';
}

function replayEquipmentRow(equipment) {
  const items = Array.isArray(equipment) ? equipment : [];
  if (!items.length) return '<span class="admin-replay-chip">无</span>';
  return items.slice(0, 18).map((eq) => {
    const card = eq.card_instance || eq.card || eq;
    const id = replayCardId(card);
    return `<span class="admin-replay-chip" title="${escapeHtml(id)}">${escapeHtml(id)}</span>`;
  }).join('');
}

function replayStatusRow(player) {
  const p = player || {};
  const items = [];
  [['P', p.poison], ['F', p.fire], ['T', p.toxic], ['A', p.armor], ['Dg', p.dodge], ['Tri', p.triangle_stacks]].forEach(([key, value]) => {
    if (Number(value || 0) > 0) items.push(`${key}:${value}`);
  });
  if (p.invincible) items.push('Invincible');
  if (p.skip_turn) items.push('Skip');
  return items.length ? items.map(item => `<span class="admin-replay-chip">${escapeHtml(item)}</span>`).join('') : '<span class="admin-replay-chip">无</span>';
}

function replayPlayerPanel(frame, role, player, playerId, fallbackName, revealHand) {
  const p = player || {};
  const current = Number(replayFrameState(frame).current_player ?? frame.current_player) === Number(playerId);
  const hand = revealHand ? (p.hand || p.revealed_hand || []) : (p.revealed_hand || []);
  const hiddenCount = revealHand ? 0 : Math.max(0, Number(p.hand_count || 0) - hand.length);
  const deck = Number(p.deck_count || (Array.isArray(p.deck) ? p.deck.length : 0) || 0);
  const discard = Number(p.discard_count || (Array.isArray(p.discard) ? p.discard.length : 0) || 0);
  return `
    <section class="admin-replay-player${current ? ' current' : ''}">
      <div class="admin-replay-player-head">
        <span>${escapeHtml(replayName(frame, playerId, fallbackName))}</span>
        <span class="admin-replay-role">${escapeHtml(role)}${current ? ' · 当前回合' : ''}</span>
      </div>
      <div class="admin-replay-bars">
        ${replayBar('H', p.health, p.max_health || 100, '#2ECC71')}
        ${replayBar('E', p.elixir, p.max_elixir || 10, '#D9A600')}
        ${replayBar('M', p.magic, p.max_magic || 10, '#3498DB')}
      </div>
      <div class="admin-replay-section-label">状态</div>
      <div class="admin-replay-chip-row">${replayStatusRow(p)}</div>
      <div class="admin-replay-section-label">装备</div>
      <div class="admin-replay-chip-row">${replayEquipmentRow(p.equipment)}</div>
      <div class="admin-replay-section-label">手牌 ${hand.length + hiddenCount} / D${deck} / X${discard}</div>
      <div class="admin-replay-chip-row">${replayChipRow(hand, hiddenCount)}</div>
    </section>`;
}

function replayActionText(frame) {
  if (!frame) return '-';
  const names = replayNames(frame);
  const action = frame.action;
  if (!action) return `摘要 · ${frame.phase || '-'}`;
  const actor = action.actor != null ? (names[Number(action.actor)] || `P${Number(action.actor) + 1}`) : '';
  const payload = action.payload || {};
  const result = payload.result || {};
  const cardId = payload.def_id || payload.card_id || (payload.card && payload.card.def_id) || (result.card && result.card.def_id) || '';
  return [actor, action.type, cardId].filter(Boolean).join(' · ');
}

async function openReplayViewer(replayId) {
  pauseReplay();
  const viewer = $('replay-viewer');
  viewer.classList.remove('hidden');
  replayData = null;
  $('replay-frame').innerHTML = '<div class="admin-replay-empty">正在生成时间线...</div>';
  try {
    const data = await api(`/api/replays/${encodeURIComponent(replayId)}/timeline`);
    replayData = data.replay || null;
    replayTimeline = data.timeline || [];
    replayFrameIndex = 0;
    const meta = (data.replay && data.replay.meta) || {};
    $('replay-viewer-title').textContent = `${meta.mode || '-'} · ${(meta.players || []).join(' / ')}`;
    const progress = $('replay-progress');
    progress.max = String(Math.max(0, replayTimeline.length - 1));
    progress.value = '0';
    renderReplayFrame();
  } catch (error) {
    $('replay-frame').innerHTML = `<div class="admin-replay-empty">回放加载失败：${escapeHtml(error.message)}</div>`;
  }
}

function renderReplayFrame() {
  const frame = replayTimeline[replayFrameIndex] || null;
  const progress = $('replay-progress');
  if (progress) progress.value = String(replayFrameIndex);
  const target = $('replay-frame');
  if (!target) return;
  if (!frame) {
    target.innerHTML = '<div class="admin-replay-empty">暂无时间线数据。</div>';
    return;
  }
  const state = replayFrameState(frame);
  const perspective = replayPerspective(frame);
  const yourId = perspective.your_id ?? 0;
  const enemyIds = Array.isArray(perspective.enemy_ids) ? perspective.enemy_ids : [];
  const top = [];
  const bottom = [];
  if (perspective.opponent) top.push(replayPlayerPanel(frame, '敌方', perspective.opponent, enemyIds[0] ?? (yourId === 0 ? 1 : 0), 'Opponent', false));
  if (perspective.opponent2) top.push(replayPlayerPanel(frame, '敌方2', perspective.opponent2, enemyIds[1] ?? 3, 'Opponent 2', false));
  if (perspective.teammate) bottom.push(replayPlayerPanel(frame, '队友', perspective.teammate, perspective.teammate_id ?? 1, 'Teammate', true));
  if (perspective.you) bottom.push(replayPlayerPanel(frame, '自己', perspective.you, yourId, 'You', true));
  if (!top.length && !bottom.length && Array.isArray(state.player_names)) {
    state.player_names.forEach((name, index) => bottom.push(replayPlayerPanel(frame, `玩家${index + 1}`, {}, index, name, false)));
  }
  const actionLines = replayTimeline.slice(Math.max(0, replayFrameIndex - 13), replayFrameIndex + 1)
    .map(item => `${replayMs(item.t)} ${replayActionText(item)}`);
  const duration = replayData && replayData.duration_ms != null ? replayMs(replayData.duration_ms) : '';
  target.innerHTML = `
    <div class="admin-replay-meta">
      <span>帧 ${replayFrameIndex + 1}/${Math.max(1, replayTimeline.length)}</span>
      <span>时间 ${replayMs(frame.t)}${duration ? ` / ${duration}` : ''}</span>
      <span>第${escapeHtml(frame.round || 0)}回合</span>
    </div>
    <div class="admin-replay-board">
      <div class="admin-replay-main">
        <div class="admin-replay-row">${top.join('') || '<div class="admin-replay-empty">无玩家状态</div>'}</div>
        <div class="admin-replay-row">${bottom.join('')}</div>
      </div>
      <aside class="admin-replay-side-card">
        <div class="admin-replay-section-label">当前操作</div>
        <div class="admin-replay-log-line">${escapeHtml(replayActionText(frame))}</div>
        <div class="admin-replay-section-label">操作时间线</div>
        <div class="admin-replay-log">${actionLines.map(line => `<div class="admin-replay-log-line">${escapeHtml(line)}</div>`).join('')}</div>
      </aside>
    </div>`;
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
      ['gui', 'storage', 'replays', 'game-chat', 'terminal'].forEach((name) => {
        const panel = $(`admin-${name}`);
        if (panel) panel.classList.toggle('hidden', target !== name);
      });
      if (target === 'storage') loadStorageSummary();
      if (target === 'replays') resetAndLoadReplays();
      if (target === 'game-chat') {
        loadGameChat();
        $('admin-game-chat-input')?.focus();
      }
      if (target === 'terminal') $('terminal-input').focus();
    });
  });

  document.querySelectorAll('[data-storage-action]').forEach((btn) => {
    btn.addEventListener('click', () => runStorageAction(btn.dataset.storageAction));
  });
  document.querySelectorAll('[data-community-storage-action]').forEach((btn) => {
    btn.addEventListener('click', loadCommunityStorage);
  });
  $('replay-refresh')?.addEventListener('click', resetAndLoadReplays);
  $('replay-load-more')?.addEventListener('click', () => loadReplays(true));
  $('replay-search-player')?.addEventListener('input', () => {
    clearTimeout(replaySearchTimer);
    replaySearchTimer = setTimeout(resetAndLoadReplays, 200);
  });
  $('replay-filter-mode')?.addEventListener('change', resetAndLoadReplays);
  $('replay-filter-mod-source')?.addEventListener('change', resetAndLoadReplays);
  $('replay-progress')?.addEventListener('input', (event) => {
    pauseReplay();
    replayFrameIndex = Number(event.target.value) || 0;
    renderReplayFrame();
  });
  document.querySelectorAll('[data-replay-control]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const action = btn.dataset.replayControl;
      if (action === 'play') playReplay();
      if (action === 'pause') pauseReplay();
      if (action === 'next') { pauseReplay(); nextReplayFrame(); }
      if (action === 'prev') { pauseReplay(); prevReplayFrame(); }
    });
  });
  document.querySelectorAll('[data-replay-speed]').forEach((btn) => {
    btn.addEventListener('click', () => {
      replaySpeed = btn.dataset.replaySpeed === 'instant' ? 'instant' : Number(btn.dataset.replaySpeed || 1);
    });
  });

  $('broadcast-send').addEventListener('click', async () => {
    const msg = $('broadcast-input').value.trim();
    if (!msg) return;
    await runCommand(`broadcast ${msg}`);
    $('broadcast-input').value = '';
  });

  $('admin-game-chat-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const input = $('admin-game-chat-input');
    const msg = input ? input.value.trim() : '';
    if (!msg) return;
    await sendGameChatMessage(msg);
    if (input) input.value = '';
  });

  document.addEventListener('click', async (event) => {
    const userToggle = event.target.closest && event.target.closest('[data-user-toggle]');
    const kickSid = event.target.dataset && event.target.dataset.kick;
    const skipRoom = event.target.dataset && event.target.dataset.skip;
    const endRoom = event.target.dataset && event.target.dataset.end;
    const suggestion = event.target.dataset && event.target.dataset.suggestion;
    const suggestionIndex = event.target.dataset && event.target.dataset.suggestionIndex;
    const replayView = event.target.dataset && event.target.dataset.replayView;
    const r2Delete = event.target.dataset && event.target.dataset.r2Delete;
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
    if (replayView) {
      await openReplayViewer(replayView);
      return;
    }
    if (r2Delete) {
      await deleteCommunityStorageObject(r2Delete);
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
