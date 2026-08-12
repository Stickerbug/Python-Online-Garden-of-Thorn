from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple


MAX_FORMULA_NODES = 64
MAX_FORMULA_DEPTH = 16
MAX_FORMULA_PREMISES = 8
MAX_FORMULA_VARIABLES = 16
MAX_FORMULA_TEXT = 256


class FormalLogicError(ValueError):
    pass


@dataclass(frozen=True)
class LogicExpr:
    kind: str
    value: str = ""
    children: Tuple["LogicExpr", ...] = ()

    @staticmethod
    def variable(name: str) -> "LogicExpr":
        normalized = str(name or "").strip()
        if not normalized.startswith("$"):
            normalized = f"${normalized}"
        return LogicExpr("var", normalized)

    @staticmethod
    def constant(value: str) -> "LogicExpr":
        return LogicExpr("const", str(value or "").strip())

    @staticmethod
    def unary(operator: str, child: "LogicExpr") -> "LogicExpr":
        return LogicExpr("unary", str(operator), (child,))

    @staticmethod
    def binary(operator: str, left: "LogicExpr", right: "LogicExpr") -> "LogicExpr":
        return LogicExpr("binary", str(operator), (left, right))

    @staticmethod
    def quantified(operator: str, variable: "LogicExpr", body: "LogicExpr") -> "LogicExpr":
        return LogicExpr("quantifier", str(operator), (variable, body))


@dataclass(frozen=True)
class ProofFormula:
    premises: Tuple[LogicExpr, ...]
    conclusion: LogicExpr


_BINARY_PRECEDENCE = {
    ">": 10,
    "<>": 20,
    "|": 30,
    "&": 40,
    "=": 50,
}


def _normalize_source(text: str) -> str:
    value = str(text or "").strip()
    value = value.replace("⊢", "├").replace("→", ">").replace("↔", "<>")
    value = value.replace("（", "(").replace("）", ")")
    value = value.replace("，", ",").replace("：", ":")
    return value


def _tokenize(text: str) -> List[str]:
    source = _normalize_source(text)
    if not source:
        raise FormalLogicError("公式为空")
    if len(source) > MAX_FORMULA_TEXT:
        raise FormalLogicError("公式过长")
    tokens: List[str] = []
    index = 0
    while index < len(source):
        char = source[index]
        if char.isspace():
            index += 1
            continue
        if source.startswith("<>", index):
            tokens.append("<>")
            index += 2
            continue
        if char in "()├,¬&|>=∀∃:":
            tokens.append(char)
            index += 1
            continue
        if char == "$":
            end = index + 1
            if end < len(source) and source[end] == "#":
                end += 1
            digit_start = end
            while end < len(source) and source[end].isdigit():
                end += 1
            if digit_start == end:
                raise FormalLogicError(f"无效变量: {source[index:index + 8]}")
            tokens.append(source[index:end])
            index = end
            continue
        if char in "[【":
            closing = "]" if char == "[" else "】"
            end = source.find(closing, index + 1)
            if end < 0:
                raise FormalLogicError("常量缺少右括号")
            value = source[index + 1:end].strip()
            if not value:
                raise FormalLogicError("常量不能为空")
            tokens.append(f"[{value}]")
            index = end + 1
            continue
        end = index
        while end < len(source):
            if source.startswith("<>", end) or source[end].isspace() or source[end] in "()├,¬&|>=∀∃:":
                break
            end += 1
        if end == index:
            raise FormalLogicError(f"无法解析字符: {char}")
        tokens.append(source[index:end])
        index = end
    return tokens


class _Parser:
    def __init__(self, tokens: Sequence[str]):
        self.tokens = list(tokens)
        self.index = 0

    def peek(self) -> Optional[str]:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def take(self, expected: Optional[str] = None) -> str:
        token = self.peek()
        if token is None:
            raise FormalLogicError("公式意外结束")
        if expected is not None and token != expected:
            raise FormalLogicError(f"需要 {expected}，实际为 {token}")
        self.index += 1
        return token

    def parse_expr(self, minimum_precedence: int = 0) -> LogicExpr:
        left = self.parse_unary()
        while True:
            operator = self.peek()
            precedence = _BINARY_PRECEDENCE.get(str(operator), -1)
            if precedence < minimum_precedence:
                break
            self.take()
            next_minimum = precedence if operator == ">" else precedence + 1
            right = self.parse_expr(next_minimum)
            left = LogicExpr.binary(str(operator), left, right)
        return left

    def parse_unary(self) -> LogicExpr:
        token = self.peek()
        if token == "¬":
            self.take()
            return LogicExpr.unary("¬", self.parse_unary())
        if token in ("∀", "∃"):
            operator = self.take()
            variable_token = self.take()
            if not variable_token.startswith("$"):
                raise FormalLogicError("量词后必须是变量")
            if self.peek() == ":":
                self.take()
            return LogicExpr.quantified(operator, LogicExpr.variable(variable_token), self.parse_expr())
        if token == "(":
            self.take()
            expression = self.parse_expr()
            self.take(")")
            return expression
        token = self.take()
        if token.startswith("$"):
            return LogicExpr.variable(token)
        if token.startswith("[") and token.endswith("]"):
            token = token[1:-1]
        return LogicExpr.constant(token)


def parse_formula(text: str) -> ProofFormula:
    tokens = _tokenize(text)
    depth = 0
    turnstile_index = -1
    for index, token in enumerate(tokens):
        if token == "(":
            depth += 1
        elif token == ")":
            depth -= 1
            if depth < 0:
                raise FormalLogicError("括号不匹配")
        elif token == "├" and depth == 0:
            if turnstile_index >= 0:
                raise FormalLogicError("公式只能包含一个主推理符号")
            turnstile_index = index
    if depth != 0:
        raise FormalLogicError("括号不匹配")
    if turnstile_index < 0:
        parser = _Parser(tokens)
        conclusion = parser.parse_expr()
        if parser.peek() is not None:
            raise FormalLogicError(f"无法解析剩余内容: {parser.peek()}")
        proof = ProofFormula((), conclusion)
        validate_formula(proof)
        return proof

    premise_tokens = tokens[:turnstile_index]
    conclusion_tokens = tokens[turnstile_index + 1:]
    if not conclusion_tokens:
        raise FormalLogicError("推理符号后缺少结论")
    premise_groups: List[List[str]] = []
    current: List[str] = []
    depth = 0
    for token in premise_tokens:
        if token == "(":
            depth += 1
        elif token == ")":
            depth -= 1
        if token == "," and depth == 0:
            if not current:
                raise FormalLogicError("前提不能为空")
            premise_groups.append(current)
            current = []
        else:
            current.append(token)
    if current:
        premise_groups.append(current)
    premises: List[LogicExpr] = []
    for group in premise_groups:
        parser = _Parser(group)
        premises.append(parser.parse_expr())
        if parser.peek() is not None:
            raise FormalLogicError(f"无法解析前提剩余内容: {parser.peek()}")
    parser = _Parser(conclusion_tokens)
    conclusion = parser.parse_expr()
    if parser.peek() is not None:
        raise FormalLogicError(f"无法解析结论剩余内容: {parser.peek()}")
    proof = ProofFormula(tuple(premises), conclusion)
    validate_formula(proof)
    return proof


def expression_to_data(expr: LogicExpr) -> dict:
    return {
        "kind": expr.kind,
        "value": expr.value,
        "children": [expression_to_data(child) for child in expr.children],
    }


def expression_from_data(data: Mapping[str, object]) -> LogicExpr:
    if not isinstance(data, Mapping):
        raise FormalLogicError("表达式数据无效")
    children = tuple(expression_from_data(child) for child in (data.get("children") or []))
    return LogicExpr(str(data.get("kind") or ""), str(data.get("value") or ""), children)


def formula_to_data(formula: ProofFormula) -> dict:
    return {
        "premises": [expression_to_data(expr) for expr in formula.premises],
        "conclusion": expression_to_data(formula.conclusion),
    }


def formula_from_data(data: Mapping[str, object]) -> ProofFormula:
    if not isinstance(data, Mapping):
        raise FormalLogicError("公式数据无效")
    premises = tuple(expression_from_data(item) for item in (data.get("premises") or []))
    conclusion_data = data.get("conclusion")
    if not isinstance(conclusion_data, Mapping):
        raise FormalLogicError("公式缺少结论")
    formula = ProofFormula(premises, expression_from_data(conclusion_data))
    validate_formula(formula)
    return formula


def _expr_precedence(expr: LogicExpr) -> int:
    if expr.kind == "binary":
        return _BINARY_PRECEDENCE.get(expr.value, 0)
    if expr.kind in ("unary", "quantifier"):
        return 60
    return 100


def format_expression(expr: LogicExpr, parent_precedence: int = 0, *, right_child: bool = False) -> str:
    if expr.kind == "var":
        return expr.value
    if expr.kind == "const":
        return expr.value
    if expr.kind == "unary" and len(expr.children) == 1:
        child = expr.children[0]
        rendered = format_expression(child, _expr_precedence(expr))
        if child.kind == "binary":
            rendered = f"({format_expression(child)})"
        return f"{expr.value}{rendered}"
    if expr.kind == "quantifier" and len(expr.children) == 2:
        return f"{expr.value}{format_expression(expr.children[0])}:{format_expression(expr.children[1])}"
    if expr.kind == "binary" and len(expr.children) == 2:
        precedence = _expr_precedence(expr)
        left, right = expr.children
        left_text = format_expression(left, precedence + (0 if expr.value != ">" else 1))
        right_text = format_expression(right, precedence, right_child=True)
        if left.kind == "binary" and _expr_precedence(left) <= precedence:
            left_text = f"({format_expression(left)})"
        if right.kind == "binary" and (expr.value == ">" or _expr_precedence(right) < precedence):
            right_text = f"({format_expression(right)})"
        rendered = f"{left_text}{expr.value}{right_text}"
        if precedence < parent_precedence:
            return f"({rendered})"
        return rendered
    raise FormalLogicError(f"未知表达式节点: {expr.kind}")


def format_formula(formula: ProofFormula) -> str:
    left = "，".join(format_expression(expr) for expr in formula.premises)
    return f"{left}├{format_expression(formula.conclusion)}"


def _walk_expression(expr: LogicExpr) -> Iterator[LogicExpr]:
    yield expr
    for child in expr.children:
        yield from _walk_expression(child)


def formula_variables(formula: ProofFormula) -> List[str]:
    ordered: List[str] = []
    seen = set()
    for expression in (*formula.premises, formula.conclusion):
        for node in _walk_expression(expression):
            if node.kind == "var" and node.value not in seen:
                seen.add(node.value)
                ordered.append(node.value)
    return ordered


def _expression_depth(expr: LogicExpr) -> int:
    if not expr.children:
        return 1
    return 1 + max(_expression_depth(child) for child in expr.children)


def validate_formula(formula: ProofFormula) -> None:
    if len(formula.premises) > MAX_FORMULA_PREMISES:
        raise FormalLogicError("前提数量超过限制")
    nodes = sum(1 for expr in (*formula.premises, formula.conclusion) for _ in _walk_expression(expr))
    if nodes > MAX_FORMULA_NODES:
        raise FormalLogicError("公式节点数量超过限制")
    depth = max(_expression_depth(expr) for expr in (*formula.premises, formula.conclusion))
    if depth > MAX_FORMULA_DEPTH:
        raise FormalLogicError("公式嵌套层数超过限制")
    if len(formula_variables(formula)) > MAX_FORMULA_VARIABLES:
        raise FormalLogicError("公式变量数量超过限制")


def _strip_double_negation(expr: LogicExpr) -> LogicExpr:
    children = tuple(_strip_double_negation(child) for child in expr.children)
    current = LogicExpr(expr.kind, expr.value, children)
    while (
        current.kind == "unary"
        and current.value == "¬"
        and current.children
        and current.children[0].kind == "unary"
        and current.children[0].value == "¬"
        and current.children[0].children
    ):
        current = current.children[0].children[0]
    return current


def normalize_for_matching(formula: ProofFormula) -> ProofFormula:
    return ProofFormula(
        tuple(_strip_double_negation(expr) for expr in formula.premises),
        _strip_double_negation(formula.conclusion),
    )


Bindings = Dict[str, LogicExpr]


def _resolve_binding(expr: LogicExpr, bindings: Mapping[str, LogicExpr]) -> LogicExpr:
    seen = set()
    current = expr
    while current.kind == "var" and current.value in bindings and current.value not in seen:
        seen.add(current.value)
        current = bindings[current.value]
    return current


def substitute_expression(expr: LogicExpr, bindings: Mapping[str, LogicExpr]) -> LogicExpr:
    resolved = _resolve_binding(expr, bindings)
    if resolved is not expr:
        return substitute_expression(resolved, bindings)
    if not expr.children:
        return expr
    return LogicExpr(expr.kind, expr.value, tuple(substitute_expression(child, bindings) for child in expr.children))


def substitute_formula(formula: ProofFormula, bindings: Mapping[str, LogicExpr]) -> ProofFormula:
    return ProofFormula(
        tuple(substitute_expression(expr, bindings) for expr in formula.premises),
        substitute_expression(formula.conclusion, bindings),
    )


def instantiate_expression(expr: LogicExpr, replacements: Mapping[str, LogicExpr]) -> LogicExpr:
    """Replace variables once, without rewriting inside replacement values."""
    if expr.kind == "var" and expr.value in replacements:
        return replacements[expr.value]
    if not expr.children:
        return expr
    return LogicExpr(
        expr.kind,
        expr.value,
        tuple(instantiate_expression(child, replacements) for child in expr.children),
    )


def instantiate_formula(formula: ProofFormula, replacements: Mapping[str, LogicExpr]) -> ProofFormula:
    result = ProofFormula(
        tuple(instantiate_expression(expr, replacements) for expr in formula.premises),
        instantiate_expression(formula.conclusion, replacements),
    )
    validate_formula(result)
    return result


def _occurs(variable: str, expr: LogicExpr, bindings: Mapping[str, LogicExpr]) -> bool:
    resolved = _resolve_binding(expr, bindings)
    if resolved.kind == "var":
        return resolved.value == variable
    return any(_occurs(variable, child, bindings) for child in resolved.children)


def unify_expressions(left: LogicExpr, right: LogicExpr, bindings: Optional[Bindings] = None) -> Optional[Bindings]:
    result: Bindings = dict(bindings or {})

    def unify_pair(a: LogicExpr, b: LogicExpr) -> bool:
        a = _strip_double_negation(_resolve_binding(a, result))
        b = _strip_double_negation(_resolve_binding(b, result))
        if a == b:
            return True
        if a.kind == "var":
            if _occurs(a.value, b, result):
                return False
            result[a.value] = b
            return True
        if b.kind == "var":
            if _occurs(b.value, a, result):
                return False
            result[b.value] = a
            return True
        if a.kind != b.kind or a.value != b.value or len(a.children) != len(b.children):
            return False
        return all(unify_pair(ac, bc) for ac, bc in zip(a.children, b.children))

    if not unify_pair(left, right):
        return None
    return {name: substitute_expression(value, result) for name, value in result.items()}


def unify_mp_antecedent(
    antecedent: LogicExpr,
    candidate: LogicExpr,
    bindings: Optional[Bindings] = None,
) -> Optional[Bindings]:
    """Apply the mod's deliberately non-standard negation rule for mp.

    A single-negated antecedent accepts any formula that does not itself match
    that negated antecedent. When possible, its inner expression is bound to the
    accepted formula. Double negation is normalized by the ordinary unifier.
    """
    normalized = _strip_double_negation(antecedent)
    candidate_normalized = _strip_double_negation(candidate)
    if normalized.kind == "unary" and normalized.value == "¬" and len(normalized.children) == 1:
        if unify_expressions(normalized, candidate_normalized, bindings) is not None:
            return None
        child_bindings = unify_expressions(normalized.children[0], candidate_normalized, bindings)
        return child_bindings if child_bindings is not None else dict(bindings or {})
    return unify_expressions(normalized, candidate_normalized, bindings)


def expressions_match(pattern: LogicExpr, candidate: LogicExpr, bindings: Optional[Bindings] = None) -> Optional[Bindings]:
    return unify_expressions(pattern, candidate, bindings)


def match_expression_pattern(
    pattern: LogicExpr,
    candidate: LogicExpr,
    bindings: Optional[Bindings] = None,
) -> Optional[Bindings]:
    """Match an inference pattern without collapsing distinct variables.

    Formal Logic cards treat a repeated variable as an equality constraint and
    different variables as an inequality constraint.  Ordinary first-order
    unification is intentionally more permissive, so it cannot be used for mp:
    it would allow ``$0>($1>$2)`` to match ``$0>($1>$0)`` by identifying two
    variables that were distinct in the source formula.
    """
    result: Bindings = {
        str(name): _strip_double_negation(value)
        for name, value in dict(bindings or {}).items()
    }

    def match_pair(left: LogicExpr, right: LogicExpr) -> bool:
        left = _strip_double_negation(left)
        right = _strip_double_negation(right)
        if left.kind == "var":
            previous = result.get(left.value)
            if previous is not None:
                return _strip_double_negation(previous) == right
            if any(
                name != left.value and _strip_double_negation(value) == right
                for name, value in result.items()
            ):
                return False
            result[left.value] = right
            return True
        if (
            left.kind != right.kind
            or left.value != right.value
            or len(left.children) != len(right.children)
        ):
            return False
        return all(match_pair(a, b) for a, b in zip(left.children, right.children))

    return result if match_pair(pattern, candidate) else None


def implication_chain(expr: LogicExpr) -> Tuple[List[LogicExpr], LogicExpr]:
    antecedents: List[LogicExpr] = []
    current = expr
    while current.kind == "binary" and current.value == ">" and len(current.children) == 2:
        antecedents.append(current.children[0])
        current = current.children[1]
    return antecedents, current


def rename_variables(formula: ProofFormula, mapping: Mapping[str, str]) -> ProofFormula:
    # Variable renaming is simultaneous.  Reusing substitute_formula here can
    # cascade through the destination names (for example $2->$1->$0), merging
    # variables that were distinct in the source formula.
    def rename(expr: LogicExpr) -> LogicExpr:
        if expr.kind == "var" and expr.value in mapping:
            return LogicExpr.variable(mapping[expr.value])
        if not expr.children:
            return expr
        return LogicExpr(expr.kind, expr.value, tuple(rename(child) for child in expr.children))

    return ProofFormula(
        tuple(rename(expr) for expr in formula.premises),
        rename(formula.conclusion),
    )


def freshen_variables(formula: ProofFormula, used: Iterable[str]) -> ProofFormula:
    occupied = set(str(name) for name in used)
    mapping: Dict[str, str] = {}
    cursor = 0
    for name in formula_variables(formula):
        while f"${cursor}" in occupied:
            cursor += 1
        mapping[name] = f"${cursor}"
        occupied.add(f"${cursor}")
        cursor += 1
    return rename_variables(formula, mapping)


def canonicalize_variables(formula: ProofFormula) -> ProofFormula:
    return rename_variables(formula, {name: f"${index}" for index, name in enumerate(formula_variables(formula))})


def formula_signature(formula: ProofFormula) -> tuple:
    canonical = canonicalize_variables(normalize_for_matching(formula))

    def signature(expr: LogicExpr):
        return expr.kind, expr.value, tuple(signature(child) for child in expr.children)

    return tuple(signature(expr) for expr in canonical.premises), signature(canonical.conclusion)


def formulas_alpha_equivalent(left: ProofFormula, right: ProofFormula) -> bool:
    return formula_signature(left) == formula_signature(right)


def formulas_special_equivalent(left: ProofFormula, right: ProofFormula) -> bool:
    """Compare special theorem forms using variable renaming only.

    Unlike ordinary inference matching, this comparison preserves every
    operator (including double negation), requires a bijective variable
    renaming, and treats premises to the left of the turnstile as unordered.
    """
    if len(left.premises) != len(right.premises):
        return False

    VariableMaps = Tuple[Dict[str, str], Dict[str, str]]

    def match_expression(
        left_expr: LogicExpr,
        right_expr: LogicExpr,
        maps: VariableMaps,
    ) -> Optional[VariableMaps]:
        left_to_right, right_to_left = maps
        if left_expr.kind == "var" or right_expr.kind == "var":
            if left_expr.kind != "var" or right_expr.kind != "var":
                return None
            existing_right = left_to_right.get(left_expr.value)
            existing_left = right_to_left.get(right_expr.value)
            if existing_right is not None and existing_right != right_expr.value:
                return None
            if existing_left is not None and existing_left != left_expr.value:
                return None
            next_left_to_right = dict(left_to_right)
            next_right_to_left = dict(right_to_left)
            next_left_to_right[left_expr.value] = right_expr.value
            next_right_to_left[right_expr.value] = left_expr.value
            return next_left_to_right, next_right_to_left

        if (
            left_expr.kind != right_expr.kind
            or left_expr.value != right_expr.value
            or len(left_expr.children) != len(right_expr.children)
        ):
            return None

        current_maps = maps
        for left_child, right_child in zip(left_expr.children, right_expr.children):
            matched = match_expression(left_child, right_child, current_maps)
            if matched is None:
                return None
            current_maps = matched
        return current_maps

    conclusion_maps = match_expression(left.conclusion, right.conclusion, ({}, {}))
    if conclusion_maps is None:
        return False

    def match_premises(
        premise_index: int,
        available_right: Tuple[int, ...],
        maps: VariableMaps,
    ) -> bool:
        if premise_index >= len(left.premises):
            return True
        left_premise = left.premises[premise_index]
        for right_index in available_right:
            matched = match_expression(left_premise, right.premises[right_index], maps)
            if matched is None:
                continue
            remaining = tuple(index for index in available_right if index != right_index)
            if match_premises(premise_index + 1, remaining, matched):
                return True
        return False

    return match_premises(0, tuple(range(len(right.premises))), conclusion_maps)


def transform_contraposition(formula: ProofFormula) -> ProofFormula:
    conclusion = formula.conclusion
    if conclusion.kind != "binary" or conclusion.value != ">":
        raise FormalLogicError("所选公式不是蕴含式")
    antecedent, consequent = conclusion.children
    transformed = ProofFormula(
        formula.premises,
        LogicExpr.binary(">", LogicExpr.unary("¬", consequent), LogicExpr.unary("¬", antecedent)),
    )
    validate_formula(transformed)
    return transformed


def transform_inverse_deduction(formula: ProofFormula) -> ProofFormula:
    conclusion = formula.conclusion
    if conclusion.kind != "binary" or conclusion.value != ">":
        raise FormalLogicError("结论至少需要一个蕴含前件")
    antecedent, consequent = conclusion.children
    transformed = ProofFormula(tuple(formula.premises) + (antecedent,), consequent)
    validate_formula(transformed)
    return canonicalize_variables(transformed)


def transform_deduction(formula: ProofFormula, premise_index: int = 0) -> ProofFormula:
    if not formula.premises:
        raise FormalLogicError("公式没有可移入结论的前提")
    index = max(0, min(int(premise_index), len(formula.premises) - 1))
    premise = formula.premises[index]
    remaining = formula.premises[:index] + formula.premises[index + 1:]
    transformed = ProofFormula(remaining, LogicExpr.binary(">", premise, formula.conclusion))
    validate_formula(transformed)
    return canonicalize_variables(transformed)


def _dedupe_expressions(expressions: Iterable[LogicExpr]) -> Tuple[LogicExpr, ...]:
    result: List[LogicExpr] = []
    signatures = set()
    for expression in expressions:
        signature = expression_to_data(expression)
        signature = repr(signature)
        if signature in signatures:
            continue
        signatures.add(signature)
        result.append(expression)
    return tuple(result)


def modus_ponens(first: ProofFormula, second: ProofFormula) -> ProofFormula:
    first = canonicalize_variables(first)
    second = freshen_variables(second, formula_variables(first))
    conclusion = first.conclusion
    if conclusion.kind != "binary" or conclusion.value != ">":
        raise FormalLogicError("第一张牌的结论不是蕴含式")
    antecedent, consequent = conclusion.children
    if len(second.premises) > MAX_FORMULA_PREMISES:
        raise FormalLogicError("第二张牌的前提过多")
    normalized_antecedent = _strip_double_negation(antecedent)
    normalized_candidate = _strip_double_negation(second.conclusion)
    if (
        normalized_antecedent.kind == "unary"
        and normalized_antecedent.value == "¬"
        and len(normalized_antecedent.children) == 1
    ):
        if match_expression_pattern(normalized_antecedent, normalized_candidate) is not None:
            bindings = None
        else:
            bindings = match_expression_pattern(
                normalized_antecedent.children[0],
                normalized_candidate,
            )
            if bindings is None:
                bindings = {}
    else:
        bindings = match_expression_pattern(normalized_antecedent, normalized_candidate)
    if bindings is None:
        raise FormalLogicError("两张牌的中间公式无法合一")
    first_resolved = substitute_formula(first, bindings)
    second_resolved = substitute_formula(second, bindings)
    resolved_conclusion = substitute_expression(consequent, bindings)
    combined = ProofFormula(
        _dedupe_expressions((*first_resolved.premises, *second_resolved.premises)),
        resolved_conclusion,
    )
    validate_formula(combined)
    return canonicalize_variables(combined)


def next_fresh_variable(formula: ProofFormula) -> str:
    used = set(formula_variables(formula))
    index = 0
    while f"${index}" in used:
        index += 1
    return f"${index}"


def constant_card_formula(card_id: str) -> ProofFormula:
    return ProofFormula((), LogicExpr.constant(str(card_id or "")))
