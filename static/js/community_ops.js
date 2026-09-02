(() => {
  'use strict';

  const state = {
    workspace: null,
    csrfToken: '',
    loading: false,
    mutating: false,
  };

  const byId = (id) => document.getElementById(id);

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text);
    return node;
  }

  function setStatus(message, kind = '') {
    const node = byId('ops-status');
    if (!node) return;
    node.textContent = String(message || '');
    node.className = `ops-status${kind ? ` is-${kind}` : ''}`;
  }

  function formatTime(value) {
    const date = new Date(String(value || ''));
    if (Number.isNaN(date.getTime())) return String(value || '—');
    return new Intl.DateTimeFormat('zh-CN', {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    }).format(date);
  }

  function localDateToIso(value) {
    const raw = String(value || '').trim();
    if (!raw) return null;
    const date = new Date(raw);
    if (Number.isNaN(date.getTime())) throw new Error('时间格式无效');
    return date.toISOString();
  }

  async function requestJson(url, options = {}) {
    const headers = { ...(options.headers || {}) };
    if (options.method && options.method !== 'GET') {
      headers['Content-Type'] = 'application/json';
      headers['X-Community-Ops-CSRF'] = state.csrfToken;
    }
    const response = await fetch(url, {
      credentials: 'same-origin',
      cache: 'no-store',
      ...options,
      headers,
    });
    let payload = null;
    try { payload = await response.json(); } catch (_) { payload = {}; }
    if (!response.ok || !payload?.success) {
      const error = new Error(String(payload?.error || `请求失败（${response.status}）`));
      error.status = response.status;
      error.code = payload?.code || '';
      throw error;
    }
    return payload;
  }

  function actionButton(label, objectType, objectId, action, danger = false) {
    const button = element('button', `ops-button is-secondary${danger ? ' is-danger' : ''}`, label);
    button.type = 'button';
    button.dataset.objectType = objectType;
    button.dataset.objectId = String(objectId);
    button.dataset.action = action;
    button.disabled = state.mutating;
    return button;
  }

  function emptyList(list, message) {
    list.textContent = '';
    list.appendChild(element('div', 'ops-empty', message));
  }

  function renderAnnouncements() {
    const list = byId('announcement-list');
    const items = Array.isArray(state.workspace?.announcements) ? state.workspace.announcements : [];
    byId('announcement-count').textContent = String(items.length);
    if (!items.length) return emptyList(list, '尚无公告。');
    list.textContent = '';
    items.forEach((item) => {
      const card = element('article', 'ops-item');
      const head = element('div', 'ops-item-head');
      head.appendChild(element('h3', 'ops-item-title', `#${item.id} ${item.title || ''}`));
      head.appendChild(element('span', 'ops-item-state', `${item.state}${item.pinned ? ' · 置顶' : ''}`));
      card.appendChild(head);
      card.appendChild(element('p', 'ops-item-body', item.body || ''));
      card.appendChild(element('div', 'ops-item-meta', `开始 ${formatTime(item.starts_at)} · 结束 ${item.ends_at ? formatTime(item.ends_at) : '长期'} · 更新 ${formatTime(item.updated_at)}`));
      const actions = element('div', 'ops-item-actions');
      if (item.state === 'draft') actions.appendChild(actionButton('发布', 'announcement', item.id, 'publish'));
      if (item.state === 'published') actions.appendChild(actionButton('撤回', 'announcement', item.id, 'retract', true));
      if (item.state !== 'retracted') actions.appendChild(actionButton(item.pinned ? '取消置顶' : '置顶', 'announcement', item.id, item.pinned ? 'unpin' : 'pin'));
      card.appendChild(actions);
      list.appendChild(card);
    });
  }

  function renderPolls() {
    const list = byId('poll-list');
    const items = Array.isArray(state.workspace?.polls) ? state.workspace.polls : [];
    byId('poll-count').textContent = String(items.length);
    if (!items.length) return emptyList(list, '尚无投票。');
    list.textContent = '';
    items.forEach((item) => {
      const card = element('article', 'ops-item');
      const head = element('div', 'ops-item-head');
      head.appendChild(element('h3', 'ops-item-title', `#${item.id} ${item.question || ''}`));
      head.appendChild(element('span', 'ops-item-state', item.effective_state || item.state));
      card.appendChild(head);
      const options = element('ol', 'ops-option-list');
      (Array.isArray(item.options) ? item.options : []).forEach((option) => {
        options.appendChild(element('li', '', `${option.label || ''} · ${Number(option.vote_count || 0)}票`));
      });
      card.appendChild(options);
      card.appendChild(element('div', 'ops-item-meta', `开始 ${formatTime(item.starts_at)} · 截止 ${formatTime(item.ends_at)} · 共 ${Number(item.total_votes || 0)}票 · 提醒窗口 ${item.reminder_hours}小时`));
      const actions = element('div', 'ops-item-actions');
      if (item.state === 'draft') actions.appendChild(actionButton('发布', 'poll', item.id, 'publish'));
      if (item.state === 'published' && item.effective_state !== 'closed') actions.appendChild(actionButton('立即结束', 'poll', item.id, 'close', true));
      if (!['closed', 'retracted'].includes(item.state)) actions.appendChild(actionButton('撤回', 'poll', item.id, 'retract', true));
      card.appendChild(actions);
      list.appendChild(card);
    });
  }

  function renderAudit() {
    const list = byId('audit-list');
    const items = Array.isArray(state.workspace?.audit) ? state.workspace.audit : [];
    byId('audit-count').textContent = String(items.length);
    if (!items.length) return emptyList(list, '尚无操作记录。');
    list.textContent = '';
    items.forEach((item) => {
      const card = element('article', 'ops-item');
      card.appendChild(element('h3', 'ops-item-title', `${item.action || '操作'} · ${item.object_type || ''} #${item.object_id || ''}`));
      card.appendChild(element('div', 'ops-item-meta', `${item.actor_username || 'unknown'} (${item.actor_role || '-'}) · ${formatTime(item.created_at)}`));
      const detail = item.detail && typeof item.detail === 'object' ? JSON.stringify(item.detail) : '';
      if (detail && detail !== '{}') card.appendChild(element('div', 'ops-item-meta', detail));
      list.appendChild(card);
    });
  }

  function renderWorkspace() {
    renderAnnouncements();
    renderPolls();
    renderAudit();
    document.querySelectorAll('form input, form textarea, form button').forEach((node) => {
      node.disabled = state.loading || state.mutating;
    });
  }

  async function loadWorkspace({ quiet = false } = {}) {
    if (state.loading) return;
    state.loading = true;
    if (!quiet) setStatus('正在加载运营数据…');
    renderWorkspace();
    try {
      const payload = await requestJson('/api/community/ops/workspace');
      state.workspace = payload.workspace || {};
      state.csrfToken = String(payload.csrf_token || '');
      setStatus(`已刷新 · 服务器时间 ${formatTime(state.workspace.server_time)}`, 'success');
    } catch (error) {
      setStatus(error.message || '运营数据加载失败', 'error');
    } finally {
      state.loading = false;
      renderWorkspace();
    }
  }

  async function mutate(url, body, successMessage) {
    if (state.mutating) return;
    state.mutating = true;
    setStatus('正在保存…');
    renderWorkspace();
    try {
      await requestJson(url, { method: 'POST', body: JSON.stringify(body) });
      await loadWorkspace({ quiet: true });
      setStatus(successMessage, 'success');
    } catch (error) {
      if (error.code === 'CSRF_FAILED') state.csrfToken = '';
      setStatus(error.message || '保存失败', 'error');
    } finally {
      state.mutating = false;
      renderWorkspace();
    }
  }

  function actionNeedsConfirmation(type, action) {
    return action === 'retract' || action === 'close';
  }

  function handleListAction(event) {
    const button = event.target.closest('[data-object-type][data-object-id][data-action]');
    if (!button || state.mutating) return;
    const type = button.dataset.objectType;
    const id = button.dataset.objectId;
    const action = button.dataset.action;
    if (actionNeedsConfirmation(type, action) && !window.confirm(`确认执行 ${action}？`)) return;
    if (type === 'announcement') {
      mutate(`/api/community/ops/announcements/${encodeURIComponent(id)}/action`, { action }, `公告 #${id} 已更新。`);
    } else if (type === 'poll') {
      mutate(`/api/community/ops/polls/${encodeURIComponent(id)}/action`, { action }, `投票 #${id} 已更新。`);
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    byId('ops-refresh')?.addEventListener('click', () => loadWorkspace());
    byId('announcement-list')?.addEventListener('click', handleListAction);
    byId('poll-list')?.addEventListener('click', handleListAction);

    byId('announcement-create-form')?.addEventListener('submit', (event) => {
      event.preventDefault();
      let startsAt;
      let endsAt;
      try {
        startsAt = localDateToIso(byId('announcement-start').value);
        endsAt = localDateToIso(byId('announcement-end').value);
      } catch (error) {
        setStatus(error.message, 'error');
        return;
      }
      mutate('/api/community/ops/announcements', {
        title: byId('announcement-title').value,
        body: byId('announcement-body').value,
        starts_at: startsAt,
        ends_at: endsAt,
        pinned: byId('announcement-pinned').checked,
        publish: byId('announcement-publish').checked,
      }, '公告已创建。').then(() => {
        if (!state.mutating && !byId('ops-status').classList.contains('is-error')) byId('announcement-create-form').reset();
      });
    });

    byId('poll-create-form')?.addEventListener('submit', (event) => {
      event.preventDefault();
      const options = byId('poll-options').value.split(/\r?\n/).map((value) => value.trim()).filter(Boolean);
      let startsAt;
      let endsAt;
      try {
        startsAt = localDateToIso(byId('poll-start').value);
        endsAt = localDateToIso(byId('poll-end').value);
      } catch (error) {
        setStatus(error.message, 'error');
        return;
      }
      mutate('/api/community/ops/polls', {
        question: byId('poll-question').value,
        options,
        starts_at: startsAt,
        ends_at: endsAt,
        reminder_hours: Number(byId('poll-reminder').value),
        publish: byId('poll-publish').checked,
      }, '投票已创建。').then(() => {
        if (!state.mutating && !byId('ops-status').classList.contains('is-error')) byId('poll-create-form').reset();
      });
    });

    loadWorkspace();
  });
})();
