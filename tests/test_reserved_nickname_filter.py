import pytest

from moderation import check_nickname_risk, match_reserved_nickname


@pytest.mark.parametrize(
    ('nickname', 'reserved_name'),
    [
        ('PHELREN', 'Phelren'),
        ('p-h-e-l-r-e-n', 'Phelren'),
        ('ph3lr3n', 'Phelren'),
        ('Phe\u200blren', 'Phelren'),
        ('рһ3ӏr3ո', 'Phelren'),
        ('Phelrenn', 'Phelren'),
        ('Phelrne', 'Phelren'),
        ('PhelrenV1', 'Phelren'),
        ('STICKERBUG', 'Stickerbug'),
        ('sticker_bug', 'Stickerbug'),
        ('5t1ck3r8ug', 'Stickerbug'),
        ('ѕtіckerbug', 'Stickerbug'),
        ('Stikerbug', 'Stickerbug'),
        ('Stcikerbug', 'Stickerbug'),
        ('OfficialStickerbug', 'Stickerbug'),
        ('NETHERDOG', 'NetherDog'),
        ('nether_dog', 'NetherDog'),
        ('n3th3rd0g', 'NetherDog'),
        ('NeterDog', 'NetherDog'),
        ('NetherDgo', 'NetherDog'),
        ('MyNetherDog', 'NetherDog'),
        ('ERIC', 'Eric'),
        ('E-r-i-c', 'Eric'),
        ('3r1c', 'Eric'),
        ('еrіс', 'Eric'),
        ('Ｅｒｉｃ', 'Eric'),
        ('Eric123', 'Eric'),
        ('OfficialEric', 'Eric'),
        ('EricAdmin', 'Eric'),
    ],
)
def test_reserved_nickname_variants_are_blocked(nickname, reserved_name):
    result = check_nickname_risk(nickname, guest=True)

    assert match_reserved_nickname(nickname) == reserved_name
    assert result['blocked'] is True
    assert result['reserved_name'] == reserved_name
    assert any(item['category'] == 'reserved_identity' for item in result['matched_rules'])


@pytest.mark.parametrize(
    'nickname',
    [
        'Phelan',
        'Felren',
        'Helen',
        '菲尔伦',
        'Sticker',
        'BugSticker',
        'Stickerboy',
        'Stingerbug',
        'Nether',
        'HotDog',
        'NetherDragon',
        'Erica',
        'Erick',
        'Erik',
        'Erin',
        'Eris',
        'America',
    ],
)
def test_unrelated_or_intentionally_allowed_names_are_not_reserved(nickname):
    assert match_reserved_nickname(nickname) is None
    assert check_nickname_risk(nickname, guest=False)['reserved_name'] is None
