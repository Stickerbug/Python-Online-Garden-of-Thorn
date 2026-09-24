(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const esc = (v) => String(v == null ? '' : v).replace(/[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  function renderStatus(data) {
    $('bind-loading').hidden = true;
    $('bind-body').hidden = false;
    $('bind-code').textContent = data.bind_code || '';
    const go = document.getElementById('afdian-go');
    if (go) {
      if (data.page_url) { go.href = data.page_url; go.hidden = false; }
      else go.hidden = true;
    }
    const plans = data.plans || [];
    if (plans.length) {
      const hasMonthly = plans.some((p) => p.kind === 'plan');
      $('plans').innerHTML = '<table><tr><th>档位</th><th>价格</th><th>兑换</th></tr>' +
        plans.map((p) => `<tr><td>${esc(p.name || p.plan_id)}</td>` +
          `<td>${p.price ? '¥' + esc(p.price) : '—'}</td>` +
          `<td><b>${esc(p.dew_amount)}</b> 荆露${p.kind === 'plan' ? '/月' : ''}</td></tr>`).join('') +
        '</table>' + (hasMonthly ? '<p class="note">按月订阅一次买多个月的，按月数累计兑换。</p>' : '');
    } else {
      $('plans').innerHTML = '';
    }
    $('plans-note').hidden = plans.length > 0;
    renderOrders(data.orders || []);
  }

  function renderOrders(orders) {
    const box = $('orders');
    if (!orders.length) {
      box.innerHTML = '<div class="empty">还没有赞助记录</div>';
      return;
    }
    box.innerHTML = '<table><tr><th>时间</th><th>档位</th><th>荆露</th><th>状态</th></tr>' +
      orders.map((o) => {
        const cls = o.status === 'credited' || o.status === 'manual' ? 'ok' : 'warn';
        return `<tr><td class="muted">${esc(String(o.created_at || '').replace('T', ' ').slice(0, 16))}</td>` +
          `<td>${esc(o.plan_name || '')}${Number(o.month || 1) > 1 ? ' ×' + esc(o.month) : ''}</td>` +
          `<td>${o.dew_amount ? '+' + esc(o.dew_amount) : '—'}</td>` +
          `<td class="${cls}">${esc(o.status_text || o.status)}</td></tr>`;
      }).join('') + '</table>';
  }

  async function load() {
    try {
      const r = await fetch('/api/afdian/status', { credentials: 'same-origin' });
      if (r.status === 401) {
        $('bind-loading').hidden = true;
        $('login-hint').hidden = false;
        $('plans').textContent = '登录后可见。';
        $('orders').textContent = '登录后可见。';
        return;
      }
      const data = await r.json();
      if (data.success) renderStatus(data);
      else $('bind-loading').textContent = data.error || '加载失败';
    } catch (_) {
      $('bind-loading').textContent = '网络不可用，稍后重试。';
    }
  }

  $('copy').addEventListener('click', async () => {
    const code = $('bind-code').textContent;
    try { await navigator.clipboard.writeText(code); $('msg').textContent = '已复制绑定码'; }
    catch (_) { $('msg').textContent = '复制失败，请手动选择复制'; }
    setTimeout(() => { $('msg').textContent = ''; }, 2500);
  });

  $('reset').addEventListener('click', async () => {
    if (!window.confirm('重置后旧绑定码立即失效，确定？')) return;
    try {
      const r = await fetch('/api/afdian/bind/reset', { method: 'POST', credentials: 'same-origin' });
      const data = await r.json();
      if (data.success) $('bind-code').textContent = data.bind_code;
      else $('msg').textContent = data.error || '重置失败';
    } catch (_) { $('msg').textContent = '网络不可用'; }
  });

  $('requery').addEventListener('click', async () => {
    $('msg').textContent = '查询中…';
    $('requery').disabled = true;
    try {
      const r = await fetch('/api/afdian/requery', { method: 'POST', credentials: 'same-origin' });
      const data = await r.json();
      if (data.success) {
        renderOrders(data.orders || []);
        $('msg').textContent = '已向爱发电核对最近订单';
      } else {
        $('msg').textContent = data.error || '查询失败';
      }
    } catch (_) { $('msg').textContent = '网络不可用'; }
    $('requery').disabled = false;
  });

  load();
})();
