const $ = (id) => document.getElementById(id);

let currentTab = 'reports';
let reports = [];
let ipBans = [];
let selectedReportId = null;
let selectedDuration = 0;
let durationTarget = 'moderation';
let reportsRequestInFlight = false;
let ipBansRequestInFlight = false;
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
  $('ip-tools').classList.toggle('hidden', tab !== 'ip');
  setText('summary', tab === 'reports' ? `举报 ${reports.length}` : `IP封禁 ${ipBans.length}`);
  renderList();
}

async function loadReports() {
  if (!handlingPageVisible() || reportsRequestInFlight) return;
  reportsRequestInFlight = true;
  const status = $('status-filter').value || 'pending';
  try {
    const data = await api(`/api/handling/reports?status=${encodeURIComponent(status)}&limit=30`);
    reports = data.items || [];
    setText('summary', `举报 ${reports.length}/${data.total || reports.length}`);
  } finally {
    reportsRequestInFlight = false;
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

async function refreshCurrent() {
  try {
    if (currentTab === 'reports') {
      await loadReports();
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
  const items = currentTab === 'reports' ? reports : ipBans;
  if (!items.length) {
    list.appendChild(el('div', 'list-item muted', currentTab === 'reports' ? '暂无举报' : '暂无 IP 封禁'));
    return;
  }
  items.forEach((item) => {
    const row = el('div', 'list-item');
    if (currentTab === 'reports') {
      if (item.id === selectedReportId) row.classList.add('active');
      const title = el('div', 'list-title');
      title.appendChild(el('strong', '', `#${item.id} ${item.object_type || ''}`));
      title.appendChild(el('span', `badge ${item.status || ''}`, item.status || '-'));
      row.appendChild(title);
      row.appendChild(el('div', 'muted', `${item.category || '-'} · ${item.reporter_username || '-'} → ${item.target_username || '-'}`));
      row.appendChild(el('div', 'mono muted', fmtTime(item.created_at)));
      const risk = el('span', `badge risk-${item.risk_level || 0}`, `risk ${item.risk_level || 0}`);
      row.appendChild(risk);
      row.addEventListener('click', () => selectReport(item.id));
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

async function selectReport(id) {
  selectedReportId = id;
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
  $('empty').classList.add('hidden');
  const detail = $('detail');
  detail.classList.remove('hidden');
  detail.textContent = '';
  detail.appendChild(el('h2', '', `举报 #${report.id}`));
  addKv(detail, '状态', report.status);
  addKv(detail, '类型', `${report.object_type || '-'} / ${report.category || '-'}`);
  addKv(detail, '对象', report.object_id, true);
  addKv(detail, '举报者', `${report.reporter_username || '-'} (#${report.reporter_user_id || '-'})`);
  addKv(detail, '目标', `${report.target_username || '-'} (#${report.target_user_id || '-'})`);
  addKv(detail, '风险', report.risk_level, true);
  addKv(detail, '创建时间', fmtTime(report.created_at), true);
  addKv(detail, '原因', report.reason_text || '-');
  if (report.resolved_at) {
    addKv(detail, '处理时间', fmtTime(report.resolved_at), true);
    addKv(detail, '处理人', report.resolved_by || '-');
    addKv(detail, '处理备注', report.resolution_note || '-');
  }
  const history = report.reporter_history || {};
  addKv(detail, '举报者历史', `属实 ${history.accepted || 0} / 驳回 ${history.rejected || 0} / 恶意 ${history.abusive || 0}`);

  detail.appendChild(el('h3', '', '证据'));
  (report.evidence || []).forEach((ev) => {
    const box = el('div', 'evidence');
    box.appendChild(el('div', 'mono muted', `${ev.evidence_type || '-'} · ${fmtTime(ev.created_at)}`));
    const pre = el('pre', 'mono');
    pre.textContent = JSON.stringify(ev.data || {}, null, 2);
    box.appendChild(pre);
    const maybeIp = findIpInEvidence(ev.data);
    if (maybeIp) {
      const btn = el('button', 'btn small danger', `封禁 IP ${maybeIp}`);
      btn.addEventListener('click', () => {
        $('ip-input').value = maybeIp;
        $('ip-reason').value = `举报 #${report.id}`;
        switchTab('ip');
      });
      box.appendChild(btn);
    }
    detail.appendChild(box);
  });

  detail.appendChild(el('h3', '', '处理记录'));
  (report.actions || []).forEach((action) => {
    const box = el('div', 'evidence');
    box.appendChild(el('div', 'mono', `${fmtTime(action.created_at)} ${action.action_type || ''}`));
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
  const btn = el('button', 'btn danger', '解除 IP 封禁');
  btn.addEventListener('click', () => unbanIp(item.ip));
  detail.appendChild(btn);
}

async function resolveReport() {
  if (!selectedReportId) {
    setText('action-result', '先选择一条举报');
    return;
  }
  const payload = {
    action: $('resolve-action').value,
    moderation_action: $('moderation-action').value,
    duration_seconds: selectedDuration,
    note: $('note').value,
  };
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
    updateDurationLabel();
    closeDurationModal();
  });
}

function openDurationModal(target = 'moderation') {
  durationTarget = target;
  setDuration(selectedDuration, true);
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
}

function bind() {
  $('login-form').addEventListener('submit', login);
  $('logout').addEventListener('click', logout);
  $('refresh').addEventListener('click', refreshCurrent);
  $('status-filter').addEventListener('change', () => {
    setText('summary', '筛选已更改，点击刷新读取');
    reports = [];
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

bind();
checkAuth();
