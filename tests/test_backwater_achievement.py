from game_engine import PlayerState, qualifies_backwater_achievement


def test_untriggered_bandage_does_not_complete_last_stand():
    player = PlayerState(0)
    player.bandage_active = True

    assert not qualifies_backwater_achievement('1v1', True, player)


def test_bandage_death_countdown_without_invincibility_does_not_complete_last_stand():
    player = PlayerState(0)
    player.bandage_death_pending = True

    assert not qualifies_backwater_achievement('1v1', True, player)


def test_active_invincibility_completes_last_stand():
    player = PlayerState(0)
    player.invincible = True
    player.bandage_death_pending = True

    assert qualifies_backwater_achievement('1v1', True, player)
