import * as Blockly from 'blockly';
import { COLORS } from './enums.js';

const C = COLORS.ACTION;

Blockly.defineBlocksWithJsonArray([
  {
    type: 'action_damage',
    message0: '对 %1 造成 %2 点物理伤害',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
    tooltip: '对目标造成物理伤害',
  },
  {
    type: 'action_damage_multi',
    message0: '对 %1 造成 %2 × %3 点物理伤害',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
      { type: 'input_value', name: 'TIMES', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
    tooltip: '对目标造成多次物理伤害',
  },
  {
    type: 'action_heal',
    message0: '回复 %1 %2 点生命',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
    tooltip: '回复目标生命值',
  },
  {
    type: 'action_set_health',
    message0: '将 %1 的生命值设为 %2',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
    tooltip: '设置目标生命值',
  },
  {
    type: 'action_modify_damage',
    message0: '修改当前伤害值：%1',
    args0: [
      { type: 'field_input', name: 'FORMULA', text: 'value - 9' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
    tooltip: '修改当前伤害值，可用value引用原值',
  },
]);
