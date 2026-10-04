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
    userId: null,
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
    startFailedAt: 0,
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
    /* 服务端字段是 inviter_name（GB-205：此前只读 from，邀请人永远显示「对方」）。 */
    const from = (payload && (payload.inviter_name || payload.from)) || '对方';
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
    // 游客聊天（#343）：游客没有账号会话，account_login 发 true 会被服务端
    // 直接拒（Account session expired），聊天永远连不上。游客改发昵称登录
    // （昵称用大厅留在 localStorage 的 gtn_nickname），账号用户保持原握手。
    const guestChat = state.options.userId == null;
    const guestNickname = () => String(localStorage.getItem('gtn_nickname') || '').trim();
    let guestLoginRetries = 0;
    const emitLogin = () => {
      socket.emit('login', {
        nickname: guestChat ? guestNickname() : String(state.options.nickname || ''),
        mode: '1v1',
        match_mode: 'casual_1v1',
        account_login: !guestChat,
        beta_mode: !!state.options.betaMode,
        skin: {},
      });
    };
    socket.on('connect', () => {
      // 小游戏标签页也是一条登录连接：同账号会接管别的标签页状态
      emitLogin();
    });
    socket.on('login_ok', () => {
      // 游客没有服务端会话，minigame_presence 会被拒（minigame_login_required）
      if (!guestChat) socket.emit('minigame_presence', { game: gameKey });
    });
    socket.on('login_fail', (payload) => {
      const reason = (payload && payload.reason) || '登录失败';
      if (!guestChat) {
        status(`登录/在线不可用：${reason}`, 'denied');
        return;
      }
      if (reason === 'Nickname already exists' && guestLoginRetries < 5) {
        // 自己的大厅标签页还开着：等服务端 15 秒空闲接管窗口过去后重试。
        guestLoginRetries += 1;
        window.setTimeout(() => {
          if (socket.connected) emitLogin();
        }, 8000);
        return;
      }
      status(guestNickname()
        ? `游客聊天不可用：${reason}`
        : '游客聊天需先在大厅用昵称进入一次', 'denied');
    });
    // 游客在大厅名单里是 lobby 状态，会被挂机检测抽中；本页正在玩游戏不算挂机，
    // 自动按住 1 秒回应即可（与大厅客户端的按住按钮等价）。
    socket.on('afk_check', (payload) => {
      const id = payload && payload.id;
      if (!id) return;
      window.setTimeout(() => {
        socket.emit('afk_check_response', { id, hold_ms: 1000 });
      }, 1000);
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
    /* 接受邀请后开局失败（模式不一致/天梯资格等）服务端只发这个事件：
     * 小游戏页此前没监听，失败就是"点了没反应"（GB-205）。失败时留在小游戏页
     * （进度不丢），错误提示在状态栏。 */
    socket.on('match_start_failed', (payload) => {
      const message = (payload && payload.message) || '邀请已失效，进入对局失败';
      status(message, 'denied');
      state.pendingInviterSid = '';
      state.startFailedAt = Date.now();
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
    window.setTimeout(() => {
      // 700ms 内开局失败事件先到：不跳走，留在小游戏页（错误已在状态栏提示）
      if (state.startFailedAt && Date.now() - state.startFailedAt < 15000) return;
      window.location.href = state.options.acceptRedirect;
    }, state.options.acceptDelayMs);
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
