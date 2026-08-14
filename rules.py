"""规则模型、校验与加载。"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

RULES_DIR = "rules/"
_REQUIRED = ("id", "profile", "priority", "match", "replace", "explain",
             "example_before", "example_after")
_PATTERNS = {}
_DANGEROUS_RE = [re.compile(r"[+*?{}]\s*\)\s*[+*?{]"),
                 re.compile(r"\((?:[^()]|\\.)*\|(?:[^()]|\\.)*\)\s*[+*?{]")]
_MAX_REGEX_LEN, _MAX_LINE_LEN = 256, 100_000


class RuleSchemaError(Exception):
    pass


@dataclass(frozen=True)
class Rule:
    id: str
    profile: str
    priority: str
    match: dict
    replace: str
    explain: str
    example_before: str
    example_after: str
    options: dict = field(default_factory=dict)


@dataclass
class Hit:
    rule: Rule
    file_path: str
    lineno: int
    before: str
    after: str


def validate_rule(rule: dict) -> Rule:
    if not isinstance(rule, dict):
        raise RuleSchemaError(f"rule 必须是对象，收到 {type(rule).__name__}")
    if any(k not in rule for k in _REQUIRED):
        raise RuleSchemaError(f"rule 缺少字段 {[k for k in _REQUIRED if k not in rule]}")
    m = rule["match"]
    if not isinstance(m, dict) or not isinstance(m.get("regex"), str):
        raise RuleSchemaError(f"rule {rule['id']} 缺少对象 match 或字符串 regex")
    _check_safe_regex(rule["id"], m["regex"])
    if rule["priority"] not in ("high", "medium", "low"):
        raise RuleSchemaError(f"rule {rule['id']} priority 非法: {rule['priority']}")
    m = dict(m)
    m["file_glob"] = m.pop("file", m.get("file_glob", "*"))  # 开发规范 file -> file_glob
    return Rule(rule["id"], rule["profile"], rule["priority"], m, rule["replace"],
                rule["explain"], rule["example_before"], rule["example_after"],
                rule.get("options", {}))


def _rules_path() -> Path:
    return Path(RULES_DIR) if Path(RULES_DIR).exists() else Path(__file__).resolve().parent / RULES_DIR


def load_rules(profile: str | None = None) -> list[Rule]:
    rules, seen = [], {}
    for f in sorted(_rules_path().glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise RuleSchemaError(f"规则文件 {f.name} 非合法 JSON: {e}")
        if not isinstance(data, (list, dict)):
            raise RuleSchemaError(f"规则文件 {f.name} 顶层必须是对象或数组")
        for item in data if isinstance(data, list) else [data]:
            r = validate_rule(item)
            if profile is not None and r.profile != profile:
                continue
            if r.id in seen:
                raise RuleSchemaError(f"rule id 重复: {r.id}")
            seen[r.id] = r
            rules.append(r)
    return rules


def _check_safe_regex(rid, regex):
    """静态拒绝潜在灾难性回溯的正则（当前 Python re 无 timeout，改从源头防护）。"""
    if len(regex) > _MAX_REGEX_LEN or any(p.search(regex) for p in _DANGEROUS_RE):
        raise RuleSchemaError(f"rule {rid} 正则不安全，拒绝: {regex}")
    try:
        re.compile(regex)
    except re.error as e:
        raise RuleSchemaError(f"rule {rid} regex 非法: {e}")


def _pattern(rule: Rule) -> re.Pattern:
    p = _PATTERNS.get(rule.id)
    if p is None:
        flags = re.I if rule.options.get("ignore_case") else 0
        p = re.compile(rule.match["regex"], flags)
        _PATTERNS[rule.id] = p
    return p


def apply_rule_to_line(rule: Rule, line: str) -> str | None:
    """匹配则返回替换结果，否则 None；始终用 re.subn 得到 count。"""
    if len(line) > _MAX_LINE_LEN:
        return None  # 超长行防御，按未命中处理
    pat, count = _pattern(rule), rule.options.get("count", 0)
    try:
        new, n = pat.subn(rule.replace, line, count=count)
    except TimeoutError:  # 3.11+ re 超时兜底，按未命中处理
        return None
    return None if n == 0 else new
