/* 休闲花园 · 小游戏通用"在线状态 + 对局邀请"外壳（所有小游戏共用一份）。

  以前这套东西只长在 2048 页面里（socket、登录、presence、邀请提示条、接受/拒绝），
  于是"以后每个小游戏都能被邀请进对局"就得每个游戏抄一遍。这里把它抽出来：
  页面只要 include 这个脚本 + 在 config 里给一个 gameKey，再提供几个可选的回调，
  就自动拥有：在线状态上报、邀请提示、接受（先保存再进对局）、拒绝、账号级拒邀开关。

  服务端那边认小游戏靠 minigame_registry，所以新游戏不需要改服务端白名单。

  用法（页面里）：先 <script src="/static/js/minigame-presence.js">，
  再 attach({ gameKey: 'suika', nickname, onSocket(socket) {...}, onStatus(text, kind) {...},
  beforeAccept: async () => saveLocal() })。
  可选的还有 onReady / onServerError / inviteBoxId 等（见下面的 DEFAULTS）。 */

(function () {
  'use strict';

  const DEFAULTS = {
    gameKey: '',
    nickname: '',
    betaMode: false,
    inviteBoxId: 'mg-invite',
    inviteTextId: 'mg-invite-text',
    acceptBtnId: 'mg-invite-accept',
    declineBtnId: 'mg-invite-decline',
    declineToggleId: 'mg-decline-invites',
    prefsUrl: '/api/minigame/prefs',
    acceptRedirect: '/?from_minigame_invite=1',
    acceptDelayMs: 700,
    saveTimeoutMs: 3000,
    onSocket: null,
    onStatus: null,
    onReady: null,
    onServerError: null,
    beforeAccept: null,
  };

  const state = {
    options: { ...DEFAULTS },
    socket: null,
    pendingInviterSid: '',
    identityRejected: false,
    ready: false,
  };

  const el = (id) => document.getElementById(id);

  function status(text, kind) {
    try {
      if (state.options.onStatus) state.options.onStatus(text, kind || '');
    } catch (_) { /* 页面自己的状态栏出错不影响邀请 */ }
  }

  function showInvitePrompt(payload) {
    const box = el(state.options.inviteBoxId);
    const text = el(state.options.inviteTextId);
    if (!box || !text) return;
    const from = (payload && payload.from) || '对方';
    const mode = payload && payload.mode ? `（${payload.mode}）` : '';
    text.textContent = `${from} 邀请你对局${mode}`;
    box.hidden = false;
  }

  function hideInvitePrompt() {
    const box = el(state.options.inviteBoxId);
    if (box) box.hidden = true;
  }

  function logEvent(name, payload) {
    window.__mgEventLog = window.__mgEventLog || [];
    try {
      window.__mgEventLog.push({ name, payload: JSON.stringify(payload || {}).slice(0, 200) });
    } catch (_) { /* 忽略 */ }
  }

  function handleServerError(payload) {
    const reason = payload && payload.reason;
    const message = (payload && payload.message) || '';
    if (reason === 'minigame_denied' || reason === 'minigame_login_required') {
      state.identityRejected = true;
      status(message || '身份或权限失效，请重新进入。', 'denied');
    } else if (reason === 'minigame_lower_priority') {
      status(message || '正在对局 / 观战 / 重连中，小游戏状态未生效', 'denied');
    }
    try {
      if (state.options.onServerError) state.options.onServerError(payload || {});
    } catch (_) { /* 忽略 */ }
  }

  function connect() {
    if (typeof window.io !== 'function') {
      status('实时连接组件没有加载，邀请功能不可用', 'denied');
      return null;
    }
    const gameKey = String(state.options.gameKey || '').trim();
    if (!gameKey) {
      status('缺少小游戏标识，邀请功能不可用', 'denied');
      return null;
    }
    const socket = window.io({ transports: ['websocket', 'polling'], withCredentials: true });
    state.socket = socket;
    window.__mgSocket = socket;                   // 探针与调试沿用这个名字
    window.__mgEventLog = window.__mgEventLog || [];
    ['login_ok', 'login_fail', 'minigame_status', 'lobby_chat_history', 'server_error'].forEach((name) => {
      socket.on(name, (payload) => logEvent(name, payload));
    });
    socket.on('connect', () => {
      // 小游戏标签页也是一条登录连接：同账号会接管别的标签页状态
      socket.emit('login', {
        nickname: String(state.options.nickname || ''),
        mode: '1v1',
        match_mode: 'casual_1v1',
        account_login: true,
        beta_mode: !!state.options.betaMode,
        skin: {},
      });
    });
    socket.on('login_ok', () => {
      socket.emit('minigame_presence', { game: gameKey });
    });
    socket.on('login_fail', (payload) => {
      const reason = (payload && payload.reason) || '登录失败';
      status(`登录/在线不可用：${reason}`, 'denied');
    });
    socket.on('minigame_status', () => {
      state.ready = true;
      try {
        if (state.options.onReady) state.options.onReady(socket);
      } catch (_) { /* 忽略 */ }
    });
    socket.on('invite_received', (payload) => {
      // 只提示，不自动离开棋盘；接受时才保存进度
      state.pendingInviterSid = String((payload && payload.inviter_sid) || '');
      showInvitePrompt(payload || {});
    });
    socket.on('invite_cancelled', () => {
      state.pendingInviterSid = '';
      hideInvitePrompt();
    });
    socket.on('server_error', handleServerError);
    try {
      if (state.options.onSocket) state.options.onSocket(socket);
    } catch (_) { /* 忽略 */ }
    return socket;
  }

  async function acceptInvite() {
    hideInvitePrompt();
    const inviterSid = state.pendingInviterSid;
    if (!inviterSid || !state.socket) {
      status('邀请已失效，请在对方重新邀请后再试', 'error');
      return;
    }
    // 接受前先可靠保存本地进度（同步最多等 3 秒，超时也照样进对局，队列会接着传）
    try {
      const save = state.options.beforeAccept;
      if (save) {
        await Promise.race([
          Promise.resolve(save()),
          new Promise((resolve) => window.setTimeout(resolve, state.options.saveTimeoutMs)),
        ]);
      }
    } catch (_) { /* 保存失败也进对局 */ }
    state.socket.emit('accept_invite', { inviter_sid: inviterSid });
    state.pendingInviterSid = '';
    status('正在进入对局…（本地进度已保存）');
    window.setTimeout(() => { window.location.href = state.options.acceptRedirect; },
      state.options.acceptDelayMs);
  }

  function declineInvite() {
    hideInvitePrompt();
    state.pendingInviterSid = '';
    if (state.socket) state.socket.emit('decline_invite', {});
  }

  async function loadPrefs() {
    const toggle = el(state.options.declineToggleId);
    if (!toggle) return;
    try {
      const response = await fetch(state.options.prefsUrl, { credentials: 'same-origin' });
      if (!response.ok) return;
      const data = await response.json();
      toggle.checked = !!(data && data.decline_invites);
    } catch (_) { /* 读不到就保持默认 */ }
  }

  async function savePrefs(checked) {
    try {
      await fetch(state.options.prefsUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decline_invites: !!checked }),
      });
    } catch (_) { /* 忽略：服务端才是权威 */ }
  }

  function attach(options) {
    state.options = { ...DEFAULTS, ...(options || {}) };
    const acceptBtn = el(state.options.acceptBtnId);
    if (acceptBtn) acceptBtn.addEventListener('click', () => { void acceptInvite(); });
    const declineBtn = el(state.options.declineBtnId);
    if (declineBtn) declineBtn.addEventListener('click', () => declineInvite());
    const toggle = el(state.options.declineToggleId);
    if (toggle) {
      void loadPrefs();
      toggle.addEventListener('change', () => { void savePrefs(toggle.checked); });
    }
    window.addEventListener('beforeunload', () => {
      if (!state.socket) return;
      try { state.socket.emit('minigame_leave', { game: state.options.gameKey }); } catch (_) { /* 忽略 */ }
    });
    connect();
    return api;
  }

  const api = {
    attach,
    acceptInvite,
    declineInvite,
    loadPrefs,
    hideInvitePrompt,
    showInvitePrompt,
    get socket() { return state.socket; },
    get ready() { return state.ready; },
    get identityRejected() { return state.identityRejected; },
  };

  window.GtnMinigamePresence = api;
})();
