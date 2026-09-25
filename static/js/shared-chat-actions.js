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

/* 撤回权限（与服务端一致）：本人的消息谁都能撤回；admin 任意；staff 只能撤回普通玩家的 */
function chatRecallAllowed(entry = {}, viewer = {}) {
  if (entry.system || chatEntryMessageId(entry) <= 0) return false;
  const role = String((viewer && viewer.role) || 'player').toLowerCase();
  const viewerId = viewer && viewer.user_id != null ? String(viewer.user_id) : '';
  const senderId = entry.sender_user_id != null ? String(entry.sender_user_id)
    : (entry.user_id != null ? String(entry.user_id) : '');
  if (viewerId && senderId && viewerId === senderId) return true;
  if (role === 'admin') return true;
  if (role === 'staff') return String(entry.sender_role || 'player').toLowerCase() === 'player';
  return false;
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
    buttons.push(`<button type="button" class="chat-recall-btn" data-chat-recall="${messageId}" title="${text.recall}">${text.recall}</button>`);
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
    button.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      confirmChatRecall(entry, { socket: options.socket, labels, confirm: options.confirm });
    });
    fragment.appendChild(button);
  }
  return fragment;
}

/* 以经典脚本暴露给页面：小游戏页（ES module）与故事模式（经典脚本）都能用。 */
window.GtnChatActions = {
  chatActionLabels,
  chatEntryMessageId,
  canReportChatEntry,
  chatRecallAllowed,
  openChatReportDialog,
  confirmChatRecall,
  chatActionButtonsHtml,
  createChatReportButton,
};

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
})();

