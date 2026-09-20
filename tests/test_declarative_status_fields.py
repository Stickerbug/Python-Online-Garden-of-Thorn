"""自定义状态的声明式字段：层数上限、自然衰减、事件上下文。

这一批把「不依赖数值修改钩子」的行为先做成通用能力：

* ``max_stack`` 截断层数（官方霜冻也在用同一字段）；
* ``decay`` / ``decay_timing`` 在自己回合开始/结束按 one/half/clear 衰减；
* 状态事件上下文补上攻击者、受击者与伤害量，供后续迁移「受击时」类状态；
* 官方 ``arctic:frost``、``jungle:fragile``、``bio:debt``、``hel:blazing_fire``
  已经改成靠声明执行，而不是逐条写在引擎里。
"""

import pytest

from pathlib import Path

import official_statuses
from cards import CARD_DEFS, CardInstance
from game_engine import ELIXIR_RECOVERY, GameEngine
from game_engine_2v2 import GameEngine2v2
from game_engine_urf import GameEngineInfiniteFire


STATUS_ID = 'probe:charged'


def make_engine(engine_cls=GameEngine, *, round_num=2):
    engine = engine_cls()
    engine.phase = 'action'
    engine.round_num = round_num
    engine.first_player = 0
    engine.current_player = 0
    for player in engine.players:
        player.health = 100
        player.max_health = 100
        player.elixir = 0
        player.magic = 100
        player.fire = 0
        player.poison = 0
        player.hand = []
        player.deck = []
        player.discard = []
        player.exile = []
        player.equipment = []
        player.custom_statuses = {}
    return engine


def apply_status(engine, player_id, status, amount):
    engine._apply_status_op(
        player_id, None, {}, False, 'status_add_named',
        player_id, status, amount,
    )


def test_custom_status_max_stack_clamps_add():
    engine = make_engine()
    engine.v2_status_defs = {
        STATUS_ID: {'id': STATUS_ID, 'stacking': 'stack', 'max_stack': 3},
    }

    apply_status(engine, 0, STATUS_ID, 5)

    assert engine.players[0].custom_statuses[STATUS_ID] == 3


def test_custom_status_flat_decay_timing_removes_one_at_turn_start():
    engine = make_engine()
    engine.v2_status_defs = {
        STATUS_ID: {'id': STATUS_ID, 'stacking': 'stack', 'decay_timing': 'turn_start'},
    }
    engine.players[0].custom_statuses[STATUS_ID] = 3

    engine._apply_declared_status_decay(0, 'turn_start')

    assert engine.players[0].custom_statuses[STATUS_ID] == 2


def test_custom_status_decay_half_and_clear_modes():
    engine = make_engine()
    engine.v2_status_defs = {
        STATUS_ID: {
            'id': STATUS_ID,
            'stacking': 'stack',
            'decay': {'timing': 'turn_end', 'mode': 'half'},
        },
        'probe:short': {
            'id': 'probe:short',
            'stacking': 'stack',
            'decay': {'timing': 'turn_end', 'mode': 'clear'},
        },
    }
    engine.players[0].custom_statuses[STATUS_ID] = 5
    engine.players[0].custom_statuses['probe:short'] = 2

    engine._apply_declared_status_decay(0, 'turn_end')

    assert engine.players[0].custom_statuses[STATUS_ID] == 2
    assert 'probe:short' not in engine.players[0].custom_statuses


def test_official_frost_declares_cap_and_turn_end_halving():
    definition = official_statuses.engine_status_def('arctic:frost')
    assert definition['max_stack'] == 60
    assert definition['decay'] == {'timing': 'turn_end', 'mode': 'half', 'log': 'zero'}

    engine = make_engine()
    # 别名键也要能被衰减归并到规范 id，避免同一个状态留两份层数。
    engine.players[0].custom_statuses['frost'] = 5

    engine._apply_declared_status_decay(0, 'turn_end')

    assert engine.players[0].custom_statuses.get('arctic:frost') == 2
    assert 'frost' not in engine.players[0].custom_statuses


def test_official_frost_zero_keeps_legacy_log():
    engine = make_engine()
    engine.players[0].custom_statuses['arctic:frost'] = 1

    engine._apply_declared_status_decay(0, 'turn_end')

    assert 'arctic:frost' not in engine.players[0].custom_statuses
    assert any('霜冻效果消失' in str(line) for line in engine.log)


def test_official_fragile_clears_at_turn_start_through_declaration():
    definition = official_statuses.engine_status_def('jungle:fragile')
    assert definition['decay'] == {'timing': 'turn_start', 'mode': 'clear'}

    engine = make_engine(round_num=1)
    engine.players[0].custom_statuses['fragile'] = 3

    engine._apply_turn_start_effects(0)

    assert 'fragile' not in engine.players[0].custom_statuses
    assert 'jungle:fragile' not in engine.players[0].custom_statuses


@pytest.mark.parametrize('engine_cls', [GameEngine, GameEngine2v2, GameEngineInfiniteFire])
def test_official_debt_declaration_loses_elixir_after_recovery(engine_cls):
    engine = make_engine(engine_cls)
    engine.players[0].custom_statuses['bio:debt'] = 2

    if engine_cls is GameEngine2v2:
        engine._apply_turn_start_effects_2v2(0)
    else:
        engine._apply_turn_start_effects(0)

    assert engine.players[0].custom_statuses.get('bio:debt') == 1
    assert engine.players[0].elixir == ELIXIR_RECOVERY - 1
    assert any('负债使其失去1E' in str(line) for line in engine.log)


def test_official_debt_does_not_lose_elixir_while_immune_but_still_decays():
    engine = make_engine()
    engine.players[0].custom_statuses['bio:debt'] = 2
    engine.players[0].custom_statuses['status_immune'] = 1

    engine._apply_turn_start_effects(0)

    assert engine.players[0].custom_statuses.get('bio:debt') == 1
    assert engine.players[0].elixir == ELIXIR_RECOVERY
    assert not any('负债使其失去1E' in str(line) for line in engine.log)


def test_status_event_context_exposes_damage_source_and_amount():
    engine = make_engine()
    engine.v2_status_defs = {
        'probe:mark': {
            'id': 'probe:mark',
            'stacking': 'stack',
            'events': {
                'on_damage_taken': [
                    {'op': 'log', 'message': 'probe:{damage_amount}:{event_source_player}:{source}'},
                ],
            },
        },
    }
    engine.players[1].custom_statuses['probe:mark'] = 1

    engine._trigger_v2_damage_status_events(1, 0, 7)

    assert any('probe:7:0:' in str(line) for line in engine.log)


def test_custom_status_stack_keys_sum_and_canonicalize_on_write():
    engine = make_engine()
    engine.v2_status_defs = {
        STATUS_ID: {
            'id': STATUS_ID,
            'stacking': 'stack',
            'stack_keys': [STATUS_ID, 'charged', '充能探针'],
        },
    }
    # 历史数据分散在两个别名键上，读取要按声明求和。
    engine.players[0].custom_statuses['charged'] = 2
    engine.players[0].custom_statuses['充能探针'] = 1
    assert engine._get_status_count(0, STATUS_ID) == 3

    apply_status(engine, 0, STATUS_ID, 2)

    # 增删归并到第一个键，不再留下两份层数。
    assert engine.players[0].custom_statuses == {STATUS_ID: 5}
    assert engine._get_status_count(0, STATUS_ID) == 5


def test_custom_status_on_heal_pre_can_modify_heal_amount():
    engine = make_engine()
    engine.v2_status_defs = {
        'probe:bandage': {
            'id': 'probe:bandage',
            'stacking': 'stack',
            'events': {
                'on_heal_pre': [
                    {
                        'op': 'add_var',
                        'name': 'heal_amount',
                        'value': {'op': 'status_stack', 'status': 'probe:bandage'},
                    }
                ],
            },
        },
    }
    player = engine.players[1]
    player.health = 50
    player.custom_statuses['probe:bandage'] = 3

    player.heal(5)

    assert player.health == 58


def test_official_extra_healing_declares_pre_heal_modifier():
    definition = official_statuses.engine_status_def('bio:extra_healing')
    assert definition['stack_keys'] == ['bio:extra_healing', 'extra_healing', '额外回复']
    assert definition['events']['on_heal_pre']

    engine = make_engine()
    player = engine.players[1]
    player.health = 50
    engine._bio_set_status_value(1, 'extra_healing', 2)

    player.heal(5)

    assert player.health == 57

    # 状态免疫只压制生效，不阻止层数存在。
    player.custom_statuses['status_immune'] = 1
    player.heal(5)
    assert player.health == 62


def test_official_toxic_poison_declares_stack_keys_and_resolved_event():
    definition = official_statuses.engine_status_def('jungle:toxic_poison')
    assert definition['stack_keys'] == ['jungle:toxic_poison', 'toxic_poison', '剧毒']
    assert definition['events']['on_poison_resolved']

    for storage_key in ('jungle:toxic_poison', 'toxic_poison'):
        engine = make_engine()
        engine.players[0].poison = 4
        engine.players[0].custom_statuses[storage_key] = 3

        engine._apply_turn_start_effects(0)

        # 中毒先造成 4 点伤害并减半为 2，再被剧毒追加 3 层。
        assert engine.players[0].poison == 5, storage_key
        assert engine.players[0].health == 96, storage_key
        assert any('剧毒施加3层中毒' in str(line) for line in engine.log), storage_key


def test_custom_status_on_cost_modifies_extra_card_cost():
    engine = make_engine()
    engine.v2_status_defs = {
        STATUS_ID: {
            'id': STATUS_ID,
            'stacking': 'stack',
            'events': {
                'on_cost': [
                    {
                        'op': 'add_var',
                        'name': 'cost_extra',
                        'value': {'op': 'div', 'values': [
                            {'op': 'status_stack', 'status': STATUS_ID}, 3,
                        ], 'round': 'floor'},
                    }
                ],
            },
        },
    }
    engine.players[0].custom_statuses[STATUS_ID] = 7
    card = CardInstance('Basic')

    assert engine._get_extra_e_for_card(0, card) == 2


def test_custom_status_modifiers_armor_is_passive():
    engine = make_engine()
    engine.v2_status_defs = {
        STATUS_ID: {
            'id': STATUS_ID,
            'stacking': 'stack',
            'modifiers': {'armor': {'op': 'add', 'value': {'op': 'stack'}}},
        },
    }
    engine.players[1].armor = 2
    engine.players[1].custom_statuses[STATUS_ID] = 3

    assert engine._effective_armor(1) == 5

    engine.players[1].custom_statuses['status_immune'] = 1
    assert engine._effective_armor(1) == 2


def test_custom_status_on_damage_pre_modifies_damage():
    engine = make_engine()
    engine.v2_status_defs = {
        STATUS_ID: {
            'id': STATUS_ID,
            'stacking': 'stack',
            'events': {
                'on_damage_pre': [
                    {
                        'op': 'set_var',
                        'name': 'damage_amount',
                        'value': {'op': 'max', 'values': [
                            0,
                            {'op': 'sub', 'values': [
                                {'op': 'var', 'name': 'damage_amount'}, 2,
                            ]},
                        ]},
                    }
                ],
            },
        },
    }
    engine.players[0].custom_statuses[STATUS_ID] = 1

    assert engine._run_declared_damage_pre(0, 5) == 3


def test_official_value_hooks_are_declared():
    frost = official_statuses.engine_status_def('arctic:frost')
    assert frost['events']['on_cost']['priority'] == 10
    fragile = official_statuses.engine_status_def('jungle:fragile')
    assert fragile['modifiers']['armor']['op'] == 'sub'
    root = official_statuses.engine_status_def('jungle:root_status')
    assert root['modifiers']['armor']['op'] == 'add'
    shield = official_statuses.engine_status_def('jungle:shield')
    assert shield['events']['on_damage_pre']['priority'] == 10
    conversion = official_statuses.engine_status_def('bio:shield_conversion')
    assert conversion['events']['on_heal_pre']['priority'] == 20


def test_official_frost_cost_and_shield_absorb_through_declarations():
    engine = make_engine()
    card = CardInstance('Basic')
    engine.players[0].custom_statuses['arctic:frost'] = 25
    assert engine._get_extra_e_for_card(0, card) == 2

    engine.players[1].health = 100
    engine.players[1].custom_statuses['jungle:shield'] = 10
    engine._deal_direct_damage(1, 6, '测试', 0)
    assert engine.players[1].health == 100
    assert engine.players[1].custom_statuses.get('jungle:shield') == 4


def test_official_fragile_and_root_armor_go_through_modifiers():
    engine = make_engine()
    engine.players[1].armor = 5
    engine.players[1].custom_statuses['jungle:fragile'] = 3
    assert engine._effective_armor(1) == 2

    engine.players[1].custom_statuses = {'jungle:root_status': 4}
    assert engine._effective_armor(1) == 9


def test_official_shield_conversion_uses_pre_heal_hook():
    engine = make_engine()
    player = engine.players[1]
    player.health = 50
    engine._bio_set_status_value(1, 'extra_healing', 2)
    engine._bio_set_status_value(1, 'shield_conversion', 2)

    player.heal(5)

    assert player.health == 50
    assert engine._custom_status_value(1, 'jungle:shield', 'shield') == 14
    assert engine._bio_status_value(1, 'shield_conversion') == 0


def test_official_luck_declares_damage_roll_and_consumes_layers():
    definition = official_statuses.engine_status_def('hel:luck')
    assert definition['events']['on_damage_roll']['priority'] == 10

    engine = make_engine()
    card = CardInstance('Basic')
    engine.players[0].custom_statuses['hel:luck'] = 10

    damage, is_crit = engine._hel_apply_lucky_crit_to_damage(0, 5, card)

    assert (damage, is_crit) == (10, True)
    assert engine._custom_status_value(0, 'hel:luck', 'luck') == 5


def test_official_luck_force_and_no_luck_flags():
    engine = make_engine()
    card = CardInstance('Basic')
    card._hel_force_crit = True
    engine.players[0].custom_statuses['hel:luck'] = 1

    damage, is_crit = engine._hel_apply_lucky_crit_to_damage(0, 5, card)
    assert (damage, is_crit) == (10, True)
    # force crit must not consume luck
    assert engine._custom_status_value(0, 'hel:luck', 'luck') == 1

    engine = make_engine()
    card = CardInstance('Basic')
    card._hel_no_luck_crit = True
    engine.players[0].custom_statuses['hel:luck'] = 99
    damage, is_crit = engine._hel_apply_lucky_crit_to_damage(0, 5, card)
    assert (damage, is_crit) == (5, False)
    assert engine._custom_status_value(0, 'hel:luck', 'luck') == 99


def test_official_luck_dry_run_prediction_does_not_consume_layers():
    engine = make_engine()
    card = CardInstance('Basic')
    engine.players[0].custom_statuses['hel:luck'] = 100

    damage, is_crit = engine._run_declared_damage_roll(0, 5, card, 0, dry_run=True)

    assert (damage, is_crit) == (10, True)
    assert engine._custom_status_value(0, 'hel:luck', 'luck') == 100


def test_official_blood_debt_declares_physical_damage_taken():
    definition = official_statuses.engine_status_def('ocean:blood_debt')
    assert definition['events']['on_damage_taken']['priority'] == 10

    engine = make_engine()
    engine.players[1].custom_statuses['blood_debt'] = 4

    engine._record_damage(1, 5, 0, damage_type='physical')

    assert engine.players[0].elixir == 4
    assert 'blood_debt' not in engine.players[1].custom_statuses
    assert any('血债解除' in str(line) for line in engine.log)


def test_official_blood_debt_ignores_magic_damage():
    engine = make_engine()
    engine.players[1].custom_statuses['ocean:blood_debt'] = 4

    engine._record_damage(1, 5, 0, damage_type='magic')

    assert engine.players[0].elixir == 0
    assert engine.players[1].custom_statuses.get('ocean:blood_debt') == 4


def test_official_unable_counter_declares_card_enter_hand():
    definition = official_statuses.engine_status_def('ocean:unable_counter')
    assert definition['events']['on_card_added_to_hand']['priority'] == 10

    from cards import CARD_DEFS, CardDef

    card_id = '__test_unable_counter_probe__'
    CARD_DEFS[card_id] = CardDef(
        id=card_id, name_en='Counter Probe', name_cn='反制探针',
        cost_e=0, cost_m=0, card_type='guard', count=1,
        quality='test', description='', effect_text='', flags=set(),
    )
    engine = make_engine()
    card = CardInstance(card_id)
    engine.players[0].custom_statuses['ocean:unable_counter'] = 2
    engine.players[0].hand = [card]

    engine._handle_card_enter_hand(0, card)

    assert card not in engine.players[0].hand
    assert card in engine.players[0].discard
    assert engine._custom_status_value(0, 'ocean:unable_counter', 'unable_counter') == 1
    assert any('无法反制' in str(line) for line in engine.log)


def test_official_shield_decay_condition_respects_sunflower(monkeypatch):
    definition = official_statuses.engine_status_def('jungle:shield')
    assert definition['decay']['condition']

    engine = make_engine()
    engine.players[0].custom_statuses['jungle:shield'] = 9
    monkeypatch.setattr(
        engine, '_has_flag_equipment',
        lambda player_id, flag: flag == 'shield_decay_immune',
    )
    engine._apply_declared_status_decay(0, 'turn_start')
    assert engine._custom_status_value(0, 'jungle:shield', 'shield') == 9

    monkeypatch.setattr(engine, '_has_flag_equipment', lambda player_id, flag: False)
    engine._apply_declared_status_decay(0, 'turn_start')
    assert engine._custom_status_value(0, 'jungle:shield', 'shield') == 4


def _with_jungle_root():
    from mod_loader import load_mod

    package = Path(__file__).resolve().parents[1] / 'mods' / 'Jungle Cards Addition.gtnmod'
    mod = load_mod(str(package))
    cards = {card.id: card for card in mod.cards}
    previous = CARD_DEFS.get('Root')
    CARD_DEFS['Root'] = cards['Root'].to_card_def()
    return previous


def _equip_jungle_root(engine, target_id=1):
    card = CardInstance('Root')
    engine.current_player = 0
    engine.players[0].elixir = 50
    engine.players[0].hand = [card]
    result = engine.play_card(
        0, card.instance_id,
        {'target_player': target_id, 'target_player_id': target_id, 'target_id': target_id},
    )
    assert result.get('success'), result
    equipment = engine.players[0].equipment[-1]
    equipment.custom_vars['jungle_root_layers'] = 2
    engine.players[target_id].custom_statuses['jungle:root_status'] = 2
    return equipment


def test_official_root_damage_taken_decrements_bound_equipment():
    previous = _with_jungle_root()
    try:
        engine = make_engine()
        equipment = _equip_jungle_root(engine)

        dealt = engine.deal_attack_damage(1, 5, attacker_id=0)

        assert dealt == 3  # root armor 2 applied before the layer is consumed
        assert equipment.custom_vars.get('jungle_root_layers') == 1
        assert engine.players[1].custom_statuses.get('jungle:root_status') == 1
    finally:
        if previous is None:
            CARD_DEFS.pop('Root', None)
        else:
            CARD_DEFS['Root'] = previous


def test_official_root_damage_taken_ignores_magic_and_immunity():
    previous = _with_jungle_root()
    try:
        engine = make_engine()
        equipment = _equip_jungle_root(engine)

        engine._deal_direct_damage(1, 5, '测试', 0, damage_type='magic')
        assert equipment.custom_vars.get('jungle_root_layers') == 2
        assert engine.players[1].custom_statuses.get('jungle:root_status') == 2

        engine.players[1].custom_statuses['status_immune'] = 1
        engine.deal_attack_damage(1, 5, attacker_id=0)
        assert equipment.custom_vars.get('jungle_root_layers') == 2
        assert engine.players[1].custom_statuses.get('jungle:root_status') == 2
    finally:
        if previous is None:
            CARD_DEFS.pop('Root', None)
        else:
            CARD_DEFS['Root'] = previous


def test_official_status_tags_are_exposed_in_engine_and_client_defs():
    shield = official_statuses.engine_status_def('jungle:shield')
    assert shield['tags'] == ['buff', 'shield']
    frost = official_statuses.engine_status_def('arctic:frost')
    assert frost['tags'] == ['debuff', 'cost']
    client = {item['id']: item for item in official_statuses.client_defs()}
    assert client['jungle:toxic_poison']['tags'] == ['debuff', 'poison']


def test_status_tag_queries_respect_immunity_and_namespace():
    engine = make_engine()
    engine.players[0].custom_statuses = {
        'jungle:shield': 3,
        'arctic:frost': 5,
        'bio:debt': 2,
    }
    assert engine._player_has_status_tag(0, 'buff')
    assert engine._player_has_status_tag(0, 'shield')
    assert engine._player_has_status_tag(0, 'debuff')
    # same tag but narrowed to one status (short id also matches)
    assert engine._player_has_status_tag(0, 'buff', status_id='shield')
    assert not engine._player_has_status_tag(0, 'cost', status_id='shield')

    engine.players[0].custom_statuses['status_immune'] = 1
    assert not engine._player_has_status_tag(0, 'buff')
    assert not engine._player_has_status_tag(0, 'debuff')


def test_status_tag_expression_ops():
    from mod_runtime_v2 import check_v2_condition, eval_v2_value

    engine = make_engine()
    engine.players[0].custom_statuses = {'jungle:shield': 3, 'hel:luck': 2}
    context = {'source_player': 0, 'target_player': 1, 'vars': {}}

    assert check_v2_condition(
        engine, context,
        {'op': 'has_status_tag', 'tag': 'buff', 'target': 'source'},
    )
    assert eval_v2_value(
        engine, context,
        {'op': 'status_tag_count', 'tag': 'buff', 'target': 'source'},
    ) == 2
    assert eval_v2_value(
        engine, context,
        {'op': 'status_tag_layers', 'tag': 'buff', 'target': 'source'},
    ) == 5
    assert eval_v2_value(
        engine, context,
        {'op': 'status_tags', 'status': 'jungle:shield'},
    ) == ['buff', 'shield']


def test_custom_status_tags_are_queryable():
    engine = make_engine()
    engine.v2_status_defs = {
        STATUS_ID: {'id': STATUS_ID, 'stacking': 'stack', 'tags': ['debuff', 'custom']},
    }
    engine.players[0].custom_statuses[STATUS_ID] = 2
    engine.players[0].custom_statuses['arctic:frost'] = 1

    from mod_runtime_v2 import eval_v2_value

    context = {'source_player': 0, 'target_player': 1, 'vars': {}}
    assert engine._player_has_status_tag(0, 'custom')
    assert eval_v2_value(
        engine, context,
        {'op': 'status_tag_count', 'tag': 'debuff', 'target': 'source'},
    ) == 2


def test_mod_validator_accepts_status_tags():
    from mod_validator_v2 import validate_mod_v2

    payload = {
        'format_version': 2,
        'manifest': {
            'id': 'tagdemo', 'resource_namespace': 'tagdemo',
            'name': 'Tag Demo', 'version': '1.0.0', 'api_version': '2.0',
        },
        'registries': {
            'statuses': [
                {'id': 'tagdemo:marked', 'stacking': 'stack', 'tags': ['debuff', 'demo']},
            ],
        },
    }
    report = validate_mod_v2(payload, source='tagdemo', allow_reserved_namespaces=True)
    assert not report.errors, report.errors

    bad = {
        'format_version': 2,
        'manifest': {
            'id': 'tagdemo', 'resource_namespace': 'tagdemo',
            'name': 'Tag Demo', 'version': '1.0.0', 'api_version': '2.0',
        },
        'registries': {'statuses': [{'id': 'tagdemo:marked', 'tags': 'debuff'}]},
    }
    report = validate_mod_v2(bad, source='tagdemo', allow_reserved_namespaces=True)
    assert any('.tags' in str(item) for item in report.errors)
