"""CLI 装配：加载规则 → 匹配 → dry-run/apply/restore 报告。"""
import argparse
import json
import os
import sys
from pathlib import Path

from .diff_engine import compute_changes, unified_diff, risk_of
from .executor import (WriteError, prepare_backup, apply_changes,
                      restore_c_from_backup, write_log, load_backup)
from .llm_advisor import LLMConfig, advise
from .rules import load_rules, RuleSchemaError

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


_C = {"high": "\x1b[31m", "medium": "\x1b[33m", "low": "\x1b[36m"}


def _col(pri: str, t: str) -> str:
    return f"{_C[pri]}{t}\x1b[0m" if sys.stdout.isatty() and pri in _C else t


def parse_args(argv=None):
    ap = argparse.ArgumentParser(prog="upm", description="旧代码升级器 UpgradeMate")
    ap.add_argument("profile")
    g = ap.add_mutually_exclusive_group(); g.add_argument("--files", nargs="+"); g.add_argument("--dir")
    g = ap.add_mutually_exclusive_group(); g.add_argument("--dry-run", action="store_true"); g.add_argument("--apply", action="store_true")
    ap.add_argument("--backup-dir", default=".upgrade-backup")
    ap.add_argument("--list-rules", action="store_true"); ap.add_argument("--json", action="store_true")
    g = ap.add_mutually_exclusive_group(); g.add_argument("--no-llm", action="store_true"); g.add_argument("--llm", action="store_true")
    ap.add_argument("--restore", action="store_true")
    return ap.parse_args(argv)


def _collect(args):
    if args.files:
        return [Path(f) for f in args.files if not Path(f).is_symlink()]
    return [p for dp, _, fns in os.walk(args.dir) for f in fns
            if not (p := Path(dp) / f).is_symlink()]  # walk 不跟随目录链接


def _summary(changes) -> dict:
    s = {"high": 0, "medium": 0, "low": 0}
    for c in changes:
        for k, v in risk_of(c).items():
            s[k] += v
    return s


def _diff(c):
    return unified_diff(c.original.splitlines(True), c.modified.splitlines(True), c.path)


def _report(args, changes, mode, advices, rep=None):
    s = _summary(changes)
    if args.json:
        out = {"profile": args.profile, "mode": mode,
               "summary": {"files": len(changes), "risk": s},
               "changes": [{"path": c.path,
                             "hits": [{"rule": h.rule.id, "priority": h.rule.priority,
                                        "lineno": h.lineno, "before": h.before,
                                        "after": h.after} for h in c.hits],
                             "diff": _diff(c)} for c in changes],
               "advice": [{"file": a.file, "snippet": a.snippet, "reason": a.reason,
                            "confidence": a.confidence} for a in advices]}
        if rep is not None:
            out.update(written=rep.written,
                       skipped=[{"path": p, "reason": r} for p, r in rep.skipped])
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    out = [f"== UpgradeMate {args.profile} [{mode}] =="]
    for c in changes:
        r = risk_of(c)
        out.append(f"[{c.path}] high={r['high']} medium={r['medium']} low={r['low']}")
        for h in c.hits:
            out.append(f"  L{h.lineno} {_col(h.rule.priority, '[' + h.rule.priority + ']')} "
                       f"{h.rule.id}: {h.before.rstrip()} -> {h.after.rstrip()}")
    for c in changes:
        out.append(f"== diff {c.path} ==\n{_diff(c).rstrip()}")
    for a in advices:
        out.append(f"[LLM] {a.file}: {a.snippet!r} - {a.reason} ({a.confidence})")
    out += [f"== 风险统计: {s} =="] + (["存在 high 风险项，请人工确认后再 apply"] if s["high"] else [])
    print("\n".join(out))


def _restore(args) -> int:
    bdir = Path(args.backup_dir)
    if not bdir.is_dir():
        print(f"错误: 备份目录 {bdir} 不存在，无法 restore", file=sys.stderr)
        return 2
    print(f"restore 完成，恢复 {restore_c_from_backup(load_backup(bdir))} 个不一致文件")
    return 0


def _load(args):
    try:
        rules = load_rules(args.profile)
    except RuleSchemaError as e:
        print(f"规则集错误: {e}", file=sys.stderr)
        return None, 3
    if not rules:
        print(f"错误: 规则集 '{args.profile}' 不存在", file=sys.stderr)
        return None, 3
    return rules, 0


def _list_rules(args) -> int:
    rules, rc = _load(args)
    if rc:
        return rc
    if args.json:
        print(json.dumps([{"id": r.id, "priority": r.priority, "explain": r.explain}
                          for r in rules], ensure_ascii=False, indent=2))
        return 0
    print(f"== rules ({args.profile}) ==")
    for r in rules:
        print(f"  {r.id} [{r.priority}] {r.explain}")
    return 0


def _llm_cfg(args):
    if not args.llm:
        return None
    key = os.environ.get("UPM_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        print("提示: --llm 已开启但未设置 UPM_LLM_API_KEY/OPENAI_API_KEY，跳过 LLM", file=sys.stderr)
        return None
    return LLMConfig(os.environ.get("UPM_LLM_API_BASE", "https://api.openai.com/v1"),
                     key, os.environ.get("UPM_LLM_MODEL", "gpt-4o-mini"))


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.restore:
        if args.apply or args.list_rules:
            print("错误: --restore 不能与 --apply/--list-rules 同时使用", file=sys.stderr)
            return 2
        return _restore(args)
    if args.list_rules:
        return _list_rules(args)
    if not args.files and not args.dir:
        print("错误: 需要 --files 或 --dir 指定检查目标", file=sys.stderr)
        return 2
    if args.dir and not Path(args.dir).is_dir():
        print(f"错误: 目录不存在: {args.dir}", file=sys.stderr)
        return 2
    rules, rc = _load(args)
    if rc:
        return rc
    changes = compute_changes(_collect(args), rules)
    advices = advise([c for c in changes if risk_of(c)["high"] > 0], _llm_cfg(args)) if args.llm else []
    if args.apply:
        try:
            backup = prepare_backup(changes, Path.cwd(), Path(args.backup_dir))
        except (WriteError, OSError) as e:
            print(f"错误: {e}", file=sys.stderr)
            return 4
        rep, mode = apply_changes(changes, backup, mode="apply"), "apply"
        write_log(Path.cwd(), Path(args.backup_dir), changes)
        for p, r in rep.skipped:
            print(f"警告: 写入失败 {p}: {r}", file=sys.stderr)
    else:
        rep, mode = None, "dry-run"
    _report(args, changes, mode, advices, rep)
    if rep is not None and rep.written == 0 and changes:
        return 2  # apply 全部写入失败，视为环境错误
    return 1 if _summary(changes)["high"] else 0


if __name__ == "__main__":
    sys.exit(main())
