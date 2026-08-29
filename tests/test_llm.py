"""llm_advisor 离线可用性测试（全程 mock，不触网）。"""
from upgrademate import llm_advisor
from upgrademate.diff_engine import FileChange
from upgrademate.llm_advisor import Advice, LLMConfig, advise
from upgrademate.rules import Hit, Rule


def _fc():
    r = Rule(id="r1", profile="t", priority="high", match={"regex": "x"},
             replace="y", explain="e", example_before="x", example_after="y")
    return FileChange(path="a.py", original="line1\nline2\n",
                      modified="line1\nline2\n",
                      hits=[Hit(r, "a.py", 1, "line1", "line1")])


def test_advise_offline_cfg_none():
    assert advise([_fc()], None) == []


def test_advise_mock_response():
    sent = {}

    def fake_call(cfg, prompt):
        sent["cfg"] = cfg
        return "2|line2|需人工确认|high"

    llm_advisor._call_llm = fake_call
    cfg = LLMConfig(api_base="http://x/v1", api_key="k", model="m")
    out = advise([_fc()], cfg)
    assert len(out) == 1
    a = out[0]
    assert isinstance(a, Advice)
    assert (a.file, a.snippet, a.reason, a.confidence) == \
        ("a.py", "line2", "需人工确认", "high")


def test_advise_tolerates_empty_llm_reply(monkeypatch):
    monkeypatch.setattr(llm_advisor, "_call_llm", lambda cfg, p: None)
    cfg = LLMConfig(api_base="http://x/v1", api_key="k", model="m")
    assert advise([_fc()], cfg) == []


def test_advise_skips_fully_covered_file(monkeypatch):
    r = Rule(id="r1", profile="t", priority="high", match={"regex": "line"},
             replace="L", explain="e", example_before="x", example_after="y")
    fc = FileChange(path="a.py", original="line1\nline2\n",
                    modified="L1\nL2\n",
                    hits=[Hit(r, "a.py", 1, "line1", "L1"),
                          Hit(r, "a.py", 2, "line2", "L2")])
    monkeypatch.setattr(llm_advisor, "_call_llm", lambda cfg, p: "1|x|y|low")
    cfg = LLMConfig(api_base="http://x/v1", api_key="k", model="m")
    assert advise([fc], cfg) == []
