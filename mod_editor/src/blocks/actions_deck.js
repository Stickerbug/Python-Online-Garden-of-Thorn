import * as Blockly from 'blockly';
import { ENUMS, COLORS } from './enums.js';

const C = COLORS.ACTION;

Blockly.defineBlocksWithJsonArray([
  {
    type: 'action_draw',
    message0: '抽 %1 张牌',
    args0: [
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_discard',
    message0: '丢弃 %1 张手牌',
    args0: [
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_choose_from_deck',
    message0: '从牌堆选择一张牌加入手牌',
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_choose_from_discard',
    message0: '从弃牌堆选择一张牌加入手牌',
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_choose_from_exile',
    message0: '从放逐区选择一张牌加入手牌',
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_reveal_hand',
    message0: '展示 %1 的手牌',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_reveal_deck_top',
    message0: '展示 %1 的牌堆顶 %2 张',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_steal_card',
    message0: '从 %1 手牌中选择一张加入己方手牌',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_copy_card',
    message0: '将一张手牌的复制加入手牌',
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_random_discard_from_hand',
    message0: '将 %1 手牌中的随机 %2 张置入弃牌堆',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'input_value', name: 'AMOUNT', check: 'Number' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_put_card_to_deck',
    message0: '将手牌中的一张牌置入牌堆 %1',
    args0: [
      { type: 'field_dropdown', name: 'POSITION', options: ENUMS.POSITION },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_shuffle_discard_into_deck',
    message0: '将弃牌堆洗入牌堆',
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_give_card_to_hand',
    message0: '将 %1 加入 %2 的手牌（若未满）',
    args0: [
      { type: 'input_value', name: 'CARD', check: 'CardSelector' },
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_give_card_to_deck',
    message0: '将 %1 加入 %2 的抽牌堆 %3',
    args0: [
      { type: 'input_value', name: 'CARD', check: 'CardSelector' },
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'field_dropdown', name: 'POSITION', options: ENUMS.POSITION },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_give_card_to_discard',
    message0: '将 %1 加入 %2 的弃牌堆',
    args0: [
      { type: 'input_value', name: 'CARD', check: 'CardSelector' },
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_remove_specific_card',
    message0: '消耗 %1 的 %2 中的 %3',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'field_dropdown', name: 'ZONE', options: ENUMS.ZONE },
      { type: 'input_value', name: 'CARD', check: 'CardSelector' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
]);
