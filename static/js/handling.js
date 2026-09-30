/* 举报处理页 · 重写版
   结构：工具 → 枚举中文化 → Promise 弹窗 → 页签/加载/分页 → 列表 → 详情 → 动作。
   与旧版的差别：所有页签打开即自动加载；时长选择在入口处可见并确认；
   禁言纳入处罚列表可管理；玩家搜索支持信誉分排序与区间；IP 列表可搜索
   含已解除并分页；原生 prompt/confirm 全部换为页内 dialog。 */

const $ = (id) => document.getElementById(id);
const HANDLING_CSRF_TOKEN = document.querySelector('meta[name="gtn-feedback-handling-csrf"]')?.content || '';
const HANDLING_FETCH_TIMEOUT_MS = 6000;

/* ── 枚举 → 中文（列表 / 详情 / 徽章共用一张表）──────────── */
const ENUM_ZH = {
  reportStatus: {
    pending: '待处理', accepted: '已接受', rejected: '已驳回', abusive: '恶意举报',
  },
  objectTypes: {
    chat_message: '聊天消息', player: '玩家', match: '对局', replay: '回放',
    mod: '模组', public_issue: '公开反馈', public_issue_comment: '公开评论',
  },
  categories: {
    abusive_language: '辱骂', sexual_content: '色情内容', spam: '刷屏广告',
    privacy_leak: '泄露隐私', harassment: '骚扰', other: '其他',
    cheating: '作弊', smurfing: '小号', boosting: '代练', stalling: '故意拖延',
    inappropriate_name: '不当昵称', bug_abuse: '利用漏洞', abnormal_match: '异常对局',
    malicious_mod: '恶意模组', stolen_content: '盗用内容', offensive_content: '冒犯内容',
    misleading: '误导内容', duplicate: '重复提交',
  },
  linkStatus: { confirmed: '已确认', likely: '较可能', suspected: '疑似', rejected: '已排除' },
  modKinds: { account_ban: '账号封禁', warning: '警告', mute: '禁言' },
  matchModes: { '1v1': '1v1', '2v2': '2v2', urf: '无限火力', random_deck: '随机卡组' },
};
const zhEnum = (map, value, fallback = '-') => (value != null && map[value] != null ? map[value] : (value || fallback));
const reportStatusZh = (v) => zhEnum(ENUM_ZH.reportStatus, v);
const categoryZh = (v) => zhEnum(ENUM_ZH.categories, v);
const riskBadgeText = (level) => `风险 ${level == null ? '-' : level}`;

/* ── 基础工具 ─────────────────────────────────── */
function text(value) {
  return String(value == null ? '' : value);
}

function setText(id, value) {
  const node = $(id);
  if (node) node.textContent = text(value);
}

function flash(message, kind = '') {
  const box = $('action-result');
  if (!box) return;
  box.textContent = '';
  if (!message) return;
  const item = document.createElement('div');
  item.className = kind;
  item.textContent = text(message);
  box.appendChild(item);
}

function el(tag, className = '', content = '') {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content !== '') node.textContent = text(content);
  return node;
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

async function api(path, options = {}) {
  const controller = new AbortController();
  const timeoutMs = Number(options.timeoutMs || HANDLING_FETCH_TIMEOUT_MS);
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const { timeoutMs: _timeoutMs, headers = {}, ...fetchOptions } = options;
  const method = String(fetchOptions.method || 'GET').toUpperCase();
  const csrfHeaders = HANDLING_CSRF_TOKEN && !['GET', 'HEAD', 'OPTIONS'].includes(method)
    ? { 'X-Feedback-Handling-CSRF': HANDLING_CSRF_TOKEN }
    : {};
  let response;
  try {
    response = await fetch(path, {
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', ...csrfHeaders, ...headers },
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

/* ── 状态 ─────────────────────────────────────── */
const state = {
  tab: 'reports',
  reports: [], users: [], matches: [], riskMatches: [], clusters: [], ipBans: [], moderationRecords: [],
  selected: { reportId: null, userId: null, matchId: null, clusterKey: null, moderationKey: '', ip: null },
  loadedOnce: {},
  totals: {},
  offsets: {},
  inFlight: {},
};
const PAGE_SIZE = { users: 20, matches: 30, moderation: 40, ip: 30 };
const PAGINATED = new Set(['users', 'matches', 'moderation', 'ip']);
const TAB_TITLES = { reports: '举报', users: '玩家', matches: '对局', risk: '风险', clusters: '关联串', moderation: '处罚', ip: 'IP封禁' };

function itemsOf(tab) {
  return tab === 'reports' ? state.reports
    : tab === 'users' ? state.users
    : tab === 'matches' ? state.matches
    : tab === 'risk' ? state.riskMatches
    : tab === 'clusters' ? state.clusters
    : tab === 'moderation' ? state.moderationRecords
    : state.ipBans;
}

/* ── Promise 式弹窗（替代 window.prompt/confirm + 时长轮盘）── */
function wireDialogClose(dialog) {
  dialog.querySelectorAll('[data-close-dialog]').forEach((btn) => {
    btn.addEventListener('click', () => dialog.close());
  });
}

function pickDuration(initialSeconds = 0, title = '选择时长') {
  return new Promise((resolve) => {
    const dialog = $('hd-duration-dialog');
    const days = $('hd-duration-days');
    const hours = $('hd-duration-hours');
    const minutes = $('hd-duration-minutes');
    const total = $('hd-duration-total');
    let value = Math.max(0, Number(initialSeconds) || 0);
    const syncInputs = () => {
      days.value = String(Math.floor(value / 86400));
      hours.value = String(Math.floor((value % 86400) / 3600));
      minutes.value = String(Math.floor((value % 3600) / 60));
      total.textContent = String(value);
      dialog.querySelectorAll('#hd-duration-quick .hd-chip').forEach((chip) => {
        chip.classList.toggle('is-active', Number(chip.dataset.seconds) === value);
      });
    };
    const onInput = () => {
      value = (Number(days.value) || 0) * 86400 + (Number(hours.value) || 0) * 3600 + (Number(minutes.value) || 0) * 60;
      total.textContent = String(value);
      dialog.querySelectorAll('#hd-duration-quick .hd-chip').forEach((chip) => {
        chip.classList.toggle('is-active', Number(chip.dataset.seconds) === value);
      });
    };
    setText('hd-duration-title', title);
    syncInputs();
    const chips = [...dialog.querySelectorAll('#hd-duration-quick .hd-chip')];
    const chipHandler = (event) => {
      value = Number(event.currentTarget.dataset.seconds) || 0;
      syncInputs();
    };
    const applyHandler = () => cleanup(value);
    const cancelHandler = () => cleanup(null);
    const inputs = [days, hours, minutes];
    const inputHandler = () => onInput();
    function cleanup(result) {
      chips.forEach((chip) => chip.removeEventListener('click', chipHandler));
      inputs.forEach((input) => input.removeEventListener('input', inputHandler));
      $('hd-duration-apply').removeEventListener('click', applyHandler);
      dialog.removeEventListener('close', cancelHandler);
      dialog.close();
      resolve(result);
    }
    chips.forEach((chip) => chip.addEventListener('click', chipHandler));
    inputs.forEach((input) => input.addEventListener('input', inputHandler));
    $('hd-duration-apply').addEventListener('click', applyHandler);
    dialog.addEventListener('close', cancelHandler);
    dialog.showModal();
  });
}

function confirmAction(title, body, confirmText = '确认执行') {
  return new Promise((resolve) => {
    const dialog = $('hd-confirm-dialog');
    setText('hd-confirm-title', title);
    setText('hd-confirm-body', body);
    $('hd-confirm-apply').textContent = confirmText;
    const applyHandler = () => cleanup(true);
    const cancelHandler = () => cleanup(false);
    function cleanup(result) {
      $('hd-confirm-apply').removeEventListener('click', applyHandler);
      dialog.removeEventListener('close', cancelHandler);
      dialog.close();
      resolve(result);
    }
    $('hd-confirm-apply').addEventListener('click', applyHandler);
    dialog.addEventListener('close', cancelHandler);
    dialog.showModal();
  });
}

function promptValue({ title, label, hint = '', initial = '', validate = null }) {
  return new Promise((resolve) => {
    const dialog = $('hd-prompt-dialog');
    const input = $('hd-prompt-input');
    const error = $('hd-prompt-error');
    setText('hd-prompt-title', title);
    setText('hd-prompt-hint', hint);
    setText('hd-prompt-label', label);
    input.value = initial;
    error.textContent = '';
    const applyHandler = () => {
      const value = input.value;
      if (validate) {
        const problem = validate(value);
        if (problem) { error.textContent = problem; return; }
      }
      cleanup(value);
    };
    const cancelHandler = () => cleanup(null);
    function cleanup(result) {
      $('hd-prompt-apply').removeEventListener('click', applyHandler);
      dialog.removeEventListener('close', cancelHandler);
      dialog.close();
      resolve(result);
    }
    $('hd-prompt-apply').addEventListener('click', applyHandler);
    dialog.addEventListener('close', cancelHandler);
    dialog.showModal();
    input.focus();
  });
}

/* 时长快捷条（详情内联用），返回 { node, get } */
function durationChips(currentSeconds, { onChange = null } = {}) {
  let value = Math.max(0, Number(currentSeconds) || 0);
  const wrap = el('span', 'hd-chip-row');
  const options = [[600, '10分钟'], [3600, '1小时'], [86400, '1天'], [604800, '7天'], [0, '永久']];
  const chips = options.map(([seconds, label]) => {
    const chip = el('button', 'hd-chip' + (seconds === 0 ? ' hd-chip-danger' : '') + (seconds === value ? ' is-active' : ''), label);
    chip.type = 'button';
    chip.dataset.seconds = String(seconds);
    chip.addEventListener('click', () => {
      value = seconds;
      chips.forEach((c) => c.classList.remove('is-active'));
      chip.classList.add('is-active');
      if (onChange) onChange(value);
    });
    wrap.appendChild(chip);
    return chip;
  });
  const custom = el('button', 'hd-chip', '自定义…');
  custom.type = 'button';
  custom.addEventListener('click', async () => {
    const picked = await pickDuration(value);
    if (picked == null) return;
    value = picked;
    chips.forEach((c) => c.classList.remove('is-active'));
    if (options.some(([seconds]) => seconds === value)) {
      chips.find((c) => Number(c.dataset.seconds) === value)?.classList.add('is-active');
    } else {
      custom.classList.add('is-active');
    }
    if (onChange) onChange(value);
  });
  wrap.appendChild(custom);
  return { node: wrap, get: () => value };
}

/* ── 页签 ─────────────────────────────────────── */
function switchTab(tab) {
  state.tab = tab;
  document.querySelectorAll('.hd-tab').forEach((btn) => btn.classList.toggle('is-active', btn.dataset.tab === tab));
  document.querySelectorAll('.hd-toolbar-group').forEach((group) => {
    group.classList.toggle('hidden', group.dataset.tools !== tab);
  });
  clearDetail();
  renderList();
  renderPagination();
  if (!state.loadedOnce[tab]) {
    refreshCurrent().catch(() => null);
  }
}

async function refreshCurrent() {
  const tab = state.tab;
  try {
    if (tab === 'reports') await loadReports();
    else if (tab === 'users') await loadUsers();
    else if (tab === 'matches') await loadMatches();
    else if (tab === 'risk') await loadRiskMatches();
    else if (tab === 'clusters') await loadClusters();
    else if (tab === 'moderation') await loadModerationRecords();
    else await loadIpBans();
  } catch (e) {
    flash(`加载失败：${e.message}`, 'err');
  }
}

/* ── 加载 ─────────────────────────────────────── */
async function loadReports() {
  if (state.inFlight.reports) return;
  state.inFlight.reports = true;
  try {
    const status = $('status-filter').value || 'all';
    const data = await api(`/api/feedback/handling/reports?status=${encodeURIComponent(status)}&limit=30`);
    state.reports = data.items || [];
    state.totals.reports = data.total || state.reports.length;
    state.loadedOnce.reports = true;
    setText('summary', `举报 ${state.reports.length}/${state.totals.reports}`);
    renderList();
  } finally {
    state.inFlight.reports = false;
  }
}

async function loadUsers() {
  if (state.inFlight.users) return;
  state.inFlight.users = true;
  try {
    const query = $('user-query').value.trim();
    const sortSel = $('user-sort').value || 'last_login_at';
    const [sort, order] = sortSel === 'reputation' ? ['reputation', 'asc']
      : sortSel === 'reputation_desc' ? ['reputation', 'desc']
      : [sortSel, 'desc'];
    const repMin = $('user-rep-min').value.trim();
    const repMax = $('user-rep-max').value.trim();
    const offset = state.offsets.users || 0;
    const params = new URLSearchParams({
      query, sort, order, limit: String(PAGE_SIZE.users), offset: String(offset),
    });
    if (repMin !== '') params.set('reputation_min', repMin);
    if (repMax !== '') params.set('reputation_max', repMax);
    const data = await api(`/api/feedback/handling/users?${params}`);
    state.users = data.users || [];
    state.totals.users = data.total || state.users.length;
    state.loadedOnce.users = true;
    setText('summary', `玩家 ${state.users.length}/${state.totals.users}（信誉区间${repMin || repMax ? ` ${repMin || 0}~${repMax || 100}` : ' 全部'}）`);
    renderList();
    renderPagination();
  } finally {
    state.inFlight.users = false;
  }
}

async function loadMatches() {
  if (state.inFlight.matches) return;
  state.inFlight.matches = true;
  try {
    const query = $('match-query').value.trim();
    const mode = $('match-mode').value || 'all';
    const offset = state.offsets.matches || 0;
    const data = await api(`/api/feedback/handling/matches?query=${encodeURIComponent(query)}&mode=${encodeURIComponent(mode)}&limit=${PAGE_SIZE.matches}&offset=${offset}`);
    state.matches = data.items || [];
    state.totals.matches = data.total || state.matches.length;
    state.loadedOnce.matches = true;
    setText('summary', `对局 ${state.matches.length}/${state.totals.matches}`);
    renderList();
    renderPagination();
  } finally {
    state.inFlight.matches = false;
  }
}

async function loadRiskMatches() {
  if (state.inFlight.risk) return;
  state.inFlight.risk = true;
  try {
    const data = await api('/api/feedback/handling/matches?risk=risk&limit=30');
    state.riskMatches = data.items || [];
    state.totals.risk = data.total || state.riskMatches.length;
    state.loadedOnce.risk = true;
    setText('summary', `风险对局 ${state.riskMatches.length}/${state.totals.risk}`);
    renderList();
  } finally {
    state.inFlight.risk = false;
  }
}

async function loadClusters() {
  if (state.inFlight.clusters) return;
  state.inFlight.clusters = true;
  try {
    const data = await api('/api/account-integrity/staff', { timeoutMs: 10000 });
    state.clusters = data.clusters || [];
    state.loadedOnce.clusters = true;
    setText('summary', `关联串 ${state.clusters.length}`);
    renderList();
  } finally {
    state.inFlight.clusters = false;
  }
}

async function loadIpBans() {
  if (state.inFlight.ip) return;
  state.inFlight.ip = true;
  try {
    const includeInactive = $('ip-include-inactive').checked;
    const query = $('ip-query').value.trim();
    const offset = state.offsets.ip || 0;
    const params = new URLSearchParams({
      active: includeInactive ? 'all' : '1',
      limit: String(PAGE_SIZE.ip),
      offset: String(offset),
    });
    if (query) params.set('query', query);
    const data = await api(`/api/feedback/handling/ip-bans?${params}`);
    state.ipBans = data.items || [];
    state.totals.ip = data.total || state.ipBans.length;
    state.loadedOnce.ip = true;
    setText('summary', `IP封禁 ${state.ipBans.length}/${state.totals.ip}${includeInactive ? '（含已解除）' : ''}`);
    renderList();
    renderPagination();
  } finally {
    state.inFlight.ip = false;
  }
}

async function loadModerationRecords() {
  if (state.inFlight.moderation) return;
  state.inFlight.moderation = true;
  try {
    const kind = $('moderation-filter').value || 'all';
    const offset = state.offsets.moderation || 0;
    const data = await api(`/api/feedback/handling/moderation?kind=${encodeURIComponent(kind)}&limit=${PAGE_SIZE.moderation}&offset=${offset}`);
    state.moderationRecords = data.items || [];
    state.totals.moderation = data.total || state.moderationRecords.length;
    state.loadedOnce.moderation = true;
    const counts = data.counts || {};
    setText('summary', `处罚 ${state.moderationRecords.length}/${state.totals.moderation} · 封禁 ${counts.account_ban || 0} · 警告 ${counts.warning || 0} · 禁言 ${counts.mute || 0}`);
    renderList();
    renderPagination();
  } finally {
    state.inFlight.moderation = false;
  }
}

function renderPagination() {
  const bar = document.querySelector('.hd-pagination');
  if (!bar) return;
  const tab = state.tab;
  const paginated = PAGINATED.has(tab);
  bar.classList.toggle('hidden', !paginated);
  if (!paginated) return;
  const size = PAGE_SIZE[tab];
  const total = state.totals[tab] || 0;
  const offset = state.offsets[tab] || 0;
  const page = Math.floor(offset / size) + 1;
  const pages = Math.max(1, Math.ceil(total / size));
  setText('page-info', `第 ${page} / ${pages} 页 · 共 ${total} 条`);
  $('page-prev').disabled = offset <= 0;
  $('page-next').disabled = offset + size >= total;
}

function changePage(delta) {
  const tab = state.tab;
  if (!PAGINATED.has(tab)) return;
  const size = PAGE_SIZE[tab];
  const total = state.totals[tab] || 0;
  const next = Math.max(0, Math.min(Math.max(0, total - size), (state.offsets[tab] || 0) + delta * size));
  state.offsets[tab] = next;
  if (tab === 'users') loadUsers().catch((e) => flash(e.message, 'err'));
  else if (tab === 'matches') loadMatches().catch((e) => flash(e.message, 'err'));
  else if (tab === 'moderation') loadModerationRecords().catch((e) => flash(e.message, 'err'));
  else loadIpBans().catch((e) => flash(e.message, 'err'));
}

/* ── 列表渲染 ─────────────────────────────────── */
function badge(kind, label) {
  return el('span', `hd-badge hd-badge-${kind}`, label);
}

function riskBadge(level) {
  const node = el('span', `hd-badge hd-badge-risk risk-${Number(level) || 0}`, riskBadgeText(level));
  return node;
}

function renderList() {
  const list = $('list');
  if (!list) return;
  list.textContent = '';
  const tab = state.tab;
  const items = itemsOf(tab);
  if (!items.length) {
    const hints = {
      reports: '暂无举报',
      users: '暂无玩家，输入条件后点击搜索',
      matches: '暂无对局，输入条件后点击搜索',
      risk: '暂无风险标记，点击「读取风险对局」',
      clusters: '暂无关联串，点击「读取关联串」',
      moderation: '暂无有效处罚',
      ip: '暂无 IP 封禁，输入 IP 后点「封禁 IP…」',
    };
    list.appendChild(el('div', 'hd-list-empty', hints[tab] || '暂无数据'));
    return;
  }
  items.forEach((item) => list.appendChild(renderItem(tab, item)));
}

function renderItem(tab, item) {
  const row = el('div', 'hd-item');
  const title = el('div', 'hd-item-title');
  if (tab === 'reports') {
    if (item.id === state.selected.reportId) row.classList.add('is-active');
    title.appendChild(el('strong', '', `${partyName(item.reporter_username, item.reporter_user_id)} → ${partyName(item.target_username, item.target_user_id)}`));
    title.appendChild(badge(item.status || 'pending', reportStatusZh(item.status)));
    row.appendChild(title);
    row.appendChild(el('div', 'hd-item-sub', reportReasonText(item)));
    const evidence = evidenceSummaryText(item);
    if (evidence) row.appendChild(el('div', 'hd-item-sub', evidence));
    const meta = el('div', 'hd-item-sub mono', `${objectText(item)} · ${fmtTime(item.created_at)}`);
    meta.appendChild(riskBadge(item.risk_level));
    row.appendChild(meta);
    row.addEventListener('click', () => selectReport(item.id));
  } else if (tab === 'users') {
    if (item.id === state.selected.userId) row.classList.add('is-active');
    title.appendChild(el('strong', '', item.username || `#${item.id}`));
    title.appendChild(item.banned ? badge('danger', '已封禁') : badge('accepted', '正常'));
    row.appendChild(title);
    row.appendChild(el('div', 'hd-item-sub mono', `ID:${item.player_id || '-'} · 注册顺序:${item.id}`));
    row.appendChild(el('div', 'hd-item-sub', `信誉 ${item.reputation ?? '-'} · ${item.online ? '在线' : '离线'} · 上次 ${fmtTime(item.last_login_at)}`));
    row.addEventListener('click', () => selectUser(item));
  } else if (tab === 'matches' || tab === 'risk') {
    if (item.id === state.selected.matchId) row.classList.add('is-active');
    title.appendChild(el('strong', '', matchTitle(item)));
    title.appendChild(riskBadge(item.risk_score != null ? item.risk_score : item.risk_level));
    row.appendChild(title);
    row.appendChild(el('div', 'hd-item-sub', `${(item.players || []).join(' / ') || '-'} · ${zhEnum(ENUM_ZH.matchModes, item.mode, item.mode)} · ${fmtTime(item.started_at)}`));
    const flags = matchFlagsText(item);
    if (flags) row.appendChild(el('div', 'hd-item-sub', flags));
    row.addEventListener('click', () => { state.selected.matchId = item.id; renderMatchDetail(item); renderList(); });
  } else if (tab === 'clusters') {
    const key = (item.member_ids || []).join(',');
    if (key === state.selected.clusterKey) row.classList.add('is-active');
    const names = (item.members || []).map((m) => `${m.username || '未知'}#${m.id}`).join(' ↔ ');
    title.appendChild(el('strong', '', names));
    title.appendChild(item.has_confirmed ? badge('accepted', '已确认') : badge('pending', '未确认'));
    row.appendChild(title);
    row.appendChild(el('div', 'hd-item-sub', `共 ${(item.member_ids || []).length} 个账号 · ${(item.edges || []).length} 条关联 · 最高风险 ${item.max_risk_score || 0}`));
    row.addEventListener('click', () => { state.selected.clusterKey = key; renderClusterDetail(item, key); renderList(); });
  } else if (tab === 'moderation') {
    if (item.key === state.selected.moderationKey) row.classList.add('is-active');
    const kindZh = zhEnum(ENUM_ZH.modKinds, item.kind, item.kind);
    title.appendChild(el('strong', '', item.username || `用户 #${item.user_id || '-'}`));
    title.appendChild(badge(item.kind === 'warning' ? 'pending' : 'danger', kindZh));
    row.appendChild(title);
    row.appendChild(el('div', 'hd-item-sub', item.reason || '未填写原因'));
    const remaining = item.permanent ? '永久' : `剩余 ${fmtDuration(item.remaining_seconds || 0)}`;
    row.appendChild(el('div', 'hd-item-sub mono', `${kindZh} · ${remaining} · ${fmtTime(item.created_at)}`));
    row.addEventListener('click', () => { state.selected.moderationKey = item.key; renderModerationDetail(item); renderList(); });
  } else {
    if (item.ip === state.selected.ip) row.classList.add('is-active');
    title.appendChild(el('strong', 'mono', item.ip));
    title.appendChild(item.active === false ? badge('rejected', '已解除') : badge(item.expires_at ? 'accepted' : 'danger', item.expires_at ? '限时' : '永久'));
    row.appendChild(title);
    row.appendChild(el('div', 'hd-item-sub', item.reason || '-'));
    row.appendChild(el('div', 'hd-item-sub mono', item.active === false ? `解除于 ${fmtTime(item.created_at)}` : `${item.banned_by || '-'} · ${fmtTime(item.created_at)}`));
    row.addEventListener('click', () => { state.selected.ip = item.ip; renderIpDetail(item); renderList(); });
  }
  return row;
}

/* ── 详情区通用 ───────────────────────────────── */
function clearDetail() {
  const empty = $('empty');
  const detail = $('detail');
  if (empty) empty.classList.remove('hidden');
  if (detail) { detail.classList.add('hidden'); detail.textContent = ''; }
}

function showDetail() {
  $('empty').classList.add('hidden');
  const detail = $('detail');
  detail.classList.remove('hidden');
  detail.textContent = '';
  return detail;
}

function addKv(parent, key, value, mono = false) {
  let dl = parent.lastElementChild;
  if (!dl || !dl.classList.contains('hd-kv')) {
    dl = document.createElement('dl');
    dl.className = 'hd-kv';
    parent.appendChild(dl);
  }
  const dt = el('dt', '', key);
  const dd = el('dd', mono ? 'mono' : '', value);
  dl.appendChild(dt);
  dl.appendChild(dd);
}

function appendJson(parent, summaryText, data) {
  const box = document.createElement('details');
  box.className = 'hd-json';
  box.appendChild(el('summary', '', summaryText));
  const pre = document.createElement('pre');
  try { pre.textContent = JSON.stringify(data, null, 2); }
  catch { pre.textContent = text(data); }
  box.appendChild(pre);
  parent.appendChild(box);
}

/* ── 举报 ─────────────────────────────────────── */
function partyName(name, id) {
  const trimmed = text(name).trim();
  if (trimmed) return trimmed;
  return id ? `用户 #${id}` : '未知玩家';
}

function objectText(report) {
  const type = zhEnum(ENUM_ZH.objectTypes, report.object_type, report.object_type || '对象');
  return report.object_id ? `${type} ${report.object_id}` : type;
}

function reportReasonText(report) {
  const reason = text(report.reason_text).trim();
  const category = categoryZh(report.category);
  return reason ? `${category}：${reason}` : category;
}

function evidenceSummaryText(report) {
  const summary = report && report.evidence_summary;
  if (!summary) return '';
  if (summary.message && summary.message.message) {
    return `消息：${summary.message.sender_name || '未知'}：${summary.message.message}`;
  }
  if (summary.player) return `玩家：${summary.player.username || summary.player.player_id || '-'}`;
  if (summary.match) {
    const players = Array.isArray(summary.match.players) ? summary.match.players.join(' / ') : '';
    return `对局：${zhEnum(ENUM_ZH.matchModes, summary.match.mode, summary.match.mode)} ${players}`;
  }
  if (summary.room) return `房间：${summary.room.room_id || summary.room.mode || '-'}`;
  if (summary.request) return `请求：${summary.request.path || summary.request.endpoint || '-'}`;
  return '';
}

async function selectReport(id) {
  state.selected.reportId = id;
  renderList();
  flash('');
  try {
    const data = await api(`/api/feedback/handling/reports/${encodeURIComponent(id)}`);
    renderReportDetail(data.report);
  } catch (e) {
    clearDetail();
    flash(e.message, 'err');
  }
}

function renderReportDetail(report) {
  if (!report) return;
  const detail = showDetail();
  detail.appendChild(el('h2', '', `举报 #${report.id}`));
  const summary = el('div', 'hd-card');
  const head = el('div', 'hd-card-head');
  head.appendChild(el('strong', '', `${partyName(report.reporter_username, report.reporter_user_id)} → ${partyName(report.target_username, report.target_user_id)}`));
  head.appendChild(badge(report.status || 'pending', reportStatusZh(report.status)));
  summary.appendChild(head);
  summary.appendChild(el('div', 'hd-item-sub', `因为：${reportReasonText(report)}`));
  summary.appendChild(el('div', 'hd-item-sub', `举报对象：${objectText(report)}`));
  detail.appendChild(summary);
  addKv(detail, '状态', reportStatusZh(report.status) || report.status);
  addKv(detail, '风险', riskBadgeText(report.risk_level), true);
  addKv(detail, '创建时间', fmtTime(report.created_at), true);
  if (report.resolved_at) {
    addKv(detail, '处理时间', fmtTime(report.resolved_at), true);
    addKv(detail, '处理人', report.resolved_by || '-');
    addKv(detail, '处理备注', report.resolution_note || '-');
  }
  const history = report.reporter_history || {};
  addKv(detail, '举报者历史', `属实 ${history.accepted || 0} / 驳回 ${history.rejected || 0} / 恶意 ${history.abusive || 0}`);

  const partyActions = el('div', 'hd-inline-actions');
  if (report.reporter_user_id || report.reporter_username) {
    const btn = el('button', 'hd-button hd-button-small', '查看举报者');
    btn.addEventListener('click', () => searchUser(report.reporter_user_id || report.reporter_username));
    partyActions.appendChild(btn);
  }
  if (report.target_user_id || report.target_username) {
    const btn = el('button', 'hd-button hd-button-small', '查看目标账号');
    btn.addEventListener('click', () => searchUser(report.target_user_id || report.target_username));
    partyActions.appendChild(btn);
  }
  if (partyActions.childNodes.length) detail.appendChild(partyActions);

  detail.appendChild(el('h3', '', '证据'));
  const readable = evidenceSummaryText(report);
  if (readable) detail.appendChild(el('div', 'hd-evidence', readable));
  (report.evidence || []).forEach((ev) => {
    const box = el('div', 'hd-evidence');
    box.appendChild(el('div', 'hd-item-sub mono', `${zhEnum(ENUM_ZH.objectTypes, ev.evidence_type, ev.evidence_type)} · ${fmtTime(ev.created_at)}`));
    appendJson(box, '查看 JSON 证据', ev.data || {});
    const maybeIp = findIpInEvidence(ev.data);
    if (maybeIp) {
      const actions = el('div', 'hd-inline-actions');
      actions.appendChild(el('span', 'hd-ip-chip', maybeIp));
      const btn = el('button', 'hd-button hd-button-small hd-button-danger', '封禁此 IP…');
      btn.addEventListener('click', () => openBanIpDialog(maybeIp, `举报 #${report.id}`));
      actions.appendChild(btn);
      box.appendChild(actions);
    }
    detail.appendChild(box);
  });

  detail.appendChild(el('h3', '', '处理记录'));
  (report.actions || []).forEach((action) => {
    const box = el('div', 'hd-evidence');
    box.appendChild(el('div', 'mono', `${fmtTime(action.created_at)} ${zhEnum(ENUM_ZH.modKinds, action.action_type, action.action_type)} → ${partyName(action.target_username, action.target_user_id)}`));
    box.appendChild(el('div', 'hd-item-sub', `${action.admin_username || '-'} · ${action.reason || '-'}`));
    detail.appendChild(box);
  });

  appendResolveForm(detail, report);
}

function appendResolveForm(parent, report) {
  if (report.status && report.status !== 'pending') return;
  const card = el('div', 'hd-action-card');
  card.appendChild(el('h4', '', '提交处理'));
  const grid = el('div', 'hd-form-grid');
  const mkSelect = (labelText, options, id) => {
    const field = el('label', 'hd-field');
    field.appendChild(el('span', '', labelText));
    const select = document.createElement('select');
    select.id = id;
    options.forEach(([value, label]) => {
      const opt = document.createElement('option');
      opt.value = value;
      opt.textContent = label;
      select.appendChild(opt);
    });
    field.appendChild(select);
    grid.appendChild(field);
    return select;
  };
  mkSelect('举报结论', [['accept', '接受举报'], ['reject', '驳回举报'], ['abusive', '标记恶意举报']], 'resolve-action');
  mkSelect('被举报人处理', [['none', '不处罚'], ['warn', '警告'], ['mute', '禁言'], ['ban', '封禁账号'], ['invalidate_match', '标记对局异常']], 'target-moderation-action');
  mkSelect('举报人处理', [['none', '不处罚'], ['warn', '警告'], ['mute', '禁言'], ['ban', '封禁账号']], 'reporter-moderation-action');
  card.appendChild(grid);

  const durationLabel = el('span', 'hd-duration-current', '当前时长：<b>永久</b>（处理封禁 / 禁言 / 警告用）');
  const chips = durationChips(0, { onChange: (v) => { durationLabel.innerHTML = ''; durationLabel.appendChild(document.createTextNode('当前时长：')); const b = el('b', '', v ? fmtDuration(v) : '永久'); durationLabel.appendChild(b); durationLabel.appendChild(document.createTextNode('（处理封禁 / 禁言 / 警告用）')); } });
  const durationRow = el('div', 'hd-chip-row');
  durationRow.appendChild(chips.node);
  durationRow.appendChild(durationLabel);
  card.appendChild(durationRow);

  const noteField = el('label', 'hd-field');
  noteField.appendChild(el('span', '', '处理备注'));
  const note = document.createElement('textarea');
  note.rows = 3;
  note.id = 'note';
  note.placeholder = '处理说明（玩家可见部分按各处罚渠道展示）';
  noteField.appendChild(note);
  card.appendChild(noteField);

  const submit = el('button', 'hd-button hd-button-primary', '提交处理');
  submit.addEventListener('click', () => resolveReport(chips.get(), note.value));
  card.appendChild(submit);
  parent.appendChild(card);
}

async function resolveReport(durationSeconds, noteText) {
  if (!state.selected.reportId) {
    flash('先选择一条举报', 'err');
    return;
  }
  const targetAction = $('target-moderation-action')?.value || 'none';
  const reporterAction = $('reporter-moderation-action')?.value || 'none';
  const action = $('resolve-action')?.value || 'accept';
  const needsDuration = [targetAction, reporterAction].some((a) => a !== 'none' && a !== 'invalidate_match');
  const duration = needsDuration ? durationSeconds : 0;
  const ok = await confirmAction(
    '提交处理',
    `结论：${{ accept: '接受举报', reject: '驳回举报', abusive: '标记恶意举报' }[action]}；被举报人：${targetAction}；举报人：${reporterAction}${needsDuration ? `；时长：${duration ? fmtDuration(duration) : '永久'}` : ''}`,
  );
  if (!ok) return;
  const payload = {
    action,
    target_moderation_action: targetAction,
    reporter_moderation_action: reporterAction,
    moderation_action: targetAction,
    duration_seconds: duration,
    note: noteText,
  };
  try {
    const data = await api(`/api/feedback/handling/reports/${encodeURIComponent(state.selected.reportId)}/resolve`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    flash('已提交处理', 'ok');
    await loadReports();
    renderList();
    if (data.report) renderReportDetail(data.report);
  } catch (e) {
    flash(e.message, 'err');
  }
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

/* ── 玩家 ─────────────────────────────────────── */
async function selectUser(user) {
  state.selected.userId = user && user.id;
  renderUserDetail(user || {});
  if (!user || !user.id) return;
  try {
    const data = await api(`/api/feedback/handling/users/${encodeURIComponent(user.id)}?match_limit=20`);
    const merged = {
      ...(data.user || user),
      matches: data.matches || [],
      linked_group: data.linked_group || null,
    };
    const idx = state.users.findIndex((item) => Number(item.id) === Number(user.id));
    if (idx >= 0) state.users[idx] = { ...state.users[idx], ...merged };
    renderUserDetail(merged);
    loadReputationLedger(user.id);
  } catch (e) {
    flash(e.message, 'err');
  }
}

function loadReputationLedger(userId) {
  api(`/api/feedback/handling/users/${encodeURIComponent(userId)}/reputation`)
    .then((data) => renderReputationLedger(data.entries || []))
    .catch(() => null);
}

function renderReputationLedger(entries) {
  const holder = $('reputation-ledger');
  if (!holder) return;
  holder.textContent = '';
  if (!entries.length) {
    holder.appendChild(el('div', 'hd-item-sub', '暂无信誉分变动记录。'));
    return;
  }
  entries.forEach((entry) => {
    const row = el('div', 'hd-evidence');
    const delta = Number(entry.delta || 0);
    const head = el('div', 'hd-card-head');
    head.appendChild(el('span', 'mono', `${fmtTime(entry.created_at)} ${delta > 0 ? '+' : ''}${delta}`));
    head.appendChild(el('span', 'hd-item-sub', `${entry.value_before} → ${entry.value_after} · ${entry.reason_code || '-'}${entry.match_id ? ` · 对局 ${entry.match_id}` : ''}`));
    row.appendChild(head);
    holder.appendChild(row);
  });
}

function renderUserDetail(user) {
  const detail = showDetail();
  detail.appendChild(el('h2', '', user.username || `玩家 #${user.id}`));
  addKv(detail, '注册顺序', user.id, true);
  addKv(detail, '玩家ID', user.player_id || '-', true);
  addKv(detail, '信誉分', user.reputation != null ? `${user.reputation} / 100` : '-', true);
  addKv(detail, '状态', user.banned ? '已封禁' : (user.muted ? '禁言中' : '正常'));
  addKv(detail, '在线', user.online ? `${user.online.status || '在线'} ${user.online.mode ? zhEnum(ENUM_ZH.matchModes, user.online.mode, user.online.mode) : ''}` : '否');
  addKv(detail, '创建时间', fmtTime(user.created_at), true);
  addKv(detail, '上次游玩', fmtTime(user.last_login_at), true);
  addKv(detail, '有效战绩', `${user.games_played || 0}局 / 胜${user.wins || 0} 负${user.losses || 0} 平${user.draws || 0}`);
  addKv(detail, '胜率', `${user.win_rate || 0}%`, true);
  if (user.banned) {
    addKv(detail, '封禁原因', user.ban_reason || '-');
    addKv(detail, '封禁到期', user.ban_until ? fmtTime(user.ban_until) : '永久', true);
  }

  detail.appendChild(el('h3', '', '信誉分变动'));
  const ledger = el('div');
  ledger.id = 'reputation-ledger';
  ledger.appendChild(el('div', 'hd-item-sub', '读取中…'));
  detail.appendChild(ledger);

  detail.appendChild(el('h3', '', '最近 IP'));
  const ips = Array.isArray(user.recent_ips) ? user.recent_ips : [];
  if (!ips.length) {
    detail.appendChild(el('div', 'hd-item-sub', '暂无 IP 记录。'));
  } else {
    ips.forEach((item) => {
      const box = el('div', 'hd-card');
      const head = el('div', 'hd-card-head');
      head.appendChild(el('span', 'hd-ip-chip', item.ip || '-'));
      const btn = el('button', 'hd-button hd-button-small hd-button-danger', '封禁此 IP…');
      btn.addEventListener('click', () => openBanIpDialog(item.ip, `玩家 ${user.username || user.id}`));
      head.appendChild(btn);
      box.appendChild(head);
      box.appendChild(el('div', 'hd-item-sub', `最后出现：${fmtTime(item.last_seen_at)} · 记录 ${item.count || 0} 次`));
      const related = Array.isArray(item.related_users)
        ? item.related_users.filter((u) => String(u.user_id || u.id) !== String(user.id))
        : [];
      if (related.length) {
        const names = related.slice(0, 6).map((u) => `${u.username || '未知'}#${u.user_id || u.id || '-'}`).join('、');
        box.appendChild(el('div', 'hd-item-sub', `关联账号：${names}`));
      }
      detail.appendChild(box);
    });
  }

  const recentMatches = Array.isArray(user.matches) ? user.matches : [];
  detail.appendChild(el('h3', '', '最近对局'));
  if (!recentMatches.length) {
    detail.appendChild(el('div', 'hd-item-sub', '暂无最近对局。'));
  } else {
    recentMatches.slice(0, 12).forEach((match) => {
      const row = el('div', 'hd-inline-actions');
      row.appendChild(el('strong', 'mono', `M-${match.id}`));
      row.appendChild(el('span', 'hd-item-sub', `${zhEnum(ENUM_ZH.matchModes, match.mode, match.mode)} · ${fmtTime(match.started_at)} · ${match.duration_seconds || 0}s · ${resultText(match)}`));
      const btn = el('button', 'hd-button hd-button-small', '查此对局');
      btn.addEventListener('click', () => searchMatch(match.id));
      row.appendChild(btn);
      detail.appendChild(row);
    });
  }

  const linkedGroup = user.linked_group || null;
  detail.appendChild(el('h3', '', '账号关联'));
  if (linkedGroup && Array.isArray(linkedGroup.members) && linkedGroup.members.length) {
    const names = linkedGroup.members.map((m) => `${m.username || '未知'}#${m.id}`).join('、');
    detail.appendChild(el('div', 'hd-item-sub', `已关联组 #${linkedGroup.group_id}（${zhEnum(ENUM_ZH.linkStatus, linkedGroup.status, linkedGroup.status)}，风险 ${linkedGroup.risk_score || 0}）：${names}`));
  } else {
    detail.appendChild(el('div', 'hd-item-sub', '该账号当前没有已确认的账号关联。'));
  }
  const linkActions = el('div', 'hd-inline-actions');
  const mergeBtn = el('button', 'hd-button hd-button-small hd-button-primary', '手动合并关联账号');
  mergeBtn.addEventListener('click', async () => {
    const raw = await promptValue({
      title: '手动合并关联账号',
      label: '要合并的账号 ID（逗号分隔，当前玩家自动包含）',
      hint: '合并会写入管理审计，请确认证据充分。',
      initial: '',
      validate: (v) => (v.trim() ? null : '至少输入一个账号 ID'),
    });
    if (raw == null) return;
    const ids = new Set([Number(user.id)]);
    raw.split(/[,，\s]+/).forEach((part) => {
      const id = Number(part);
      if (Number.isInteger(id) && id > 0) ids.add(id);
    });
    const reason = await promptValue({
      title: '合并原因',
      label: '原因（会写入管理审计）',
      initial: '举报处理页手动关联',
      validate: (v) => (v.trim() ? null : '原因不能为空'),
    });
    if (reason == null || !reason.trim()) return;
    const ok = await confirmAction('确认合并账号', `将合并：${[...ids].join('、')}`);
    if (!ok) return;
    accountLinkStaffAction('/api/account-integrity/staff/merge', { user_ids: [...ids], reason: reason.trim() }, user);
  });
  linkActions.appendChild(mergeBtn);
  const unlinkBtn = el('button', 'hd-button hd-button-small hd-button-danger', '解除此账号关联');
  unlinkBtn.addEventListener('click', async () => {
    const startingText = await promptValue({
      title: '解除账号关联',
      label: '解除后起始信誉（0-100）',
      hint: '解除后各账号信誉分会重置为你填写的值。',
      initial: '',
      validate: (v) => {
        const n = Number(v);
        return Number.isInteger(n) && n >= 0 && n <= 100 ? null : '必须是 0 至 100 的整数';
      },
    });
    if (startingText == null) return;
    const reason = await promptValue({
      title: '解除原因',
      label: '原因（会写入管理审计）',
      initial: '举报处理页解除关联',
      validate: (v) => (v.trim() ? null : '原因不能为空'),
    });
    if (reason == null || !reason.trim()) return;
    const ok = await confirmAction('确认解除关联', `将解除 #${user.id} 的账号关联，起始信誉 ${Number(startingText)}`);
    if (!ok) return;
    accountLinkStaffAction('/api/account-integrity/staff/unlink', {
      user_id: Number(user.id),
      starting_reputation: Number(startingText),
      reason: reason.trim(),
    }, user);
  });
  linkActions.appendChild(unlinkBtn);
  detail.appendChild(linkActions);

  const actions = el('div', 'hd-inline-actions');
  if (user.banned) {
    const unban = el('button', 'hd-button hd-button-primary', '解除账号封禁');
    unban.addEventListener('click', async () => {
      const ok = await confirmAction('解除账号封禁', `将解除 ${user.username || '#' + user.id} 的封禁`);
      if (!ok) return;
      setUserBan(user.id, false);
    });
    actions.appendChild(unban);
  } else {
    const ban = el('button', 'hd-button hd-button-danger', '封禁账号…');
    ban.addEventListener('click', async () => {
      const duration = await pickDuration(86400, `封禁 ${user.username || '#' + user.id}`);
      if (duration == null) return;
      const ok = await confirmAction('确认封禁账号', `将封禁 ${user.username || '#' + user.id}，时长：${duration ? fmtDuration(duration) : '永久'}`);
      if (!ok) return;
      setUserBan(user.id, true, duration, `举报处理页封禁 ${user.username || user.id}`);
    });
    actions.appendChild(ban);
  }
  detail.appendChild(actions);
}

async function setUserBan(userId, banned, durationSeconds = 0, reasonText = '') {
  if (!userId) return;
  const reason = reasonText || (banned ? '举报处理页封禁' : '');
  try {
    const data = await api(`/api/feedback/handling/users/${encodeURIComponent(userId)}/ban`, {
      method: 'POST',
      body: JSON.stringify({
        banned,
        reason,
        duration_seconds: banned ? durationSeconds : 0,
      }),
    });
    flash(banned ? `已封禁账号（${durationSeconds ? fmtDuration(durationSeconds) : '永久'}），踢出 ${data.kicked || 0} 个在线会话` : '已解除账号封禁', 'ok');
    const idx = state.users.findIndex((item) => Number(item.id) === Number(userId));
    if (idx >= 0 && data.user) state.users[idx] = { ...state.users[idx], ...data.user };
    renderList();
    if (data.user && state.tab === 'users' && idx >= 0) {
      renderUserDetail({ ...state.users[idx], matches: state.users[idx].matches || [], linked_group: state.users[idx].linked_group || null });
    }
    return data;
  } catch (e) {
    flash(e.message, 'err');
  }
}

async function accountLinkStaffAction(path, body, user) {
  try {
    await api(path, { method: 'POST', body: JSON.stringify(body), timeoutMs: 10000 });
    flash('账号关联操作已完成。', 'ok');
    if (user && user.id) await selectUser({ id: user.id });
    else if (state.tab === 'clusters') {
      await loadClusters();
      renderList();
    }
  } catch (e) {
    flash(e.message, 'err');
  }
}

/* ── 对局 / 风险 ─────────────────────────────── */
function matchTitle(match) {
  return `M-${match.id}`;
}

function matchFlagsText(match) {
  const flags = Array.isArray(match.risk_flags) ? match.risk_flags : [];
  return flags.map((flag) => categoryZh(flag.code) !== '-' ? `${categoryZh(flag.code)}${flag.detail ? `：${flag.detail}` : ''}` : (flag.label || flag.code || '')).join('；');
}

function resultText(match) {
  const map = { win: '胜', lose: '负', draw: '平' };
  return map[match.result] || match.result || '-';
}

function renderRiskFlags(parent, match) {
  const flags = Array.isArray(match.risk_flags) ? match.risk_flags : [];
  if (!flags.length) {
    parent.appendChild(el('div', 'hd-item-sub', '暂无自动风险标记。'));
    return;
  }
  const wrap = el('div', 'hd-card');
  flags.forEach((flag) => {
    const chip = el('div', 'hd-item-sub');
    chip.appendChild(el('strong', '', `${categoryZh(flag.code) !== '-' ? categoryZh(flag.code) : (flag.label || flag.code || '风险')}`));
    if (flag.detail) chip.appendChild(document.createTextNode(`：${flag.detail}`));
    wrap.appendChild(chip);
  });
  parent.appendChild(wrap);
}

function renderMatchIpEvidence(parent, match) {
  const players = Array.isArray(match.players) ? match.players : [];
  const playerIds = Array.isArray(match.player_ids) ? match.player_ids : [];
  const ipByUser = match.ip_by_user || {};
  if (!playerIds.length) {
    parent.appendChild(el('div', 'hd-item-sub', '此对局没有账号 ID 记录，无法关联 IP。'));
    return;
  }
  playerIds.forEach((uid, index) => {
    const box = el('div', 'hd-card');
    const name = players[index] || `用户 #${uid}`;
    box.appendChild(el('div', 'hd-card-head', '')).appendChild(el('strong', '', `${name} / #${uid}`));
    const ips = Array.isArray(ipByUser[uid]) ? ipByUser[uid] : [];
    if (!ips.length) {
      box.appendChild(el('div', 'hd-item-sub', '暂无 IP 历史。'));
    } else {
      ips.forEach((item) => {
        const row = el('div', 'hd-inline-actions');
        row.appendChild(el('span', 'hd-ip-chip', item.ip || '-'));
        row.appendChild(el('span', 'hd-item-sub', `${fmtTime(item.last_seen_at)} · ${item.count || 0}次`));
        const ban = el('button', 'hd-button hd-button-small hd-button-danger', '封禁…');
        ban.addEventListener('click', () => openBanIpDialog(item.ip, `对局 ${matchTitle(match)}`));
        row.appendChild(ban);
        box.appendChild(row);
      });
    }
    parent.appendChild(box);
  });
}

function renderMatchDetail(match) {
  const detail = showDetail();
  detail.appendChild(el('h2', '', `对局 ${matchTitle(match)}`));
  addKv(detail, '模式', zhEnum(ENUM_ZH.matchModes, match.mode, match.mode));
  addKv(detail, '玩家', (match.players || []).join(' / ') || '-');
  addKv(detail, '开始时间', fmtTime(match.started_at), true);
  addKv(detail, '时长', `${match.duration_seconds || 0}s`, true);
  addKv(detail, '风险', riskBadgeText(match.risk_score != null ? match.risk_score : match.risk_level), true);
  detail.appendChild(el('h3', '', '风险标记'));
  renderRiskFlags(detail, match);
  detail.appendChild(el('h3', '', '参赛 IP 线索'));
  renderMatchIpEvidence(detail, match);
  if (match.gr_result) {
    detail.appendChild(el('h3', '', 'GR 结算'));
    appendJson(detail, '查看 GR 结算 JSON', match.gr_result);
  }
  const actions = el('div', 'hd-inline-actions');
  const playerBtn = el('button', 'hd-button hd-button-small', '搜索相关玩家');
  playerBtn.addEventListener('click', () => {
    const name = (match.players || [])[0];
    if (name) searchUser(name);
  });
  actions.appendChild(playerBtn);
  detail.appendChild(actions);
}

/* ── 关联串 ───────────────────────────────────── */
function renderClusterDetail(cluster, key = null) {
  const detail = showDetail();
  detail.appendChild(el('h2', '', `关联串（${(cluster.member_ids || []).length} 个账号）`));
  addKv(detail, '确认状态', cluster.has_confirmed ? '含已确认关联' : '全部未确认');
  addKv(detail, '最高风险', String(cluster.max_risk_score || 0), true);
  detail.appendChild(el('h3', '', '成员'));
  (cluster.members || []).forEach((member) => {
    const row = el('div', 'hd-inline-actions');
    row.appendChild(el('strong', '', `${member.username || '未知'}#${member.id}`));
    if (member.risk_score != null) row.appendChild(riskBadge(member.risk_score));
    const btn = el('button', 'hd-button hd-button-small', '查看');
    btn.addEventListener('click', () => searchUser(member.id));
    row.appendChild(btn);
    detail.appendChild(row);
  });
  detail.appendChild(el('h3', '', '关联边'));
  (cluster.edges || []).forEach((edge) => {
    const box = el('div', 'hd-evidence');
    box.appendChild(el('div', 'mono', `${edge.user_id_a} ↔ ${edge.user_id_b}`));
    box.appendChild(el('div', 'hd-item-sub', `${zhEnum(ENUM_ZH.linkStatus, edge.status, edge.status)} · 风险 ${edge.risk_score || 0}${edge.reason ? ` · ${edge.reason}` : ''}`));
    detail.appendChild(box);
  });
}

/* ── 处罚（账号封禁 / 警告 / 禁言）────────────── */
function renderModerationDetail(item) {
  const detail = showDetail();
  const kindZh = zhEnum(ENUM_ZH.modKinds, item.kind, item.kind);
  detail.appendChild(el('h2', '', `${kindZh} · ${item.username || `用户 #${item.user_id || '-'}`}`));
  addKv(detail, '类型', kindZh);
  addKv(detail, '用户', `${item.username || '-'} #${item.user_id != null ? item.user_id : '-'}${item.player_id ? ` / ${item.player_id}` : ''}`, true);
  addKv(detail, '原因', item.reason || '-');
  if (item.muted_by) addKv(detail, '操作人', item.muted_by);
  if (item.admin_username) addKv(detail, '操作人', item.admin_username);
  addKv(detail, '创建时间', fmtTime(item.created_at), true);
  addKv(detail, '到期时间', item.expires_at ? fmtTime(item.expires_at) : '永久', true);
  addKv(detail, '剩余时长', item.permanent ? '永久' : fmtDuration(item.remaining_seconds || 0), true);

  const card = el('div', 'hd-action-card');
  card.appendChild(el('h4', '', `调整${kindZh}`));
  const reasonField = el('label', 'hd-field');
  reasonField.appendChild(el('span', '', '原因 / 说明'));
  const reasonInput = document.createElement('textarea');
  reasonInput.rows = 2;
  reasonInput.value = item.reason || '';
  reasonField.appendChild(reasonInput);
  card.appendChild(reasonField);

  const durationLabel = el('span', 'hd-duration-current');
  const writeDuration = (v) => {
    durationLabel.textContent = '';
    durationLabel.appendChild(document.createTextNode('当前时长：'));
    durationLabel.appendChild(el('b', '', v ? fmtDuration(v) : '永久'));
  };
  const currentSeconds = item.permanent ? 0 : (item.remaining_seconds || 0);
  writeDuration(currentSeconds);
  const chips = durationChips(currentSeconds, { onChange: writeDuration });
  const durationRow = el('div', 'hd-chip-row');
  durationRow.appendChild(chips.node);
  durationRow.appendChild(durationLabel);
  card.appendChild(durationRow);

  const actions = el('div', 'hd-dialog-actions');
  const save = el('button', 'hd-button hd-button-primary', '保存修改');
  save.addEventListener('click', async () => {
    const ok = await confirmAction('保存修改', `将更新${kindZh}：${item.username || '#' + item.user_id}，时长 ${chips.get() ? fmtDuration(chips.get()) : '永久'}`);
    if (!ok) return;
    if (item.kind === 'mute') updateMute(item.user_id, reasonInput.value.trim(), chips.get());
    else if (item.kind === 'warning') updateWarning(item.id, reasonInput.value.trim(), chips.get(), true);
    else updateAccountBan(item.user_id, reasonInput.value.trim(), chips.get());
  });
  actions.appendChild(save);
  const end = el('button', 'hd-button hd-button-danger', `解除${kindZh}`);
  end.addEventListener('click', async () => {
    const ok = await confirmAction(`解除${kindZh}`, `将提前解除 ${item.username || '#' + item.user_id} 的${kindZh}`);
    if (!ok) return;
    if (item.kind === 'mute') endMute(item.user_id);
    else if (item.kind === 'warning') updateWarning(item.id, reasonInput.value.trim(), 0, false);
    else endAccountBan(item.user_id);
  });
  actions.appendChild(end);
  card.appendChild(actions);
  detail.appendChild(card);

  const userBtn = el('button', 'hd-button hd-button-small', '查看玩家');
  userBtn.addEventListener('click', () => searchUser(item.user_id));
  detail.appendChild(el('div', 'hd-inline-actions')).appendChild(userBtn);
}

async function updateWarning(warningId, reason, duration, active) {
  try {
    await api(`/api/feedback/handling/warnings/${encodeURIComponent(warningId)}`, {
      method: active ? 'PATCH' : 'DELETE',
      body: JSON.stringify({ reason, duration_seconds: duration, active }),
    });
    flash(active ? `警告已更新（${duration ? fmtDuration(duration) : '永久'}）` : '警告已结束', 'ok');
    await loadModerationRecords();
    renderList();
    clearDetail();
  } catch (e) {
    flash(e.message, 'err');
  }
}

async function updateAccountBan(userId, reason, duration) {
  try {
    await api(`/api/feedback/handling/users/${encodeURIComponent(userId)}/ban`, {
      method: 'PATCH',
      body: JSON.stringify({ reason, duration_seconds: duration }),
    });
    flash(`账号封禁已更新（${duration ? fmtDuration(duration) : '永久'}）`, 'ok');
    await loadModerationRecords();
    renderList();
    const updated = state.moderationRecords.find((entry) => entry.kind === 'account_ban' && Number(entry.user_id) === Number(userId));
    if (updated) renderModerationDetail(updated);
  } catch (e) {
    flash(e.message, 'err');
  }
}

async function endAccountBan(userId) {
  const result = await setUserBan(userId, false);
  if (!result) return;
  await loadModerationRecords();
  renderList();
  clearDetail();
}

async function updateMute(userId, reason, duration) {
  try {
    await api(`/api/feedback/handling/mutes/${encodeURIComponent(userId)}`, {
      method: 'PATCH',
      body: JSON.stringify({ reason, duration_seconds: Math.max(60, duration || 600) }),
    });
    flash(`禁言已更新（${fmtDuration(Math.max(60, duration || 600))}）`, 'ok');
    await loadModerationRecords();
    renderList();
    clearDetail();
  } catch (e) {
    flash(e.message, 'err');
  }
}

async function endMute(userId) {
  try {
    await api(`/api/feedback/handling/mutes/${encodeURIComponent(userId)}`, { method: 'DELETE' });
    flash('禁言已提前解除', 'ok');
    await loadModerationRecords();
    renderList();
    clearDetail();
  } catch (e) {
    flash(e.message, 'err');
  }
}

/* ── IP 封禁 ─────────────────────────────────── */
async function openBanIpDialog(ip, reason = '') {
  const value = String(ip || '').trim();
  if (!value) return;
  $('ip-input').value = value;
  if (reason) $('ip-reason').value = reason;
  const duration = await pickDuration(0, `封禁 IP ${value}`);
  if (duration == null) return;
  const ok = await confirmAction('确认封禁 IP', `将封禁 ${value}，时长：${duration ? fmtDuration(duration) : '永久'}${$('ip-reason').value ? `；原因：${$('ip-reason').value}` : ''}`);
  if (!ok) return;
  banIp(value, duration, $('ip-reason').value);
}

async function banIp(ip, durationSeconds, reason) {
  const value = String(ip || '').trim() || $('ip-input').value.trim();
  if (!value) {
    flash('IP 不能为空', 'err');
    return;
  }
  const duration = durationSeconds != null ? durationSeconds : 0;
  try {
    const data = await api('/api/feedback/handling/ip-bans', {
      method: 'POST',
      body: JSON.stringify({
        ip: value,
        reason: reason != null ? reason : $('ip-reason').value,
        duration_seconds: duration,
      }),
    });
    flash(`已封禁 IP ${value}（${duration ? fmtDuration(duration) : '永久'}），踢出 ${data.kicked || 0} 个在线会话`, 'ok');
    state.offsets.ip = 0;
    await loadIpBans();
    switchTab('ip');
  } catch (e) {
    flash(e.message, 'err');
  }
}

async function unbanIp(ip) {
  try {
    await api(`/api/feedback/handling/ip-bans/${encodeURIComponent(ip)}`, { method: 'DELETE' });
    flash('已解除 IP 封禁', 'ok');
    await loadIpBans();
    renderList();
    clearDetail();
  } catch (e) {
    flash(e.message, 'err');
  }
}

async function updateIpBan(ip, reason, duration) {
  try {
    const data = await api(`/api/feedback/handling/ip-bans/${encodeURIComponent(ip)}`, {
      method: 'PATCH',
      body: JSON.stringify({ reason, duration_seconds: duration }),
    });
    flash(`IP 封禁已更新（${duration ? fmtDuration(duration) : '永久'}）`, 'ok');
    await loadIpBans();
    renderList();
    if (data.ip_ban) renderIpDetail(data.ip_ban);
  } catch (e) {
    flash(e.message, 'err');
  }
}

function renderIpDetail(item) {
  const detail = showDetail();
  detail.appendChild(el('h2', '', 'IP 封禁'));
  addKv(detail, 'IP', item.ip, true);
  addKv(detail, '状态', item.active ? '有效' : '已解除');
  addKv(detail, '原因', item.reason || '-');
  addKv(detail, '封禁人', item.banned_by || '-');
  addKv(detail, '创建时间', fmtTime(item.created_at), true);
  addKv(detail, '到期时间', item.expires_at ? fmtTime(item.expires_at) : '永久', true);
  if (item.active === false) return;

  const card = el('div', 'hd-action-card');
  card.appendChild(el('h4', '', '调整封禁'));
  const reasonField = el('label', 'hd-field');
  reasonField.appendChild(el('span', '', '原因'));
  const reasonInput = document.createElement('textarea');
  reasonInput.rows = 2;
  reasonInput.value = item.reason || '';
  reasonField.appendChild(reasonInput);
  card.appendChild(reasonField);
  const durationLabel = el('span', 'hd-duration-current');
  const currentSeconds = item.expires_at ? secondsUntil(item.expires_at) : 0;
  const writeDuration = (v) => {
    durationLabel.textContent = '';
    durationLabel.appendChild(document.createTextNode('当前时长：'));
    durationLabel.appendChild(el('b', '', v ? fmtDuration(v) : '永久'));
  };
  writeDuration(currentSeconds);
  const chips = durationChips(currentSeconds, { onChange: writeDuration });
  const durationRow = el('div', 'hd-chip-row');
  durationRow.appendChild(chips.node);
  durationRow.appendChild(durationLabel);
  card.appendChild(durationRow);
  const actions = el('div', 'hd-dialog-actions');
  const save = el('button', 'hd-button hd-button-primary', '保存修改');
  save.addEventListener('click', async () => {
    const ok = await confirmAction('保存修改', `将更新 ${item.ip} 的封禁，时长 ${chips.get() ? fmtDuration(chips.get()) : '永久'}`);
    if (!ok) return;
    updateIpBan(item.ip, reasonInput.value.trim(), chips.get());
  });
  const end = el('button', 'hd-button hd-button-danger', '解除封禁');
  end.addEventListener('click', async () => {
    const ok = await confirmAction('解除 IP 封禁', `将解除 ${item.ip} 的封禁`);
    if (!ok) return;
    unbanIp(item.ip);
  });
  actions.appendChild(save);
  actions.appendChild(end);
  card.appendChild(actions);
  detail.appendChild(card);
}

function secondsUntil(value) {
  if (!value) return 0;
  const expires = new Date(String(value).replace('Z', '+00:00')).getTime();
  if (!Number.isFinite(expires)) return 0;
  return Math.max(1, Math.ceil((expires - Date.now()) / 1000));
}

/* ── 跨页入口（保留旧版全局函数）──────────────── */
async function searchUser(query) {
  switchTab('users');
  $('user-query').value = text(query);
  state.offsets.users = 0;
  state.loadedOnce.users = true;
  try { await loadUsers(); } catch (e) { flash(e.message, 'err'); }
}

async function searchMatch(query) {
  switchTab('matches');
  $('match-query').value = text(query);
  state.offsets.matches = 0;
  state.loadedOnce.matches = true;
  try { await loadMatches(); } catch (e) { flash(e.message, 'err'); }
}

async function openReport(reportId) {
  $('status-filter').value = 'all';
  switchTab('reports');
  try { await loadReports(); } catch (e) { flash(e.message, 'err'); }
  await selectReport(reportId);
}

function prepareIpBan(ip, reason = '') {
  openBanIpDialog(ip, reason);
}

/* ── 绑定与启动 ───────────────────────────────── */
function bind() {
  $('handling-exit').addEventListener('click', exitHandling);
  $('refresh').addEventListener('click', () => refreshCurrent());
  $('search-users').addEventListener('click', () => { state.offsets.users = 0; loadUsers().catch((e) => flash(e.message, 'err')); });
  $('search-matches').addEventListener('click', () => { state.offsets.matches = 0; loadMatches().catch((e) => flash(e.message, 'err')); });
  $('search-risk').addEventListener('click', () => loadRiskMatches().catch((e) => flash(e.message, 'err')));
  $('search-clusters').addEventListener('click', () => loadClusters().catch((e) => flash(e.message, 'err')));
  $('search-ip').addEventListener('click', () => { state.offsets.ip = 0; loadIpBans().catch((e) => flash(e.message, 'err')); });
  $('ban-ip').addEventListener('click', () => {
    const ip = $('ip-input').value.trim();
    if (!ip) { flash('先填写要封禁的 IP', 'err'); return; }
    openBanIpDialog(ip, $('ip-reason').value);
  });
  $('page-prev').addEventListener('click', () => changePage(-1));
  $('page-next').addEventListener('click', () => changePage(1));
  $('user-query').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') { state.offsets.users = 0; loadUsers().catch((e) => flash(e.message, 'err')); }
  });
  $('ip-query').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') { state.offsets.ip = 0; loadIpBans().catch((e) => flash(e.message, 'err')); }
  });
  $('match-query').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') { state.offsets.matches = 0; loadMatches().catch((e) => flash(e.message, 'err')); }
  });
  $('match-mode').addEventListener('change', () => {
    setText('summary', '筛选已更改，点击搜索读取');
    state.matches = [];
    renderList();
  });
  $('status-filter').addEventListener('change', () => {
    setText('summary', '筛选已更改，读取中…');
    loadReports().catch(() => null);
  });
  $('moderation-filter').addEventListener('change', () => {
    setText('summary', '筛选已更改，读取中…');
    state.offsets.moderation = 0;
    loadModerationRecords().catch(() => null);
  });
  document.querySelectorAll('.hd-tab').forEach((btn) => btn.addEventListener('click', () => switchTab(btn.dataset.tab)));
  ['hd-duration-dialog', 'hd-confirm-dialog', 'hd-prompt-dialog'].forEach((id) => {
    const dialog = $(id);
    if (dialog) wireDialogClose(dialog);
  });
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && state.loadedOnce[state.tab]) {
      setText('summary', '页面已恢复，点击刷新读取最新列表');
    }
  });
}

function exitHandling() {
  window.close();
  window.location.href = '/feedback-center/bug';
}

function showApp() {
  const app = $('app');
  if (app) app.classList.remove('hidden');
  setText('summary', '加载中…');
  renderList();
  refreshCurrent().catch(() => null);
}

bind();
showApp();
