import * as Blockly from 'blockly';
import { ENUMS, COLORS } from './enums.js';

const C = COLORS.VALUE;

Blockly.defineBlocksWithJsonArray([
  {
    type: 'value_number',
    message0: '%1',
    args0: [
      { type: 'field_number', name: 'NUM', value: 0 },
    ],
    output: 'Number',
    colour: C,
  },
  {
    type: 'value_target_attribute',
    message0: '%1 的 %2',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'field_dropdown', name: 'ATTR', options: ENUMS.ATTRIBUTE },
    ],
    output: 'Number',
    colour: C,
  },
  {
    type: 'value_play_count',
    message0: '此卡牌打出次数',
    output: 'Number',
    colour: C,
  },
  {
    type: 'value_equip_turns',
    message0: '此牌已装备回合数',
    output: 'Number',
    colour: C,
  },
  {
    type: 'value_durability',
    message0: '此牌当前耐久',
    output: 'Number',
    colour: C,
  },
  {
    type: 'value_incoming_damage',
    message0: '当前/即将受到的伤害值',
    output: 'Number',
    colour: C,
  },
  {
    type: 'value_last_damage',
    message0: '上次受到的伤害值',
    output: 'Number',
    colour: C,
  },
  {
    type: 'value_status_count',
    message0: '%1 的 %2 层数',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'field_dropdown', name: 'STATUS', options: ENUMS.STATUS },
    ],
    output: 'Number',
    colour: C,
  },
  {
    type: 'value_hand_size',
    message0: '%1 的手牌数量',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    output: 'Number',
    colour: C,
  },
  {
    type: 'value_discard_size',
    message0: '%1 的弃牌堆数量',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    output: 'Number',
    colour: C,
  },
  {
    type: 'value_equip_count',
    message0: '%1 的装备数量',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    output: 'Number',
    colour: C,
  },
  {
    type: 'value_exile_size',
    message0: '%1 的放逐区数量',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    output: 'Number',
    colour: C,
  },
  {
    type: 'value_deck_remaining',
    message0: '%1 的牌堆剩余数量',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    output: 'Number',
    colour: C,
  },
  {
    type: 'value_turn_number',
    message0: '当前回合数',
    output: 'Number',
    colour: C,
  },
  {
    type: 'value_random',
    message0: '随机数（%1 到 %2）',
    args0: [
      { type: 'input_value', name: 'MIN', check: 'Number' },
      { type: 'input_value', name: 'MAX', check: 'Number' },
    ],
    output: 'Number',
    colour: C,
  },
  {
    type: 'value_math_op',
    message0: '%1 %2 %3',
    args0: [
      { type: 'input_value', name: 'A', check: 'Number' },
      { type: 'field_dropdown', name: 'OP', options: ENUMS.MATH_OP },
      { type: 'input_value', name: 'B', check: 'Number' },
    ],
    output: 'Number',
    colour: C,
  },
  {
    type: 'value_round',
    message0: '%1 %2',
    args0: [
      { type: 'field_dropdown', name: 'MODE', options: ENUMS.ROUND_MODE },
      { type: 'input_value', name: 'VALUE', check: 'Number' },
    ],
    output: 'Number',
    colour: C,
  },
  {
    type: 'value_min_max',
    message0: '取 %1 和 %2 的 %3',
    args0: [
      { type: 'input_value', name: 'A', check: 'Number' },
      { type: 'input_value', name: 'B', check: 'Number' },
      { type: 'field_dropdown', name: 'MODE', options: [['较大', 'max'], ['较小', 'min']] },
    ],
    output: 'Number',
    colour: C,
  },
  {
    type: 'value_clamp',
    message0: '钳制 %1 在 %2 和 %3 之间',
    args0: [
      { type: 'input_value', name: 'VALUE', check: 'Number' },
      { type: 'input_value', name: 'MIN', check: 'Number' },
      { type: 'input_value', name: 'MAX', check: 'Number' },
    ],
    output: 'Number',
    colour: C,
  },
]);
