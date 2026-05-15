import * as Blockly from 'blockly';
import './blocks/index.js';
import './generator.js';
import { toolbox } from './toolbox.js';
import { editor } from './app.js';

const blocklyArea = document.getElementById('blockly-area');

const workspace = Blockly.inject(blocklyArea, {
  toolbox: toolbox,
  renderer: 'zelos',
  grid: {
    spacing: 25,
    length: 3,
    colour: '#44446a',
    snap: true,
  },
  zoom: {
    controls: true,
    wheel: true,
    startScale: 1.0,
    maxScale: 3,
    minScale: 0.3,
    scaleSpeed: 1.2,
  },
  trashcan: true,
  move: {
    scrollbars: true,
    drag: true,
    wheel: true,
  },
  theme: Blockly.Theme.Classic,
  sounds: false,
});

editor.init(workspace);

  window.addEventListener('resize', () => {
  Blockly.svgResize(workspace);
});
setTimeout(() => Blockly.svgResize(workspace), 100);

document.getElementById('btn-add-card').addEventListener('click', () => editor.createCard());
document.getElementById('btn-duplicate-card').addEventListener('click', () => editor.duplicateCard(editor.currentCardIndex));
document.getElementById('btn-delete-card').addEventListener('click', () => {
  if (editor.currentCardIndex >= 0 && confirm('确定删除此卡牌？')) {
    editor.deleteCard(editor.currentCardIndex);
  }
});

const propInputIds = [
  'prop-id', 'prop-name-cn', 'prop-name-en', 'prop-cost-e', 'prop-cost-m',
  'prop-card-type', 'prop-quality', 'prop-effect-text', 'prop-description',
  'prop-durability', 'prop-max-copies',
];
propInputIds.forEach(id => {
  const el = document.getElementById(id);
  if (el) {
    el.addEventListener('change', () => {
      editor.readPropsToCard();
      editor.renderCardList();
      editor.saveToStorage();
    });
  }
});
document.querySelectorAll('#prop-flags input[type="checkbox"]').forEach(cb => {
  cb.addEventListener('change', () => {
    editor.readPropsToCard();
    editor.saveToStorage();
  });
});

document.getElementById('btn-new-mod').addEventListener('click', () => {
  if (confirm('创建新模组将丢弃当前未保存的更改，确定？')) {
    editor.newMod();
  }
});

document.getElementById('btn-open-mod').addEventListener('click', async () => {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.json';
  input.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const text = await file.text();
    if (editor.importModJson(text)) {
      alert('导入成功！');
    } else {
      alert('导入失败，请检查 JSON 格式。');
    }
  };
  input.click();
});

document.getElementById('btn-save-mod').addEventListener('click', () => {
  const json = editor.exportModJson();
  if (window.pywebview) {
    window.pywebview.api.save_file(json);
  } else {
    downloadJson(json, editor.modData.info.name + '.json');
  }
});

document.getElementById('btn-export-mod').addEventListener('click', () => {
  const json = editor.exportModJson();
  downloadJson(json, editor.modData.info.name + '.json');
});

document.getElementById('btn-import-card').addEventListener('click', () => {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.json';
  input.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const text = await file.text();
    try {
      const data = JSON.parse(text);
      const cards = Array.isArray(data) ? data : [data];
      for (const card of cards) {
        editor.modData.cards.push(card);
      }
      editor.renderCardList();
      if (editor.modData.cards.length > 0) {
        editor.selectCard(editor.modData.cards.length - 1);
      }
      editor.saveToStorage();
      alert(`成功导入 ${cards.length} 张卡牌！`);
    } catch(e) {
      alert('导入失败，请检查 JSON 格式。');
    }
  };
  input.click();
});

document.getElementById('btn-edit-info').addEventListener('click', () => {
  showModal('编辑模组信息', renderModInfoForm());
});

document.getElementById('btn-edit-globals').addEventListener('click', () => {
  showModal('编辑全局设置', renderGlobalsForm());
});

document.getElementById('btn-json-preview').addEventListener('click', () => {
  const json = editor.exportModJson();
  showModal('JSON 预览', `<pre>${escapeHtml(json)}</pre>`);
});

document.getElementById('modal-close').addEventListener('click', hideModal);
document.getElementById('modal-overlay').addEventListener('click', (e) => {
  if (e.target === document.getElementById('modal-overlay')) hideModal();
});

function downloadJson(json, filename) {
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function showModal(title, bodyHtml) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = bodyHtml;
  document.getElementById('modal-overlay').classList.remove('hidden');
}

function hideModal() {
  document.getElementById('modal-overlay').classList.add('hidden');
}

function renderModInfoForm() {
  const info = editor.modData.info;
  return `
    <div class="modal-prop-row"><label>模组名称</label><input id="mi-name" value="${escapeHtml(info.name || '')}"></div>
    <div class="modal-prop-row"><label>版本</label><input id="mi-version" value="${escapeHtml(info.version || '')}"></div>
    <div class="modal-prop-row"><label>作者</label><input id="mi-author" value="${escapeHtml(info.author || '')}"></div>
    <div class="modal-prop-row"><label>描述</label><input id="mi-description" value="${escapeHtml(info.description || '')}"></div>
    <div class="modal-prop-row"><label>游戏版本</label><input id="mi-game-version" value="${escapeHtml(info.game_version || '')}"></div>
    <div class="modal-buttons">
      <button class="btn" onclick="document.getElementById('modal-overlay').classList.add('hidden')">取消</button>
      <button class="btn btn-primary" onclick="saveModInfo()">保存</button>
    </div>
  `;
}

window.saveModInfo = function() {
  editor.modData.info.name = document.getElementById('mi-name').value.trim() || '未命名模组';
  editor.modData.info.version = document.getElementById('mi-version').value.trim() || '1.0.0';
  editor.modData.info.author = document.getElementById('mi-author').value.trim();
  editor.modData.info.description = document.getElementById('mi-description').value.trim();
  editor.modData.info.game_version = document.getElementById('mi-game-version').value.trim();
  document.getElementById('mod-name-display').textContent = editor.modData.info.name;
  editor.saveToStorage();
  hideModal();
};

function renderGlobalsForm() {
  const g = editor.modData.globals;
  const fields = [
    ['初始生命', 'initial_health'], ['生命上限', 'max_health'],
    ['初始能量', 'initial_energy'], ['能量上限', 'max_energy'],
    ['初始魔力', 'initial_magic'], ['魔力上限', 'max_magic'],
    ['每回合抽牌数', 'draw_per_turn'], ['能量回复', 'energy_regen'],
    ['魔力回复', 'magic_regen'], ['手牌上限', 'max_hand'],
    ['先手初始能量', 'first_energy'], ['后手生命加成', 'second_health_bonus'],
    ['全局伤害倍率', 'global_damage_mult'], ['选牌轮数', 'draft_rounds'],
    ['重选次数', 'rerolls'],
  ];
  let html = '';
  for (const [label, key] of fields) {
    html += `<div class="modal-prop-row"><label>${label}</label><input id="gl-${key}" type="number" step="any" value="${g[key] ?? 0}"></div>`;
  }
  html += `<div class="modal-buttons">
    <button class="btn" onclick="document.getElementById('modal-overlay').classList.add('hidden')">取消</button>
    <button class="btn btn-primary" onclick="saveGlobals()">保存</button>
  </div>`;
  return html;
}

window.saveGlobals = function() {
  const keys = [
    'initial_health','max_health','initial_energy','max_energy',
    'initial_magic','max_magic','draw_per_turn','energy_regen',
    'magic_regen','max_hand','first_energy','second_health_bonus',
    'global_damage_mult','draft_rounds','rerolls',
  ];
  for (const key of keys) {
    const el = document.getElementById('gl-' + key);
    if (el) editor.modData.globals[key] = parseFloat(el.value) || 0;
  }
  editor.saveToStorage();
  hideModal();
};
