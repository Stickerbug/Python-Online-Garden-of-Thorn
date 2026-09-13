"""性能回归：模组数据不能在每个请求里重新深拷贝整包。

背景：login 一次会调用 load_all_mods() 3-6 次，旧实现每次 deepcopy 20 个包 /
352 张卡，玩家登录要 ~870ms、改模组设置要 ~1.2s，全部阻塞在单进程 eventlet
事件循环上。这里锁住「共享缓存 + 只读」的约定。
"""

import mod_loader
import mod_unlocks


def test_load_all_mods_returns_shared_cache():
    first = mod_loader.load_all_mods()
    second = mod_loader.load_all_mods()
    assert first is second


def test_get_enabled_mods_does_not_mutate_shared_cache():
    mods = mod_loader.load_all_mods()
    target = mods[0]
    original_enabled = target.enabled
    target.enabled = True
    try:
        copies = mod_loader.get_enabled_mods()
        assert copies[0] is not target
        assert copies[0].cards is target.cards
        assert target.enabled is True
    finally:
        target.enabled = original_enabled


def test_card_def_does_not_alias_mutable_mod_containers():
    mod = next(m for m in mod_loader.load_all_mods() if m.cards)
    card = mod.cards[0]
    card_def = card.to_card_def()
    assert card_def.flags is not card.flags
    assert card_def.effects is not card.effects
    assert card_def.scripts is not card.scripts
    card_def.flags.add('__perf_probe__')
    assert '__perf_probe__' not in card.flags


def test_official_mod_filenames_is_cached_by_signature(monkeypatch):
    mod_unlocks._OFFICIAL_NAMES_CACHE = None
    first = mod_unlocks.official_mod_filenames()
    calls = {'count': 0}
    original = mod_loader.load_all_mods

    def counted(force=False):
        calls['count'] += 1
        return original(force=force)

    monkeypatch.setattr(mod_loader, 'load_all_mods', counted)
    monkeypatch.setattr(mod_unlocks, 'load_all_mods', counted)
    second = mod_unlocks.official_mod_filenames()

    assert first == second
    assert calls['count'] == 0
