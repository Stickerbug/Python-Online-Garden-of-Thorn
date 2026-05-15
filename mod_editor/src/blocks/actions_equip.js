import * as Blockly from 'blockly';
import { COLORS } from './enums.js';

const C = COLORS.ACTION;

Blockly.defineBlocksWithJsonArray([
  {
    type: 'action_destroy_random_equip',
    message0: '摧毁 %1 的一张随机装备',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_destroy_all_equip',
    message0: '摧毁 %1 的所有装备',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_destroy_all_field_equip',
    message0: '摧毁场上所有装备',
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_equip_protection',
    message0: '获得一层装备保护',
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_remove_equip_protection',
    message0: '移除 %1 的装备保护',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_place_as_equip',
    message0: '将此牌作为装备置于场上',
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
]);
