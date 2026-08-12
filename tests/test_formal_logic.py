import pytest

from formal_logic import (
    FormalLogicError,
    LogicExpr,
    ProofFormula,
    canonicalize_variables,
    constant_card_formula,
    formula_from_data,
    formula_signature,
    formula_to_data,
    formula_variables,
    formulas_alpha_equivalent,
    formulas_special_equivalent,
    format_formula,
    implication_chain,
    instantiate_formula,
    match_expression_pattern,
    modus_ponens,
    parse_formula,
    transform_contraposition,
    transform_deduction,
    transform_inverse_deduction,
    unify_expressions,
)


@pytest.mark.parametrize(
    ("source", "variables"),
    [
        ("├$0>($1>$0)", ["$0", "$1"]),
        ("├($0>($1>$2))>(($0>$1)>($0>$2))", ["$0", "$1", "$2"]),
        ("$0，¬$0├$1", ["$0", "$1"]),
        ("∀$0:$0├∃$1:($0>$1)", ["$0", "$1"]),
    ],
)
def test_parser_tracks_variables_and_round_trips(source, variables):
    formula = parse_formula(source)
    assert formula_variables(formula) == variables
    assert formula_from_data(formula_to_data(formula)) == formula


def test_implication_is_right_associative():
    formula = parse_formula("├$0>$1>$2")
    antecedents, result = implication_chain(formula.conclusion)
    assert [node.value for node in antecedents] == ["$0", "$1"]
    assert result == LogicExpr.variable("$2")


def test_double_negation_is_equal_for_matching():
    left = parse_formula("├¬¬$7>$7")
    right = parse_formula("├$0>$0")
    assert formulas_alpha_equivalent(left, right)


def test_special_formula_equivalence_preserves_double_negation():
    identity = parse_formula("├$0>$0")
    introduction = parse_formula("├$7>¬¬$7")
    elimination = parse_formula("├¬¬$3>$3")
    assert not formulas_special_equivalent(identity, introduction)
    assert not formulas_special_equivalent(identity, elimination)
    assert not formulas_special_equivalent(introduction, elimination)


def test_special_formula_equivalence_ignores_premise_order():
    left = parse_formula("$0>$1，$1>$2├$0>$2")
    right = parse_formula("$8>$9，$7>$8├$7>$9")
    assert formulas_special_equivalent(left, right)


def test_special_formula_equivalence_requires_bijective_variable_renaming():
    left = parse_formula("$0，$1├$0")
    collapsed = parse_formula("$7，$7├$7")
    assert not formulas_special_equivalent(left, collapsed)


def test_simultaneous_variable_renaming_preserves_distinct_variables():
    source = parse_formula("├$2>($1>$2)")
    assert format_formula(canonicalize_variables(source)) == "├$0>($1>$0)"


def test_mp_pattern_matching_preserves_variable_equalities_and_inequalities():
    pattern = parse_formula("├$0>($1>$2)").conclusion
    repeated_candidate = parse_formula("├$7>($8>$7)").conclusion
    assert match_expression_pattern(pattern, repeated_candidate) is None

    matching_candidate = parse_formula("├$7>($8>$9)").conclusion
    bindings = match_expression_pattern(pattern, matching_candidate)
    assert bindings is not None
    assert len(set(bindings.values())) == 3


def test_unification_has_occurs_check():
    variable = LogicExpr.variable("$0")
    recursive = LogicExpr.binary(">", variable, LogicExpr.variable("$1"))
    assert unify_expressions(variable, recursive) is None


def test_modus_ponens_freshens_independent_variables():
    first = parse_formula("$0├$1>$2")
    second = parse_formula("$0├$1")
    result = modus_ponens(first, second)
    assert len(result.premises) == 2
    assert len(formula_variables(result)) == 3
    assert format_formula(result).endswith("├$2")


def test_modus_ponens_deduplicates_equivalent_premises():
    result = modus_ponens(parse_formula("[A]├$0>$1"), parse_formula("[A]├$0"))
    assert len(result.premises) == 1


def test_modus_ponens_uses_the_mods_single_negation_rule():
    result = modus_ponens(parse_formula("├¬$0>$0"), parse_formula("├[A]"))
    assert format_formula(result) == "├A"
    with pytest.raises(FormalLogicError, match="无法合一"):
        modus_ponens(parse_formula("├¬$0>$0"), parse_formula("├¬[A]"))


def test_modus_ponens_rejects_a_candidate_that_collapses_distinct_variables():
    with pytest.raises(FormalLogicError, match="无法合一"):
        modus_ponens(
            parse_formula("├($0>($1>$2))>(($0>$1)>($0>$2))"),
            parse_formula("├$0>($1>$0)"),
        )


def test_modus_ponens_accepts_card_constants():
    result = modus_ponens(
        parse_formula("├[Basic]>($1>[Basic])"),
        constant_card_formula("Basic"),
    )
    assert format_formula(result) == "├$0>Basic"


def test_formula_instantiation_does_not_recurse_inside_its_replacement():
    formula = parse_formula("├$0>$0")
    replacement = parse_formula("├$0>$1").conclusion
    result = instantiate_formula(formula, {"$0": replacement})
    assert format_formula(result) == "├($0>$1)>($0>$1)"


def test_metatheorem_transformations():
    source = parse_formula("$0├$1>$2")
    inverse = transform_inverse_deduction(source)
    assert len(inverse.premises) == 2
    assert transform_deduction(inverse) is not None
    contraposition = transform_contraposition(source)
    assert contraposition.conclusion.value == ">"
    assert contraposition.conclusion.children[0].value == "¬"


def test_formula_limits_reject_too_many_premises():
    source = ",".join(f"${index}" for index in range(9)) + "├$9"
    with pytest.raises(FormalLogicError, match="前提数量"):
        parse_formula(source)


def test_constant_card_formula_is_not_a_pattern_variable():
    basic = constant_card_formula("vanilla:basic")
    other = constant_card_formula("vanilla:bone")
    assert formula_signature(basic) != formula_signature(other)
    assert canonicalize_variables(basic) == basic
