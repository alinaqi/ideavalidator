from pipeline.gates import Gate, RULES, evaluate, rollup


def _out(scores, flags=()):
    return {"scores": scores, "kill_flags": list(flags)}


def test_rules_exist_for_all_stages():
    from pipeline.stages import stage_ids

    assert set(RULES) == set(stage_ids())
    for r in RULES.values():
        assert r.criteria and set(r.critical) <= set(r.criteria)


def test_go_when_all_criteria_strong():
    crit = RULES["problem"].criteria
    g = evaluate("problem", _out({c: 4 for c in crit}))
    assert isinstance(g, Gate)
    assert g.verdict == "GO"
    assert g.score == 4.0


def test_kill_flag_forces_kill():
    crit = RULES["problem"].criteria
    g = evaluate("problem", _out({c: 5 for c in crit}, ["tarpit"]))
    assert g.verdict == "KILL"
    assert "tarpit" in " ".join(g.reasons)


def test_critical_criterion_below_two_kills():
    rule = RULES["wtp"]
    scores = {c: 4 for c in rule.criteria}
    scores[rule.critical[0]] = 1
    assert evaluate("wtp", _out(scores)).verdict == "KILL"


def test_middling_scores_pivot():
    crit = RULES["market"].criteria
    assert evaluate("market", _out({c: 3 for c in crit})).verdict == "PIVOT"


def test_missing_scores_unknown():
    assert evaluate("market", {}).verdict == "UNKNOWN"
    assert evaluate("market", _out({"nonsense": 5})).verdict == "UNKNOWN"


def test_rollup_precedence():
    mk = lambda v: Gate("x", v, 3.0, [])
    assert rollup([mk("GO"), mk("GO")]).verdict == "GO"
    assert rollup([mk("GO"), mk("PIVOT")]).verdict == "PIVOT"
    assert rollup([mk("PIVOT"), mk("KILL")]).verdict == "KILL"
    assert rollup([mk("GO"), mk("UNKNOWN")]).verdict == "UNKNOWN"
    assert rollup([]).verdict == "UNKNOWN"


def test_objective_demotes_critical_so_low_score_caps_at_pivot():
    rule = RULES["wtp"]
    scores = {c: 4 for c in rule.criteria}
    scores["budget_exists"] = 1  # critical by default -> KILL
    assert evaluate("wtp", _out(scores)).verdict == "KILL"
    out = _out(scores); out["objective"] = "plg_network"
    g = evaluate("wtp", out)
    assert g.verdict == "PIVOT"  # demoted: low immediate WTP no longer hard-kills a PLG thesis


def test_objective_does_not_rescue_kill_flags():
    out = _out({c: 5 for c in RULES["wtp"].criteria}, ["category_price_near_zero"])
    out["objective"] = "plg_network"
    assert evaluate("wtp", out).verdict == "KILL"


def test_unknown_objective_behaves_like_default():
    rule = RULES["economics"]
    scores = {c: 4 for c in rule.criteria}; scores["breakeven_reachability"] = 1
    out = _out(scores); out["objective"] = "bogus"
    assert evaluate("economics", out).verdict == "KILL"


def test_validation_mode_demotes_problem_existing_spend():
    rule = RULES["problem"]
    scores = {c: 4 for c in rule.criteria}; scores["existing_spend"] = 1
    assert evaluate("problem", _out(scores)).verdict == "KILL"
    out = _out(scores); out["validation_mode"] = "new_market"
    assert evaluate("problem", out).verdict == "PIVOT"


def test_objective_and_mode_demotions_union():
    rule = RULES["market"]
    scores = {c: 4 for c in rule.criteria}; scores["market_pull"] = 1
    out = _out(scores); out["validation_mode"] = "new_market"
    assert evaluate("market", out).verdict == "PIVOT"  # market_pull demoted by mode
