import * as Blockly from 'blockly';
import { COLORS } from './enums.js';

const C = COLORS.TARGET;

Blockly.defineBlocksWithJsonArray([
  {
    type: 'target_self',
    message0: '己方',
    output: 'Target',
    colour: C,
  },
  {
    type: 'target_enemy',
    message0: '敌方',
    output: 'Target',
    colour: C,
  },
  {
    type: 'target_both',
    message0: '双方',
    output: 'Target',
    colour: C,
  },
  {
    type: 'target_random',
    message0: '随机一方',
    output: 'Target',
    colour: C,
  },
  {
    type: 'target_event_target',
    message0: '当前事件的目标',
    output: 'Target',
    colour: C,
  },
  {
    type: 'target_event_source',
    message0: '当前事件的来源',
    output: 'Target',
    colour: C,
  },
  {
    type: 'target_last_actor',
    message0: '上次行动的一方',
    output: 'Target',
    colour: C,
  },
  {
    type: 'target_highest_health',
    message0: '生命值最高的一方',
    output: 'Target',
    colour: C,
  },
  {
    type: 'target_lowest_health',
    message0: '生命值最低的一方',
    output: 'Target',
    colour: C,
  },
]);
