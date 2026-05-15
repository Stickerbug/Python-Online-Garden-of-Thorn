import * as Blockly from 'blockly';
import { ENUMS, COLORS } from './enums.js';

const C = COLORS.CARD_SELECTOR;

Blockly.defineBlocksWithJsonArray([
  {
    type: 'card_selector_by_id',
    message0: '卡牌 ID 为 %1',
    args0: [
      { type: 'field_input', name: 'CARD_ID', text: 'CardID' },
    ],
    output: 'CardSelector',
    colour: C,
  },
  {
    type: 'card_selector_by_type',
    message0: '卡牌类型为 %1',
    args0: [
      { type: 'field_dropdown', name: 'CARD_TYPE', options: ENUMS.CARD_TYPE },
    ],
    output: 'CardSelector',
    colour: C,
  },
  {
    type: 'card_selector_by_quality',
    message0: '卡牌品质为 %1',
    args0: [
      { type: 'field_dropdown', name: 'QUALITY', options: ENUMS.QUALITY },
    ],
    output: 'CardSelector',
    colour: C,
  },
  {
    type: 'card_selector_by_tag',
    message0: '卡牌拥有标签 %1',
    args0: [
      { type: 'field_dropdown', name: 'TAG', options: ENUMS.TAG },
    ],
    output: 'CardSelector',
    colour: C,
  },
  {
    type: 'card_selector_random',
    message0: '随机 %1 张满足 %2 的牌',
    args0: [
      { type: 'input_value', name: 'COUNT', check: 'Number' },
      { type: 'input_value', name: 'CONDITION', check: 'Boolean' },
    ],
    output: 'CardSelector',
    colour: C,
  },
  {
    type: 'card_selector_all',
    message0: '所有满足 %1 的牌',
    args0: [
      { type: 'input_value', name: 'CONDITION', check: 'Boolean' },
    ],
    output: 'CardSelector',
    colour: C,
  },
]);
