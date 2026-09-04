"""Trace: 谁在绷带检查前清除了药丸/免疫。"""
import sys
sys.path.insert(0, r'E:\Garden of Thorn 荆棘花园\Python联机版')

from mod_loader import load_mod
from cards import CardInstance, CARD_DEFS
from game_engine import EquipmentInstance
from game_engine_2v2 import GameEngine2v2

vanilla = load_mod(r'E:\Garden of Thorn 荆棘花园\Python联机版\mods\Vanilla Cards.gtnmod')
for card in vanilla.cards:
    CARD_DEFS.setdefault(card.id, card.to_card_def())

TARGET = 2

engine = GameEngine2v2()
engine.phase = 'action'
engine.current_player = 0
for player in engine.players:
    player.hand = []
    player.deck = []
    player.discard = []
    player.exile = []
    player.equipment = []
    player.health = 6
    player.max_health = 30
    player.elixir = 30
    player.magic = 30
    player.dodge = 0
    player.armor = 0
    player.custom_statuses = {}
    player.custom_vars = {}

engine.players[TARGET].bandage_active = True
pill_card = CardInstance('Pill')
eq = EquipmentInstance(pill_card, owner=0)
eq.effect_target = TARGET
engine.players[0].equipment.append(eq)
engine.players[TARGET].custom_statuses['status_immune'] = 1

# 埋点：观察关键函数的调用顺序与状态
orig_check_yggs = GameEngine2v2._check_yggdrasil
orig_on_death = GameEngine2v2._on_player_death
orig_remove_eq_tp = GameEngine2v2._remove_equipment_targeting_dead_player
orig_is_immune = GameEngine2v2._is_status_immune
orig_expel = GameEngine2v2._expire_bandages_after_action

def traced_check_yggs(self, player_id):
    import traceback
    stack = ''.join(traceback.format_stack()[:-1])
    # 只显示文件:行号
    lines = [l.strip() for l in stack.splitlines() if 'File "' in l]
    print(f'>> _check_yggdrasil({player_id}) health={self.players[player_id].health} '
          f'bandage={self.players[player_id].bandage_active} '
          f'immune={self._is_status_immune(player_id)}')
    for l in lines[-6:]:
        print('    ', l)
    return orig_check_yggs(self, player_id)

def traced_on_death(self, player_id):
    import traceback
    lines = [l.strip() for l in ''.join(traceback.format_stack()[:-1]).splitlines() if 'File "' in l]
    print(f'>> _on_player_death({player_id}) health={self.players[player_id].health} '
          f'immune={self._is_status_immune(player_id)}')
    for l in lines[-8:]:
        print('    ', l)
    return orig_on_death(self, player_id)

def traced_remove_eq(self, dead_id):
    print(f'>> _remove_equipment_targeting_dead_player({dead_id})')
    return orig_remove_eq_tp(self, dead_id)

def traced_expel(self, action_player_id=None):
    print(f'>> _expire_bandages_after_action({action_player_id})')
    return orig_expel(self, action_player_id)

GameEngine2v2._check_yggdrasil = traced_check_yggs
GameEngine2v2._on_player_death = traced_on_death
GameEngine2v2._remove_equipment_targeting_dead_player = traced_remove_eq
GameEngine2v2._expire_bandages_after_action = traced_expel

attack = CardInstance('Basic')
engine.players[0].hand.append(attack)
result = engine.play_card(0, attack.instance_id, TARGET,
                          {'target_player': TARGET, 'target_player_id': TARGET, 'target_id': TARGET})
print(f'最终: health={engine.players[TARGET].health} '
      f'bandage={engine.players[TARGET].bandage_active} '
      f'death_pending={engine.players[TARGET].bandage_death_pending}')
