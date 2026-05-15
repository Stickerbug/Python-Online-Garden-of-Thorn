import * as Blockly from 'blockly';
import { ENUMS, COLORS } from './enums.js';

const C = COLORS.ACTION;

Blockly.defineBlocksWithJsonArray([
  {
    type: 'action_fission',
    message0: '选择手中一张 %1，使其下次打出额外打出 %2 次',
    args0: [
      { type: 'field_dropdown', name: 'CARD_TYPE', options: ENUMS.CARD_TYPE },
      { type: 'input_value', name: 'TIMES', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_multiply_next_damage',
    message0: '将选定卡牌的下次伤害变为 %1 倍',
    args0: [
      { type: 'input_value', name: 'MULTIPLIER', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_reduce_next_cost',
    message0: '将选定卡牌的下次费用减少 %1',
    args0: [
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_increase_next_cost',
    message0: '将选定卡牌的下次费用增加 %1',
    args0: [
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_fusion',
    message0: '选择手中 %1 张相同 %2，第一张伤害增加 %3 倍，丢弃其余',
    args0: [
      { type: 'input_value', name: 'COUNT', check: 'Number' },
      { type: 'field_dropdown', name: 'CARD_TYPE', options: ENUMS.CARD_TYPE },
      { type: 'input_value', name: 'MULTIPLIER', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_add_tag',
    message0: '为一张卡牌添加标签 %1',
    args0: [
      { type: 'field_dropdown', name: 'TAG', options: ENUMS.TAG },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_remove_tag',
    message0: '移除一张卡牌的标签 %1',
    args0: [
      { type: 'field_dropdown', name: 'TAG', options: ENUMS.TAG },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_transform_card',
    message0: '将一张手牌变为另一张牌的复制',
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
]);
