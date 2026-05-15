import * as Blockly from 'blockly';
import { ENUMS, COLORS } from './enums.js';

const C = COLORS.RESPONSE;

Blockly.defineBlocksWithJsonArray([
  {
    type: 'response_declare',
    message0: '响应声明：时机 %1 消耗 E:%2 M:%3',
    args0: [
      { type: 'field_dropdown', name: 'TIMING', options: ENUMS.RESPONSE_TIMING },
      { type: 'field_number', name: 'COST_E', value: 0, min: 0 },
      { type: 'field_number', name: 'COST_M', value: 0, min: 0 },
    ],
    nextStatement: null,
    colour: C,
    tooltip: '反制响应声明',
  },
]);
