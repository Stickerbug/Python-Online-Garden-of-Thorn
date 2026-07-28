import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')


def source_between(source, start, end):
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


class ClientShortcutRuleTests(unittest.TestCase):
    def test_right_click_cancels_selected_card_before_term_handlers(self):
        helper = source_between(
            GAME_JS,
            'function cancelSelectedBattleActionFromContextMenu(',
            'function isTypingKeyboardTarget(',
        )
        init = source_between(
            GAME_JS,
            'async function init()',
            'window.GTN_SHORTCUT_HOST =',
        )

        self.assertIn("if (activeViewId !== 'view-game') return false;", helper)
        self.assertIn('if (selectedPlayCardId == null && classicSelectedTriggerEquipmentId == null) return false;', helper)
        self.assertIn('clearSelectedPlayCard();', helper)
        self.assertIn('event.stopImmediatePropagation();', helper)
        self.assertLess(
            init.index('bindSelectedBattleContextMenuPriority();'),
            init.index('bindCardTextTokenContextMenu();'),
        )

    def test_shortcut_slots_keep_disabled_elements_in_visual_order(self):
        visibility_section = source_between(
            GAME_JS,
            'function isShortcutElementRendered(',
            'function createShortcutScene(',
        )
        slot_section = source_between(
            GAME_JS,
            'function setShortcutSceneSlots(',
            'function addShortcutSceneAction(',
        )
        battle_section = source_between(
            GAME_JS,
            "if (activeViewId === 'view-game') {",
            "if (activeViewId === 'view-gameover') {",
        )

        self.assertIn('return isShortcutElementRendered(element) && !element.disabled;', visibility_section)
        self.assertIn('.filter(isShortcutElementRendered)', slot_section)
        self.assertIn("{ includeDisabled: true }", battle_section)

    def test_disabled_slot_is_consumed_without_selecting_a_later_card(self):
        section = source_between(
            GAME_JS,
            'function activateShortcutSlot(',
            'function setShortcutSecondPage(',
        )

        self.assertIn('if (!isKeyboardNavigationCandidate(sceneSlot)) return true;', section)
        self.assertIn('if (topmostShortcutBlockingRoot()) return true;', section)

    def test_prompt_and_response_slots_include_disabled_visual_items(self):
        context = source_between(
            GAME_JS,
            'function getGameShortcutContext()',
            'function shortcutSceneHasAction(',
        )

        self.assertIn("'#game-prompt-options .game-prompt-option'", context)
        self.assertIn("'.counter-card-btn, .response-btn-row .btn'", context)
        self.assertGreaterEqual(context.count('{ includeDisabled: true }'), 5)

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

    def test_escape_leaves_live_spectate_after_closing_higher_priority_ui(self):
        battle_section = source_between(
            GAME_JS,
            "if (activeViewId === 'view-game') {",
            "if (activeViewId === 'view-gameover') {",
        )
        cancel_section = source_between(
            GAME_JS,
            'function cancelShortcutContext()',
            'function focusShortcutChat()',
        )

        self.assertIn("if (isSpectating && !replayMode)", battle_section)
        self.assertIn("addShortcutSceneAction(scene, 'cancel'", battle_section)
        self.assertIn("'btn-leave-spectate'", battle_section)
        self.assertIn("'classic-leave-spectate'", battle_section)
        spectate_exit = cancel_section.index(
            "if (activeViewId === 'view-game' && isSpectating && !replayMode)"
        )
        self.assertLess(cancel_section.index('if (blockingRoot) return false;'), spectate_exit)
        self.assertLess(cancel_section.index('if (targetPickCleanup)'), spectate_exit)
        self.assertIn('leaveSpectateAction();', cancel_section[spectate_exit:])


if __name__ == '__main__':
    unittest.main()
