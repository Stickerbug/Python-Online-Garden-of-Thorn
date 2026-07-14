const $ = (id) => document.getElementById(id);

let currentTab = 'reports';
let reports = [];
let users = [];
let ipBans = [];
let moderationRecords = [];
let selectedReportId = null;
let selectedReport = null;
let selectedUserId = null;
let selectedModerationKey = '';
let selectedDuration = 0;
let durationTarget = 'moderation';
let reportsRequestInFlight = false;
let usersRequestInFlight = false;
let ipBansRequestInFlight = false;
let moderationRequestInFlight = false;
let reportsLoadedOnce = false;
const HANDLING_FETCH_TIMEOUT_MS = 5000;

function text(value) {
  return value == null ? '' : String(value);
}

function setText(id, value) {
  const el = $(id);
  if (el) el.textContent = text(value);
}

async function api(path, options = {}) {
  const controller = new AbortController();
  const timeoutMs = Number(options.timeoutMs || HANDLING_FETCH_TIMEOUT_MS);
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const { timeoutMs: _timeoutMs, headers = {}, ...fetchOptions } = options;
  let response;
  try {
    response = await fetch(path, {
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', ...headers },
      ...fetchOptions,
      signal: controller.signal,
    });
  } catch (error) {
    if (error && error.name === 'AbortError') {
      throw new Error('后台暂时不可用，请稍后手动刷新');
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
  const raw = await response.text();
  let data = {};
  try { data = raw ? JSON.parse(raw) : {}; }
  catch { data = { success: false, error: raw || response.statusText }; }
  if (!response.ok) {
    throw new Error(data.error || response.statusText);
  }
  return data;
}

function handlingPageVisible() {
  const app = $('app');
  return !document.hidden && app && !app.classList.contains('hidden');
}

function fmtTime(value) {
  if (!value) return '-';
  const d = new Date(String(value).replace('Z', '+00:00'));
  if (Number.isNaN(d.getTime())) return value;
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function fmtDuration(seconds) {
  seconds = Math.max(0, Number(seconds) || 0);
  if (!seconds) return '永久';
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  const parts = [];
  if (d) parts.push(`${d}天`);
  if (h) parts.push(`${h}时`);
  if (m) parts.push(`${m}分`);
  if (s || !parts.length) parts.push(`${s}秒`);
  return parts.join('');
}

function el(tag, className = '', content = '') {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content !== '') node.textContent = text(content);
  return node;
}

function showApp() {
  $('login').classList.add('hidden');
  $('app').classList.remove('hidden');
  setText('summary', '未加载，点击刷新读取当前列表');
  renderList();
  if (currentTab === 'reports' && !reportsLoadedOnce) {
    setTimeout(() => {
      refreshCurrent().catch(() => null);
    }, 0);
  }
}

function showLogin() {
  $('login').classList.remove('hidden');
  $('app').classList.add('hidden');
}

async function checkAuth() {
  try {
    const data = await api('/api/handling/me');
    if (data.authenticated) {
      showApp();
    } else {
      showLogin();
    }
  } catch {
    showLogin();
  }
}

async function login(event) {
  event.preventDefault();
  setText('login-error', '');
  try {
    await api('/api/handling/login', {
      method: 'POST',
      body: JSON.stringify({ password: $('password').value }),
    });
    $('password').value = '';
    showApp();
  } catch (e) {
    setText('login-error', e.message || '登录失败');
  }
}

async function logout() {
  await api('/api/handling/logout', { method: 'POST', body: '{}' }).catch(() => null);
  showLogin();
}

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab').forEach((btn) => btn.classList.toggle('active', btn.dataset.tab === tab));
  $('reports-tools').classList.toggle('hidden', tab !== 'reports');
  $('users-tools').classList.toggle('hidden', tab !== 'users');
  $('ip-tools').classList.toggle('hidden', tab !== 'ip');
  $('moderation-tools').classList.toggle('hidden', tab !== 'moderation');
  const hideActionPanel = tab === 'moderation' || tab === 'ip';
  $('handling-actions').classList.toggle('hidden', hideActionPanel);
  $('handling-layout').classList.toggle('no-right', hideActionPanel);
  const summaryText = tab === 'reports'
    ? `举报 ${reports.length}`
    : (tab === 'users'
      ? `玩家 ${users.length}`
      : (tab === 'moderation' ? `处罚 ${moderationRecords.length}` : `IP封禁 ${ipBans.length}`));
  setText('summary', `${summaryText}，点击刷新读取`);
  clearDetail();
  renderList();
  if (tab === 'reports' && !reportsLoadedOnce) {
    refreshCurrent().catch(() => null);
  }
}

async function loadReports() {
  if (!handlingPageVisible() || reportsRequestInFlight) return;
  reportsRequestInFlight = true;
  const status = $('status-filter').value || 'all';
  try {
    const data = await api(`/api/handling/reports?status=${encodeURIComponent(status)}&limit=30`);
    reports = data.items || [];
    reportsLoadedOnce = true;
    setText('summary', `举报 ${reports.length}/${data.total || reports.length}`);
    renderList();
  } finally {
    reportsRequestInFlight = false;
  }
}

async function loadUsers() {
  if (!handlingPageVisible() || usersRequestInFlight) return;
  usersRequestInFlight = true;
  const query = $('user-query').value.trim();
  try {
    const data = await api(`/api/handling/users?query=${encodeURIComponent(query)}&limit=20`);
    users = data.users || [];
    setText('summary', `玩家 ${users.length}/${data.total || users.length}`);
  } finally {
    usersRequestInFlight = false;
  }
}

async function loadIpBans() {
  if (!handlingPageVisible() || ipBansRequestInFlight) return;
  ipBansRequestInFlight = true;
  try {
    const data = await api('/api/handling/ip-bans?active=1&limit=30');
    ipBans = data.items || [];
    setText('summary', `IP封禁 ${ipBans.length}/${data.total || ipBans.length}`);
  } finally {
    ipBansRequestInFlight = false;
  }
}

async function loadModerationRecords() {
  if (!handlingPageVisible() || moderationRequestInFlight) return;
  moderationRequestInFlight = true;
  const kind = $('moderation-filter').value || 'all';
  try {
    const data = await api(`/api/handling/moderation?kind=${encodeURIComponent(kind)}&limit=40`);
    moderationRecords = data.items || [];
    const counts = data.counts || {};
    setText('summary', `处罚 ${moderationRecords.length}/${data.total || moderationRecords.length} · 封禁 ${counts.account_ban || 0} · 警告 ${counts.warning || 0}`);
  } finally {
    moderationRequestInFlight = false;
  }
}

async function refreshCurrent() {
  try {
    if (currentTab === 'reports') {
      await loadReports();
    } else if (currentTab === 'users') {
      await loadUsers();
    } else if (currentTab === 'moderation') {
      await loadModerationRecords();
    } else {
      await loadIpBans();
    }
    renderList();
  } catch (e) {
    setText('summary', `加载失败：${e.message}`);
  }
}

function renderList() {
  const list = $('list');
  list.textContent = '';
  const items = currentTab === 'reports'
    ? reports
    : (currentTab === 'users' ? users : (currentTab === 'moderation' ? moderationRecords : ipBans));
  if (!items.length) {
    const emptyText = currentTab === 'reports'
      ? '暂无举报'
      : (currentTab === 'users'
        ? '暂无玩家，输入条件后点击搜索'
        : (currentTab === 'moderation' ? '暂无有效处罚' : '暂无 IP 封禁'));
    list.appendChild(el('div', 'list-item muted', emptyText));
    return;
  }
  items.forEach((item) => {
    const row = el('div', 'list-item');
    if (currentTab === 'reports') {
      if (item.id === selectedReportId) row.classList.add('active');
      const title = el('div', 'list-title');
      title.appendChild(el('strong', '', `${reportPartyName(item.reporter_username, item.reporter_user_id)} → ${reportPartyName(item.target_username, item.target_user_id)}`));
      title.appendChild(el('span', `badge ${item.status || ''}`, item.status || '-'));
      row.appendChild(title);
      row.appendChild(el('div', 'report-list-reason', reportReasonText(item)));
      const readable = evidenceSummaryText(item);
      if (readable) row.appendChild(el('div', 'report-list-evidence', readable));
      row.appendChild(el('div', 'muted', `举报对象：${reportObjectText(item)} · ${fmtTime(item.created_at)}`));
      const risk = el('span', `badge risk-${item.risk_level || 0}`, `risk ${item.risk_level || 0}`);
      row.appendChild(risk);
      row.addEventListener('click', () => selectReport(item.id));
    } else if (currentTab === 'users') {
      if (item.id === selectedUserId) row.classList.add('active');
      const title = el('div', 'list-title');
      title.appendChild(el('strong', '', item.username || `#${item.id}`));
      title.appendChild(el('span', item.banned ? 'badge danger-badge' : 'badge accepted', item.banned ? '已封禁' : '正常'));
      row.appendChild(title);
      row.appendChild(el('div', 'mono muted', `ID:${item.player_id || '-'} 注册顺序:${item.id || '-'}`));
      row.appendChild(el('div', 'muted', `${item.online ? '在线' : '离线'} · 上次 ${fmtTime(item.last_login_at)}`));
      row.addEventListener('click', () => renderUserDetail(item));
    } else if (currentTab === 'moderation') {
      if (item.key === selectedModerationKey) row.classList.add('active');
      const isWarning = item.kind === 'warning';
      const title = el('div', 'list-title');
      title.appendChild(el('strong', '', item.username || `用户 #${item.user_id || '-'}`));
      title.appendChild(el('span', isWarning ? 'badge pending' : 'badge danger-badge', isWarning ? '警告' : '账号封禁'));
      row.appendChild(title);
      row.appendChild(el('div', 'report-list-reason', item.reason || (isWarning ? '请注意游戏内行为' : '未填写原因')));
      const remaining = item.permanent ? '永久' : `剩余 ${fmtDuration(item.remaining_seconds || 0)}`;
      row.appendChild(el('div', 'muted', `${remaining} · ${fmtTime(item.created_at)}`));
      row.addEventListener('click', () => renderModerationDetail(item));
    } else {
      const title = el('div', 'list-title');
      title.appendChild(el('strong', 'mono', item.ip));
      title.appendChild(el('span', 'badge pending', item.expires_at ? '限时' : '永久'));
      row.appendChild(title);
      row.appendChild(el('div', 'muted', item.reason || '-'));
      row.appendChild(el('div', 'mono muted', fmtTime(item.created_at)));
      row.addEventListener('click', () => renderIpDetail(item));
    }
    list.appendChild(row);
  });
}

function clearDetail() {
  selectedReport = null;
  $('empty').classList.remove('hidden');
  $('detail').classList.add('hidden');
  $('detail').textContent = '';
}

function addKv(parent, key, value, mono = false) {
  const row = el('div', 'kv');
  row.appendChild(el('div', 'muted', key));
  row.appendChild(el('div', mono ? 'mono' : '', value == null || value === '' ? '-' : value));
  parent.appendChild(row);
}

function reportPartyName(name, id) {
  const text = String(name || '').trim();
  if (text) return text;
  return id ? `用户 #${id}` : '未知玩家';
}

function reportObjectText(report) {
  const typeMap = { chat_message: '聊天消息', player: '玩家', match: '对局', replay: '回放', mod: '模组' };
  const type = typeMap[report.object_type] || report.object_type || '对象';
  return report.object_id ? `${type} ${report.object_id}` : type;
}

function evidenceSummaryText(report) {
  const summary = report && report.evidence_summary;
  if (!summary) return '';
  const message = summary.message;
  if (message && message.message) {
    return `消息：${message.sender_name || '未知'}：${message.message}`;
  }
  if (summary.player) {
    return `玩家：${summary.player.username || summary.player.player_id || '-'}`;
  }
  if (summary.match) {
    const players = Array.isArray(summary.match.players) ? summary.match.players.join(' / ') : '';
    return `对局：${summary.match.mode || '-'} ${players}`;
  }
  if (summary.room) {
    return `房间：${summary.room.room_id || summary.room.mode || '-'}`;
  }
  if (summary.request) {
    return `请求：${summary.request.path || summary.request.endpoint || '-'}`;
  }
  return '';
}

function reportReasonText(report) {
  const category = report.category || '-';
  const reason = String(report.reason_text || '').trim();
  return reason ? `${category}：${reason}` : category;
}

function prepareIpBan(ip, reason = '') {
  const value = String(ip || '').trim();
  if (!value) return;
  $('ip-input').value = value;
  $('ip-reason').value = reason;
  switchTab('ip');
  setText('summary', `准备封禁 IP ${value}`);
}

function appendEvidenceSummary(parent, report) {
  const summary = report && report.evidence_summary;
  if (!summary) return false;
  let added = false;
  const wrap = el('div', 'evidence-readable');

  if (summary.message && summary.message.message) {
    const message = summary.message;
    wrap.appendChild(el('h3', '', '被举报消息'));
    wrap.appendChild(el('div', 'context-meta', `${message.sender_name || '未知'} · ${message.channel || '-'} · ${fmtTime(message.created_at)}`));
    wrap.appendChild(el('div', 'evidence-message', message.message));
    added = true;
  }

  if (Array.isArray(summary.context) && summary.context.length) {
    wrap.appendChild(el('h3', '', '聊天上下文'));
    const list = el('div', 'context-list');
    summary.context.forEach((line) => {
      const row = el('div', `context-line ${summary.message && String(line.id) === String(summary.message.id) ? 'focus' : ''}`.trim());
      row.appendChild(el('div', 'context-meta', `${line.sender_name || '未知'} · ${fmtTime(line.created_at)}`));
      row.appendChild(el('div', '', line.message || ''));
      list.appendChild(row);
    });
    wrap.appendChild(list);
    added = true;
  }

  if (summary.player || summary.room || summary.match || summary.request) {
    wrap.appendChild(el('h3', '', '关联信息'));
    const info = el('div', 'compact-kv');
    if (summary.player) {
      info.appendChild(el('div', '', `玩家：${summary.player.username || '-'} ${summary.player.player_id || ''}`));
    }
    if (summary.room) {
      info.appendChild(el('div', '', `房间：${summary.room.room_id || '-'} ${summary.room.mode || ''}`));
    }
    if (summary.match) {
      const players = Array.isArray(summary.match.players) ? summary.match.players.join(' / ') : '';
      info.appendChild(el('div', '', `对局：${summary.match.mode || '-'} ${players}`));
    }
    if (summary.request) {
      info.appendChild(el('div', '', `请求：${summary.request.path || summary.request.endpoint || '-'}`));
    }
    wrap.appendChild(info);
    added = true;
  }

  if (added) parent.appendChild(wrap);
  return added;
}

function updateReportActionHints(report) {
  const targetName = report ? reportPartyName(report.target_username, report.target_user_id) : '被举报人';
  const reporterName = report ? reportPartyName(report.reporter_username, report.reporter_user_id) : '举报人';
  setText('target-action-hint', `作用于：${targetName}`);
  setText('reporter-action-hint', `作用于：${reporterName}`);
}

function appendCollapsedJson(parent, summaryText, data) {
  const details = document.createElement('details');
  details.className = 'json-details';
  const summary = document.createElement('summary');
  summary.textContent = summaryText;
  details.appendChild(summary);
  const pre = el('pre', 'mono');
  pre.textContent = JSON.stringify(data || {}, null, 2);
  details.appendChild(pre);
  parent.appendChild(details);
}

async function selectReport(id) {
  selectedReportId = id;
  selectedReport = null;
  renderList();
  setText('action-result', '');
  try {
    const data = await api(`/api/handling/reports/${encodeURIComponent(id)}`);
    renderReportDetail(data.report);
  } catch (e) {
    clearDetail();
    setText('action-result', e.message);
  }
}

function renderReportDetail(report) {
  selectedReport = report || null;
  updateReportActionHints(report);
  $('empty').classList.add('hidden');
  const detail = $('detail');
  detail.classList.remove('hidden');
  detail.textContent = '';
  detail.appendChild(el('h2', '', `举报 #${report.id}`));
  const summary = el('div', 'report-summary-card');
  const flow = el('div', 'report-flow');
  flow.appendChild(el('strong', '', reportPartyName(report.reporter_username, report.reporter_user_id)));
  flow.appendChild(el('span', 'report-arrow', '→'));
  flow.appendChild(el('strong', '', reportPartyName(report.target_username, report.target_user_id)));
  summary.appendChild(flow);
  summary.appendChild(el('div', 'report-reason', `因为：${reportReasonText(report)}`));
  summary.appendChild(el('div', 'report-object', `举报对象：${reportObjectText(report)}`));
  detail.appendChild(summary);
  addKv(detail, '状态', report.status);
  addKv(detail, '风险', report.risk_level, true);
  addKv(detail, '创建时间', fmtTime(report.created_at), true);
  if (report.resolved_at) {
    addKv(detail, '处理时间', fmtTime(report.resolved_at), true);
    addKv(detail, '处理人', report.resolved_by || '-');
    addKv(detail, '处理备注', report.resolution_note || '-');
  }
  const reportUserActions = el('div', 'inline-actions');
  if (report.reporter_user_id || report.reporter_username) {
    const btn = el('button', 'btn small', '查看举报者');
    btn.addEventListener('click', () => searchUser(report.reporter_user_id || report.reporter_username));
    reportUserActions.appendChild(btn);
  }
  if (report.target_user_id || report.target_username) {
    const btn = el('button', 'btn small danger', '查看目标账号');
    btn.addEventListener('click', () => searchUser(report.target_user_id || report.target_username));
    reportUserActions.appendChild(btn);
  }
  if (reportUserActions.childNodes.length) detail.appendChild(reportUserActions);
  const history = report.reporter_history || {};
  addKv(detail, '举报者历史', `属实 ${history.accepted || 0} / 驳回 ${history.rejected || 0} / 恶意 ${history.abusive || 0}`);

  if (!appendEvidenceSummary(detail, report)) {
    detail.appendChild(el('div', 'muted', '暂无可直接展示的证据摘要。'));
  }

  detail.appendChild(el('h3', '', '原始证据'));
  (report.evidence || []).forEach((ev) => {
    const box = el('div', 'evidence');
    box.appendChild(el('div', 'mono muted', `${ev.evidence_type || '-'} · ${fmtTime(ev.created_at)}`));
    appendCollapsedJson(box, '查看 JSON 证据', ev.data || {});
    const maybeIp = findIpInEvidence(ev.data);
    if (maybeIp) {
      const actions = el('div', 'inline-actions');
      actions.appendChild(el('span', 'mono ip-chip', maybeIp));
      const btn = el('button', 'btn small danger', '封禁此 IP');
      btn.addEventListener('click', () => prepareIpBan(maybeIp, `举报 #${report.id}`));
      actions.appendChild(btn);
      box.appendChild(actions);
    }
    detail.appendChild(box);
  });

  detail.appendChild(el('h3', '', '处理记录'));
  (report.actions || []).forEach((action) => {
    const box = el('div', 'evidence');
    const actionTarget = reportPartyName(action.target_username, action.target_user_id);
    box.appendChild(el('div', 'mono', `${fmtTime(action.created_at)} ${action.action_type || ''} → ${actionTarget}`));
    box.appendChild(el('div', 'muted', `${action.admin_username || '-'} · ${action.reason || '-'}`));
    detail.appendChild(box);
  });
}

function findIpInEvidence(data) {
  const seen = new Set();
  function walk(value) {
    if (value == null) return '';
    if (typeof value === 'string') {
      const m = value.match(/\b(?:\d{1,3}\.){3}\d{1,3}\b|[a-fA-F0-9:]{3,}/);
      return m ? m[0] : '';
    }
    if (typeof value === 'object') {
      if (seen.has(value)) return '';
      seen.add(value);
      if (value.ip) return String(value.ip);
      for (const item of Object.values(value)) {
        const found = walk(item);
        if (found) return found;
      }
    }
    return '';
  }
  return walk(data);
}

function renderIpDetail(item) {
  selectedDuration = item.expires_at ? secondsUntil(item.expires_at) : 0;
  $('empty').classList.add('hidden');
  const detail = $('detail');
  detail.classList.remove('hidden');
  detail.textContent = '';
  detail.appendChild(el('h2', '', 'IP 封禁'));
  addKv(detail, 'IP', item.ip, true);
  addKv(detail, '状态', item.active ? '有效' : '已解除');
  addKv(detail, '原因', item.reason || '-');
  addKv(detail, '封禁人', item.banned_by || '-');
  addKv(detail, '创建时间', fmtTime(item.created_at), true);
  addKv(detail, '到期时间', item.expires_at ? fmtTime(item.expires_at) : '永久', true);
  appendRecordEditor(detail, {
    reason: item.reason,
    remaining_seconds: item.expires_at ? secondsUntil(item.expires_at) : 0,
    permanent: !item.expires_at,
  }, {
    durationMode: 'ip-record',
    saveText: '保存 IP 封禁',
    endText: '解除 IP 封禁',
    onSave: (reason, duration) => updateIpBan(item.ip, reason, duration),
    onEnd: () => unbanIp(item.ip),
  });
}

function secondsUntil(value) {
  if (!value) return 0;
  const expires = new Date(String(value).replace('Z', '+00:00')).getTime();
  if (!Number.isFinite(expires)) return 0;
  return Math.max(1, Math.ceil((expires - Date.now()) / 1000));
}

function appendRecordEditor(parent, item, options = {}) {
  const editor = el('div', 'record-editor');
  editor.appendChild(el('label', '', '内容 / 原因'));
  const reason = document.createElement('textarea');
  reason.id = 'record-edit-reason';
  reason.rows = 4;
  reason.value = item.reason || '';
  reason.placeholder = '填写玩家可见的说明';
  editor.appendChild(reason);
  editor.appendChild(el('label', '', '剩余时长'));
  const durationRow = el('div', 'record-duration-row');
  const durationButton = el('button', 'btn', '修改时长');
  const durationLabel = el('span', 'mono muted', item.permanent ? '永久' : fmtDuration(item.remaining_seconds || 0));
  durationLabel.id = 'record-duration-label';
  durationButton.addEventListener('click', () => {
    openDurationModal(options.durationMode || 'record');
  });
  durationRow.appendChild(durationButton);
  durationRow.appendChild(durationLabel);
  editor.appendChild(durationRow);
  const actions = el('div', 'inline-actions');
  const save = el('button', 'btn primary', options.saveText || '保存修改');
  save.addEventListener('click', () => options.onSave && options.onSave(reason.value.trim(), selectedDuration));
  actions.appendChild(save);
  if (options.onEnd) {
    const end = el('button', 'btn danger', options.endText || '结束处罚');
    end.addEventListener('click', () => options.onEnd());
    actions.appendChild(end);
  }
  editor.appendChild(actions);
  parent.appendChild(editor);
}

function renderModerationDetail(item) {
  selectedModerationKey = item.key || '';
  selectedDuration = item.permanent ? 0 : Math.max(1, Number(item.remaining_seconds) || secondsUntil(item.expires_at));
  renderList();
  setText('action-result', '');
  $('empty').classList.add('hidden');
  const detail = $('detail');
  detail.classList.remove('hidden');
  detail.textContent = '';
  const isWarning = item.kind === 'warning';
  detail.appendChild(el('h2', '', isWarning ? '有效警告' : '账号封禁'));
  addKv(detail, '玩家', item.username || `用户 #${item.user_id || '-'}`);
  addKv(detail, '玩家ID', item.player_id || '-', true);
  addKv(detail, '创建时间', fmtTime(item.created_at), true);
  addKv(detail, '到期时间', item.permanent ? '永久' : fmtTime(item.expires_at), true);
  if (isWarning) {
    addKv(detail, '处理人', item.admin_username || '-');
    if (item.related_report_id) addKv(detail, '关联举报', `#${item.related_report_id}`, true);
  }
  const links = el('div', 'inline-actions');
  if (item.user_id || item.username) {
    const user = el('button', 'btn small', '查看玩家');
    user.addEventListener('click', () => searchUser(item.user_id || item.username));
    links.appendChild(user);
  }
  if (item.related_report_id) {
    const report = el('button', 'btn small', '查看关联举报');
    report.addEventListener('click', () => openReport(item.related_report_id));
    links.appendChild(report);
  }
  if (links.childNodes.length) detail.appendChild(links);
  appendRecordEditor(detail, item, {
    durationMode: isWarning ? 'warning' : 'account-ban-record',
    saveText: '保存修改',
    endText: isWarning ? '结束警告' : '解除封禁',
    onSave: (reason, duration) => isWarning
      ? updateWarning(item.id, reason, duration, true)
      : updateAccountBan(item.user_id, reason, duration),
    onEnd: () => isWarning ? updateWarning(item.id, item.reason || '', 0, false) : endAccountBan(item.user_id),
  });
}

async function openReport(reportId) {
  $('status-filter').value = 'all';
  switchTab('reports');
  await loadReports();
  renderList();
  await selectReport(reportId);
}

async function updateWarning(warningId, reason, duration, active) {
  try {
    await api(`/api/handling/warnings/${encodeURIComponent(warningId)}`, {
      method: active ? 'PATCH' : 'DELETE',
      body: JSON.stringify({ reason, duration_seconds: duration, active }),
    });
    $('action-result').className = 'result ok';
    setText('action-result', active ? '警告已更新' : '警告已结束');
    await loadModerationRecords();
    renderList();
    clearDetail();
  } catch (e) {
    $('action-result').className = 'result';
    setText('action-result', e.message);
  }
}

async function updateAccountBan(userId, reason, duration) {
  try {
    await api(`/api/handling/users/${encodeURIComponent(userId)}/ban`, {
      method: 'PATCH',
      body: JSON.stringify({ reason, duration_seconds: duration }),
    });
    $('action-result').className = 'result ok';
    setText('action-result', '账号封禁已更新');
    await loadModerationRecords();
    renderList();
    const updated = moderationRecords.find((entry) => entry.kind === 'account_ban' && Number(entry.user_id) === Number(userId));
    if (updated) renderModerationDetail(updated);
  } catch (e) {
    $('action-result').className = 'result';
    setText('action-result', e.message);
  }
}

async function endAccountBan(userId) {
  const result = await setUserBan(userId, false);
  if (!result) return;
  await loadModerationRecords();
  renderList();
  clearDetail();
}

async function updateIpBan(ip, reason, duration) {
  try {
    const data = await api(`/api/handling/ip-bans/${encodeURIComponent(ip)}`, {
      method: 'PATCH',
      body: JSON.stringify({ reason, duration_seconds: duration }),
    });
    $('action-result').className = 'result ok';
    setText('action-result', 'IP 封禁已更新');
    await loadIpBans();
    renderList();
    if (data.ip_ban) renderIpDetail(data.ip_ban);
  } catch (e) {
    $('action-result').className = 'result';
    setText('action-result', e.message);
  }
}

function renderUserDetail(user) {
  selectedUserId = user.id;
  renderList();
  setText('action-result', '');
  $('empty').classList.add('hidden');
  const detail = $('detail');
  detail.classList.remove('hidden');
  detail.textContent = '';
  detail.appendChild(el('h2', '', user.username || `玩家 #${user.id}`));
  addKv(detail, '注册顺序', user.id, true);
  addKv(detail, '玩家ID', user.player_id || '-', true);
  addKv(detail, '状态', user.banned ? '已封禁' : '正常');
  addKv(detail, '在线', user.online ? `${user.online.status || '在线'} ${user.online.mode || ''}` : '否');
  addKv(detail, '创建时间', fmtTime(user.created_at), true);
  addKv(detail, '上次游玩', fmtTime(user.last_login_at), true);
  addKv(detail, '有效战绩', `${user.games_played || 0}局 / 胜${user.wins || 0} 负${user.losses || 0} 平${user.draws || 0}`);
  addKv(detail, '胜率', `${user.win_rate || 0}%`, true);
  if (user.banned) {
    addKv(detail, '封禁原因', user.ban_reason || '-');
    addKv(detail, '封禁到期', user.ban_until ? fmtTime(user.ban_until) : '永久', true);
  }
  detail.appendChild(el('h3', '', '最近 IP'));
  const ips = Array.isArray(user.recent_ips) ? user.recent_ips : [];
  if (!ips.length) {
    detail.appendChild(el('div', 'muted', '暂无 IP 记录。'));
  } else {
    ips.forEach((item) => {
      const box = el('div', 'ip-history-card');
      const main = el('div', 'ip-history-main');
      main.appendChild(el('span', 'mono ip-chip', item.ip || '-'));
      const btn = el('button', 'btn small danger', '封禁此 IP');
      btn.addEventListener('click', () => prepareIpBan(item.ip, `玩家 ${user.username || user.id}`));
      main.appendChild(btn);
      box.appendChild(main);
      box.appendChild(el('div', 'muted', `最后出现：${fmtTime(item.last_seen_at)} · 记录 ${item.count || 0} 次`));
      const related = Array.isArray(item.related_users)
        ? item.related_users.filter((u) => String(u.user_id || u.id) !== String(user.id))
        : [];
      if (related.length) {
        const names = related.slice(0, 6).map((u) => `${u.username || '未知'}#${u.user_id || u.id || '-'}`).join('、');
        box.appendChild(el('div', 'muted ip-related', `关联账号：${names}`));
      }
      detail.appendChild(box);
    });
  }
  const actions = el('div', 'inline-actions');
  if (user.banned) {
    const unban = el('button', 'btn primary', '解除账号封禁');
    unban.addEventListener('click', () => setUserBan(user.id, false));
    actions.appendChild(unban);
  } else {
    const ban = el('button', 'btn danger', '封禁账号');
    ban.addEventListener('click', () => setUserBan(user.id, true));
    actions.appendChild(ban);
  }
  detail.appendChild(actions);
}

async function setUserBan(userId, banned) {
  if (!userId) return;
  const reason = $('note').value || (banned ? '举报处理页封禁' : '');
  try {
    const data = await api(`/api/handling/users/${encodeURIComponent(userId)}/ban`, {
      method: 'POST',
      body: JSON.stringify({
        banned,
        reason,
        duration_seconds: banned ? selectedDuration : 0,
      }),
    });
    $('action-result').className = 'result ok';
    setText('action-result', banned ? `已封禁账号，踢出 ${data.kicked || 0} 个在线会话` : '已解除账号封禁');
    const idx = users.findIndex((item) => item.id === userId);
    if (idx >= 0 && data.user) users[idx] = { ...users[idx], ...data.user };
    renderList();
    if (data.user && currentTab === 'users') renderUserDetail(data.user);
    return data;
  } catch (e) {
    $('action-result').className = 'result';
    setText('action-result', e.message);
  }
}

async function resolveReport() {
  if (!selectedReportId) {
    setText('action-result', '先选择一条举报');
    return;
  }
  const payload = {
    action: $('resolve-action').value,
    target_moderation_action: $('target-moderation-action').value,
    reporter_moderation_action: $('reporter-moderation-action').value,
    duration_seconds: selectedDuration,
    note: $('note').value,
  };
  payload.moderation_action = payload.target_moderation_action;
  try {
    const data = await api(`/api/handling/reports/${encodeURIComponent(selectedReportId)}/resolve`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    $('action-result').className = 'result ok';
    setText('action-result', '已提交处理');
    await loadReports();
    renderList();
    renderReportDetail(data.report);
  } catch (e) {
    $('action-result').className = 'result';
    setText('action-result', e.message);
  }
}

async function banIp() {
  const ip = $('ip-input').value.trim();
  if (!ip) return;
  try {
    const data = await api('/api/handling/ip-bans', {
      method: 'POST',
      body: JSON.stringify({
        ip,
        reason: $('ip-reason').value,
        duration_seconds: selectedDuration,
      }),
    });
    $('action-result').className = 'result ok';
    setText('action-result', `已封禁 IP，踢出 ${data.kicked || 0} 个在线会话`);
    await loadIpBans();
    switchTab('ip');
  } catch (e) {
    $('action-result').className = 'result';
    setText('action-result', e.message);
  }
}

async function unbanIp(ip) {
  try {
    await api(`/api/handling/ip-bans/${encodeURIComponent(ip)}`, { method: 'DELETE' });
    $('action-result').className = 'result ok';
    setText('action-result', '已解除 IP 封禁');
    await loadIpBans();
    renderList();
    clearDetail();
  } catch (e) {
    $('action-result').className = 'result';
    setText('action-result', e.message);
  }
}

function fillWheel(id, max, start = 0) {
  const select = $(id);
  select.textContent = '';
  for (let i = start; i <= max; i += 1) {
    const option = document.createElement('option');
    option.value = String(i);
    option.textContent = String(i).padStart(2, '0');
    select.appendChild(option);
  }
}

function setupDurationPicker() {
  fillWheel('wheel-days', 1000, 0);
  fillWheel('wheel-hours', 23, 0);
  fillWheel('wheel-minutes', 59, 0);
  fillWheel('wheel-seconds', 59, 0);
  ['wheel-days', 'wheel-hours', 'wheel-minutes', 'wheel-seconds'].forEach((id) => {
    $(id).addEventListener('change', syncSecondsFromWheels);
  });
  document.querySelectorAll('[data-wheel]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const select = $(`wheel-${btn.dataset.wheel}`);
      const max = select.options.length - 1;
      const next = Math.max(0, Math.min(max, select.selectedIndex + Number(btn.dataset.delta || 0)));
      select.selectedIndex = next;
      syncSecondsFromWheels();
    });
  });
  $('duration-seconds').addEventListener('input', () => setDuration(Number($('duration-seconds').value) || 0, true));
  $('duration-permanent').addEventListener('click', () => setDuration(0, true));
  $('duration-close').addEventListener('click', closeDurationModal);
  $('duration-apply').addEventListener('click', () => {
    selectedDuration = Number($('duration-seconds').value) || 0;
    if (durationTarget === 'warning' && selectedDuration <= 0) selectedDuration = 3600;
    updateDurationLabel();
    closeDurationModal();
  });
}

function openDurationModal(target = 'moderation') {
  durationTarget = target;
  setDuration(selectedDuration, true);
  $('duration-permanent').classList.toggle('hidden', target === 'warning');
  $('duration-modal').classList.remove('hidden');
  $('duration-modal').setAttribute('aria-hidden', 'false');
}

function closeDurationModal() {
  $('duration-modal').classList.add('hidden');
  $('duration-modal').setAttribute('aria-hidden', 'true');
}

function syncSecondsFromWheels() {
  const days = Number($('wheel-days').value) || 0;
  const hours = Number($('wheel-hours').value) || 0;
  const minutes = Number($('wheel-minutes').value) || 0;
  const seconds = Number($('wheel-seconds').value) || 0;
  const total = days * 86400 + hours * 3600 + minutes * 60 + seconds;
  $('duration-seconds').value = String(total);
}

function setDuration(total, syncWheels = false) {
  total = Math.max(0, Math.min(86400000, Number(total) || 0));
  $('duration-seconds').value = String(total);
  if (syncWheels) {
    let left = total;
    const days = Math.floor(left / 86400); left %= 86400;
    const hours = Math.floor(left / 3600); left %= 3600;
    const minutes = Math.floor(left / 60);
    const seconds = left % 60;
    $('wheel-days').value = String(days);
    $('wheel-hours').value = String(hours);
    $('wheel-minutes').value = String(minutes);
    $('wheel-seconds').value = String(seconds);
  }
}

function updateDurationLabel() {
  setText('duration-label', fmtDuration(selectedDuration));
  const recordLabel = $('record-duration-label');
  if (recordLabel) recordLabel.textContent = fmtDuration(selectedDuration);
}

function bind() {
  $('login-form').addEventListener('submit', login);
  $('logout').addEventListener('click', logout);
  $('refresh').addEventListener('click', refreshCurrent);
  $('search-users').addEventListener('click', loadUsersThenRender);
  $('user-query').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') loadUsersThenRender();
  });
  $('status-filter').addEventListener('change', () => {
    setText('summary', '筛选已更改，点击刷新读取');
    reports = [];
    renderList();
  });
  $('moderation-filter').addEventListener('change', () => {
    setText('summary', '筛选已更改，点击刷新读取');
    moderationRecords = [];
    renderList();
  });
  document.querySelectorAll('.tab').forEach((btn) => btn.addEventListener('click', () => switchTab(btn.dataset.tab)));
  $('resolve').addEventListener('click', resolveReport);
  $('ban-ip').addEventListener('click', banIp);
  $('mod-duration').addEventListener('click', () => openDurationModal('moderation'));
  $('ip-duration').addEventListener('click', () => openDurationModal('ip'));
  document.querySelectorAll('.quick').forEach((btn) => {
    btn.addEventListener('click', () => {
      selectedDuration = Number(btn.dataset.seconds) || 0;
      updateDurationLabel();
    });
  });
  setupDurationPicker();
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) setText('summary', '页面已恢复，点击刷新读取当前列表');
  });
}

async function loadUsersThenRender() {
  try {
    await loadUsers();
    renderList();
  } catch (e) {
    setText('summary', `玩家搜索失败：${e.message}`);
  }
}

async function searchUser(query) {
  switchTab('users');
  $('user-query').value = text(query);
  await loadUsersThenRender();
}

bind();
checkAuth();
