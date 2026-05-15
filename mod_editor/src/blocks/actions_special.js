import * as Blockly from 'blockly';
import { ENUMS, COLORS } from './enums.js';

const C = COLORS.ACTION;

Blockly.defineBlocksWithJsonArray([
  {
    type: 'action_exile_this',
    message0: '放逐此牌',
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_move_to_discard',
    message0: '将此牌移入弃牌堆',
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_move_to_deck',
    message0: '将此牌移入牌堆 %1',
    args0: [
      { type: 'field_dropdown', name: 'POSITION', options: ENUMS.POSITION },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_global_damage_mult',
    message0: '全场伤害倍率设为 %1',
    args0: [
      { type: 'input_value', name: 'MULTIPLIER', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_global_heal_mult',
    message0: '全场治疗倍率设为 %1',
    args0: [
      { type: 'input_value', name: 'MULTIPLIER', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_global_cost_mult',
    message0: '全场能量消耗倍率设为 %1',
    args0: [
      { type: 'input_value', name: 'MULTIPLIER', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_swap_health',
    message0: '交换 %1 与 %2 的生命值',
    args0: [
      { type: 'input_value', name: 'TARGET1', check: 'Target' },
      { type: 'input_value', name: 'TARGET2', check: 'Target' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_swap_hands',
    message0: '交换 %1 与 %2 的手牌',
    args0: [
      { type: 'input_value', name: 'TARGET1', check: 'Target' },
      { type: 'input_value', name: 'TARGET2', check: 'Target' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
]);
