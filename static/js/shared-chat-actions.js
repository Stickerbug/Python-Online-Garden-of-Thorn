/* 共享聊天操作：**举报** + **撤回**（休闲花园小游戏页、故事模式聊天行共用）。

   举报：POST /api/report（object_type=chat_message），服务端照旧校验身份与对象。
   撤回：socket 事件 admin_chat_recall（服务端再判一次权限：本人 / admin / staff 对普通玩家）。
   样式见 shared-lobby-chat.css 里的 .gtn-chat-report-* 与 .report-inline-btn / .chat-recall-btn。 */

(function () {
'use strict';

const DEFAULT_LABELS = {
  report: '举报',
  recall: '撤回',
  reportTitle: '举报聊天消息',
  reportObject: '对象',
  reportCategory: '类型',
  reportReason: '补充说明',
  reportPlaceholder: '可以补充说明情况（选填）',
  reportSubmit: '提交举报',
  reportCancel: '取消',
  reportSuccess: '举报已提交',
  reportFailed: '举报失败',
  recallDone: (count) => `已撤回 ${count} 条消息`,
  recallFailed: '撤回失败：消息可能已被撤回，或你没有权限',
  recallConfirm: (name) => `撤回 ${name} 的这条消息？撤回后所有玩家都看不到它。`,
  linkExternal: '这不是本站链接（非 *.stickerbug.top），确定要打开吗？',
  multiplayer: '多人',
  categories: {
    abusive_language: '辱骂 / 攻击性语言',
    sexual_content: '色情内容',
    spam: '刷屏 / 广告',
    privacy_leak: '泄露隐私',
    harassment: '骚扰',
    other: '其他',
  },
};

const REPORT_CATEGORIES = ['abusive_language', 'sexual_content', 'spam', 'privacy_leak', 'harassment', 'other'];

function chatActionLabels(custom = {}) {
  return {
    ...DEFAULT_LABELS,
    ...(custom || {}),
    categories: { ...DEFAULT_LABELS.categories, ...((custom || {}).categories || {}) },
  };
}

function chatEntryMessageId(entry = {}) {
  const value = Number(entry.message_id || entry.messageId || 0);
  return Number.isFinite(value) && value > 0 ? value : 0;
}

function canReportChatEntry(entry = {}) {
  return !entry.system && chatEntryMessageId(entry) > 0;
}

/* ===== 撤回核心（各聊天窗口共用：大厅 / 对局 / 故事模式 / 休闲花园）===== */

/* 玩家（含 staff）只能在发送后 2 分钟内撤回；管理员不受限制。 */
const CHAT_RECALL_WINDOW_MS = 120 * 1000;

function chatEntryTsSeconds(entry = {}) {
  const rawTs = Number(entry.ts || 0);
  if (rawTs > 0) return rawTs;
  const rawTime = String(entry.time || entry.created_at || '').trim();
  if (!rawTime) return 0;
  const parsed = Date.parse(rawTime.includes('T') ? rawTime : rawTime.replace(' ', 'T') + 'Z');
  return Number.isFinite(parsed) ? parsed / 1000 : 0;
}

function chatRecallWithinWindow(entry = {}, nowMs = Date.now()) {
  const ts = chatEntryTsSeconds(entry);
  if (!ts) return false;
  return nowMs - ts * 1000 <= CHAT_RECALL_WINDOW_MS;
}

/* 撤回按钮的过期时刻（毫秒）；管理员返回 0 表示永不过期。 */
function chatRecallDeadlineMs(entry = {}, viewer = {}) {
  if (String((viewer && viewer.role) || '').toLowerCase() === 'admin') return 0;
  const ts = chatEntryTsSeconds(entry);
  return ts ? ts * 1000 + CHAT_RECALL_WINDOW_MS : 0;
}

/* 撤回权限（与服务端一致）：本人 / staff 对普通玩家限 2 分钟；admin 任意且不限时。 */
function chatRecallAllowed(entry = {}, viewer = {}, nowMs = Date.now()) {
  if (entry.system || entry.recalled || chatEntryMessageId(entry) <= 0) return false;
  const role = String((viewer && viewer.role) || 'player').toLowerCase();
  const viewerId = viewer && viewer.user_id != null ? String(viewer.user_id) : '';
  const senderId = entry.sender_user_id != null ? String(entry.sender_user_id)
    : (entry.user_id != null ? String(entry.user_id) : '');
  if (role === 'admin') return true;
  const own = !!(viewerId && senderId && viewerId === senderId);
  if (own) return chatRecallWithinWindow(entry, nowMs);
  if (role === 'staff') {
    if (!senderId) return false;
    return String(entry.sender_role || 'player').toLowerCase() === 'player'
      && chatRecallWithinWindow(entry, nowMs);
  }
  return false;
}

const DEFAULT_RECALL_LABELS = {
  recall: '撤回',
  recallConfirm: (name) => `撤回 ${name} 的这条消息？撤回后所有玩家都看不到它。`,
  recallSelf: (actor) => `${actor}撤回了一条消息`,
  recallEntry: (actor, target) => `${actor}撤回了${target}的一条消息`,
  adminLabel: '管理员',
  playerLabel: '玩家',
};

function recallLabels(custom = {}) {
  return { ...DEFAULT_RECALL_LABELS, ...(custom || {}) };
}

/* 原位占位文本：被撤回的消息在原位置显示这一句，而不是在底部新增一条。 */
function chatRecallPlaceholderText(entry = {}, custom = {}) {
  const text = recallLabels(custom);
  const target = String(entry.nickname || entry.sender_name || entry.senderName || entry.nick || '?');
  const actorName = String(entry.recalled_by || entry.recalledBy || '').trim();
  const roleLabel = (key) => {
    const normalized = String(key || '').toLowerCase();
    if (normalized === 'admin' || normalized === 'staff') return text.adminLabel;
    if (normalized === 'player') return text.playerLabel;
    return '';
  };
  const actorRole = roleLabel(entry.recalled_role || entry.recalledRole);
  const targetRole = roleLabel(entry.sender_role || entry.senderRole);
  const self = entry.self_recall != null
    ? !!entry.self_recall
    : (!actorName || actorName === target);
  const actor = `${actorRole}${actorName || target}`;
  const targetText = `${targetRole}${target}`;
  return self ? text.recallSelf(actor) : text.recallEntry(actor, targetText);
}

/* 收到撤回广播 / 历史里的占位条目都长这样：文本清空，原位保留。 */
function markChatEntryRecalled(entry = {}, notice = {}) {
  if (!entry || typeof entry !== 'object') return false;
  entry.recalled = 1;
  entry.recalled_by = String(notice.actor_name || notice.recalled_by || notice.recalledBy || entry.nickname || '');
  if (notice.actor_role != null) entry.recalled_role = String(notice.actor_role);
  if (notice.self_recall != null) entry.self_recall = !!notice.self_recall;
  entry.text = '';
  entry.mentions = undefined;
  entry.repeat_count = 1;
  entry.repeatCount = 1;
  return true;
}

/* 撤回广播落到一组聊天条目上：条目全部命中 → 原位变占位；
   折叠条目只命中一部分 → 从折叠里剔除被撤回的，剩下的照常显示。
   与服务端缓存标记逻辑保持一致（app.py 的 _mark_*_chat_*_recalled）。 */
function applyRecallToEntryList(entries, notice = {}) {
  if (!Array.isArray(entries)) return;
  const ids = new Set(
    (Array.isArray(notice.message_ids) ? notice.message_ids : [])
      .map((value) => String(value || ''))
      .filter(Boolean),
  );
  if (!ids.size) return;
  entries.forEach((entry) => {
    if (!entry || typeof entry !== 'object' || entry.type === 'time') return;
    const entryIds = [...new Set(
      [entry.message_id, entry.messageId, ...(Array.isArray(entry.message_ids) ? entry.message_ids : [])]
        .filter((value) => value !== undefined && value !== null && value !== '')
        .map(String),
    )];
    if (!entryIds.length) return;
    const matched = entryIds.filter((id) => ids.has(id));
    if (!matched.length) return;
    const remaining = entryIds.filter((id) => !ids.has(id));
    if (remaining.length) {
      entry.message_id = remaining[remaining.length - 1];
      entry.messageId = entry.message_id;
      entry.message_ids = remaining.slice(-20);
      const count = Math.max(1, Math.min(Number(entry.repeat_count || entry.repeatCount || 1), remaining.length));
      entry.repeat_count = count;
      entry.repeatCount = count;
      return;
    }
    markChatEntryRecalled(entry, notice);
  });
}

/* 2 分钟一到自动把过期撤回按钮从界面上拿掉（管理员按钮没有 deadline，不受影响）。 */
let chatRecallExpiryTimer = null;
function startChatRecallExpiryWatcher() {
  if (chatRecallExpiryTimer != null) return;
  chatRecallExpiryTimer = setInterval(() => {
    const now = Date.now();
    document.querySelectorAll('.chat-recall-btn[data-recall-deadline]').forEach((button) => {
      const deadline = Number(button.getAttribute('data-recall-deadline') || 0);
      if (deadline && now >= deadline) button.remove();
    });
  }, 15000);
}

/* DOM 版撤回按钮（大厅 / 对局 / 故事模式）；确认流程可由调用方注入。 */
function createChatRecallButton(entry = {}, viewer = {}, options = {}) {
  const messageId = chatEntryMessageId(entry);
  if (!messageId || !chatRecallAllowed(entry, viewer)) return null;
  const text = recallLabels(options.labels || {});
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'chat-recall-btn';
  button.textContent = text.recall;
  button.title = text.recall;
  button.setAttribute('aria-label', text.recall);
  const deadline = chatRecallDeadlineMs(entry, viewer);
  if (deadline) {
    button.setAttribute('data-recall-deadline', String(deadline));
    if (Date.now() >= deadline) return null;
  }
  button.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopPropagation();
    confirmChatRecall(entry, options);
  });
  return button;
}

function reportTargetName(entry = {}) {
  return String(entry.nickname || entry.sender_name || entry.senderName || entry.nick || '');
}

async function openChatReportDialog(entry = {}, labels = {}) {
  const text = chatActionLabels(labels);
  const messageId = chatEntryMessageId(entry);
  if (!messageId) {
    window.alert(text.reportFailed);
    return false;
  }
  const overlay = document.createElement('div');
  overlay.className = 'gtn-chat-report-overlay';
  overlay.innerHTML = `
    <div class="gtn-chat-report-modal" role="dialog" aria-modal="true" aria-label="${text.reportTitle}">
      <h3>${text.reportTitle}</h3>
      <p class="gtn-chat-report-target">${text.reportObject}：<strong>${(entry.text || '').slice(0, 60)}</strong></p>
      <label class="gtn-chat-report-field">
        <span>${text.reportCategory}</span>
        <select class="gtn-chat-report-category">
          ${REPORT_CATEGORIES.map((key) => `<option value="${key}">${text.categories[key] || key}</option>`).join('')}
        </select>
      </label>
      <label class="gtn-chat-report-field">
        <span>${text.reportReason}</span>
        <textarea class="gtn-chat-report-reason" maxlength="300" placeholder="${text.reportPlaceholder}"></textarea>
      </label>
      <p class="gtn-chat-report-error" hidden></p>
      <div class="gtn-chat-report-actions">
        <button type="button" class="gtn-chat-report-cancel">${text.reportCancel}</button>
        <button type="button" class="gtn-chat-report-submit">${text.reportSubmit}</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  const close = () => overlay.remove();
  overlay.addEventListener('click', (event) => { if (event.target === overlay) close(); });
  overlay.querySelector('.gtn-chat-report-cancel').addEventListener('click', close);
  const errorEl = overlay.querySelector('.gtn-chat-report-error');
  const submit = overlay.querySelector('.gtn-chat-report-submit');
  return await new Promise((resolve) => {
    submit.addEventListener('click', async () => {
      submit.disabled = true;
      errorEl.hidden = true;
      try {
        const response = await fetch('/api/report', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            object_type: 'chat_message',
            object_id: String(messageId),
            category: overlay.querySelector('.gtn-chat-report-category').value,
            reason_text: overlay.querySelector('.gtn-chat-report-reason').value,
            target_user_id: entry.sender_user_id || entry.user_id || undefined,
            target_username: reportTargetName(entry) || undefined,
          }),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || !data.success) {
          throw new Error(data.error || data.message || text.reportFailed);
        }
        close();
        resolve(true);
      } catch (err) {
        errorEl.textContent = (err && err.message) || text.reportFailed;
        errorEl.hidden = false;
        submit.disabled = false;
        resolve(false);
      }
    });
  });
}

function confirmChatRecall(entry = {}, options = {}) {
  const text = chatActionLabels(options.labels || {});
  const socket = options.socket;
  const messageId = chatEntryMessageId(entry);
  if (!socket || !messageId) return;
  const target = reportTargetName(entry) || '?';
  const confirmFn = typeof window.confirm === 'function' ? window.confirm : null;
  // 游戏内页面通常有自带确认框；调用方可以用 options.confirm 覆盖（返回 Promise<boolean>）
  const ask = typeof options.confirm === 'function'
    ? options.confirm
    : async (message) => (confirmFn ? confirmFn(message) : true);
  Promise.resolve(ask(text.recallConfirm(target))).then((ok) => {
    if (!ok) return;
    socket.emit('admin_chat_recall', { message_ids: [messageId] });
  });
}

/* 给"HTML 字符串渲染"的聊天行（小游戏页）用 */
function chatActionButtonsHtml(entry = {}, viewer = {}, labels = {}) {
  const text = chatActionLabels(labels);
  const messageId = chatEntryMessageId(entry);
  if (!messageId) return '';
  const buttons = [];
  if (canReportChatEntry(entry)) {
    buttons.push(`<button type="button" class="report-inline-btn chat-report-btn" data-chat-report="${messageId}" title="${text.report}">${text.report}</button>`);
  }
  if (chatRecallAllowed(entry, viewer)) {
    const deadline = chatRecallDeadlineMs(entry, viewer);
    if (!deadline || Date.now() < deadline) {
      buttons.push(`<button type="button" class="chat-recall-btn" data-chat-recall="${messageId}"${deadline ? ` data-recall-deadline="${deadline}"` : ''} title="${text.recall}">${text.recall}</button>`);
    }
  }
  return buttons.join('');
}

/* 给"DOM 节点渲染"的聊天行（故事模式）用 */
function createChatActionButtons(entry = {}, viewer = {}, labels = {}, options = {}) {
  const text = chatActionLabels(labels);
  const fragment = document.createDocumentFragment();
  const messageId = chatEntryMessageId(entry);
  if (!messageId) return fragment;
  if (canReportChatEntry(entry)) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'report-inline-btn chat-report-btn';
    button.textContent = text.report;
    button.title = text.report;
    button.setAttribute('aria-label', text.report);
    button.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      void openChatReportDialog(entry, labels);
    });
    fragment.appendChild(button);
  }
  if (chatRecallAllowed(entry, viewer)) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'chat-recall-btn';
    button.textContent = text.recall;
    button.title = text.recall;
    button.setAttribute('aria-label', text.recall);
    const deadline = chatRecallDeadlineMs(entry, viewer);
    if (deadline) {
      button.setAttribute('data-recall-deadline', String(deadline));
      if (Date.now() >= deadline) return fragment;
    }
    button.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      confirmChatRecall(entry, { socket: options.socket, labels, confirm: options.confirm });
    });
    fragment.appendChild(button);
  }
  return fragment;
}

/* ===== 聊天链接化（各聊天窗口共用）===== */

/* 两类识别：
   1) 带协议：http(s)://… （原样信任）
   2) 裸域名：domain.tld[/path]，tld 必须在白名单里（b.c、v1.2、setup.exe 这类不算）。
   域名段禁止全角字符；站内域 = 任意 *.stickerbug.top 子域。 */
const CHAT_URL_PATTERN = /https?:\/\/[^\s<>"'\u3000-\u9fff\uff00-\uffef]+/gi;

/* 回放编号（R-12345 / P-12345）：可点击的 chip（见 game.js 的委托处理——
   弹确认框显示双方与胜负后进入回放）。只在纯文本段里识别，前后不能是
   字母数字或连字符（避免误伤 RP-12345 / ABCR-1 之类的普通词）；
   只认 5 位数字（当前量级 ~2 万/年，一年内不会到 6 位）。 */
const CHAT_REPLAY_REF_PATTERN = /(?<![\w-])[RP]-\d{5}(?![\w-])/gi;

/* 常用顶级域白名单（小写）。覆盖主流 gTLD/ccTLD 与游戏社区常见域；
   不在名单里的裸域名不会被识别（带 http(s):// 的不受限）。 */
const CHAT_KNOWN_TLDS = new Set((
  'com net org edu gov mil int info biz xyz top club online site website space fun store shop '
  + 'tech cloud app dev io ai cc tv me co us uk ca de fr es it nl se no fi dk pl pt cz ru ua '
  + 'cn jp kr hk tw sg in au nz br mx ar cl th vn my ph id tr il za eu gg fm am gs '
  + 'moe king red link pro one vip live life world games game video chat social media network '
  + 'wiki zone icu ink lol moe fanbox page page dev app gay'
).split(/\s+/).filter(Boolean));

/* 裸域名：host.tld（tld 纯字母且在白名单）+ 可选路径/查询。
   (?<![\w@.]) 防止匹配文件名尾巴（v1.2 / setup.exe）与邮箱域名部分。 */
const CHAT_BARE_DOMAIN_PATTERN = new RegExp(
  '(?<![\\w@.])'
  + '((?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\\.)+'
  + '([a-z]{2,24}))'
  + '(?::\\d{1,5})?'
  + '(/[^\\s<>"\'\\u3000-\\u9fff\\uff00-\\uffef]*)?',
  'gi',
);

const CHAT_INTERNAL_URL = /^https?:\/\/([a-z0-9-]+\.)*stickerbug\.top(?::\d+)?(?:[/?#]|$)/i;
const CHAT_INTERNAL_BARE = /^([a-z0-9-]+\.)*stickerbug\.top(?::\d+)?(?:[/?#]|$)/i;

function chatUrlLooksLikeHost(url) {
  // 裸域名补协议前先做一次整段校验：host 部分每段 ≤63 字符且非空。
  const withoutScheme = String(url || '').replace(/^https?:\/\//i, '');
  const hostPart = withoutScheme.split(/[/?#:]/, 1)[0] || '';
  if (!hostPart || hostPart.length > 253) return false;
  return hostPart.split('.').every((label) => /^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/i.test(label));
}

function chatUrlFromMatch(raw) {
  let url = String(raw || '');
  // 剥掉黏在链接尾部的标点（右括号只在左侧有配对时保留）。
  url = url.replace(/[),.;:!?'"\]]+$/, (punct) => {
    if (/[\])]/.test(punct)) {
      const opens = (url.match(/[(\[]/g) || []).length;
      const closes = (url.match(/[)\]]/g) || []).length;
      if (opens >= closes) return punct;
    }
    return '';
  });
  if (/[\])],?$/.test(url) && (url.match(/[(\[]/g) || []).length < (url.match(/[)\]]/g) || []).length) {
    url = url.replace(/[)\]]+$/, '');
  }
  return url;
}

function chatLinkTargetAllowed(url) {
  const text = String(url || '');
  return CHAT_INTERNAL_URL.test(text) || CHAT_INTERNAL_BARE.test(text);
}

/* 把一段纯文本切成片段：{text} 纯文本 / {url, display, external} 链接。
   display 是用户看到的内容（裸域名不带补的协议）；matchedLength 是链接消费掉的
   原文长度（剥掉的尾部标点留在纯文本里）。 */
function chatSplitLinkSegments(text) {
  const raw = String(text || '');
  const segments = [];

  const pushPlain = (slice) => {
    if (!slice) return;
    const last = segments[segments.length - 1];
    if (last && last.text !== undefined) last.text += slice;
    else segments.push({ text: slice });
  };

  pushPlain(raw);

  const scanWith = (pattern, toPiece) => {
    // 只在「纯文本段」里扫描；已识别的 URL/回放编号不再二次处理。
    for (let si = 0; si < segments.length; si += 1) {
      const segment = segments[si];
      if (segment.url !== undefined || segment.replayRef !== undefined) continue;
      const source = segment.text;
      pattern.lastIndex = 0;
      let match;
      let cursor = 0;
      const pieces = [];
      let changed = false;
      while ((match = pattern.exec(source)) !== null) {
        const piece = toPiece(match);
        const start = match.index;
        if (piece && (piece.url !== undefined || piece.replayRef !== undefined)) {
          changed = true;
          if (start > cursor) pieces.push({ text: source.slice(cursor, start) });
          pieces.push(piece);
          cursor = start + piece.matchedLength;
          if (piece.matchedLength <= 0) pattern.lastIndex = start + 1;
        } else {
          const end = start + match[0].length;
          if (end > cursor) {
            pieces.push({ text: source.slice(cursor, end) });
            cursor = end;
          }
        }
      }
      if (!changed) continue;
      if (cursor < source.length) pieces.push({ text: source.slice(cursor) });
      if (!pieces.length) pieces.push({ text: source });
      segments.splice(si, 1, ...pieces);
      si += pieces.length - 1;
    }
  };

  scanWith(CHAT_URL_PATTERN, (match) => {
    const url = chatUrlFromMatch(match[0]);
    if (!url || !chatUrlLooksLikeHost(url)) return null;
    return {
      url,
      display: url,
      matchedLength: url.length,
      external: !chatLinkTargetAllowed(url),
    };
  });
  scanWith(CHAT_BARE_DOMAIN_PATTERN, (match) => {
    const tld = String(match[2] || '').toLowerCase();
    if (!CHAT_KNOWN_TLDS.has(tld)) return null;
    const url = chatUrlFromMatch(match[0]);
    if (!url) return null;
    const hostPart = url.split(/[/?#:]/, 1)[0] || '';
    if (!/^[a-z]/i.test(hostPart)) return null;
    const full = /^https?:\/\//i.test(url) ? url : `https://${url}`;
    return {
      url: full,
      display: url.replace(/^https?:\/\//i, ''),
      matchedLength: url.length,
      external: !chatLinkTargetAllowed(full),
    };
  });
  scanWith(CHAT_REPLAY_REF_PATTERN, (match) => {
    const ref = String(match[0] || '').toUpperCase();
    return {
      replayRef: ref,
      display: ref,
      matchedLength: ref.length,
    };
  });

  // 相邻同型段合并；空段丢弃（只合并文本段——URL/回放编号段直接透传）
  const out = [];
  segments.forEach((segment) => {
    if (segment.text !== undefined && !segment.text) return;
    const prev = out[out.length - 1];
    if (prev && prev.text !== undefined && segment.text !== undefined) prev.text += segment.text;
    else out.push(segment);
  });
  return out;
}

/* 对局编号识别状态（2026-10-06 设计）：只有服务端已验证（随消息载荷
   replay_refs.v 回带）或复检通过的编号才渲染为可点 chip；其余（不存在/
   前缀写错/超 30 天/尚未生成的未来编号）渲染为纯文本样式的 pending span，
   复检通过后原位升级——未来编号在对局生成后的下一次复检自动变可点。 */
const chatReplayRefValidated = new Set();

function normalizeChatReplayRef(ref) {
  return String(ref || '').trim().toUpperCase();
}

function isChatReplayRefValidated(ref) {
  return chatReplayRefValidated.has(normalizeChatReplayRef(ref));
}

function seedChatReplayRefs(entry) {
  const refs = entry && entry.replay_refs;
  if (refs && Array.isArray(refs.v)) {
    refs.v.forEach((ref) => chatReplayRefValidated.add(normalizeChatReplayRef(ref)));
  }
}

function collectPendingChatReplayRefs(root) {
  const found = new Set();
  (root || document).querySelectorAll('.chat-replay-pending[data-replay-ref]').forEach((el) => {
    const ref = normalizeChatReplayRef(el.dataset.replayRef);
    if (ref) found.add(ref);
  });
  return [...found];
}

function upgradeChatReplayRefs(validity) {
  Object.entries(validity || {}).forEach(([ref, ok]) => {
    if (ok) chatReplayRefValidated.add(normalizeChatReplayRef(ref));
  });
  let upgraded = 0;
  document.querySelectorAll('.chat-replay-pending[data-replay-ref]').forEach((el) => {
    if (chatReplayRefValidated.has(normalizeChatReplayRef(el.dataset.replayRef))) {
      el.className = 'chat-replay-link';
      upgraded += 1;
    }
  });
  return upgraded;
}

/* 复检调度：渲染后调用，收集 pending 编号批量问服务端（去重 + 节流）。
   emitFn 由各页面注入自己的 socket（主连接/故事连接）。 */
let chatReplayRefCheckTimer = null;
const chatReplayRefChecked = new Set();
function scheduleChatReplayRefRecheck(emitFn, delayMs = 8000) {
  if (chatReplayRefCheckTimer != null || typeof emitFn !== 'function') return;
  chatReplayRefCheckTimer = window.setTimeout(() => {
    chatReplayRefCheckTimer = null;
    const refs = collectPendingChatReplayRefs()
      .filter((ref) => !chatReplayRefValidated.has(ref) && !chatReplayRefChecked.has(ref))
      .slice(0, 25);
    if (!refs.length) return;
    refs.forEach((ref) => chatReplayRefChecked.add(ref));
    try {
      emitFn({ refs });
    } catch (_) { /* 页面已卸载等：忽略 */ }
  }, Math.max(1000, Number(delayMs) || 8000));
}

function chatAppendSegment(parent, segment, confirmExternal) {
  if (segment.replayRef !== undefined) {
    if (!chatReplayRefValidated.has(normalizeChatReplayRef(segment.replayRef))) {
      const pending = document.createElement('span');
      pending.className = 'chat-replay-pending';
      pending.textContent = segment.display || segment.replayRef;
      pending.dataset.replayRef = segment.replayRef;
      parent.appendChild(pending);
      return;
    }
    const chip = document.createElement('span');
    chip.className = 'chat-replay-link';
    chip.textContent = segment.display || segment.replayRef;
    chip.dataset.replayRef = segment.replayRef;
    parent.appendChild(chip);
    return;
  }
  if (segment.url === undefined) {
    parent.appendChild(document.createTextNode(segment.text));
    return;
  }
  const url = segment.url;
  const anchor = document.createElement('a');
  anchor.className = 'chat-link';
  anchor.textContent = segment.display || url;
  anchor.href = url;
  anchor.target = '_blank';
  anchor.rel = 'noopener noreferrer';
  anchor.addEventListener('click', (event) => {
    if (chatLinkTargetAllowed(url)) return;
    event.preventDefault();
    if (!confirmExternal) {
      window.open(url, '_blank', 'noopener,noreferrer');
      return;
    }
    Promise.resolve(confirmExternal(url)).then((ok) => {
      if (ok) window.open(url, '_blank', 'noopener,noreferrer');
    });
  });
  parent.appendChild(anchor);
}

/* DOM 版：把文本按提及+URL 分段渲染进 parent（转义在前、协议白名单在后）。
   options.appendPlain(parent, slice) 可接管纯文本渲染（提及管线用）；
   options.entry 为聊天条目时顺带播种服务端已验证的编号。 */
function appendChatTextWithLinks(parent, text, options = {}) {
  const confirmExternal = typeof options.confirmExternal === 'function' ? options.confirmExternal : null;
  if (options.entry) seedChatReplayRefs(options.entry);
  chatSplitLinkSegments(text).forEach((segment) => {
    if (segment.url === undefined && segment.replayRef === undefined && typeof options.appendPlain === 'function') {
      options.appendPlain(parent, segment.text);
    } else {
      chatAppendSegment(parent, segment, confirmExternal);
    }
  });
}

/* HTML 版（小游戏页）：返回 HTML 字符串；输入必须已是 escapeHtml 后的文本。 */
function chatLinkHtml(escapedText, entry = null) {
  if (entry) seedChatReplayRefs(entry);
  return chatSplitLinkSegments(escapedText).map((segment) => {
    if (segment.replayRef !== undefined) {
      if (!chatReplayRefValidated.has(normalizeChatReplayRef(segment.replayRef))) {
        return `<span class="chat-replay-pending" data-replay-ref="${segment.replayRef}">${segment.display || segment.replayRef}</span>`;
      }
      return `<span class="chat-replay-link" data-replay-ref="${segment.replayRef}">${segment.display || segment.replayRef}</span>`;
    }
    if (segment.url === undefined) return segment.text;
    const external = segment.external || !chatLinkTargetAllowed(segment.url);
    return `<a href="${segment.url}" target="_blank" rel="noopener noreferrer" class="chat-link"`
      + `${external ? ' data-chat-external="1"' : ''}>${segment.display || segment.url}</a>`;
  }).join('');
}

/* 以经典脚本暴露给页面：小游戏页（ES module）与故事模式（经典脚本）都能用。 */
window.GtnChatActions = {
  chatActionLabels,
  chatTitlesHtml,
  namePaintHtml,
  chatEntryMessageId,
  canReportChatEntry,
  chatRecallAllowed,
  openChatReportDialog,
  confirmChatRecall,
  chatActionButtonsHtml,
  createChatReportButton,
  createChatRecallButton,
  chatLinkHtml,
};

/* 撤回统一机制的独立入口：窗口判定、原位占位、过期按钮清理。
   大厅 / 对局 / 故事 / 休闲花园全部走这一份，别再各自复制。 */
window.GtnChatRecall = {
  WINDOW_MS: CHAT_RECALL_WINDOW_MS,
  entryTsSeconds: chatEntryTsSeconds,
  withinWindow: chatRecallWithinWindow,
  deadlineMs: chatRecallDeadlineMs,
  allowed: chatRecallAllowed,
  labels: recallLabels,
  placeholderText: chatRecallPlaceholderText,
  markEntryRecalled: markChatEntryRecalled,
  applyRecallToEntryList,
  startExpiryWatcher: startChatRecallExpiryWatcher,
};

/* 聊天链接化入口（同上：一份实现，四处接入）。 */
window.GtnChatLinks = {
  pattern: CHAT_URL_PATTERN,
  replayPattern: CHAT_REPLAY_REF_PATTERN,
  urlFromMatch: chatUrlFromMatch,
  internalAllowed: chatLinkTargetAllowed,
  appendTextWithLinks: appendChatTextWithLinks,
  html: chatLinkHtml,
  isReplayRefValidated: isChatReplayRefValidated,
  seedReplayRefs: seedChatReplayRefs,
  collectPendingReplayRefs: collectPendingChatReplayRefs,
  upgradeReplayRefs: upgradeChatReplayRefs,
  scheduleReplayRefRecheck: scheduleChatReplayRefRecheck,
};

if (typeof document !== 'undefined') startChatRecallExpiryWatcher();

/* 只给"已经有自己撤回按钮"的页面（故事模式）用的举报按钮 */
function createChatReportButton(entry = {}, labels = {}) {
  const text = chatActionLabels(labels);
  if (!canReportChatEntry(entry)) return null;
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'report-inline-btn chat-report-btn';
  button.textContent = text.report;
  button.title = text.report;
  button.setAttribute('aria-label', text.report);
  button.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopPropagation();
    void openChatReportDialog(entry, labels);
  });
  return button;
}

/* ===== 排行榜/身份渲染帮手（2026-09-25 从 2048 内联聊天恢复）=====
   聊天迁到共用外壳（3b96031）时把这两个函数连同内联代码一起删掉了，
   2048 排行榜渲染随之 ReferenceError——客户端把一切失败显示成
   「离线，暂时读不到排行榜」。放这里：2048 / suika 两页都加载本文件。 */

/* 称号配色：与 game.js 的 titleColorCss 同一张表（多人大厅就是这么给称号上色的）。
   色板 / 称号色调整时两边一起改。 */
const TITLE_COLOR_TOKENS = {
  admin: '#C0392B', thorn: '#C0392B', bloom: '#1ABC9C', root: '#8D6E63', guard: '#2980B9',
  curse: '#704B87', infect: '#7E9638', health: '#2ECC71', elixir: '#F1C40F', energy: '#F1C40F',
  magic: '#3498DB', damage: '#C0392B', electric: '#4BA3FF', poison: '#8E44AD', fire: '#E67E22',
  armor: '#95A5A6', precision: '#546E7A', banish: '#6C3483', indestructible: '#D4AC0D',
  critical: '#D4AC0D', primary: '#7EEF6D', common: '#7EEF6D', unusual: '#FFE65D', rare: '#4D52E3',
  epic: '#861FDE', legendary: '#DE1F1F', mythic: '#1FDBDE', ultra: '#FF2B75', super: '#2BFFA3',
  omega: '#F329D9', eternal: '#EEEEEE', unique: '#555555', milestone: '#5AA469', hidden: '#7257A8',
  neutral: '#7F8C8D', spectator: '#95A5A6',
};

function titleColorCss(color) {
  const key = String(color || '').trim().toLowerCase();
  if (TITLE_COLOR_TOKENS[key]) return TITLE_COLOR_TOKENS[key];
  if (/^#[0-9a-f]{6}(?:[0-9a-f]{2})?$/i.test(key)) return key;
  return '';
}

/* 游戏称号前缀：和多人游戏大厅一样渲染成 [称号名]（按称号自带颜色）。 */
function chatTitlesHtml(item) {
  const titles = Array.isArray(item && item.equipped_titles) ? item.equipped_titles : [];
  return titles.slice(0, 3).map((title) => {
    const name = String((title && title.name) || '').trim();
    if (!name) return '';
    const color = titleColorCss(title.color);
    return `<span class="player-title-inline"${color ? ` style="color:${color}"` : ''}>[${escapeHtml(name)}]</span>`;
  }).join('');
}

/* 信誉徽章：新人 / 低信誉（与多人大厅同名同类，样式见 shared-lobby-chat.css）。 */
function chatReputationHtml(item) {
  const labels = chatLabels();
  const profile = (item && item.reputation_profile) || null;
  const newcomer = profile && profile.newcomer && profile.newcomer.is_newcomer === true
    ? `<span class="reputation-badge newcomer-badge">${escapeHtml(labels.newcomer)}</span>`
    : '';
  const level = String((profile && profile.level) || '');
  if (!['yellow', 'orange', 'red'].includes(level)) return newcomer;
  return newcomer
    + `<span class="reputation-badge reputation-${level}">${escapeHtml(labels.lowReputation)}</span>`;
}

/* 昵称名牌配色：数据形状与 game.js 的 getPlayerNamePaint / titlePaintPresentation 一致——
   渐变（含彩虹）与随主题变色都存在 ``name_style.paint`` 里，不是 name_style.kind。
   返回 ``{ className, style }``；没有自定义名牌时返回 null（用默认色）。 */
function chatNamePaint(item) {
  const style = (item && item.name_style) || null;
  const paint = (style && typeof style.paint === 'object' && style.paint) || null;
  if (paint) {
    const kind = String(paint.kind || '').toLowerCase();
    if (kind === 'gradient' || kind === 'rainbow') {
      const colors = (Array.isArray(paint.colors) ? paint.colors : [])
        .map((color) => titleColorCss(color))
        .filter(Boolean)
        .slice(0, 12);
      if (colors.length >= 2) {
        const numeric = Number(paint.angle);
        const angle = Number.isFinite(numeric) ? ((numeric % 360) + 360) % 360 : 90;
        return {
          className: 'title-paint-gradient',
          style: `--title-paint-gradient:linear-gradient(${angle}deg,${colors.join(',')})`,
        };
      }
    } else if (kind === 'theme') {
      const light = titleColorCss(paint.light && paint.light.color) || titleColorCss('neutral');
      const dark = titleColorCss(paint.dark && paint.dark.color) || titleColorCss('neutral');
      return {
        className: 'title-paint-theme',
        style: `--title-paint-light:${light};--title-paint-dark:${dark};background-image:none;-webkit-text-fill-color:currentColor`,
      };
    } else if (kind === 'solid') {
      const color = titleColorCss(paint.color);
      if (color) {
        return {
          className: 'title-paint-solid',
          style: `color:${color};background-image:none;-webkit-text-fill-color:currentColor`,
        };
      }
    }
  }
  const solid = titleColorCss(item && item.name_color);
  return solid
    ? { className: 'title-paint-solid', style: `color:${solid};background-image:none;-webkit-text-fill-color:currentColor` }
    : null;
}

/* 带配色的昵称（聊天行与排行榜共用）：渐变 / 纯色 / 随主题。 */
function namePaintHtml(item, name) {
  const text = String(name || '?');
  const paint = chatNamePaint(item);
  return `<span class="player-name-value${paint ? ` ${paint.className}` : ''}"`
    + `${paint ? ` style="${paint.style}"` : ''}>${escapeHtml(text)}</span>`;
}

function chatNameHtml(item, fallback) {
  return namePaintHtml(item, (item && item.nickname) || fallback || '?');
}

/* minigame_2048.js 是独立脚本：把排行榜渲染要用的帮手挂到全局。
   escapeHtml 也是当年内联聊天的一员（模块作用域里有同名函数但这里拿不到），
   这里自带一份局部实现，避免再漏依赖。 */
function _lbEscapeHtml(text) {
  return String(text == null ? '' : text).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[char]));
}

window.chatTitlesHtml = function (item) {
  const titles = Array.isArray(item && item.equipped_titles) ? item.equipped_titles : [];
  return titles.slice(0, 3).map((title) => {
    const name = String((title && title.name) || '').trim();
    if (!name) return '';
    const color = titleColorCss(title.color);
    return `<span class="player-title-inline"${color ? ` style="color:${color}"` : ''}>[${_lbEscapeHtml(name)}]</span>`;
  }).join('');
};
window.namePaintHtml = function (item, name) {
  const text = String(name || '?');
  const paint = chatNamePaint(item);
  return `<span class="player-name-value${paint ? ` ${paint.className}` : ''}" `
    + `${paint ? `style="${paint.style}" ` : ''}>${_lbEscapeHtml(text)}</span>`;
};
window.chatNameHtml = chatNameHtml;
})();

