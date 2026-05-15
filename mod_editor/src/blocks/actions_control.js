import * as Blockly from 'blockly';
import { ENUMS, COLORS } from './enums.js';

const C = COLORS.ACTION;

Blockly.defineBlocksWithJsonArray([
  {
    type: 'action_block_action',
    message0: '%1 本回合无法行动',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_block_card_type',
    message0: '%1 本回合无法使用 %2',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'field_dropdown', name: 'CARD_TYPE', options: ENUMS.CARD_TYPE },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_force_card_type',
    message0: '%1 本回合仅可使用 %2',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'field_dropdown', name: 'CARD_TYPE', options: ENUMS.CARD_TYPE },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_nullify_current_card',
    message0: '使 %1 当前使用的 %2 失效',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
      { type: 'field_dropdown', name: 'CARD_TYPE', options: ENUMS.CARD_TYPE },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_invincible',
    message0: '%1 本回合无敌',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_untargetable',
    message0: '%1 无法被攻击选中',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_skip_turn',
    message0: '跳过 %1 的下一个回合',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_extra_turn',
    message0: '%1 获得一个额外回合',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_force_end_turn',
    message0: '强制结束当前回合',
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
  {
    type: 'action_mark_self_damage_source',
    message0: '将 %1 受到的下次伤害来源标记为自身',
    args0: [
      { type: 'input_value', name: 'TARGET', check: 'Target' },
    ],
    previousStatement: null,
    nextStatement: null,
    colour: C,
  },
]);
