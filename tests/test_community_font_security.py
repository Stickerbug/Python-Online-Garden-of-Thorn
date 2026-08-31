from pathlib import Path

import font_subsets


def test_font_subset_rejects_excessive_unique_characters(monkeypatch):
    monkeypatch.setattr(font_subsets, 'MAX_COMMUNITY_FONT_CHARS', 4)
    report = font_subsets.ensure_community_font_subset([{'text': 'ABCDE'}], generate=True)
    assert report['success'] is False
    assert report['generated'] is False
    assert '最多处理 4 个' in report['warnings'][0]


def test_font_subset_cache_limit_prevents_new_files(tmp_path, monkeypatch):
    font_dir = tmp_path / 'community'
    font_dir.mkdir()
    (font_dir / 'existing.woff2').write_bytes(b'cached')
    base_ttf = tmp_path / 'base.ttf'
    base_subset = tmp_path / 'base.woff2'
    base_ttf.write_bytes(b'test')
    base_subset.write_bytes(b'test')

    monkeypatch.setattr(font_subsets, 'COMMUNITY_FONT_DIR', str(font_dir))
    monkeypatch.setattr(font_subsets, 'BASE_REGULAR_TTF', str(base_ttf))
    monkeypatch.setattr(font_subsets, 'BASE_REGULAR_SUBSET', str(base_subset))
    monkeypatch.setattr(font_subsets, 'MAX_COMMUNITY_FONT_FILES', 1)
    monkeypatch.setattr(
        font_subsets,
        'font_cmap',
        lambda path: set() if Path(path) == base_subset else {ord('新')},
    )
    monkeypatch.setattr(
        font_subsets,
        '_subset_font',
        lambda *_args: (_ for _ in ()).throw(AssertionError('font generation must be blocked')),
    )

    report = font_subsets.ensure_community_font_subset([{'name': '新'}], hash_key='abc', generate=True)
    assert report['success'] is True
    assert report['generated'] is False
    assert any('缓存已达到上限' in warning for warning in report['warnings'])
