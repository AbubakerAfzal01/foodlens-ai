from backend.services import engine


def test_split_ingredients():
    assert engine.split_ingredients("Ingredients: sugar, Gelatin; E471.") == ["sugar", "Gelatin", "E471"]


def test_halal_doubtful_for_gelatin_and_ecode():
    r = engine.analyze(["sugar", "gelatin", "E471"], "halal")
    assert r["verdict"] == "doubtful"


def test_pork_not_ok_halal():
    assert engine.analyze(["lard"], "halal")["verdict"] == "not_ok"


def test_vegan_flags_milk_and_alerts_allergy():
    r = engine.analyze(["sugar", "milk powder"], "vegan", ["milk"])
    assert r["verdict"] == "not_ok" and r["allergy_alerts"] == ["milk"]


def test_clean_label_ok():
    assert engine.analyze(["water", "sugar", "citric acid"], "vegan")["verdict"] in {"ok", "unknown"}


def test_unknown_ingredient_is_flagged_not_ok():
    r = engine.analyze(["sugar", "zzz-mystery-additive"], "halal")
    assert r["items"][1]["status"] == "unknown" and r["unrecognized"] == ["zzz-mystery-additive"]
    assert "status is unconfirmed" in r["items"][1]["note"]


def test_plain_label_is_ok():
    assert engine.analyze(["water", "sugar", "salt", "citric acid"], "vegan")["verdict"] == "ok"


def test_may_contain_is_separate_from_ingredients():
    ings, prec = engine.split_label("Ingredients: sugar, cocoa butter, whey powder. May contain peanuts, tree nuts.")
    assert ings == ["sugar", "cocoa butter", "whey powder"]
    assert prec == ["May contain peanuts, tree nuts"]
    r = engine.analyze(ings, "halal", ["peanuts", "milk"], prec)
    assert r["allergy_alerts"] == ["milk"] and r["precautionary_alerts"] == ["peanuts"]
    assert "peanuts" not in r["allergens"]


def test_made_in_country_is_not_a_warning():
    ings, prec = engine.split_label("sugar, salt, made in Pakistan")
    assert prec == [] and "made in Pakistan" in ings


def test_generic_nuts_alias_triggers_both_nut_allergens():
    assert set(engine.analyze(["roasted nuts"], "halal")["allergens"]) == {"peanuts", "tree nuts"}


def test_every_ingredient_rule_covers_every_profile():
    allowed = {"ok", "doubtful", "not_ok", "unknown"}
    for entry in engine.DATA["ingredients"]:
        assert set(entry["status"]) == set(engine.DIETS), entry["names"]
        assert set(entry["status"].values()) <= allowed, entry["names"]


def test_missing_profile_rule_is_unknown(monkeypatch):
    entry = next(row for row in engine.DATA["ingredients"] if "milk" in row["names"])
    monkeypatch.delitem(entry["status"], "kosher")
    result = engine.analyze(["milk"], "kosher")
    assert result["verdict"] == "unknown"
    assert result["items"][0]["status"] == "unknown"


def test_hindu_friendly_profile_checks_beef_only():
    assert engine.analyze(["beef extract"], "hindu")["verdict"] == "not_ok"


def test_specific_source_labels_override_broad_aliases():
    assert engine.analyze(["animal rennet"], "vegan")["verdict"] == "not_ok"
    assert engine.analyze(["wine vinegar"], "halal")["verdict"] == "ok"


def test_chia_seed_label_is_recognized():
    result = engine.analyze(["organic chia seeds"], "vegan")
    assert result["verdict"] == "ok" and result["unrecognized"] == []


def test_confident_ai_estimate_resolves_unknown_and_recalculates_verdict():
    result = engine.analyze(["Vitamin D3"], "halal")
    applied = engine.apply_ai_assessments(result, [{
        "ingredient": "Vitamin D3", "status": "doubtful", "confidence": "medium",
        "reason": "The source is not identified on the label.",
    }])
    assert applied == 1
    assert result["verdict"] == "doubtful"
    assert result["items"][0]["status"] == "doubtful"
    assert result["items"][0]["ai_estimated"] is True
    assert result["unrecognized"] == []


def test_low_confidence_ai_estimate_does_not_override_unknown():
    result = engine.analyze(["mystery ingredient"], "halal")
    applied = engine.apply_ai_assessments(result, [{
        "ingredient": "mystery ingredient", "status": "ok", "confidence": "low",
        "reason": "Possibly plant-derived.",
    }])
    assert applied == 0 and result["verdict"] == "unknown"


def test_ai_estimate_cannot_override_explicit_local_conflict():
    result = engine.analyze(["lard"], "halal")
    applied = engine.apply_ai_assessments(result, [{
        "ingredient": "lard", "status": "ok", "confidence": "high",
        "reason": "A contradictory model estimate.",
    }])
    assert applied == 0 and result["verdict"] == "not_ok"
