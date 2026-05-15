import * as Blockly from 'blockly';
import { generateEffectsFromWorkspace } from './generator.js';

const STORAGE_KEY = 'gt_mod_editor_state';

class ModEditor {
  constructor() {
    this.modData = {
      info: { name: '未命名模组', version: '1.0.0', author: '', description: '', game_version: '' },
      globals: {
        initial_health: 100, max_health: 100, initial_energy: 3, max_energy: 10,
        initial_magic: 0, max_magic: 10, draw_per_turn: 1, energy_regen: 3,
        magic_regen: 0, max_hand: 10, first_energy: 3, second_health_bonus: 0,
        global_damage_mult: 1.0, deck_composition: {}, draft_rounds: 15, rerolls: 3,
      },
      cards: [],
      events: [],
    };
    this.currentCardIndex = -1;
    this.workspace = null;
    this.cardXmlCache = {};
  }

  init(workspace) {
    this.workspace = workspace;
    this.loadFromStorage();
    if (this.modData.cards.length > 0) {
      this.selectCard(0);
    }
    this.renderCardList();
    this.updateStatusBar();
    this.setupAutoSave();
  }

  createCard() {
    const id = 'Card_' + Date.now().toString(36);
    const card = {
      id, name_cn: '新卡牌', name_en: 'NewCard',
      cost_e: 0, cost_m: 0, card_type: 'bloom', quality: 'Common',
      flags: [], effect_text: '', description: '', durability: -1, max_copies: 99,
      effects: [],
    };
    this.modData.cards.push(card);
    this.renderCardList();
    this.selectCard(this.modData.cards.length - 1);
    this.saveToStorage();
    return card;
  }

  duplicateCard(index) {
    if (index < 0 || index >= this.modData.cards.length) return;
    const src = this.modData.cards[index];
    const card = JSON.parse(JSON.stringify(src));
    card.id = card.id + '_copy';
    card.name_cn = card.name_cn + '（副本）';
    this.modData.cards.splice(index + 1, 0, card);
    this.renderCardList();
    this.selectCard(index + 1);
    this.saveToStorage();
  }

  deleteCard(index) {
    if (index < 0 || index >= this.modData.cards.length) return;
    const cardId = this.modData.cards[index].id;
    this.modData.cards.splice(index, 1);
    delete this.cardXmlCache[cardId];
    if (this.currentCardIndex >= this.modData.cards.length) {
      this.currentCardIndex = this.modData.cards.length - 1;
    }
    this.renderCardList();
    if (this.currentCardIndex >= 0) {
      this.selectCard(this.currentCardIndex);
    } else {
      this.workspace.clear();
      this.clearPropsPanel();
    }
    this.saveToStorage();
  }

  selectCard(index) {
    if (index < 0 || index >= this.modData.cards.length) return;
    this.saveCurrentCardWorkspace();
    this.currentCardIndex = index;
    const card = this.modData.cards[index];
    this.loadCardWorkspace(card);
    this.updatePropsPanel(card);
    this.renderCardList();
    this.updateStatusBar();
  }

  saveCurrentCardWorkspace() {
    if (this.currentCardIndex < 0 || !this.workspace) return;
    const card = this.modData.cards[this.currentCardIndex];
    if (!card) return;
    const xml = Blockly.Xml.workspaceToDom(this.workspace);
    this.cardXmlCache[card.id] = Blockly.Xml.domToText(xml);
    card.effects = generateEffectsFromWorkspace(this.workspace);
  }

  loadCardWorkspace(card) {
    this.workspace.clear();
    if (this.cardXmlCache[card.id]) {
      try {
        const xml = Blockly.utils.xml.textToDom(this.cardXmlCache[card.id]);
        Blockly.Xml.domToWorkspace(xml, this.workspace);
      } catch(e) {
        console.warn('Failed to load workspace XML:', e);
      }
    } else if (card.effects && card.effects.length > 0) {
      this._effectsToBlocks(card.effects);
    }
  }

  _effectsToBlocks(effects) {
    const REVERSE_MAP = {
      'deal_damage': 'action_damage',
      'heal': 'action_heal',
      'draw': 'action_draw',
      'gain_e': 'action_gain_e',
      'gain_m': 'action_gain_m',
      'gain_armor': 'action_add_armor',
      'gain_dodge': 'action_dodge_permanent',
      'apply_poison': 'action_poison',
      'apply_burn': 'action_burn',
      'apply_toxic': 'action_toxic',
      'apply_vulnerable': 'action_vulnus',
      'reveal_enemy_hand': 'action_reveal_hand',
      'steal_enemy_card': 'action_steal_card',
      'choose_from_deck': 'action_choose_from_deck',
      'choose_from_discard': 'action_choose_from_discard',
      'choose_from_exile': 'action_choose_from_exile',
      'set_health': 'action_set_health',
      'set_invincible': 'action_invincible',
      'set_untargetable': 'action_untargetable',
      'block_enemy_attacks': 'action_block_card_type',
      'force_enemy_attacks_only': 'action_force_card_type',
      'block_own_actions': 'action_block_action',
      'counter_dodge': 'action_dodge_this',
      'counter_nazar': 'action_dodge_permanent',
      'counter_negate_skill': 'action_nullify_current_card',
      'counter_equip_protect': 'action_equip_protection',
      'counter_block_enemy_attacks': 'action_block_card_type',
      'counter_set_invincible_then_die': 'action_invincible',
      'equip_sponge': 'action_place_as_equip',
      'equip_reduce_enemy_draw': 'action_mod_draw',
      'equip_reduce_enemy_e': 'action_mod_e_regen',
      'equip_reduce_own_draw': 'action_mod_draw',
      'equip_reduce_own_e': 'action_mod_e_regen',
      'equip_add_toxic': 'action_toxic',
      'equip_set_health': 'action_set_health',
      'equip_on_destroy_remove_poison_damage': 'action_clear_status',
      'on_fatal_invincible_then_die': 'action_invincible',
      'on_fatal_set_health_exile': 'action_exile_this',
      'damage': 'action_damage',
      'damage_multi': 'action_damage_multi',
      'poison': 'action_poison',
      'burn': 'action_burn',
      'vulnus': 'action_vulnus',
      'toxic': 'action_toxic',
      'add_armor': 'action_add_armor',
      'remove_armor': 'action_remove_armor',
      'set_armor': 'action_set_armor',
      'dodge_this': 'action_dodge_this',
      'dodge_permanent': 'action_dodge_permanent',
      'clear_buffs': 'action_clear_buffs',
      'clear_debuffs': 'action_clear_debuffs',
      'clear_all_effects': 'action_clear_all_effects',
      'clear_status': 'action_clear_status',
      'cost_e': 'action_cost_e',
      'cost_m': 'action_cost_m',
      'mod_e_regen': 'action_mod_e_regen',
      'mod_m_regen': 'action_mod_m_regen',
      'mod_draw': 'action_mod_draw',
      'discard': 'action_discard',
      'reveal_deck_top': 'action_reveal_deck_top',
      'steal_card': 'action_steal_card',
      'copy_card': 'action_copy_card',
      'random_discard_from_hand': 'action_random_discard_from_hand',
      'put_card_to_deck': 'action_put_card_to_deck',
      'shuffle_discard_into_deck': 'action_shuffle_discard_into_deck',
      'give_card_to_hand': 'action_give_card_to_hand',
      'give_card_to_deck': 'action_give_card_to_deck',
      'give_card_to_discard': 'action_give_card_to_discard',
      'remove_specific_card': 'action_remove_specific_card',
      'destroy_random_equip': 'action_destroy_random_equip',
      'destroy_all_equip': 'action_destroy_all_equip',
      'destroy_all_field_equip': 'action_destroy_all_field_equip',
      'equip_protection': 'action_equip_protection',
      'remove_equip_protection': 'action_remove_equip_protection',
      'place_as_equip': 'action_place_as_equip',
      'block_action': 'action_block_action',
      'block_card_type': 'action_block_card_type',
      'force_card_type': 'action_force_card_type',
      'nullify_current_card': 'action_nullify_current_card',
      'invincible': 'action_invincible',
      'untargetable': 'action_untargetable',
      'skip_turn': 'action_skip_turn',
      'extra_turn': 'action_extra_turn',
      'force_end_turn': 'action_force_end_turn',
      'mark_self_damage_source': 'action_mark_self_damage_source',
      'fission': 'action_fission',
      'multiply_next_damage': 'action_multiply_next_damage',
      'reduce_next_cost': 'action_reduce_next_cost',
      'increase_next_cost': 'action_increase_next_cost',
      'fusion': 'action_fusion',
      'add_tag': 'action_add_tag',
      'remove_tag': 'action_remove_tag',
      'transform_card': 'action_transform_card',
      'gain_durability': 'action_gain_durability',
      'lose_durability': 'action_lose_durability',
      'set_durability': 'action_set_durability',
      'record_play_count': 'action_record_play_count',
      'record_equip_turns': 'action_record_equip_turns',
      'reset_counter': 'action_reset_counter',
      'create_counter': 'action_create_counter',
      'exile_this': 'action_exile_this',
      'move_to_discard': 'action_move_to_discard',
      'move_to_deck': 'action_move_to_deck',
      'global_damage_mult': 'action_global_damage_mult',
      'global_heal_mult': 'action_global_heal_mult',
      'global_cost_mult': 'action_global_cost_mult',
      'swap_health': 'action_swap_health',
      'swap_hands': 'action_swap_hands',
      'broadcast_event': 'action_broadcast_event',
      'modify_damage': 'action_modify_damage',
      'log': 'action_draw',
    };

    let prevBlock = null;
    for (const effect of effects) {
      const blockType = REVERSE_MAP[effect.type] || effect.type;
      try {
        const block = this.workspace.newBlock(blockType);
        const params = effect.params || {};

        if (blockType === 'action_damage' || blockType === 'action_heal' ||
            blockType === 'action_set_health' || blockType === 'action_add_armor' ||
            blockType === 'action_remove_armor' || blockType === 'action_set_armor' ||
            blockType === 'action_poison' || blockType === 'action_burn' ||
            blockType === 'action_vulnus' || blockType === 'action_toxic' ||
            blockType === 'action_gain_e' || blockType === 'action_gain_m' ||
            blockType === 'action_cost_e' || blockType === 'action_cost_m' ||
            blockType === 'action_mod_e_regen' || blockType === 'action_mod_m_regen' ||
            blockType === 'action_mod_draw' || blockType === 'action_draw' ||
            blockType === 'action_discard' || blockType === 'action_dodge_permanent') {
          if (params.amount !== undefined && block.getField('AMOUNT')) {
            block.getField('AMOUNT').setValue(String(params.amount));
          }
        }
        if (blockType === 'action_block_card_type' || blockType === 'action_force_card_type') {
          if (params.duration !== undefined && block.getField('DURATION')) {
            block.getField('DURATION').setValue(String(params.duration));
          }
          if (params.card_type && block.getField('CARD_TYPE')) {
            block.getField('CARD_TYPE').setValue(params.card_type);
          }
        }
        if (blockType === 'action_modify_damage') {
          if (params.formula && block.getField('FORMULA')) {
            block.getField('FORMULA').setValue(params.formula);
          }
        }
        if (blockType === 'action_put_card_to_deck' || blockType === 'action_move_to_deck' ||
            blockType === 'action_give_card_to_deck') {
          if (params.position && block.getField('POSITION')) {
            block.getField('POSITION').setValue(params.position);
          }
        }
        if (blockType === 'action_remove_specific_card') {
          if (params.zone && block.getField('ZONE')) {
            block.getField('ZONE').setValue(params.zone);
          }
        }
        if (blockType === 'action_clear_status') {
          if (params.status && block.getField('STATUS')) {
            block.getField('STATUS').setValue(params.status);
          }
        }
        if (blockType === 'action_add_tag' || blockType === 'action_remove_tag') {
          if (params.tag && block.getField('TAG')) {
            block.getField('TAG').setValue(params.tag);
          }
        }
        if (blockType === 'action_create_counter') {
          if (params.name && block.getField('NAME')) {
            block.getField('NAME').setValue(params.name);
          }
        }
        if (blockType === 'action_broadcast_event') {
          if (params.event_name && block.getField('EVENT_NAME')) {
            block.getField('EVENT_NAME').setValue(params.event_name);
          }
        }
        if (blockType === 'action_fission') {
          if (params.card_type && block.getField('CARD_TYPE')) {
            block.getField('CARD_TYPE').setValue(params.card_type);
          }
        }

        block.initSvg();
        block.render();

        if (prevBlock && block.previousConnection && prevBlock.nextConnection) {
          block.previousConnection.connect(prevBlock.nextConnection);
        }
        prevBlock = block;
      } catch(e) {
        console.warn(`Failed to create block for effect type ${effect.type} (mapped to ${blockType}):`, e);
      }
    }
  }

  renderCardList() {
    const list = document.getElementById('card-list');
    if (!list) return;
    list.innerHTML = '';
    for (let i = 0; i < this.modData.cards.length; i++) {
      const card = this.modData.cards[i];
      const item = document.createElement('div');
      item.className = 'card-item' + (i === this.currentCardIndex ? ' active' : '');
      item.innerHTML = `
        <span class="card-type-dot ${card.card_type}"></span>
        <span class="card-name">${card.name_cn || card.id}</span>
        <span class="card-cost">${card.cost_e}E${card.cost_m > 0 ? '/' + card.cost_m + 'M' : ''}</span>
      `;
      item.addEventListener('click', () => this.selectCard(i));
      list.appendChild(item);
    }
  }

  updatePropsPanel(card) {
    if (!card) { this.clearPropsPanel(); return; }
    document.getElementById('prop-id').value = card.id || '';
    document.getElementById('prop-name-cn').value = card.name_cn || '';
    document.getElementById('prop-name-en').value = card.name_en || '';
    document.getElementById('prop-cost-e').value = card.cost_e ?? 0;
    document.getElementById('prop-cost-m').value = card.cost_m ?? 0;
    document.getElementById('prop-card-type').value = card.card_type || 'bloom';
    document.getElementById('prop-quality').value = card.quality || 'Common';
    document.getElementById('prop-effect-text').value = card.effect_text || '';
    document.getElementById('prop-description').value = card.description || '';
    document.getElementById('prop-durability').value = card.durability ?? -1;
    document.getElementById('prop-max-copies').value = card.max_copies ?? 99;
    const checkboxes = document.querySelectorAll('#prop-flags input[type="checkbox"]');
    checkboxes.forEach(cb => {
      cb.checked = (card.flags || []).includes(cb.value);
    });
  }

  clearPropsPanel() {
    ['prop-id','prop-name-cn','prop-name-en','prop-effect-text','prop-description'].forEach(id => {
      document.getElementById(id).value = '';
    });
    document.getElementById('prop-cost-e').value = 0;
    document.getElementById('prop-cost-m').value = 0;
    document.getElementById('prop-card-type').value = 'bloom';
    document.getElementById('prop-quality').value = 'Common';
    document.getElementById('prop-durability').value = -1;
    document.getElementById('prop-max-copies').value = 99;
    document.querySelectorAll('#prop-flags input[type="checkbox"]').forEach(cb => cb.checked = false);
  }

  readPropsToCard() {
    if (this.currentCardIndex < 0) return;
    const card = this.modData.cards[this.currentCardIndex];
    if (!card) return;
    card.id = document.getElementById('prop-id').value.trim() || card.id;
    card.name_cn = document.getElementById('prop-name-cn').value.trim();
    card.name_en = document.getElementById('prop-name-en').value.trim();
    card.cost_e = parseInt(document.getElementById('prop-cost-e').value) || 0;
    card.cost_m = parseInt(document.getElementById('prop-cost-m').value) || 0;
    card.card_type = document.getElementById('prop-card-type').value;
    card.quality = document.getElementById('prop-quality').value;
    card.effect_text = document.getElementById('prop-effect-text').value.trim();
    card.description = document.getElementById('prop-description').value.trim();
    card.durability = parseInt(document.getElementById('prop-durability').value);
    card.max_copies = parseInt(document.getElementById('prop-max-copies').value) || 99;
    const flags = [];
    document.querySelectorAll('#prop-flags input[type="checkbox"]:checked').forEach(cb => flags.push(cb.value));
    card.flags = flags;
  }

  updateStatusBar() {
    const card = this.modData.cards[this.currentCardIndex];
    document.getElementById('status-current-card').textContent =
      card ? `当前编辑：${card.name_cn || card.id}` : '当前编辑：无';
    const effectCount = card?.effects?.length || 0;
    document.getElementById('status-effect-count').textContent = `效果数量：${effectCount}`;
  }

  exportModJson() {
    this.saveCurrentCardWorkspace();
    this.readPropsToCard();
    const exportData = {
      info: { ...this.modData.info },
      globals: { ...this.modData.globals },
      cards: this.modData.cards.map(c => ({
        id: c.id, name_cn: c.name_cn, name_en: c.name_en,
        cost_e: c.cost_e, cost_m: c.cost_m, card_type: c.card_type,
        quality: c.quality, flags: [...(c.flags || [])],
        effect_text: c.effect_text, description: c.description,
        durability: c.durability, max_copies: c.max_copies,
        effects: c.effects || [],
      })),
      events: this.modData.events || [],
    };
    return JSON.stringify(exportData, null, 2);
  }

  importModJson(jsonStr) {
    try {
      const data = JSON.parse(jsonStr);
      this.modData.info = data.info || this.modData.info;
      this.modData.globals = data.globals || this.modData.globals;
      this.modData.cards = data.cards || [];
      this.modData.events = data.events || [];
      this.cardXmlCache = {};
      this.currentCardIndex = -1;
      this.workspace.clear();
      this.renderCardList();
      if (this.modData.cards.length > 0) {
        this.selectCard(0);
      }
      document.getElementById('mod-name-display').textContent = this.modData.info.name;
      this.saveToStorage();
      return true;
    } catch(e) {
      console.error('Import failed:', e);
      return false;
    }
  }

  saveToStorage() {
    try {
      this.saveCurrentCardWorkspace();
      this.readPropsToCard();
      const state = {
        modData: this.modData,
        cardXmlCache: this.cardXmlCache,
        currentCardIndex: this.currentCardIndex,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch(e) {}
  }

  loadFromStorage() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const state = JSON.parse(raw);
      if (state.modData) this.modData = state.modData;
      if (state.cardXmlCache) this.cardXmlCache = state.cardXmlCache;
      if (typeof state.currentCardIndex === 'number') this.currentCardIndex = state.currentCardIndex;
      document.getElementById('mod-name-display').textContent = this.modData.info.name;
    } catch(e) {}
  }

  setupAutoSave() {
    setInterval(() => this.saveToStorage(), 30000);
    this.workspace.addChangeListener((e) => {
      if (e.isUiEvent) return;
      this.saveToStorage();
      this.updateStatusBar();
    });
  }

  newMod() {
    this.modData = {
      info: { name: '未命名模组', version: '1.0.0', author: '', description: '', game_version: '' },
      globals: {
        initial_health: 100, max_health: 100, initial_energy: 3, max_energy: 10,
        initial_magic: 0, max_magic: 10, draw_per_turn: 1, energy_regen: 3,
        magic_regen: 0, max_hand: 10, first_energy: 3, second_health_bonus: 0,
        global_damage_mult: 1.0, deck_composition: {}, draft_rounds: 15, rerolls: 3,
      },
      cards: [],
      events: [],
    };
    this.cardXmlCache = {};
    this.currentCardIndex = -1;
    this.workspace.clear();
    this.renderCardList();
    this.clearPropsPanel();
    this.updateStatusBar();
    document.getElementById('mod-name-display').textContent = this.modData.info.name;
    localStorage.removeItem(STORAGE_KEY);
  }
}

export const editor = new ModEditor();
