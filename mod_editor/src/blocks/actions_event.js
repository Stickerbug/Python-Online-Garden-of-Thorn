import * as Blockly from 'blockly';
import { COLORS } from './enums.js';

const C = COLORS.ACTION;

Blockly.defineBlocksWithJsonArray([
  {
    type: 'action_broadcast_event',
    message0: '广播事件 %1',
    args0: [
      { type: 'field_input', name: 'EVENT_NAME', text: 'custom_event' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'trigger_on_event',
    message0: '当收到事件 %1 时',
    args0: [
      { type: 'field_input', name: 'EVENT_NAME', text: 'custom_event' },
    ],
    nextStatement: null,
    colour: COLORS.TRIGGER,
    tooltip: '当收到自定义事件时触发（帽子积木）',
  },
]);
