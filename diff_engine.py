"""匹配与 diff 生成，纯函数零副作用，结果仅内存。"""
import difflib
import fnmatch
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from rules import Rule, Hit, apply_rule_to_line


@dataclass
class FileChange:
    path: str
    original: str
    modified: str
    hits: list


def process_text(name: str, text: str, rules: list[Rule]) -> FileChange | None:
    """内存版逐行匹配（前端复用），无 IO；返回 None 表示无变化。"""
    lines, out, hits = text.splitlines(keepends=True), [], []
    for i, line in enumerate(lines, 1):
        base, tail = (line[:-2], "\r\n") if line.endswith("\r\n") else (line, "")
        for rule in rules:
            if not fnmatch.fnmatch(name, rule.match.get("file_glob", "*")):
                continue
            new = apply_rule_to_line(rule, base)
            if new is not None:
                hits.append(Hit(rule, name, i, line, new + tail))
                out.append(new + tail)
                break
        else:
            out.append(line)
    modified = "".join(out)
    return None if modified == text else FileChange(name, text, modified, hits)


def _process(path: Path, rules: list[Rule]) -> FileChange | None:
    try:
        text = path.read_bytes().decode("utf-8", "surrogateescape")
    except OSError:
        return None
    return process_text(str(path), text, rules)


def compute_changes(files: list[Path], rules: list[Rule], *, workers: int = 4) -> list[FileChange]:
    scan = lambda f: _process(f, rules)
    if workers > 1 and len(files) > 1:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            return [c for c in ex.map(scan, files) if c]
    return [c for f in files if (c := scan(f)) is not None]


def unified_diff(original_lines, modified_lines, path: str) -> str:
    return "".join(difflib.unified_diff(original_lines, modified_lines, str(path), str(path)))


def risk_of(c: FileChange) -> dict:
    return {"high": sum(h.rule.priority == "high" for h in c.hits),
            "medium": sum(h.rule.priority == "medium" for h in c.hits),
            "low": sum(h.rule.priority == "low" for h in c.hits)}
