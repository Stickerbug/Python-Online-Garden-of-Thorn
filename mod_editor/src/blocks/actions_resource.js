import * as Blockly from 'blockly';
import { COLORS } from './enums.js';

const C = COLORS.ACTION;

Blockly.defineBlocksWithJsonArray([
  {
    type: 'action_gain_e',
    message0: '增加 %1 %2 点能量',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_gain_m',
    message0: '增加 %1 %2 点魔力',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_cost_e',
    message0: '消耗 %1 %2 点能量',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_cost_m',
    message0: '消耗 %1 %2 点魔力',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_mod_e_regen',
    message0: '%1 每回合能量回复增加 %2',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_mod_m_regen',
    message0: '%1 每回合魔力回复增加/减少 %2',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_mod_draw',
    message0: '%1 每回合抽牌数增加/减少 %2',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
]);
