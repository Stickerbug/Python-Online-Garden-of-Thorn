/* 休闲花园 · 小游戏通用聊天面板（大厅那条聊天，所有小游戏共用一份渲染）。

   以前聊天行渲染（称号 / 信誉徽章 / 彩虹昵称 / [休闲] 前缀 / @提及 / 举报撤回按钮）
   只写在 2048 页面里。这里抽出来做成通用模块：页面给一组元素 id + 已经连上的 socket，
   就能得到和多人游戏大厅完全一致的聊天面板。

   依赖：shared-lobby-chat.css（面板样式）、shared-chat-actions.js（举报 / 撤回按钮）。
   用法见 docs/休闲花园-小游戏接入规范.md。 */

(function () {
  'use strict';

  const els = (id) => document.getElementById(id);
  const escapeHtml = (text) => String(text == null ? '' : text)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

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

  function namePaint(item) {
    const style = (item && item.name_style) || null;
    const paint = (style && typeof style.paint === 'object' && style.paint) || null;
    if (paint) {
      const kind = String(paint.kind || '').toLowerCase();
      if (kind === 'gradient' || kind === 'rainbow') {
        const colors = (Array.isArray(paint.colors) ? paint.colors : [])
          .map((color) => titleColorCss(color)).filter(Boolean).slice(0, 12);
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

  function nameHtml(item, fallback) {
    const text = String((item && item.nickname) || fallback || '?');
    const paint = namePaint(item);
    return `<span class="player-name-value${paint ? ` ${paint.className}` : ''}"`
      + `${paint ? ` style="${paint.style}"` : ''}>${escapeHtml(text)}</span>`;
  }

  function attach(config) {
    const options = {
      socket: null,
      gameKey: '',
      userId: null,
      username: '',
      chatRole: 'player',
      toggleId: 'mg-chat-toggle',
      panelId: 'mg-chat',
      closeId: 'mg-chat-close',
      logId: 'mg-chat-log',
      formId: 'mg-chat-form',
      inputId: 'mg-chat-input',
      unreadId: 'mg-chat-unread',
      emptyHtml: '<p class="mg-hint">还没有人说话。</p>',
      ...(config || {}),
    };
    const actions = window.GtnChatActions || {};
    const entriesById = new Map();
    let unread = 0;
    let unreadCursor = 0;
    let unreadCursorReady = false;

    const labels = () => (typeof actions.chatActionLabels === 'function' ? actions.chatActionLabels() : {});
    const isOwn = (item) => {
      if (!item) return false;
      if (options.userId != null && item.user_id != null
          && String(item.user_id) === String(options.userId)) return true;
      return String(item.nickname || '') !== ''
        && String(item.nickname) === String(options.username || '');
    };

    function originBadgeHtml(item) {
      /* 服务端的字段名是 chat_origin（旧内联实现也读这个）；只认 item.origin 的话
         [休闲]/[故事] 前缀从来没渲染出来过——迁移到外壳后才被探针暴露 */
      const origin = String((item && (item.chat_origin || item.origin)) || '').toLowerCase();
      const text = (item && item.origin_label) || (origin === 'leisure' ? '休闲' : origin === 'story' ? '故事' : '');
      if (!text) return '';
      const cls = origin === 'leisure' ? 'chat-origin-leisure'
        : origin === 'story' ? 'chat-origin-story' : 'chat-origin-multiplayer';
      /* 类名用 shared-lobby-chat.css 认的 chat-origin-prefix（此前写成 chat-origin-badge，
         没有任何样式——[休闲] 前缀的紫色一直没生效，迁移后才被发现） */
      return `<span class="chat-origin-prefix ${cls}">[${escapeHtml(text)}]</span>`;
    }

    function titlesHtml(item) {
      const titles = Array.isArray(item && item.equipped_titles) ? item.equipped_titles : [];
      return titles.slice(0, 3).map((title) => {
        const name = String((title && title.name) || '').trim();
        if (!name) return '';
        const color = titleColorCss(title.color);
        return `<span class="player-title-inline"${color ? ` style="color:${color}"` : ''}>[${escapeHtml(name)}]</span>`;
      }).join('');
    }

    function reputationHtml(item) {
      const names = labels();
      const profile = (item && item.reputation_profile) || null;
      const newcomer = profile && profile.newcomer && profile.newcomer.is_newcomer === true
        ? `<span class="reputation-badge newcomer-badge">${escapeHtml(names.newcomer || '新人')}</span>` : '';
      const level = String((profile && profile.level) || '');
      if (!['yellow', 'orange', 'red'].includes(level)) return newcomer;
      return newcomer
        + `<span class="reputation-badge reputation-${level}">${escapeHtml(names.lowReputation || '低信誉')}</span>`;
    }

    function mentionHtml(item) {
      let out = escapeHtml((item && item.text) || '');
      const mentions = Array.isArray(item && item.mentions) ? item.mentions : [];
      const ownUserId = options.userId != null ? String(options.userId) : '';
      mentions.slice(0, 8).forEach((mention) => {
        const name = escapeHtml((mention && mention.nickname) || '');
        if (!name) return;
        const token = `@${name}`;
        const isSelf = !!ownUserId && mention && mention.user_id != null
          && String(mention.user_id) === ownUserId;
        out = out.split(token).join(`<span class="chat-mention-token${isSelf ? ' mention-self' : ''}">${token}</span>`);
      });
      return out;
    }

    function actionsHtml(item) {
      if (typeof actions.chatActionButtonsHtml !== 'function') return '';
      return actions.chatActionButtonsHtml(item, { role: String(options.chatRole || 'player').toLowerCase(), user_id: options.userId }, labels());
    }

    /* 撤回占位文本：统一走 shared-chat-actions 的 GtnChatRecall。 */
    function recallText(item) {
      const recallApi = window.GtnChatRecall;
      if (recallApi && typeof recallApi.placeholderText === 'function') {
        return recallApi.placeholderText(item || {}, recallApi.labels());
      }
      return `${String((item && item.nickname) || '?')}撤回了一条消息`;
    }

    function lineHtml(item) {
      if (!item) return '';
      if (item.type === 'time') {
        const label = escapeHtml(String(item.display_time || '').trim());
        return label ? `<div class="chat-time-separator">${label}</div>` : '';
      }
      if (item.recalled) {
        // 撤回占位：显示在消息原位（服务端历史带回 recalled 标记，刷新不消失）。
        const recalledId = Number(item.message_id || item.messageId || 0);
        return `<div class="chat-msg chat-recall-entry"${recalledId > 0 ? ` data-chat-message-id="${recalledId}"` : ''}>`
          + `${escapeHtml(recallText(item))}</div>`;
      }
      const names = labels();
      const system = !!item.system;
      const name = escapeHtml(String(item.nickname || '').trim());
      const spectator = item.is_spectator
        ? `<span class="chat-spectator-prefix">[${escapeHtml(names.spectator || '观战')}]</span>` : '';
      const consolePrefix = (!system && (item.console_player || item.special_role === 'console'))
        ? `<span class="player-title-inline">[${escapeHtml(names.console || '控制台')}]</span>` : '';
      const head = system
        ? `${name || `[${escapeHtml(names.system || '系统')}]`} `
        : spectator + '<span class="chat-player-name">' + reputationHtml(item) + consolePrefix
          + titlesHtml(item) + nameHtml(item, name || '?') + '</span>: ';
      const messageId = Number(item.message_id || item.messageId || 0);
      return `<div class="chat-msg"${messageId > 0 ? ` data-chat-message-id="${messageId}"` : ''}>`
        + `<span class="chat-nick${system ? ' system-name' : ''}">${originBadgeHtml(item)}${head}</span>`
        + mentionHtml(item) + actionsHtml(item) + '</div>';
    }

    function remember(item) {
      const id = Number((item && (item.message_id || item.messageId)) || 0);
      if (Number.isFinite(id) && id > 0) entriesById.set(id, item);
    }

    /* 服务端消息的标识字段是 message_id（GB-204：append 守卫与 render 游标
       此前误读 item.id——服务端没有这个字段，游标恒为 0（死代码）、
       重复投递的单条消息每条都计未读，红点曾炸到几十条）。 */
    const messageKey = (item) => Number((item && (item.message_id || item.messageId)) || 0);

    function updateUnreadBadge() {
      const badge = els(options.unreadId);
      if (!badge) return;
      const count = Math.max(0, Number(unread) || 0);
      badge.hidden = count <= 0;
      badge.textContent = count > 99 ? '99+' : String(count);
      badge.setAttribute('aria-label', count > 0 ? `${count} 条未读消息` : '没有未读消息');
    }

    function clearUnread() {
      if (!unread) return;
      unread = 0;
      updateUnreadBadge();
    }

    /* 滑动进度缓存（反馈：每次打开聊天都翻回顶部）。面板隐藏时 display:none 会让
       scrollTop 归零，隐藏状态下的 render/append 也不能写滚动（scrollHeight=0）。
       规则：收起时记下位置、打开时恢复；面板可见且贴底时新消息跟随到底；
       可见且在往上翻时重渲染保持原位，不被新消息拽走。 */
    let savedScrollTop = null;

    function chatPanelOpen() {
      const panel = els(options.panelId);
      return !!(panel && !panel.hidden);
    }

    function chatNearBottom(log) {
      return log.scrollHeight - log.scrollTop - log.clientHeight <= 40;
    }

    function append(item) {
      const log = els(options.logId);
      if (!log || !item) return;
      /* 重连/重进时服务端可能重发已见过的消息：按 id 去重（GB-204：重复投递
         曾把未读红点炸到几十条）。render 路径本就有游标去重，这里补单条路径。 */
      const itemId = messageKey(item);
      if (Number.isFinite(itemId) && itemId > 0 && entriesById.has(itemId)) return;
      if (log.querySelector('p.mg-hint')) log.innerHTML = '';
      remember(item);
      /* 游标跟着已展示的消息走：这条消息若随后又随整段历史（render）到达，
         不会在两条路径各计一次未读。 */
      if (itemId > unreadCursor) unreadCursor = itemId;
      const open = chatPanelOpen();
      const pin = open && chatNearBottom(log);
      log.insertAdjacentHTML('beforeend', lineHtml(item));
      if (pin) log.scrollTop = log.scrollHeight;
      /* 面板收起时收到别人的消息自动计未读（红点在 toggle 打开时清零） */
      if (!open) markUnread(item);
    }

    function render(items) {
      const log = els(options.logId);
      if (!log) return;
      const list = (Array.isArray(items) ? items : []).slice(-200);
      const html = [];
      list.forEach((item, index) => {
        if (item && item.type === 'time') {
          const next = list[index + 1];
          if (!next || next.type === 'time') return;
        }
        remember(item);
        html.push(lineHtml(item));
      });
      const openNow = chatPanelOpen();
      const wasNearBottom = openNow ? chatNearBottom(log) : false;
      const prevTop = openNow ? log.scrollTop : 0;
      log.innerHTML = html.filter(Boolean).join('') || options.emptyHtml;
      if (openNow) {
        log.scrollTop = (wasNearBottom || savedScrollTop === null)
          ? log.scrollHeight
          : prevTop;
      }
      // 未读按消息 id 计：首屏只记游标，之后新增（且面板收起）的才算未读
      const rows = list;
      const maxId = rows.reduce((max, item) => Math.max(max, messageKey(item)), 0);
      if (!unreadCursorReady) {
        unreadCursorReady = true;
        unreadCursor = maxId;
        return;
      }
      if (maxId <= unreadCursor) return;
      const panel = els(options.panelId);
      if (!panel || panel.hidden) {
        rows.forEach((item) => {
          if (!item || item.type === 'time' || item.system) return;
          if (messageKey(item) <= unreadCursor) return;
          if (isOwn(item)) return;
          unread += 1;
        });
        updateUnreadBadge();
      }
      unreadCursor = maxId;
    }

    function markUnread(item) {
      if (!item || item.type === 'time' || item.system || isOwn(item)) return;
      unread += 1;
      updateUnreadBadge();
    }

    /* 有人撤回消息：对应行原位变成占位提示（不再删行、不在底部新增）。 */
    function recall(payload) {
      const log = els(options.logId);
      if (!log) return;
      const ids = (((payload || {}).message_ids) || [])
        .map((value) => Number(value) || 0)
        .filter((value) => value > 0);
      const pin = chatPanelOpen() && chatNearBottom(log);
      ids.forEach((id) => {
        const item = entriesById.get(id);
        const fallback = {
          nickname: String((payload || {}).target_name || ''),
          recalled_by: String((payload || {}).actor_name || ''),
          self_recall: (payload || {}).self_recall,
        };
        if (item && window.GtnChatRecall
            && typeof window.GtnChatRecall.markEntryRecalled === 'function') {
          window.GtnChatRecall.markEntryRecalled(item, payload || {});
        }
        const row = log.querySelector(`.chat-msg[data-chat-message-id="${id}"]`);
        if (row) {
          row.classList.add('chat-recall-entry');
          row.textContent = recallText(item || fallback);
        }
      });
      if (pin) log.scrollTop = log.scrollHeight;
    }

    function toggle(force) {
      const panel = els(options.panelId);
      const toggleBtn = els(options.toggleId);
      if (!panel) return;
      const open = force === undefined ? panel.hidden : !!force;
      if (!open) {
        const log = els(options.logId);
        if (log) savedScrollTop = log.scrollTop;   // 收起：记下滑动进度
      }
      panel.hidden = !open;
      if (toggleBtn) toggleBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (open) {
        clearUnread();
        const log = els(options.logId);
        if (log) {
          // 打开：恢复上次的滑动进度；从未记录（首次）则贴底。
          // 重显后先读一次 scrollHeight 强制布局，scrollTop 才写得进去。
          log.scrollTop = savedScrollTop === null
            ? log.scrollHeight
            : Math.max(0, Math.min(savedScrollTop, log.scrollHeight));
        }
        const input = els(options.inputId);
        if (input) input.focus();
      }
    }

    function send() {
      const input = els(options.inputId);
      if (!input || !options.socket) return;
      const text = input.value.trim();
      if (!text) return;
      options.socket.emit('chat', { text });
      input.value = '';
    }

    /* 举报 / 撤回按钮是渲染进 HTML 字符串的，用事件委托按消息 id 找回来。
       按钮由 chatActionButtonsHtml 渲染，选择器跟着它的类名/数据属性走
       （.report-inline-btn[data-chat-report] / .chat-recall-btn[data-chat-recall]）——
       此前这里找的是不存在的 [data-chat-action]，两个按钮在小游戏页点了都没反应；
       参数签名也要对齐 shared-chat-actions：举报 (entry, labels)，
       撤回 (entry, {socket, labels, confirm})。 */
    function bindActions() {
      const log = els(options.logId);
      if (!log || typeof actions.chatActionButtonsHtml !== 'function') return;
      log.addEventListener('click', (event) => {
        const reportBtn = event.target.closest('.report-inline-btn[data-chat-report]');
        if (reportBtn) {
          event.preventDefault();
          const id = Number(reportBtn.dataset.chatReport || 0);
          const item = entriesById.get(id) || {};
          if (typeof actions.openChatReportDialog === 'function') {
            void actions.openChatReportDialog(item, labels());
          }
          return;
        }
        const recallBtn = event.target.closest('.chat-recall-btn[data-chat-recall]');
        if (recallBtn) {
          event.preventDefault();
          const id = Number(recallBtn.dataset.chatRecall || 0);
          const item = entriesById.get(id) || {};
          if (typeof actions.confirmChatRecall === 'function') {
            /* 行的移除等 chat_recall 广播（recall()）来做：用户取消确认时不能提前删 */
            actions.confirmChatRecall(item, {
              socket: options.socket,
              labels: labels(),
              confirm: options.confirmRecall,
            });
          }
        }
      });
    }

    function bind() {
      const toggleBtn = els(options.toggleId);
      if (toggleBtn) toggleBtn.addEventListener('click', () => toggle());
      const closeBtn = els(options.closeId);
      if (closeBtn) closeBtn.addEventListener('click', () => toggle(false));
      const form = els(options.formId);
      if (form) form.addEventListener('submit', (event) => { event.preventDefault(); send(); });
      bindActions();
    }

    bind();
    return { render, append, recall, toggle, send, markUnread, lineHtml, clearUnread };
  }

  window.GtnMinigameChat = { attach };
})();
