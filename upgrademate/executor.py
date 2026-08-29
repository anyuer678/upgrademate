"""唯一写盘者：备份、原子写 apply、restore、审计日志。"""
import hashlib
import json
import os
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path


class WriteError(Exception):
    pass


@dataclass
class Backup:
    dir: Path
    entries: list  # [(相对原路径, sha256)]
    workdir: Path | None = None


@dataclass
class ApplyReport:
    files: list
    written: int
    skipped: list


def _rel(path, base) -> Path:
    p = Path(path)
    if p.is_symlink():
        raise WriteError(f"拒绝符号链接文件: {path}")
    if p.is_absolute():
        try:
            p = Path(os.path.relpath(p, base))
        except ValueError:
            raise WriteError(f"跨盘路径，拒绝处理: {path}")
    if ".." in p.parts:
        raise WriteError(f"路径越界，拒绝处理: {path}")
    return p


def _sha256(raw: bytes) -> bytes:
    return hashlib.sha256(raw).digest()


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".upm-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        if path.exists():  # 原子替换保留原权限
            os.chmod(tmp, os.stat(path).st_mode)
        os.replace(tmp, path)
    except OSError:
        with suppress(OSError):
            os.close(fd)
        with suppress(OSError):
            os.unlink(tmp)
        raise


def prepare_backup(changes: list, workdir: Path,
                   backup_dir: Path = ".upgrade-backup") -> Backup:
    workdir, bdir = Path(workdir), Path(workdir) / backup_dir
    if bdir.exists() and not bdir.is_dir():
        raise WriteError(f"backup 路径存在但不是目录: {bdir}")
    if bdir.exists() and any(bdir.iterdir()):
        raise WriteError(f"backup 冲突: {bdir} 已存在且非空，拒绝执行")
    bdir.mkdir(parents=True, exist_ok=True)
    (bdir / ".upgrade-workdir").write_text(str(workdir.resolve()), encoding="utf-8")
    entries = []
    for c in changes:
        rel = _rel(c.path, workdir)
        raw = c.original.encode("utf-8", "surrogateescape")
        dst = bdir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(dst, raw)
        with suppress(OSError):
            os.chmod(dst, 0o600)
        entries.append((rel, _sha256(raw)))
    return Backup(dir=bdir, entries=entries, workdir=workdir)


def apply_changes(changes: list, backup: Backup, *, mode: str) -> ApplyReport:
    if mode == "dry-run":
        return ApplyReport([c.path for c in changes], 0, [])
    base = backup.workdir or backup.dir.parent
    written, skipped = 0, []
    for c in changes:
        rel = _rel(c.path, base)
        try:
            _atomic_write(base / rel, c.modified.encode("utf-8", "surrogateescape"))
            written += 1
        except OSError as e:
            skipped.append((c.path, str(e)))
    return ApplyReport([c.path for c in changes], written, skipped)


def restore_c_from_backup(backup: Backup) -> int:
    base = backup.workdir or backup.dir.parent
    restored = 0
    for rel, sha in backup.entries:
        target, src = base / rel, backup.dir / rel
        try:
            if target.exists() and _sha256(target.read_bytes()) == sha:
                continue  # 与备份一致，跳过
            _atomic_write(target, src.read_bytes())
            restored += 1
        except OSError:
            continue
    return restored


def load_backup(backup_dir) -> Backup:
    bdir = Path(backup_dir)
    meta = bdir / ".upgrade-workdir"
    workdir = Path(meta.read_text(encoding="utf-8").strip()) if meta.is_file() else None
    entries = [(p.relative_to(bdir), _sha256(p.read_bytes())) for p in bdir.rglob("*")
               if p.is_file() and p.name not in ("upgrade_log.json", ".upgrade-workdir")]
    return Backup(dir=bdir, entries=entries, workdir=workdir)


def upgrade_log(changes: list) -> str:
    files = [{
        "path": c.path,
        "sha256_before": hashlib.sha256(c.original.encode("utf-8")).hexdigest(),
        "sha256_after": hashlib.sha256(c.modified.encode("utf-8")).hexdigest(),
        "hits": [{"rule": h.rule.id, "priority": h.rule.priority, "lineno": h.lineno,
                   "before": h.before, "after": h.after} for h in c.hits],
    } for c in changes]
    return json.dumps({"tool": "upgrademate", "files": files}, ensure_ascii=False, indent=2)


def write_log(workdir: Path, backup_dir: Path, changes: list) -> Path:
    log = Path(workdir) / backup_dir / "upgrade_log.json"
    _atomic_write(log, upgrade_log(changes).encode("utf-8"))
    return log
