import * as Blockly from 'blockly';
import {javascriptGenerator} from 'blockly/javascript';

const O = javascriptGenerator.ORDER_ATOMIC;

function v(block, name, fallback = '0') {
  return javascriptGenerator.valueToCode(block, name, O) || fallback;
}

function field(block, name) {
  return block.getFieldValue(name) || '';
}

function numField(block, name) {
  return Number(block.getFieldValue(name) || 0);
}

function makeEffect(type, params, log) {
  const obj = { type, params };
  if (log) obj.log = log;
  return JSON.stringify(obj);
}

javascriptGenerator['trigger_on_play'] = function(b) { return ''; };
javascriptGenerator['trigger_on_friendly_turn_start'] = function(b) { return ''; };
javascriptGenerator['trigger_on_enemy_turn_start'] = function(b) { return ''; };
javascriptGenerator['trigger_on_phys_damage'] = function(b) { return ''; };
javascriptGenerator['trigger_on_any_damage'] = function(b) { return ''; };
javascriptGenerator['trigger_on_lethal_damage'] = function(b) { return ''; };
javascriptGenerator['trigger_on_draw_this'] = function(b) { return ''; };
javascriptGenerator['trigger_on_end_turn_hand'] = function(b) { return ''; };
javascriptGenerator['trigger_on_overflow_discard'] = function(b) { return ''; };
javascriptGenerator['trigger_on_destroy'] = function(b) { return ''; };
javascriptGenerator['trigger_on_durability_zero'] = function(b) { return ''; };
javascriptGenerator['trigger_on_enemy_use_type'] = function(b) {
  return makeEffect('trigger_on_enemy_use_type', { card_type: field(b, 'CARD_TYPE') });
};
javascriptGenerator['trigger_on_friendly_use_type'] = function(b) {
  return makeEffect('trigger_on_friendly_use_type', { card_type: field(b, 'CARD_TYPE') });
};
javascriptGenerator['trigger_on_card_exile'] = function(b) { return ''; };
javascriptGenerator['trigger_on_deck_empty'] = function(b) { return ''; };
javascriptGenerator['trigger_on_self_magic_heal_cumulative'] = function(b) {
  return makeEffect('trigger_on_self_magic_heal_cumulative', { threshold: numField(b, 'THRESHOLD') });
};
javascriptGenerator['trigger_on_self_damage'] = function(b) { return ''; };

javascriptGenerator['trigger_manual'] = function(b) {
  return makeEffect('trigger_manual', {
    timing: field(b, 'TIMING'),
    cost_e: numField(b, 'COST_E'),
    cost_m: numField(b, 'COST_M'),
    condition: v(b, 'CONDITION', 'null'),
    destroy: field(b, 'DESTROY') === 'true',
  });
};

javascriptGenerator['response_declare'] = function(b) {
  return makeEffect('response_declare', {
    timing: field(b, 'TIMING'),
    cost_e: numField(b, 'COST_E'),
    cost_m: numField(b, 'COST_M'),
  });
};

javascriptGenerator['action_damage'] = function(b) {
  return makeEffect('damage', { target: v(b, 'TARGET', '"self"'), amount: v(b, 'AMOUNT', '0') });
};
javascriptGenerator['action_damage_multi'] = function(b) {
  return makeEffect('damage_multi', { target: v(b, 'TARGET', '"self"'), amount: v(b, 'AMOUNT', '0'), times: v(b, 'TIMES', '1') });
};
javascriptGenerator['action_heal'] = function(b) {
  return makeEffect('heal', { target: v(b, 'TARGET', '"self"'), amount: v(b, 'AMOUNT', '0') });
};
javascriptGenerator['action_set_health'] = function(b) {
  return makeEffect('set_health', { target: v(b, 'TARGET', '"self"'), amount: v(b, 'AMOUNT', '0') });
};
javascriptGenerator['action_modify_damage'] = function(b) {
  return makeEffect('modify_damage', { formula: field(b, 'FORMULA') });
};

javascriptGenerator['action_poison'] = function(b) {
  return makeEffect('poison', { target: v(b, 'TARGET', '"self"'), amount: v(b, 'AMOUNT', '0') });
};
javascriptGenerator['action_burn'] = function(b) {
  return makeEffect('burn', { target: v(b, 'TARGET', '"self"'), amount: v(b, 'AMOUNT', '0') });
};
javascriptGenerator['action_vulnus'] = function(b) {
  return makeEffect('vulnus', { target: v(b, 'TARGET', '"self"'), amount: v(b, 'AMOUNT', '0') });
};
javascriptGenerator['action_toxic'] = function(b) {
  return makeEffect('toxic', { target: v(b, 'TARGET', '"self"'), amount: v(b, 'AMOUNT', '0') });
};
javascriptGenerator['action_add_armor'] = function(b) {
  return makeEffect('add_armor', { target: v(b, 'TARGET', '"self"'), amount: v(b, 'AMOUNT', '0') });
};
javascriptGenerator['action_remove_armor'] = function(b) {
  return makeEffect('remove_armor', { target: v(b, 'TARGET', '"self"'), amount: v(b, 'AMOUNT', '0') });
};
javascriptGenerator['action_set_armor'] = function(b) {
  return makeEffect('set_armor', { target: v(b, 'TARGET', '"self"'), amount: v(b, 'AMOUNT', '0') });
};
javascriptGenerator['action_dodge_this'] = function(b) {
  return makeEffect('dodge_this', {});
};
javascriptGenerator['action_dodge_permanent'] = function(b) {
  return makeEffect('dodge_permanent', { amount: v(b, 'AMOUNT', '1') });
};
javascriptGenerator['action_clear_buffs'] = function(b) {
  return makeEffect('clear_buffs', { target: v(b, 'TARGET', '"self"') });
};
javascriptGenerator['action_clear_debuffs'] = function(b) {
  return makeEffect('clear_debuffs', { target: v(b, 'TARGET', '"self"') });
};
javascriptGenerator['action_clear_all_effects'] = function(b) {
  return makeEffect('clear_all_effects', { target: v(b, 'TARGET', '"self"') });
};
javascriptGenerator['action_clear_status'] = function(b) {
  return makeEffect('clear_status', { target: v(b, 'TARGET', '"self"'), status: field(b, 'STATUS') });
};

javascriptGenerator['action_gain_e'] = function(b) {
  return makeEffect('gain_e', { target: v(b, 'TARGET', '"self"'), amount: v(b, 'AMOUNT', '0') });
};
javascriptGenerator['action_gain_m'] = function(b) {
  return makeEffect('gain_m', { target: v(b, 'TARGET', '"self"'), amount: v(b, 'AMOUNT', '0') });
};
javascriptGenerator['action_cost_e'] = function(b) {
  return makeEffect('cost_e', { target: v(b, 'TARGET', '"self"'), amount: v(b, 'AMOUNT', '0') });
};
javascriptGenerator['action_cost_m'] = function(b) {
  return makeEffect('cost_m', { target: v(b, 'TARGET', '"self"'), amount: v(b, 'AMOUNT', '0') });
};
javascriptGenerator['action_mod_e_regen'] = function(b) {
  return makeEffect('mod_e_regen', { target: v(b, 'TARGET', '"self"'), amount: v(b, 'AMOUNT', '0') });
};
javascriptGenerator['action_mod_m_regen'] = function(b) {
  return makeEffect('mod_m_regen', { target: v(b, 'TARGET', '"self"'), amount: v(b, 'AMOUNT', '0') });
};
javascriptGenerator['action_mod_draw'] = function(b) {
  return makeEffect('mod_draw', { target: v(b, 'TARGET', '"self"'), amount: v(b, 'AMOUNT', '0') });
};

javascriptGenerator['action_draw'] = function(b) {
  return makeEffect('draw', { amount: v(b, 'AMOUNT', '1') });
};
javascriptGenerator['action_discard'] = function(b) {
  return makeEffect('discard', { amount: v(b, 'AMOUNT', '1') });
};
javascriptGenerator['action_choose_from_deck'] = function(b) {
  return makeEffect('choose_from_deck', {});
};
javascriptGenerator['action_choose_from_discard'] = function(b) {
  return makeEffect('choose_from_discard', {});
};
javascriptGenerator['action_choose_from_exile'] = function(b) {
  return makeEffect('choose_from_exile', {});
};
javascriptGenerator['action_reveal_hand'] = function(b) {
  return makeEffect('reveal_hand', { target: v(b, 'TARGET', '"enemy"') });
};
javascriptGenerator['action_reveal_deck_top'] = function(b) {
  return makeEffect('reveal_deck_top', { target: v(b, 'TARGET', '"enemy"'), amount: v(b, 'AMOUNT', '1') });
};
javascriptGenerator['action_steal_card'] = function(b) {
  return makeEffect('steal_card', { target: v(b, 'TARGET', '"enemy"') });
};
javascriptGenerator['action_copy_card'] = function(b) {
  return makeEffect('copy_card', {});
};
javascriptGenerator['action_random_discard_from_hand'] = function(b) {
  return makeEffect('random_discard_from_hand', { target: v(b, 'TARGET', '"enemy"'), amount: v(b, 'AMOUNT', '1') });
};
javascriptGenerator['action_put_card_to_deck'] = function(b) {
  return makeEffect('put_card_to_deck', { position: field(b, 'POSITION') });
};
javascriptGenerator['action_shuffle_discard_into_deck'] = function(b) {
  return makeEffect('shuffle_discard_into_deck', {});
};
javascriptGenerator['action_give_card_to_hand'] = function(b) {
  return makeEffect('give_card_to_hand', { card: v(b, 'CARD', '""'), target: v(b, 'TARGET', '"self"') });
};
javascriptGenerator['action_give_card_to_deck'] = function(b) {
  return makeEffect('give_card_to_deck', { card: v(b, 'CARD', '""'), target: v(b, 'TARGET', '"self"'), position: field(b, 'POSITION') });
};
javascriptGenerator['action_give_card_to_discard'] = function(b) {
  return makeEffect('give_card_to_discard', { card: v(b, 'CARD', '""'), target: v(b, 'TARGET', '"self"') });
};
javascriptGenerator['action_remove_specific_card'] = function(b) {
  return makeEffect('remove_specific_card', { target: v(b, 'TARGET', '"self"'), zone: field(b, 'ZONE'), card: v(b, 'CARD', '""') });
};

javascriptGenerator['action_destroy_random_equip'] = function(b) {
  return makeEffect('destroy_random_equip', { target: v(b, 'TARGET', '"enemy"') });
};
javascriptGenerator['action_destroy_all_equip'] = function(b) {
  return makeEffect('destroy_all_equip', { target: v(b, 'TARGET', '"enemy"') });
};
javascriptGenerator['action_destroy_all_field_equip'] = function(b) {
  return makeEffect('destroy_all_field_equip', {});
};
javascriptGenerator['action_equip_protection'] = function(b) {
  return makeEffect('equip_protection', {});
};
javascriptGenerator['action_remove_equip_protection'] = function(b) {
  return makeEffect('remove_equip_protection', { target: v(b, 'TARGET', '"enemy"') });
};
javascriptGenerator['action_place_as_equip'] = function(b) {
  return makeEffect('place_as_equip', {});
};

javascriptGenerator['action_block_action'] = function(b) {
  return makeEffect('block_action', { target: v(b, 'TARGET', '"enemy"') });
};
javascriptGenerator['action_block_card_type'] = function(b) {
  return makeEffect('block_card_type', { target: v(b, 'TARGET', '"enemy"'), card_type: field(b, 'CARD_TYPE') });
};
javascriptGenerator['action_force_card_type'] = function(b) {
  return makeEffect('force_card_type', { target: v(b, 'TARGET', '"enemy"'), card_type: field(b, 'CARD_TYPE') });
};
javascriptGenerator['action_nullify_current_card'] = function(b) {
  return makeEffect('nullify_current_card', { target: v(b, 'TARGET', '"enemy"'), card_type: field(b, 'CARD_TYPE') });
};
javascriptGenerator['action_invincible'] = function(b) {
  return makeEffect('invincible', { target: v(b, 'TARGET', '"self"') });
};
javascriptGenerator['action_untargetable'] = function(b) {
  return makeEffect('untargetable', { target: v(b, 'TARGET', '"self"') });
};
javascriptGenerator['action_skip_turn'] = function(b) {
  return makeEffect('skip_turn', { target: v(b, 'TARGET', '"enemy"') });
};
javascriptGenerator['action_extra_turn'] = function(b) {
  return makeEffect('extra_turn', { target: v(b, 'TARGET', '"self"') });
};
javascriptGenerator['action_force_end_turn'] = function(b) {
  return makeEffect('force_end_turn', {});
};
javascriptGenerator['action_mark_self_damage_source'] = function(b) {
  return makeEffect('mark_self_damage_source', { target: v(b, 'TARGET', '"self"') });
};

javascriptGenerator['action_fission'] = function(b) {
  return makeEffect('fission', { card_type: field(b, 'CARD_TYPE'), times: v(b, 'TIMES', '1') });
};
javascriptGenerator['action_multiply_next_damage'] = function(b) {
  return makeEffect('multiply_next_damage', { multiplier: v(b, 'MULTIPLIER', '2') });
};
javascriptGenerator['action_reduce_next_cost'] = function(b) {
  return makeEffect('reduce_next_cost', { amount: v(b, 'AMOUNT', '1') });
};
javascriptGenerator['action_increase_next_cost'] = function(b) {
  return makeEffect('increase_next_cost', { amount: v(b, 'AMOUNT', '1') });
};
javascriptGenerator['action_fusion'] = function(b) {
  return makeEffect('fusion', { count: v(b, 'COUNT', '2'), card_type: field(b, 'CARD_TYPE'), multiplier: v(b, 'MULTIPLIER', '2') });
};
javascriptGenerator['action_add_tag'] = function(b) {
  return makeEffect('add_tag', { tag: field(b, 'TAG') });
};
javascriptGenerator['action_remove_tag'] = function(b) {
  return makeEffect('remove_tag', { tag: field(b, 'TAG') });
};
javascriptGenerator['action_transform_card'] = function(b) {
  return makeEffect('transform_card', {});
};

javascriptGenerator['action_gain_durability'] = function(b) {
  return makeEffect('gain_durability', { amount: v(b, 'AMOUNT', '1') });
};
javascriptGenerator['action_lose_durability'] = function(b) {
  return makeEffect('lose_durability', { amount: v(b, 'AMOUNT', '1') });
};
javascriptGenerator['action_set_durability'] = function(b) {
  return makeEffect('set_durability', { amount: v(b, 'AMOUNT', '3') });
};
javascriptGenerator['action_record_play_count'] = function(b) {
  return makeEffect('record_play_count', {});
};
javascriptGenerator['action_record_equip_turns'] = function(b) {
  return makeEffect('record_equip_turns', {});
};
javascriptGenerator['action_reset_counter'] = function(b) {
  return makeEffect('reset_counter', {});
};
javascriptGenerator['action_create_counter'] = function(b) {
  return makeEffect('create_counter', { amount: v(b, 'AMOUNT', '1'), name: field(b, 'NAME') });
};

javascriptGenerator['action_exile_this'] = function(b) {
  return makeEffect('exile_this', {});
};
javascriptGenerator['action_move_to_discard'] = function(b) {
  return makeEffect('move_to_discard', {});
};
javascriptGenerator['action_move_to_deck'] = function(b) {
  return makeEffect('move_to_deck', { position: field(b, 'POSITION') });
};
javascriptGenerator['action_global_damage_mult'] = function(b) {
  return makeEffect('global_damage_mult', { multiplier: v(b, 'MULTIPLIER', '1') });
};
javascriptGenerator['action_global_heal_mult'] = function(b) {
  return makeEffect('global_heal_mult', { multiplier: v(b, 'MULTIPLIER', '1') });
};
javascriptGenerator['action_global_cost_mult'] = function(b) {
  return makeEffect('global_cost_mult', { multiplier: v(b, 'MULTIPLIER', '1') });
};
javascriptGenerator['action_swap_health'] = function(b) {
  return makeEffect('swap_health', { target1: v(b, 'TARGET1', '"self"'), target2: v(b, 'TARGET2', '"enemy"') });
};
javascriptGenerator['action_swap_hands'] = function(b) {
  return makeEffect('swap_hands', { target1: v(b, 'TARGET1', '"self"'), target2: v(b, 'TARGET2', '"enemy"') });
};

javascriptGenerator['action_broadcast_event'] = function(b) {
  return makeEffect('broadcast_event', { event_name: field(b, 'EVENT_NAME') });
};
javascriptGenerator['trigger_on_event'] = function(b) {
  return makeEffect('trigger_on_event', { event_name: field(b, 'EVENT_NAME') });
};

javascriptGenerator['control_if'] = function(b) {
  const cond = v(b, 'CONDITION', 'true');
  const branch = javascriptGenerator.statementToCode(b, 'DO');
  return makeEffect('if', { condition: cond, then: __collectEffects(branch) });
};
javascriptGenerator['control_if_else'] = function(b) {
  const cond = v(b, 'CONDITION', 'true');
  const thenCode = javascriptGenerator.statementToCode(b, 'DO');
  const elseCode = javascriptGenerator.statementToCode(b, 'ELSE');
  return makeEffect('if_else', { condition: cond, then: __collectEffects(thenCode), else: __collectEffects(elseCode) });
};
javascriptGenerator['control_repeat'] = function(b) {
  const times = v(b, 'TIMES', '1');
  const body = javascriptGenerator.statementToCode(b, 'DO');
  return makeEffect('repeat', { times, body: __collectEffects(body) });
};
javascriptGenerator['control_repeat_until'] = function(b) {
  const cond = v(b, 'CONDITION', 'true');
  const body = javascriptGenerator.statementToCode(b, 'DO');
  return makeEffect('repeat_until', { condition: cond, body: __collectEffects(body) });
};
javascriptGenerator['control_for_each'] = function(b) {
  const targets = v(b, 'TARGET_LIST', '"both"');
  const body = javascriptGenerator.statementToCode(b, 'DO');
  return makeEffect('for_each', { targets, body: __collectEffects(body) });
};
javascriptGenerator['control_after_all'] = function(b) {
  const body = javascriptGenerator.statementToCode(b, 'DO');
  return makeEffect('after_all', { body: __collectEffects(body) });
};
javascriptGenerator['control_random'] = function(b) {
  const a = javascriptGenerator.statementToCode(b, 'BRANCH_A');
  const bCode = javascriptGenerator.statementToCode(b, 'BRANCH_B');
  return makeEffect('random', { a: __collectEffects(a), b: __collectEffects(bCode) });
};

function __collectEffects(code) {
  if (!code || !code.trim()) return [];
  const lines = code.trim().split('\n').filter(l => l.trim());
  const effects = [];
  for (const line of lines) {
    try { effects.push(JSON.parse(line.trim().replace(/,$/, ''))); } catch(e) {}
  }
  return effects;
}

javascriptGenerator['condition_compare'] = function(b) {
  return [JSON.stringify({ op: 'compare', a: v(b, 'A', '0'), operator: field(b, 'OP'), b: v(b, 'B', '0') }), O];
};
javascriptGenerator['condition_equip_turns'] = function(b) {
  return [JSON.stringify({ op: 'equip_turns', operator: field(b, 'OP'), value: v(b, 'VALUE', '0') }), O];
};
javascriptGenerator['condition_durability'] = function(b) {
  return [JSON.stringify({ op: 'durability', operator: field(b, 'OP'), value: v(b, 'VALUE', '0') }), O];
};
javascriptGenerator['condition_damage_value'] = function(b) {
  return [JSON.stringify({ op: 'damage_value', operator: field(b, 'OP'), value: v(b, 'VALUE', '0') }), O];
};
javascriptGenerator['condition_target_attribute'] = function(b) {
  return [JSON.stringify({ op: 'target_attribute', target: v(b, 'TARGET', '"self"'), attr: field(b, 'ATTR'), operator: field(b, 'OP'), value: v(b, 'VALUE', '0') }), O];
};
javascriptGenerator['condition_has_tag'] = function(b) {
  return [JSON.stringify({ op: 'has_tag', tag: field(b, 'TAG') }), O];
};
javascriptGenerator['condition_has_status'] = function(b) {
  return [JSON.stringify({ op: 'has_status', target: v(b, 'TARGET', '"self"'), status: field(b, 'STATUS') }), O];
};
javascriptGenerator['condition_hand_has_type'] = function(b) {
  return [JSON.stringify({ op: 'hand_has_type', target: v(b, 'TARGET', '"self"'), card_type: field(b, 'CARD_TYPE') }), O];
};
javascriptGenerator['condition_has_equip'] = function(b) {
  return [JSON.stringify({ op: 'has_equip', target: v(b, 'TARGET', '"self"') }), O];
};
javascriptGenerator['condition_event_card_type'] = function(b) {
  return [JSON.stringify({ op: 'event_card_type', card_type: field(b, 'CARD_TYPE') }), O];
};
javascriptGenerator['condition_turn_number'] = function(b) {
  return [JSON.stringify({ op: 'turn_number', operator: field(b, 'OP'), value: v(b, 'VALUE', '0') }), O];
};
javascriptGenerator['condition_and_or'] = function(b) {
  return [JSON.stringify({ op: field(b, 'OP'), a: v(b, 'A', 'true'), b: v(b, 'B', 'true') }), O];
};
javascriptGenerator['condition_not'] = function(b) {
  return [JSON.stringify({ op: 'not', value: v(b, 'BOOL', 'true') }), O];
};
javascriptGenerator['condition_hand_full'] = function(b) {
  return [JSON.stringify({ op: 'hand_full', target: v(b, 'TARGET', '"self"') }), O];
};
javascriptGenerator['condition_zone_contains'] = function(b) {
  return [JSON.stringify({ op: 'zone_contains', target: v(b, 'TARGET', '"self"'), zone: field(b, 'ZONE'), card: v(b, 'CARD', '""') }), O];
};

javascriptGenerator['value_number'] = function(b) {
  return [String(numField(b, 'NUM')), O];
};
javascriptGenerator['value_target_attribute'] = function(b) {
  return [JSON.stringify({ ref: 'target_attribute', target: v(b, 'TARGET', '"self"'), attr: field(b, 'ATTR') }), O];
};
javascriptGenerator['value_play_count'] = function(b) {
  return [JSON.stringify({ ref: 'play_count' }), O];
};
javascriptGenerator['value_equip_turns'] = function(b) {
  return [JSON.stringify({ ref: 'equip_turns' }), O];
};
javascriptGenerator['value_durability'] = function(b) {
  return [JSON.stringify({ ref: 'durability' }), O];
};
javascriptGenerator['value_incoming_damage'] = function(b) {
  return [JSON.stringify({ ref: 'incoming_damage' }), O];
};
javascriptGenerator['value_last_damage'] = function(b) {
  return [JSON.stringify({ ref: 'last_damage' }), O];
};
javascriptGenerator['value_status_count'] = function(b) {
  return [JSON.stringify({ ref: 'status_count', target: v(b, 'TARGET', '"self"'), status: field(b, 'STATUS') }), O];
};
javascriptGenerator['value_hand_size'] = function(b) {
  return [JSON.stringify({ ref: 'hand_size', target: v(b, 'TARGET', '"self"') }), O];
};
javascriptGenerator['value_discard_size'] = function(b) {
  return [JSON.stringify({ ref: 'discard_size', target: v(b, 'TARGET', '"self"') }), O];
};
javascriptGenerator['value_equip_count'] = function(b) {
  return [JSON.stringify({ ref: 'equip_count', target: v(b, 'TARGET', '"self"') }), O];
};
javascriptGenerator['value_exile_size'] = function(b) {
  return [JSON.stringify({ ref: 'exile_size', target: v(b, 'TARGET', '"self"') }), O];
};
javascriptGenerator['value_deck_remaining'] = function(b) {
  return [JSON.stringify({ ref: 'deck_remaining', target: v(b, 'TARGET', '"self"') }), O];
};
javascriptGenerator['value_turn_number'] = function(b) {
  return [JSON.stringify({ ref: 'turn_number' }), O];
};
javascriptGenerator['value_random'] = function(b) {
  return [JSON.stringify({ ref: 'random', min: v(b, 'MIN', '1'), max: v(b, 'MAX', '10') }), O];
};
javascriptGenerator['value_math_op'] = function(b) {
  return [JSON.stringify({ ref: 'math_op', a: v(b, 'A', '0'), op: field(b, 'OP'), b: v(b, 'B', '0') }), O];
};
javascriptGenerator['value_round'] = function(b) {
  return [JSON.stringify({ ref: 'round', mode: field(b, 'MODE'), value: v(b, 'VALUE', '0') }), O];
};
javascriptGenerator['value_min_max'] = function(b) {
  return [JSON.stringify({ ref: 'min_max', a: v(b, 'A', '0'), b: v(b, 'B', '0'), mode: field(b, 'MODE') }), O];
};
javascriptGenerator['value_clamp'] = function(b) {
  return [JSON.stringify({ ref: 'clamp', value: v(b, 'VALUE', '0'), min: v(b, 'MIN', '0'), max: v(b, 'MAX', '99') }), O];
};

javascriptGenerator['target_self'] = function(b) { return ['"self"', O]; };
javascriptGenerator['target_enemy'] = function(b) { return ['"enemy"', O]; };
javascriptGenerator['target_both'] = function(b) { return ['"both"', O]; };
javascriptGenerator['target_random'] = function(b) { return ['"random"', O]; };
javascriptGenerator['target_event_target'] = function(b) { return ['"event_target"', O]; };
javascriptGenerator['target_event_source'] = function(b) { return ['"event_source"', O]; };
javascriptGenerator['target_last_actor'] = function(b) { return ['"last_actor"', O]; };
javascriptGenerator['target_highest_health'] = function(b) { return ['"highest_health"', O]; };
javascriptGenerator['target_lowest_health'] = function(b) { return ['"lowest_health"', O]; };

javascriptGenerator['card_selector_by_id'] = function(b) {
  return [JSON.stringify({ selector: 'by_id', id: field(b, 'CARD_ID') }), O];
};
javascriptGenerator['card_selector_by_type'] = function(b) {
  return [JSON.stringify({ selector: 'by_type', card_type: field(b, 'CARD_TYPE') }), O];
};
javascriptGenerator['card_selector_by_quality'] = function(b) {
  return [JSON.stringify({ selector: 'by_quality', quality: field(b, 'QUALITY') }), O];
};
javascriptGenerator['card_selector_by_tag'] = function(b) {
  return [JSON.stringify({ selector: 'by_tag', tag: field(b, 'TAG') }), O];
};
javascriptGenerator['card_selector_random'] = function(b) {
  return [JSON.stringify({ selector: 'random', count: v(b, 'COUNT', '1'), condition: v(b, 'CONDITION', 'true') }), O];
};
javascriptGenerator['card_selector_all'] = function(b) {
  return [JSON.stringify({ selector: 'all', condition: v(b, 'CONDITION', 'true') }), O];
};

export function generateEffectsFromWorkspace(workspace) {
  const effects = [];
  const topBlocks = workspace.getTopBlocks(true);
  for (const topBlock of topBlocks) {
    let block = topBlock;
    while (block) {
      const code = javascriptGenerator.blockToCode(block, true);
      if (typeof code === 'string' && code.trim()) {
        try {
          const parsed = JSON.parse(code.trim().replace(/,$/, ''));
          effects.push(parsed);
        } catch(e) {}
      }
      block = block.getNextBlock();
    }
  }
  return effects;
}
