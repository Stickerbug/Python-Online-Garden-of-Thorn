import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')


def source_between(source, start, end):
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


class ClientShortcutRuleTests(unittest.TestCase):
    def test_battle_hand_slot_uses_shortcut_selection_instead_of_dom_click(self):
        section = source_between(
            GAME_JS,
            'function activateShortcutSlot(',
            'function setShortcutSecondPage(',
        )
        hand_guard = section.index("sceneSlot.closest('#classic-hand-fan, #you-hand')")
        hand_select = section.index('return selectHandCardByShortcutIndex(index, options.event || null)')
        generic_click = section.index('sceneSlot.click()')

        self.assertLess(hand_guard, hand_select)
        self.assertLess(hand_select, generic_click)

    def test_minimal_ui_shortcut_forces_card_selection(self):
        section = source_between(
            GAME_JS,
            'function selectHandCardByShortcutIndex(',
            'function selectPlayCardForConfirm(',
        )
        self.assertIn(
            'selectPlayCardForConfirm(card.instance_id, { force: true })',
            section,
        )

    def test_minimal_ui_confirm_is_available_in_battle_shortcut_scene(self):
        section = source_between(
            GAME_JS,
            "if (activeViewId === 'view-game') {",
            "if (activeViewId === 'view-gameover') {",
        )
        self.assertIn(
            "addShortcutSceneAction(scene, 'confirm', [mobileConfirm])",
            section,
        )

    def test_minimal_ui_confirm_precedes_virtual_card_focus(self):
        section = source_between(
            GAME_JS,
            'function clickShortcutPrimaryButton(',
            'function cancelShortcutContext(',
        )
        mobile_confirm = section.index("const mobileConfirm = $('mobile-play-ok')")
        guarded_confirm = section.index(
            'if (!blockingRoot && mobileConfirm && isShortcutElementVisible(mobileConfirm))'
        )
        focused_selection = section.index('if (hasCurrentFocus && activateKeyboardFocusedSelection())')

        self.assertLess(mobile_confirm, focused_selection)
        self.assertLess(guarded_confirm, focused_selection)


if __name__ == '__main__':
    unittest.main()
