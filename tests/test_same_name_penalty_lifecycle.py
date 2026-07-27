import pathlib
import unittest

from cards import CardInstance
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2


ROOT = pathlib.Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
LOCAL_WORKER_JS = (ROOT / 'static' / 'js' / 'local_solo_worker.js').read_text(encoding='utf-8')
APP_PY = (ROOT / 'app.py').read_text(encoding='utf-8')


def source_between(source, start, end):
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


class SameNamePenaltyLifecycleTests(unittest.TestCase):
    @staticmethod
    def _prime_1v1():
        engine = GameEngine()
        engine.phase = 'action'
        engine.round_num = 2
        engine.first_player = 0
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.deck = []
            player.hand = []
            player.discard = []
            player.exile = []
        return engine

    @staticmethod
    def _set_turn_cards(engine, player_id, count=2, instance_ids=None):
        player = engine.players[player_id]
        player.cards_played_this_turn = {'Basic': count}
        player.cards_played_this_turn_instance_ids = list(instance_ids or [101, 102])

    def test_end_turn_clears_penalty_after_cogwheel_returns_cards(self):
        engine = self._prime_1v1()
        player = engine.players[0]
        played_card = CardInstance('Basic')
        player.discard.append(played_card)
        self._set_turn_cards(engine, 0, 1, [played_card.instance_id])
        engine._cogwheel_active = {0: True}
        engine._cogwheel_exclude_instance_ids = {}

        engine._end_player_turn(0)

        self.assertIn(played_card, player.hand)
        self.assertIn('symbiosis', played_card.instance_flags)
        self.assertEqual(player.cards_played_this_turn, {})
        self.assertEqual(player.cards_played_this_turn_instance_ids, [])

    def test_game_over_clears_penalty_for_every_player(self):
        engine = self._prime_1v1()
        self._set_turn_cards(engine, 0)
        self._set_turn_cards(engine, 1)
        engine.players[0].health = 0

        engine._check_game_over()

        self.assertTrue(engine.game_over)
        for player in engine.players:
            self.assertEqual(player.cards_played_this_turn, {})
            self.assertEqual(player.cards_played_this_turn_instance_ids, [])

    def test_2v2_death_clears_only_the_dead_players_penalty(self):
        engine = GameEngine2v2()
        self._set_turn_cards(engine, 0)
        self._set_turn_cards(engine, 1)
        engine.players[0].health = 0

        engine._on_player_death(0)

        self.assertFalse(engine.game_over)
        self.assertEqual(engine.players[0].cards_played_this_turn, {})
        self.assertEqual(engine.players[0].cards_played_this_turn_instance_ids, [])
        self.assertEqual(engine.players[1].cards_played_this_turn, {'Basic': 2})
        self.assertEqual(engine.players[1].cards_played_this_turn_instance_ids, [101, 102])

    def test_rematch_draw_phase_ignores_previous_match_penalty(self):
        section = source_between(
            GAME_JS,
            'function getCardDisplayCosts(',
            'function isOwnBlindActive(',
        )
        self.assertIn("new Set(['action', 'response', 'choice'])", section)
        self.assertNotIn("'draw'", section)
        self.assertIn('!gameState.game_over', section)
        self.assertIn('ownerId != null', section)
        self.assertIn('ownerId === currentPlayerId', section)

    def test_local_training_clears_at_turn_and_game_end(self):
        end_turn = source_between(
            LOCAL_WORKER_JS,
            '    endPlayerTurn(playerId) {',
            '    runOwnerTurnEndEquipment(playerId) {',
        )
        game_over = source_between(
            LOCAL_WORKER_JS,
            '    checkGameOver() {',
            '    resetOneShotAttackAttrs(card) {',
        )
        self.assertLess(
            end_turn.index('this.returnCogwheelCardsNow(playerId);'),
            end_turn.index('this.clearTurnCardTracking(playerId);'),
        )
        self.assertGreaterEqual(game_over.count('this.clearTurnCardTracking();'), 2)

    def test_forced_server_end_paths_clear_penalty(self):
        draw = source_between(
            APP_PY,
            'def _set_room_draw(',
            'def _finish_room_by_health_tiebreak(',
        )
        health_tiebreak = source_between(
            APP_PY,
            'def _finish_room_by_health_tiebreak(',
            'def _finish_room_by_forfeit(',
        )
        forfeit = source_between(
            APP_PY,
            'def _finish_room_by_forfeit(',
            'def _display_width(',
        )
        self.assertIn('_clear_engine_turn_card_tracking(e)', draw)
        self.assertGreaterEqual(health_tiebreak.count('_clear_engine_turn_card_tracking(e)'), 2)
        self.assertGreaterEqual(forfeit.count('_clear_engine_turn_card_tracking(e)'), 2)


if __name__ == '__main__':
    unittest.main()
