import * as Blockly from 'blockly';
import { ENUMS, COLORS } from './enums.js';

const C = COLORS.MANUAL_TRIGGER;

Blockly.defineBlocksWithJsonArray([
  {
    type: 'trigger_manual',
    message0: '触发声明：时机 %1 消耗 E:%2 M:%3 条件：%4 触发后摧毁：%5',
    args0: [
      { type: 'field_dropdown', name: 'TIMING', options: ENUMS.TRIGGER_TIMING },
      { type: 'field_number', name: 'COST_E', value: 0, min: 0 },
      { type: 'field_number', name: 'COST_M', value: 0, min: 0 },
      { type: 'input_value', name: 'CONDITION', check: 'Boolean' },
      { type: 'field_dropdown', name: 'DESTROY', options: ENUMS.BOOL_DROPDOWN },
    ],
    nextStatement: null,
    colour: C,
    tooltip: '手动触发声明，指定触发时机和消耗',
  },
]);
