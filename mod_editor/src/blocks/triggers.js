import * as Blockly from 'blockly';
import { ENUMS, COLORS } from './enums.js';

const C = COLORS.TRIGGER;

Blockly.defineBlocksWithJsonArray([
  {
    type: 'trigger_on_play',
    message0: '当卡牌打出时',
    nextStatement: null,
    colour: C,
    tooltip: '卡牌被打出时触发',
  },
  {
    type: 'trigger_on_friendly_turn_start',
    message0: '当友方回合开始时',
    nextStatement: null,
    colour: C,
    tooltip: '友方回合开始时触发',
  },
  {
    type: 'trigger_on_enemy_turn_start',
    message0: '当敌方回合开始时',
    nextStatement: null,
    colour: C,
    tooltip: '敌方回合开始时触发',
  },
  {
    type: 'trigger_on_phys_damage',
    message0: '当受到物理伤害时',
    nextStatement: null,
    colour: C,
    tooltip: '受到物理伤害时触发',
  },
  {
    type: 'trigger_on_any_damage',
    message0: '当受到任意伤害时',
    nextStatement: null,
    colour: C,
    tooltip: '受到任意类型伤害时触发',
  },
  {
    type: 'trigger_on_lethal_damage',
    message0: '当即将受到致命伤害时',
    nextStatement: null,
    colour: C,
    tooltip: '即将受到致命伤害时触发',
  },
  {
    type: 'trigger_on_draw_this',
    message0: '当抽到此牌时',
    nextStatement: null,
    colour: C,
    tooltip: '此牌被抽到时触发',
  },
  {
    type: 'trigger_on_end_turn_hand',
    message0: '当回合结束时（手牌中）',
    nextStatement: null,
    colour: C,
    tooltip: '回合结束且此牌在手牌中时触发',
  },
  {
    type: 'trigger_on_overflow_discard',
    message0: '当因爆牌将弃入弃牌堆时',
    nextStatement: null,
    colour: C,
    tooltip: '因手牌溢出被弃入弃牌堆时触发',
  },
  {
    type: 'trigger_on_destroy',
    message0: '当此牌被摧毁时',
    nextStatement: null,
    colour: C,
    tooltip: '此牌被摧毁时触发',
  },
  {
    type: 'trigger_on_durability_zero',
    message0: '当此牌耐久 ≤ 0 时',
    nextStatement: null,
    colour: C,
    tooltip: '此牌耐久度降为0或以下时触发',
  },
  {
    type: 'trigger_on_enemy_use_type',
    message0: '当敌方使用 %1 时',
    args0: [
      { type: 'field_dropdown', name: 'CARD_TYPE', options: ENUMS.CARD_TYPE },
    ],
    nextStatement: null,
    colour: C,
    tooltip: '敌方使用指定类型卡牌时触发',
  },
  {
    type: 'trigger_on_friendly_use_type',
    message0: '当友方使用 %1 时',
    args0: [
      { type: 'field_dropdown', name: 'CARD_TYPE', options: ENUMS.CARD_TYPE },
    ],
    nextStatement: null,
    colour: C,
    tooltip: '友方使用指定类型卡牌时触发',
  },
  {
    type: 'trigger_on_card_exile',
    message0: '当任意卡牌被放逐时',
    nextStatement: null,
    colour: C,
    tooltip: '任意卡牌被放逐时触发',
  },
  {
    type: 'trigger_on_deck_empty',
    message0: '当抽牌堆为空时',
    nextStatement: null,
    colour: C,
    tooltip: '抽牌堆为空时触发',
  },
  {
    type: 'trigger_on_self_magic_heal_cumulative',
    message0: '当友方累计回复 %1 点魔力时',
    args0: [
      { type: 'field_number', name: 'THRESHOLD', value: 5, min: 1 },
    ],
    nextStatement: null,
    colour: C,
    tooltip: '友方累计回复魔力达到阈值时触发',
  },
  {
    type: 'trigger_on_self_damage',
    message0: '当受到来自自身的伤害时',
    nextStatement: null,
    colour: C,
    tooltip: '受到来自自身的伤害时触发',
  },
]);
