/* 休闲花园门票门 + 10 分钟游玩期计时（2048 页共用逻辑，也挂到 window 给 suika 页复用）。
   服务端是权威：/api/leisure/ticket/* 三个接口；客户端只做门禁 UI 和倒计时显示。 */

(function () {
  'use strict';

  const WARN_THRESHOLDS = [30, 10];   // 剩余秒数提示点（每档只提示一次）
  let timerHandle = null;
  let warned = new Set();
  let settled = false;
  let ticketMode = false;            // 本次进入走的是门票（免费时段不需要暂停/恢复）

  /* 反馈 #371：切走/关页时暂停倒计时（keepalive 信标），切回时静默恢复。
     服务端本就有 pause/resume，此前客户端从未调用——10 分钟按墙钟硬烧，
     玩家中途离开回来不是时间没了就是重进被多扣一张票。 */
  function pauseBeacon() {
    if (!ticketMode || settled) return;
    try {
      fetch('/api/leisure/ticket/leave', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
        keepalive: true,
      }).catch(() => {});
    } catch (_) { /* 忽略：无会话时服务端本来也是 no-op */ }
  }

  function resumeAfterHidden() {
    if (!ticketMode || settled) return;
    try {
      fetch('/api/leisure/ticket/enter', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resume_only: true }),
      }).catch(() => {});
    } catch (_) { /* 忽略 */ }
  }

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) pauseBeacon();
    else resumeAfterHidden();
  });
  window.addEventListener('pagehide', pauseBeacon);

  function banner() {
    let el = document.getElementById('leisure-timer-banner');
    if (!el) {
      el = document.createElement('div');
      el.id = 'leisure-timer-banner';
      el.style.cssText = 'position:fixed;top:10px;right:10px;z-index:9999;'
        + 'padding:8px 14px;border-radius:8px;font-weight:700;font-size:14px;'
        + 'background:rgba(30,40,30,.9);color:#fff;box-shadow:0 2px 8px rgba(0,0,0,.3);'
        + 'display:none;pointer-events:none;';
      document.body.appendChild(el);
    }
    return el;
  }

  function showBanner(text, level) {
    const el = banner();
    el.textContent = text;
    el.style.display = 'block';
    el.style.background = level === 'warn'
      ? 'rgba(160,60,30,.92)'
      : level === 'end'
        ? 'rgba(120,20,20,.94)'
        : 'rgba(30,40,30,.9)';
  }

  function hideBanner() {
    banner().style.display = 'none';
  }

  function formatRemaining(seconds) {
    const total = Math.max(0, Math.round(seconds));
    const minutes = Math.floor(total / 60);
    const rest = total % 60;
    return `${minutes}:${String(rest).padStart(2, '0')}`;
  }

  /* 门票门：免费时段直接放行；否则调 enter（消耗 1 张票开 10 分钟）。
     返回 true 表示放行；false 表示已渲染拦截提示（调用方应中止启动）。 */
  async function enterGate() {
    let data;
    try {
      const response = await fetch('/api/leisure/ticket/enter', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
      });
      data = await response.json().catch(() => ({}));
      if (!response.ok || !data.success) {
        showGateScreen(data.error || '进入失败', data.code === 'NO_TICKET'
          ? '门票不足：每天签到可得 1 张（连续 7 天再得 1 张）；工作日 8:00-10:00、15:00-17:00 免费开放。'
          : '');
        return false;
      }
    } catch (err) {
      showGateScreen('网络异常，无法进入休闲花园', '');
      return false;
    }
    if (data.mode === 'free') {
      ticketMode = false;
      showBanner('免费时段（不限时）', 'ok');
      window.setTimeout(hideBanner, 4000);
      return true;
    }
    ticketMode = data.mode !== 'none';
    return true;
  }

  function showGateScreen(title, detail) {
    const screen = document.createElement('div');
    screen.style.cssText = 'position:fixed;inset:0;z-index:10000;display:flex;'
      + 'align-items:center;justify-content:center;background:rgba(10,14,10,.94);';
    const box = document.createElement('div');
    box.style.cssText = 'max-width:420px;padding:28px;border-radius:12px;'
      + 'background:#1c261c;color:#e8f0e8;text-align:center;';
    box.innerHTML = `<div style="font-size:20px;font-weight:800;margin-bottom:12px">🌸 ${title}</div>`
      + (detail ? `<div style="font-size:14px;line-height:1.6;opacity:.85">${detail}</div>` : '')
      + '<div style="margin-top:18px"><button id="leisure-gate-back" '
      + 'style="padding:8px 24px;border-radius:8px;border:0;background:#3a7d44;color:#fff;'
      + 'font-size:15px;cursor:pointer">返回大厅</button></div>';
    screen.appendChild(box);
    document.body.appendChild(screen);
    screen.querySelector('#leisure-gate-back').addEventListener('click', () => {
      window.location.href = '/';
    });
  }

  /* 10 分钟游玩期倒计时：轮询服务端权威剩余时间（断线暂停由服务端记账）。 */
  function startTimer() {
    if (timerHandle) return;
    const tick = async () => {
      if (settled) return;
      let data;
      try {
        const response = await fetch('/api/leisure/ticket/session', { credentials: 'same-origin' });
        data = await response.json().catch(() => ({}));
      } catch (err) {
        return;   // 网络异常：跳过本轮轮询，下一轮再试
      }
      if (!data.success || !data.session) return;
      if (data.expired) {
        settleAndExit();
        return;
      }
      const remaining = Number(data.session.remaining || 0);
      WARN_THRESHOLDS.forEach((threshold) => {
        if (remaining <= threshold && !warned.has(threshold)) {
          warned.add(threshold);
          showBanner(`剩余 ${formatRemaining(remaining)}！`, 'warn');
        }
      });
      if (remaining > 10) showBanner(`游玩剩余 ${formatRemaining(remaining)}`, 'ok');
    };
    tick();
    timerHandle = window.setInterval(tick, 5000);
  }

  /* 到点结算：立即交成绩、锁界面、提示返回大厅。 */
  function settleAndExit() {
    if (settled) return;
    settled = true;
    if (timerHandle) { window.clearInterval(timerHandle); timerHandle = null; }
    showBanner('时间到！本段游玩已结算', 'end');
    document.dispatchEvent(new CustomEvent('leisure:expired'));
    window.setTimeout(() => { window.location.href = '/'; }, 4000);
  }

  window.GtnLeisureTicket = {
    enterGate,
    startTimer,
    settleAndExit,
    recordResult: async (game, score, bestTier) => {
      try {
        await fetch('/api/leisure/ticket/result', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ game, score, best_tier: bestTier }),
        });
      } catch (err) { /* 分数已在正常链路落库，这里只影响奖励 */ }
    },
  };
})();
