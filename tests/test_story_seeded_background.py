from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / 'templates' / 'story.html').read_text(encoding='utf-8')
STORY_JS = (ROOT / 'static' / 'js' / 'story.js').read_text(encoding='utf-8')
STORY_CSS = (ROOT / 'static' / 'css' / 'story.css').read_text(encoding='utf-8')


def test_story_template_has_one_inert_seeded_backdrop_surface():
    assert TEMPLATE.count('id="story-seeded-backdrop"') == 1
    assert (
        'id="story-seeded-backdrop" class="story-seeded-backdrop" '
        'aria-hidden="true"'
    ) in TEMPLATE
    assert TEMPLATE.count('id="story-coop-seeded-backdrop"') == 1
    assert (
        'id="story-coop-seeded-backdrop" '
        'class="story-seeded-backdrop story-coop-seeded-backdrop" '
        'aria-hidden="true"'
    ) in TEMPLATE


def test_landmarks_are_transparent_extracted_svg_assets():
    expected = {
        'garden-sunflower.svg': ('150 140 95 95', 'g'),
        'garden-rock.svg': ('75 62 110 100', 'polygon'),
        'jungle-branch.svg': ('82 42 90 70', 'g'),
        'jungle-leaf.svg': ('105 138 100 96', 'g'),
        'ocean-bubble.svg': ('85 45 95 95', 'ellipse'),
        'ocean-lily.svg': ('105 137 105 105', 'g'),
        'factory-plate.svg': ('88 50 78 72', 'g'),
        'factory-gear.svg': ('108 150 98 92', 'path'),
    }
    for filename, (view_box, expected_element) in expected.items():
        path = ROOT / 'static' / 'assets' / 'story-backgrounds' / filename
        assert path.is_file()
        root = ET.parse(path).getroot()
        assert root.attrib['viewBox'] == view_box
        element_names = [child.tag.rsplit('}', 1)[-1] for child in root]
        assert 'rect' not in element_names
        assert expected_element in element_names


def test_directional_biome_bases_are_kept_as_unrotated_tiles():
    for filename in ('jungle-tile.svg', 'ocean-tile.svg', 'factory-tile.svg'):
        path = ROOT / 'static' / 'assets' / 'story-backgrounds' / filename
        assert path.is_file()
        assert ET.parse(path).getroot().attrib['viewBox'] == '0 0 283.46 283.46'
    base_block = STORY_JS.split('function appendStoryBackdropBase', 1)[1].split(
        'function appendGardenBackdropPatches', 1,
    )[0]
    assert 'base.style.backgroundPosition' in base_block
    assert 'base.style.backgroundSize' in base_block
    assert 'base.style.transform' not in base_block


def test_garden_layout_uses_seeded_static_jitter_without_math_random():
    block = STORY_JS.split('function storyBackdropHash(value) {', 1)[1].split(
        'const STORY_TAG_STYLES', 1,
    )[0]
    assert 'Math.imul(hash, 0x01000193)' in block
    assert 'Math.random' not in block
    assert "STORY_BACKDROP_LAYOUT_VERSION = 'story-backdrop-v3'" in STORY_JS
    assert "['garden', 'desert', 'ocean', 'jungle', 'factory']" in STORY_JS
    assert "run?.visual_seed || run?.seed || run?.id" in block
    assert 'appendGardenBackdropPatches(container, signature)' in block
    assert 'appendDesertBackdropPatches(container, signature)' in block
    assert 'appendStoryBackdropBase(container, signature, biome)' in block
    assert 'appendStoryBackdropLandmarks(container, signature, biome)' in block
    assert '!STORY_BACKDROP_BIOMES.includes(biome)' in block
    assert 'renderStorySeededBackdrop(run);' in STORY_JS
    assert "'story-coop-seeded-backdrop'" in STORY_JS
    assert "snapshot ? { id: run?.id, visual_seed: run?.visual_seed, state: snapshot }" in STORY_JS
    assert "clearStorySeededBackdrop($('story-coop-seeded-backdrop'))" in STORY_JS


def test_garden_backdrop_keeps_readability_and_reduced_motion_contracts():
    assert ".story-seeded-backdrop[data-biome='garden']" in STORY_CSS
    assert '.story-seeded-backdrop::after' in STORY_CSS
    assert 'var(--story-backdrop-wash)' in STORY_CSS
    assert '@media (prefers-reduced-motion: reduce)' in STORY_CSS
    assert '.story-seeded-backdrop-patch.is-dark' in STORY_CSS
    assert '.story-seeded-backdrop-landmark' in STORY_CSS
    assert 'opacity: .16;' in STORY_CSS
    assert 'opacity: .2;' in STORY_CSS
    assert 'rgba(251, 251, 247, .72)' in STORY_CSS
    for biome in ('garden', 'desert', 'ocean', 'jungle', 'factory'):
        assert f".story-seeded-backdrop[data-biome='{biome}']" in STORY_CSS
    for filename in ('jungle-tile.svg', 'ocean-tile.svg', 'factory-tile.svg'):
        assert f"/static/assets/story-backgrounds/{filename}" in STORY_CSS


def test_garden_backdrop_uses_dense_small_motifs():
    patches = STORY_JS.split('function appendGardenBackdropPatches', 1)[1].split(
        'function appendDesertBackdropPatches', 1,
    )[0]
    desert = STORY_JS.split('function appendDesertBackdropPatches', 1)[1].split(
        'function appendStoryBackdropLandmarks', 1,
    )[0]
    landmarks = STORY_JS.split('function appendStoryBackdropLandmarks', 1)[1].split(
        'function renderStorySeededBackdrop', 1,
    )[0]
    assert 'const columns = 10;' in patches
    assert 'const rows = 7;' in patches
    assert '`${key}:width`, 3.2, 7.2' in patches
    assert 'const columns = 10;' in desert
    assert 'const rows = 7;' in desert
    assert 'const columns = 5;' in landmarks
    assert 'const rows = 3;' in landmarks
    assert '`${key}:size`, 5.5, 9.5' in landmarks
    assert 'clamp(36px, ${size.toFixed(3)}vmin, 96px)' in landmarks
