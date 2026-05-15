import * as Blockly from 'blockly';
import { ENUMS, COLORS } from './enums.js';

const C = COLORS.ACTION;

Blockly.defineBlocksWithJsonArray([
  {
    type: 'action_poison',
    message0: '对 %1 施加 %2 层中毒',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_burn',
    message0: '对 %1 施加 %2 层灼烧',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_vulnus',
    message0: '对 %1 施加 %2 层易伤',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_toxic',
    message0: '对 %1 施加 %2 层淬毒',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_add_armor',
    message0: '增加 %1 %2 点护甲',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_remove_armor',
    message0: '减少 %1 %2 点护甲',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_set_armor',
    message0: '将 %1 的护甲设为 %2',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_dodge_this',
    message0: '获得 1 层闪避（针对本次攻击）',
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_dodge_permanent',
    message0: '获得 %1 层常驻闪避',
    args0: [
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_clear_buffs',
    message0: '清除 %1 的所有正面效果',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_clear_debuffs',
    message0: '清除 %1 的所有负面效果',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_clear_all_effects',
    message0: '清除 %1 的所有效果',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_clear_status',
    message0: '清除 %1 的 %2',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'field_dropdown', name: 'STATUS', options: ENUMS.STATUS },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
]);
