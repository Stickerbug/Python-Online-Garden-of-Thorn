import math
import random


def install_runtime_ext(GameEngine):
    # The main GameEngine now owns the complete atomic-expression runtime.
    # Keep this hook as a compatibility no-op so older imports still work
    # without replacing the richer in-class implementation.
    return

    def _eval_expr(self, player_id, expr, card=None):
        if isinstance(expr, (int, float, bool)):
            return expr
        if isinstance(expr, str):
            try:
                return int(expr)
            except Exception:
                return expr
        if not isinstance(expr, dict):
            return 0
        ref = expr.get('ref')
        if ref == 'var':
            tid = self._resolve_target(player_id, expr.get('target', 'self'))
            return int(self.players[tid].custom_vars.get(str(expr.get('name', 'var')), 0))
        if ref == 'target_attribute':
            tid = self._resolve_target(player_id, expr.get('target', 'self'))
            return int(getattr(self.players[tid], expr.get('attr', 'health'), 0))
        if ref == 'math_op':
            a = int(self._eval_expr(player_id, expr.get('a', 0), card))
            b = int(self._eval_expr(player_id, expr.get('b', 0), card))
            return a + b if expr.get('op') == '+' else a - b if expr.get('op') == '-' else a * b if expr.get('op') == '*' else (0 if b == 0 else a // b)
        if ref == 'turn_number':
            return int(self.round_num)
        return 0

    def _eval_condition(self, player_id, cond, card=None):
        if isinstance(cond, bool):
            return cond
        if not isinstance(cond, dict):
            return False
        op = cond.get('op')
        if op == 'compare':
            a = self._eval_expr(player_id, cond.get('a', 0), card)
            b = self._eval_expr(player_id, cond.get('b', 0), card)
            cmp = cond.get('operator', '=')
            return (a == b) if cmp == '=' else (a != b) if cmp == '!=' else (a < b) if cmp == '<' else (a > b) if cmp == '>' else (a <= b) if cmp == '<=' else (a >= b)
        if op == 'var_compare':
            tid = self._resolve_target(player_id, cond.get('target', 'self'))
            a = int(self.players[tid].custom_vars.get(str(cond.get('name', 'var')), 0))
            b = int(self._eval_expr(player_id, cond.get('value', 0), card))
            cmp = cond.get('operator', '=')
            return (a == b) if cmp == '=' else (a != b) if cmp == '!=' else (a < b) if cmp == '<' else (a > b) if cmp == '>' else (a <= b) if cmp == '<=' else (a >= b)
        return False

    def _run_effect_list(self, player_id, card, effects, choice, context):
        for eff in effects or []:
            et = eff if isinstance(eff, str) else eff.get('type', '')
            pm = {} if isinstance(eff, str) else eff.get('params', {})
            lg = None if isinstance(eff, str) else eff.get('log')
            fn = getattr(self, f'_atomic_{self._EFFECT_ALIASES.get(et, et)}', None)
            if callable(fn):
                fn(player_id, card, pm, lg, choice, context)
            elif lg:
                self.log_msg(lg)
            else:
                self.log_msg(f"未实现效果: {et}")

    GameEngine._eval_expr = _eval_expr
    GameEngine._eval_condition = _eval_condition
    GameEngine._run_effect_list = _run_effect_list
