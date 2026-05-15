import * as Blockly from 'blockly';
import { ENUMS, COLORS } from './enums.js';

const C = COLORS.CONDITION;

Blockly.defineBlocksWithJsonArray([
  {
    type: 'condition_compare',
    message0: '%1 %2 %3',
    args0: [
      { type: 'input_value', name: 'A', check: 'Number' },
      { type: 'field_dropdown', name: 'OP', options: ENUMS.COMPARE },
      { type: 'input_value', name: 'B', check: 'Number' },
    ],
    output: 'Boolean',
    colour: C,
  },
  {
    type: 'condition_equip_turns',
    message0: '此牌已装备回合数 %1 %2',
    args0: [
      { type: 'field_dropdown', name: 'OP', options: ENUMS.COMPARE },
      { type: 'input_value', name: 'VALUE', check: 'Number' },
    ],
    output: 'Boolean',
    colour: C,
  },
  {
    type: 'condition_durability',
    message0: '此牌耐久 %1 %2',
    args0: [
      { type: 'field_dropdown', name: 'OP', options: ENUMS.COMPARE },
      { type: 'input_value', name: 'VALUE', check: 'Number' },
    ],
    output: 'Boolean',
    colour: C,
  },
  {
    type: 'condition_damage_value',
    message0: '伤害值 %1 %2',
    args0: [
      { type: 'field_dropdown', name: 'OP', options: ENUMS.COMPARE },
      { type: 'input_value', name: 'VALUE', check: 'Number' },
    ],
    output: 'Boolean',
    colour: C,
  },
  {
    type: 'condition_target_attribute',
    message0: '%1 的 %2 %3 %4',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'field_dropdown', name: 'ATTR', options: ENUMS.ATTRIBUTE },
      { type: 'field_dropdown', name: 'OP', options: ENUMS.COMPARE },
      { type: 'input_value', name: 'VALUE', check: 'Number' },
    ],
    output: 'Boolean',
    colour: C,
  },
  {
    type: 'condition_has_tag',
    message0: '卡牌拥有标签 %1',
    args0: [
      { type: 'field_dropdown', name: 'TAG', options: ENUMS.TAG },
    ],
    output: 'Boolean',
    colour: C,
  },
  {
    type: 'condition_has_status',
    message0: '%1 拥有状态 %2',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'field_dropdown', name: 'STATUS', options: ENUMS.STATUS },
    ],
    output: 'Boolean',
    colour: C,
  },
  {
    type: 'condition_hand_has_type',
    message0: '%1 手牌中有 %2',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'field_dropdown', name: 'CARD_TYPE', options: ENUMS.CARD_TYPE },
    ],
    output: 'Boolean',
    colour: C,
  },
  {
    type: 'condition_has_equip',
    message0: '%1 装备槽中有卡牌',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    output: 'Boolean',
    colour: C,
  },
  {
    type: 'condition_event_card_type',
    message0: '事件来源的卡牌类型等于 %1',
    args0: [
      { type: 'field_dropdown', name: 'CARD_TYPE', options: ENUMS.CARD_TYPE },
    ],
    output: 'Boolean',
    colour: C,
  },
  {
    type: 'condition_turn_number',
    message0: '当前回合数 %1 %2',
    args0: [
      { type: 'field_dropdown', name: 'OP', options: ENUMS.COMPARE },
      { type: 'input_value', name: 'VALUE', check: 'Number' },
    ],
    output: 'Boolean',
    colour: C,
  },
  {
    type: 'condition_and_or',
    message0: '%1 %2 %3',
    args0: [
      { type: 'input_value', name: 'A', check: 'Boolean' },
      { type: 'field_dropdown', name: 'OP', options: ENUMS.AND_OR },
      { type: 'input_value', name: 'B', check: 'Boolean' },
    ],
    output: 'Boolean',
    colour: C,
  },
  {
    type: 'condition_not',
    message0: '非 %1',
    args0: [
      { type: 'input_value', name: 'BOOL', check: 'Boolean' },
    ],
    output: 'Boolean',
    colour: C,
  },
  {
    type: 'condition_hand_full',
    message0: '%1 的手牌已满',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    output: 'Boolean',
    colour: C,
  },
  {
    type: 'condition_zone_contains',
    message0: '%1 的 %2 包含 %3',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'field_dropdown', name: 'ZONE', options: ENUMS.ZONE },
      { type: 'input_value', name: 'CARD', check: 'CardSelector' },
    ],
    output: 'Boolean',
    colour: C,
  },
]);
