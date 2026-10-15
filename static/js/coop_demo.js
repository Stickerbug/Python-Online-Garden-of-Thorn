
let snap = null;
async function api(path, body) {
  const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
  const j = await r.json();
  if (!j.success) { log('⚠ ' + (j.error || '操作失败')); }
  if (j.snapshot) { snap = j.snapshot; render(); }
  if (j.events) log(j.events.join('\n'));
  return j;
}
const start = () => api('/api/coop-demo/start');
const switchSeat = () => api('/api/coop-demo/action', { type: 'switch' });
const endTurn = () => api('/api/coop-demo/action', { type: 'end_turn' });
const cancelReady = () => api('/api/coop-demo/action', { type: 'cancel_ready' });
const play = (id) => api('/api/coop-demo/action', { type: 'play_card', card_instance_id: id });

function log(t) { if (!t) return; const el = document.getElementById('log'); el.textContent = t + '\n' + el.textContent; }

function render() {
  if (!snap) return;
  const board = document.getElementById('board');
  board.innerHTML = '';
  snap.seats.forEach((s, i) => {
    const d = document.createElement('div');
    d.className = 'panel seat' + (i === snap.active_seat ? ' active' : '') + (s.hp <= 0 ? ' down' : '');
    d.innerHTML = `<h3>玩家${i}${i === snap.active_seat ? '（你在操控）' : ''}${s.ready ? '<span class="badge ready">已就绪</span>' : ''}${s.hp <= 0 ? '<span class="badge">倒地</span>' : ''}</h3>
      <div class="stats">H ${s.hp}/${s.max_hp} · E ${s.elixir} · 盾 ${s.shield}<br>手牌 ${s.hand_count} 张</div>`;
    board.appendChild(d);
  });
  const e = snap.enemy;
  if (e) {
    const d = document.createElement('div');
    d.className = 'panel enemy';
    const pct = Math.max(0, Math.round(100 * e.hp / e.max_hp));
    d.innerHTML = `<h3>${e.name}</h3>
      <div class="hpbar"><i style="width:${pct}%"></i></div>
      <div class="stats">${e.hp}/${e.max_hp}H${e.shield ? ' · 盾' + e.shield : ''}</div>
      <div class="intent">意图：${e.intent}</div>`;
    board.appendChild(d);
  } else {
    const d = document.createElement('div');
    d.className = 'panel enemy';
    d.innerHTML = `<h3>${snap.phase === 'game_over' ? '💀 全席倒地，战斗失败' : '🏆 战斗胜利！'}</h3>`;
    board.appendChild(d);
  }
  const hand = document.getElementById('hand');
  hand.innerHTML = '';
  (snap.hand || []).forEach(c => {
    const b = document.createElement('button');
    b.className = 'card';
    b.disabled = !!snap.my_ready || snap.phase !== 'combat';
    b.innerHTML = `<span class="cost">${c.cost_e}E</span><b>${c.name}</b>${c.desc || ''}`;
    b.onclick = () => play(c.instance_id);
    hand.appendChild(b);
  });
  document.getElementById('cancel-btn').disabled = !snap.my_ready;
}
start();
// CSP 禁止内联 onclick 属性——改用 JS 绑定动作按钮
function bindActs() {
  const gold = document.querySelector('button.act.gold');
  if (gold) gold.addEventListener('click', start);
  const acts = [...document.querySelectorAll('button.act')];
  acts.find((b) => (b.textContent || '').includes('切换操控玩家'))?.addEventListener('click', switchSeat);
  acts.find((b) => (b.textContent || '').includes('结束回合'))?.addEventListener('click', endTurn);
  acts.find((b) => (b.textContent || '').includes('撤回就绪'))?.addEventListener('click', cancelReady);
}
bindActs();
