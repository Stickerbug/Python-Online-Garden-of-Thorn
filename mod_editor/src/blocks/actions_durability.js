import * as Blockly from 'blockly';
import { COLORS } from './enums.js';

const C = COLORS.ACTION;

Blockly.defineBlocksWithJsonArray([
  {
    type: 'action_gain_durability',
    message0: '获得 %1 层耐久',
    args0: [
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_lose_durability',
    message0: '减少 %1 层耐久',
    args0: [
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_set_durability',
    message0: '设置耐久为 %1',
    args0: [
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_record_play_count',
    message0: '记录此牌打出次数，叠加层数',
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_record_equip_turns',
    message0: '记录此牌装备回合数',
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_reset_counter',
    message0: '重置此牌计数',
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_create_counter',
    message0: '获得 %1 个自定义计数器 %2',
    args0: [
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
      { type: 'field_input', name: 'NAME', text: 'counter1' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
]);
