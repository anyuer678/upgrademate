"""规则加载/校验/行级匹配测试。"""
import json

import pytest

from upgrademate import rules
from upgrademate.rules import (RuleSchemaError, apply_rule_to_line, load_rules,
                   validate_rule)

ALL_RULES = load_rules()


@pytest.mark.parametrize("r", ALL_RULES, ids=lambda r: r.id)
def test_example_match(r):
    """每条内置规则按 example_before → example_after 断言。"""
    assert apply_rule_to_line(r, r.example_before) == r.example_after


def test_required_rulesets_present():
    profiles = {r.profile for r in ALL_RULES}
    assert {"springboot3", "python3"} <= profiles
    assert len(ALL_RULES) >= 10


def test_no_match_returns_none():
    r = [x for x in load_rules("springboot3") if x.id == "s2s3.javax.servlet"][0]
    assert apply_rule_to_line(r, "import org.junit.Test;") is None
    assert apply_rule_to_line(r, "package com.demo;") is None


def test_priority_values_valid():
    for r in ALL_RULES:
        assert r.priority in ("high", "medium", "low")


def test_missing_field_raises():
    base = {"id": "x", "profile": "p", "priority": "high", "match": {"regex": "a"},
            "replace": "b", "explain": "e", "example_before": "a", "example_after": "b"}
    del base["match"]
    with pytest.raises(RuleSchemaError):
        validate_rule(base)


def test_bad_priority_raises():
    base = {"id": "x", "profile": "p", "priority": "urgent", "match": {"regex": "a"},
            "replace": "b", "explain": "e", "example_before": "a", "example_after": "b"}
    with pytest.raises(RuleSchemaError):
        validate_rule(base)


def test_bad_regex_raises():
    base = {"id": "x", "profile": "p", "priority": "high", "match": {"regex": "("},
            "replace": "b", "explain": "e", "example_before": "a", "example_after": "b"}
    with pytest.raises(RuleSchemaError):
        validate_rule(base)


def test_duplicate_id_raises(tmp_path, monkeypatch):
    rule = {"id": "dup", "profile": "t", "priority": "low", "match": {"regex": "a"},
            "replace": "b", "explain": "e", "example_before": "a", "example_after": "b"}
    (tmp_path / "a.json").write_text(json.dumps([rule]), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps([rule]), encoding="utf-8")
    monkeypatch.setattr(rules, "RULES_DIR", str(tmp_path))
    with pytest.raises(RuleSchemaError):
        load_rules()


def test_bad_json_raises(tmp_path, monkeypatch):
    (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(rules, "RULES_DIR", str(tmp_path))
    with pytest.raises(RuleSchemaError):
        load_rules()


def test_profile_filter():
    boot = load_rules("springboot3")
    assert boot and all(r.profile == "springboot3" for r in boot)


def test_file_glob_mapped(tmp_path, monkeypatch):
    """开发规范 file 字段被映射为 file_glob。"""
    rule = {"id": "g", "profile": "t", "priority": "low",
            "match": {"file": "*.x", "regex": "A"}, "replace": "B", "explain": "e",
            "example_before": "A", "example_after": "B"}
    (tmp_path / "a.json").write_text(json.dumps([rule]), encoding="utf-8")
    monkeypatch.setattr(rules, "RULES_DIR", str(tmp_path))
    loaded = load_rules("t")[0]
    assert loaded.match["file_glob"] == "*.x" and "file" not in loaded.match


def test_match_not_dict_raises():
    base = {"id": "x", "profile": "p", "priority": "high", "match": ["regex", "a"],
            "replace": "b", "explain": "e", "example_before": "a", "example_after": "b"}
    with pytest.raises(RuleSchemaError):
        validate_rule(base)


def test_regex_not_str_raises():
    base = {"id": "x", "profile": "p", "priority": "high", "match": {"regex": 42},
            "replace": "b", "explain": "e", "example_before": "a", "example_after": "b"}
    with pytest.raises(RuleSchemaError):
        validate_rule(base)


def test_rule_not_dict_raises():
    with pytest.raises(RuleSchemaError):
        validate_rule("not-a-dict")


def test_top_level_scalar_raises(tmp_path, monkeypatch):
    (tmp_path / "s.json").write_text('"just a string"', encoding="utf-8")
    monkeypatch.setattr(rules, "RULES_DIR", str(tmp_path))
    with pytest.raises(RuleSchemaError):
        load_rules()


def test_catastrophic_regex_rejected():
    """防 ReDoS：嵌套量词等灾难性回溯正则在加载时被静态拒绝。"""
    for bad in ["(a+)+$", "(a*)*x", "(a|a)+", "(a{2,})+"]:
        base = {"id": "x", "profile": "p", "priority": "high", "match": {"regex": bad},
                "replace": "b", "explain": "e", "example_before": "a", "example_after": "b"}
        with pytest.raises(RuleSchemaError):
            validate_rule(base)


def test_very_long_line_no_match():
    """超长行按未命中处理（防 ReDoS 第二道防线）。"""
    base = {"id": "x", "profile": "p", "priority": "high", "match": {"regex": "a+"},
            "replace": "b", "explain": "e", "example_before": "a", "example_after": "b"}
    r = validate_rule(base)
    assert apply_rule_to_line(r, "a" * 150_000) is None
