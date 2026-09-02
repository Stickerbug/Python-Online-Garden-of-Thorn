(() => {
  'use strict';

  const state = {
    feed: null,
    csrfToken: '',
    loadPromise: null,
    votePromise: null,
    epoch: 0,
  };
  const ANNOUNCEMENT_READ_KEY = 'gtn_community_announcement_reads_v1';
  const announcementReadMemory = new Set();

  const byId = (id) => document.getElementById(id);

  function announcementStorageKey() {
    if (typeof window.gtnBetaStorageKey === 'function') {
      return String(window.gtnBetaStorageKey(ANNOUNCEMENT_READ_KEY));
    }
    return ANNOUNCEMENT_READ_KEY;
  }

  function announcementReceipt(item) {
    const id = Number(item?.id || 0);
    if (!Number.isInteger(id) || id <= 0) return '';
    const publishedAt = String(item?.published_at || item?.starts_at || '');
    return `${id}:${publishedAt}`;
  }

  function readAnnouncementReceipts() {
    const receipts = new Set(announcementReadMemory);
    const key = announcementStorageKey();
    ['localStorage', 'sessionStorage'].forEach((name) => {
      try {
        const storage = window[name];
        const values = JSON.parse(storage.getItem(key) || '[]');
        if (Array.isArray(values)) values.forEach((value) => receipts.add(String(value || '')));
      } catch (_) {}
    });
    receipts.delete('');
    return receipts;
  }

  function writeAnnouncementReceipts(receipts) {
    const values = Array.from(receipts).filter(Boolean).slice(-120);
    announcementReadMemory.clear();
    values.forEach((value) => announcementReadMemory.add(value));
    const serialized = JSON.stringify(values);
    const key = announcementStorageKey();
    ['localStorage', 'sessionStorage'].forEach((name) => {
      try { window[name].setItem(key, serialized); } catch (_) {}
    });
  }

  function currentAnnouncementReceipts() {
    const items = Array.isArray(state.feed?.announcements) ? state.feed.announcements : [];
    return items.map(announcementReceipt).filter(Boolean);
  }

  function updateAnnouncementBadge() {
    const button = byId('btn-community-top');
    if (!button) return;
    const read = readAnnouncementReceipts();
    const hasUnread = currentAnnouncementReceipts().some((receipt) => !read.has(receipt));
    button.classList.toggle('has-unread', hasUnread);
    button.setAttribute('aria-label', hasUnread ? '公告与投票（有新公告）' : '公告与投票');
  }

  function markAnnouncementsRead() {
    const receipts = readAnnouncementReceipts();
    currentAnnouncementReceipts().forEach((receipt) => receipts.add(receipt));
    writeAnnouncementReceipts(receipts);
    updateAnnouncementBadge();
  }

  function isCommunityPopoverOpen() {
    const popover = byId('community-popover');
    return Boolean(popover && !popover.classList.contains('hidden'));
  }

  function setStatus(message, kind = '') {
    const node = byId('community-status');
    if (!node) return;
    node.textContent = String(message || '');
    node.className = `community-status ${kind ? `is-${kind}` : 'muted'}`;
  }

  function formatTime(value) {
    const date = new Date(String(value || ''));
    if (Number.isNaN(date.getTime())) return String(value || '');
    try {
      return new Intl.DateTimeFormat(document.documentElement.lang || 'zh-CN', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }).format(date);
    } catch (_) {
      return String(value || '');
    }
  }

  function createElement(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text);
    return node;
  }

  function renderAnnouncement(item) {
    const article = createElement('article', 'community-card community-announcement');
    const heading = createElement('div', 'community-card-heading');
    const title = createElement('h3', '', item.title || '公告');
    heading.appendChild(title);
    if (item.pinned) heading.appendChild(createElement('span', 'community-badge is-pinned', '置顶'));
    article.appendChild(heading);
    article.appendChild(createElement('p', 'community-card-body', item.body || ''));
    article.appendChild(createElement('div', 'community-card-meta', `发布于 ${formatTime(item.starts_at)}`));
    return article;
  }

  function renderPoll(item) {
    const article = createElement('article', 'community-card community-poll');
    const heading = createElement('div', 'community-card-heading');
    heading.appendChild(createElement('h3', '', item.question || '投票'));
    if (item.reminder_due) heading.appendChild(createElement('span', 'community-badge is-reminder', '即将截止'));
    if (item.effective_state === 'closed') heading.appendChild(createElement('span', 'community-badge', '已结束'));
    article.appendChild(heading);

    const options = createElement('div', 'community-poll-options');
    const totalVotes = Number(item.total_votes || 0);
    (Array.isArray(item.options) ? item.options : []).forEach((option) => {
      const selected = Number(item.selected_option_id) === Number(option.id);
      const button = createElement('button', `community-poll-option${selected ? ' is-selected' : ''}`);
      button.type = 'button';
      button.dataset.pollId = String(item.id);
      button.dataset.optionId = String(option.id);
      const label = createElement('span', 'community-option-label', option.label || '');
      button.appendChild(label);
      if (item.effective_state === 'closed') {
        const count = Number(option.vote_count || 0);
        const percent = totalVotes > 0 ? Math.round((count / totalVotes) * 100) : 0;
        button.appendChild(createElement('span', 'community-option-count', `${count}票 · ${percent}%`));
        button.disabled = true;
      } else if (selected) {
        button.appendChild(createElement('span', 'community-option-count', '已选择'));
        button.disabled = true;
      } else {
        button.disabled = !item.can_vote || Boolean(state.votePromise);
      }
      options.appendChild(button);
    });
    article.appendChild(options);

    let footer = `截止 ${formatTime(item.ends_at)}`;
    if (item.effective_state === 'closed') footer += ` · 共 ${totalVotes} 票`;
    else if (!state.feed?.viewer?.authenticated) footer += ' · 登录后可投票';
    else if (item.selected_option_id) footer += ' · 投票后不可改票';
    article.appendChild(createElement('div', 'community-card-meta', footer));
    return article;
  }

  function renderFeed() {
    const feed = byId('community-feed');
    if (!feed) return;
    feed.textContent = '';
    const announcements = Array.isArray(state.feed?.announcements) ? state.feed.announcements : [];
    const polls = Array.isArray(state.feed?.polls) ? state.feed.polls : [];
    if (!announcements.length && !polls.length) {
      feed.appendChild(createElement('p', 'community-empty muted', '目前没有正在展示的公告或投票。'));
    } else {
      announcements.forEach((item) => feed.appendChild(renderAnnouncement(item)));
      polls.forEach((item) => feed.appendChild(renderPoll(item)));
    }
    const manage = byId('community-manage-link');
    if (manage) manage.classList.toggle('hidden', !state.feed?.viewer?.can_manage);
  }

  async function requestJson(url, options = {}) {
    const response = await fetch(url, {
      credentials: 'same-origin',
      cache: 'no-store',
      ...options,
    });
    let payload = null;
    try {
      payload = await response.json();
    } catch (_) {
      payload = {};
    }
    if (!response.ok || !payload?.success) {
      const error = new Error(String(payload?.error || `请求失败（${response.status}）`));
      error.status = response.status;
      error.code = payload?.code || '';
      throw error;
    }
    return payload;
  }

  async function loadFeed({ silent = false } = {}) {
    if (state.loadPromise) return state.loadPromise;
    const epoch = state.epoch;
    if (!silent) setStatus('正在加载…');
    const promise = requestJson('/api/community/feed')
      .then((payload) => {
        if (epoch !== state.epoch) return;
        state.feed = payload;
        state.csrfToken = String(payload.csrf_token || '');
        renderFeed();
        updateAnnouncementBadge();
        if (isCommunityPopoverOpen()) markAnnouncementsRead();
        if (!silent) setStatus('');
      })
      .catch((error) => {
        if (epoch !== state.epoch) return;
        if (!silent) setStatus(error.message || '公告加载失败', 'error');
      })
      .finally(() => {
        if (state.loadPromise === promise) state.loadPromise = null;
      });
    state.loadPromise = promise;
    return promise;
  }

  async function vote(pollId, optionId) {
    if (state.votePromise) return;
    if (!state.csrfToken) {
      setStatus('请先登录账号再投票。', 'error');
      return;
    }
    renderFeed();
    setStatus('正在提交投票…');
    const epoch = state.epoch;
    const promise = requestJson(`/api/community/polls/${encodeURIComponent(pollId)}/vote`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Community-CSRF': state.csrfToken,
      },
      body: JSON.stringify({ option_id: Number(optionId) }),
    })
      .then((payload) => {
        if (epoch !== state.epoch) return;
        const polls = Array.isArray(state.feed?.polls) ? state.feed.polls : [];
        const index = polls.findIndex((item) => Number(item.id) === Number(payload.poll?.id));
        if (index >= 0) polls.splice(index, 1, payload.poll);
        renderFeed();
        setStatus(payload.duplicate ? '该选择此前已提交。' : '投票已提交，选择不可更改。', 'success');
      })
      .catch((error) => {
        if (epoch !== state.epoch) return;
        setStatus(error.message || '投票提交失败', 'error');
      })
      .finally(() => {
        if (state.votePromise === promise) state.votePromise = null;
        if (epoch === state.epoch) renderFeed();
      });
    state.votePromise = promise;
    renderFeed();
    await promise;
  }

  function closePopover() {
    const popover = byId('community-popover');
    if (!popover) return;
    popover.classList.add('hidden');
    state.epoch += 1;
  }

  function openPopover() {
    const popover = byId('community-popover');
    if (!popover) return;
    document.querySelectorAll('.account-popover:not(#community-popover)').forEach((node) => node.classList.add('hidden'));
    state.epoch += 1;
    popover.classList.remove('hidden');
    loadFeed();
  }

  function togglePopover() {
    const popover = byId('community-popover');
    if (!popover || popover.classList.contains('hidden')) openPopover();
    else closePopover();
  }

  document.addEventListener('DOMContentLoaded', () => {
    byId('btn-community-top')?.addEventListener('click', togglePopover);
    byId('btn-community-close')?.addEventListener('click', closePopover);
    byId('btn-community-refresh')?.addEventListener('click', () => loadFeed());
    byId('community-feed')?.addEventListener('click', (event) => {
      const button = event.target.closest('[data-poll-id][data-option-id]');
      if (!button || button.disabled) return;
      vote(button.dataset.pollId, button.dataset.optionId);
    });
    document.addEventListener('click', (event) => {
      const otherTopButton = event.target.closest('.top-icon-btn:not(#btn-community-top)');
      if (otherTopButton) closePopover();
    }, true);
    document.addEventListener('keydown', (event) => {
      if (event.key !== 'Escape' || byId('community-popover')?.classList.contains('hidden')) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      closePopover();
      byId('btn-community-top')?.focus();
    }, true);
    updateAnnouncementBadge();
    loadFeed({ silent: true });
    window.setInterval(() => {
      if (document.visibilityState === 'visible') loadFeed({ silent: true });
    }, 60000);
    window.addEventListener('focus', () => loadFeed({ silent: true }));
  });

  window.toggleCommunityPopover = (force) => {
    if (force === true) openPopover();
    else if (force === false) closePopover();
    else togglePopover();
  };
})();
