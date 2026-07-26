import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')


def source_between(source, start, end):
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


class ClientPredictionRuleTests(unittest.TestCase):
    def test_toxic_prediction_uses_the_damage_target(self):
        section = source_between(
            GAME_JS,
            'function getCardPlayEffectPredictionParts(',
            'function shouldShowCardPlayEffectPrediction(',
        )
        toxic_block = re.search(
            r'const targetImmune = .*?result\.target\.poison \+= toxic \* positiveHits;',
            section,
            re.DOTALL,
        )
        self.assertIsNotNone(toxic_block)
        self.assertIn('targetState.toxic', toxic_block.group(0))
        self.assertNotIn('attackerState.toxic', toxic_block.group(0))

    def test_server_response_poison_replaces_local_estimate(self):
        section = source_between(
            GAME_JS,
            'function getResponseBaseEffectPrediction(',
            'function appendResponseEffectToken(',
        )
        self.assertIn('prediction.target.poison = Math.max(', section)
        self.assertNotIn('prediction.target.poison +=', section)

    def test_fission_total_is_not_capped_as_one_damage_call(self):
        self.assertIn(
            'const MAX_CLIENT_DAMAGE_SEGMENTS = MAX_CLIENT_CARD_LAYER * MAX_CLIENT_DAMAGE_HITS;',
            GAME_JS,
        )
        section = source_between(
            GAME_JS,
            'function getActualAttackDamageHits(',
            'function getActualAttackDamageText(',
        )
        self.assertIn('const hitsPerFission = clampClientDamageHits(', section)
        self.assertIn('const totalHits = clampClientDamageSegments(hitsPerFission * fission);', section)

    def test_multi_hit_visuals_and_audio_share_the_float_timeline(self):
        section = source_between(
            GAME_JS,
            'function showStateDeltas(',
            'function clearScheduledGameOver(',
        )
        timeline_call = section.index('const scheduledEvents = showCombatFloatSequence(')
        effects_call = section.index('scheduleCombatEventEffects(', timeline_call)
        bar_call = section.index('animateBarEventSequence(', effects_call)
        self.assertLess(timeline_call, effects_call)
        self.assertLess(effects_call, bar_call)
        self.assertNotIn('triggerCombatImpact(', section[:timeline_call])
        helper = source_between(
            GAME_JS,
            'function scheduleCombatEventEffects(',
            'function scheduleSkinDamageMoods(',
        )
        self.assertIn('triggerCombatImpact(selector, event.impactKind, delay)', helper)
        self.assertIn('triggerCombatPulse(selector, event.pulseKind, delay)', helper)


if __name__ == '__main__':
    unittest.main()
