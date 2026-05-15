import * as Blockly from 'blockly';
import { COLORS } from './enums.js';

const C = COLORS.CONTROL;

Blockly.defineBlocksWithJsonArray([
  {
    type: 'control_if',
    message0: '如果 %1 那么',
    args0: [
      { type: 'input_value', name: 'CONDITION', check: 'Boolean' },
    ],
    message1: '%1',
    args1: [
      { type: 'input_statement', name: 'DO' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'control_if_else',
    message0: '如果 %1 那么',
    args0: [
      { type: 'input_value', name: 'CONDITION', check: 'Boolean' },
    ],
    message1: '%1',
    args1: [
      { type: 'input_statement', name: 'DO' },
    ],
    message2: '否则',
    message3: '%1',
    args3: [
      { type: 'input_statement', name: 'ELSE' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'control_repeat',
    message0: '重复 %1 次',
    args0: [
      { type: 'input_value', name: 'TIMES', check: 'Number' },
    ],
    message1: '%1',
    args1: [
      { type: 'input_statement', name: 'DO' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'control_repeat_until',
    message0: '重复直到 %1',
    args0: [
      { type: 'input_value', name: 'CONDITION', check: 'Boolean' },
    ],
    message1: '%1',
    args1: [
      { type: 'input_statement', name: 'DO' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'control_for_each',
    message0: '对每个 %1 中的目标执行',
    args0: [
      { type: 'input_value', name: 'TARGET_LIST', check: 'Target' },
    ],
    message1: '%1',
    args1: [
      { type: 'input_statement', name: 'DO' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'control_after_all',
    message0: '执行所有效果后',
    message1: '%1',
    args1: [
      { type: 'input_statement', name: 'DO' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'control_random',
    message0: '随机执行 %1 或 %2',
    args0: [
      { type: 'input_statement', name: 'BRANCH_A' },
      { type: 'input_statement', name: 'BRANCH_B' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
]);
