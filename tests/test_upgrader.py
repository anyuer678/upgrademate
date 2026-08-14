"""upgrader 核心行为测试：dry-run 零副作用 / apply / restore / 原子写。"""
import json
import os

import pytest

import rules
from diff_engine import FileChange, compute_changes
from executor import (ApplyReport, WriteError, apply_changes, load_backup,
                      prepare_backup, restore_c_from_backup, upgrade_log,
                      write_log)

JAVA = "import javax.servlet.http.HttpServletRequest;\npublic class A {}\n"


def _boot_rule():
    return [r for r in rules.load_rules("springboot3")
            if r.id == "s2s3.javax.servlet"][0]


def _changes(tmp_path):
    f = tmp_path / "A.java"
    f.write_text(JAVA, encoding="utf-8")
    return compute_changes([f], [_boot_rule()]), f


def test_dry_run_no_fs_side_effect(tmp_path):
    changes, f = _changes(tmp_path)
    before_mtime = f.stat().st_mtime_ns
    # dry-run 全流程只读：不再触碰文件，也不产生备份目录
    assert not (tmp_path / ".upgrade-backup").exists()
    assert f.read_text(encoding="utf-8") == JAVA
    assert f.stat().st_mtime_ns == before_mtime
    assert changes[0].hits[0].after.strip() == \
        "import jakarta.servlet.http.HttpServletRequest;"


def test_apply_creates_backup_and_writes(tmp_path):
    changes, f = _changes(tmp_path)
    orig = f.read_bytes()
    backup = prepare_backup(changes, tmp_path, ".upgrade-backup")
    rep = apply_changes(changes, backup, mode="apply")
    assert isinstance(rep, ApplyReport) and rep.written == 1
    assert (tmp_path / ".upgrade-backup" / "A.java").read_bytes() == orig
    assert f.read_text(encoding="utf-8").startswith("import jakarta.servlet")


def test_restore_byte_identical(tmp_path):
    changes, f = _changes(tmp_path)
    orig = f.read_bytes()
    backup = prepare_backup(changes, tmp_path, ".upgrade-backup")
    apply_changes(changes, backup, mode="apply")
    assert f.read_text(encoding="utf-8") != JAVA
    n = restore_c_from_backup(backup)
    assert n == 1
    assert f.read_bytes() == orig


def test_restore_only_inconsistent_files(tmp_path):
    changes, f = _changes(tmp_path)
    backup = prepare_backup(changes, tmp_path, ".upgrade-backup")
    apply_changes(changes, backup, mode="apply")
    f.write_text(JAVA, encoding="utf-8")  # 手动还原，与备份一致
    assert restore_c_from_backup(backup) == 0  # 与备份一致的文件跳过
    assert f.read_text(encoding="utf-8") == JAVA


def test_atomic_write_failure_no_partial_file(tmp_path, monkeypatch):
    changes, f = _changes(tmp_path)
    backup = prepare_backup(changes, tmp_path, ".upgrade-backup")

    def boom(src, dst):
        raise OSError("simulated replace failure")

    monkeypatch.setattr("os.replace", boom)
    rep = apply_changes(changes, backup, mode="apply")
    assert rep.written == 0 and len(rep.skipped) == 1
    assert f.read_text(encoding="utf-8") == JAVA  # 目标文件未被破坏
    leftovers = [p for p in (tmp_path).rglob(".upm-*")]
    assert leftovers == []  # 不留半文件


def test_crlf_line_endings_preserved(tmp_path):
    f = tmp_path / "x.py"
    f.write_bytes(b"print \"hi\"\r\nimport urlparse\r\n")
    changes = compute_changes([f], rules.load_rules("python3"))
    assert changes[0].modified == 'print("hi")\r\nfrom urllib.parse import urlparse\r\n'
    backup = prepare_backup(changes, tmp_path, ".upgrade-backup")
    apply_changes(changes, backup, mode="apply")
    assert f.read_bytes() == b"print(\"hi\")\r\nfrom urllib.parse import urlparse\r\n"


def test_prepare_backup_rejects_parent_escape(tmp_path):
    changes = [FileChange("../evil.py", "x", "y", [])]
    with pytest.raises(WriteError):
        prepare_backup(changes, tmp_path, ".upgrade-backup")


def test_prepare_backup_conflict_raises(tmp_path):
    changes, _ = _changes(tmp_path)
    prepare_backup(changes, tmp_path, ".upgrade-backup")
    with pytest.raises(WriteError):
        prepare_backup(changes, tmp_path, ".upgrade-backup")


def test_upgrade_log_valid_json(tmp_path):
    changes, f = _changes(tmp_path)
    log = json.loads(upgrade_log(changes))
    assert log["tool"] == "upgrademate"
    entry = log["files"][0]
    assert entry["path"] == str(f) and entry["hits"][0]["rule"] == "s2s3.javax.servlet"


def test_load_backup_and_write_log(tmp_path):
    changes, f = _changes(tmp_path)
    backup = prepare_backup(changes, tmp_path, ".upgrade-backup")
    apply_changes(changes, backup, mode="apply")
    log = write_log(tmp_path, ".upgrade-backup", changes)
    assert log.exists() and json.loads(log.read_text(encoding="utf-8"))
    loaded = load_backup(tmp_path / ".upgrade-backup")
    assert loaded.entries and str(loaded.entries[0][0]) == "A.java"


def test_backup_dir_anywhere_roundtrip(tmp_path):
    """backup-dir 为多级/绝对路径时 apply/restore 仍正确（回归 dir.parent 反推 bug）。"""
    changes, f = _changes(tmp_path)
    orig = f.read_bytes()
    bdir = tmp_path / "backups" / "nested"
    backup = prepare_backup(changes, tmp_path, bdir)
    assert backup.workdir == tmp_path
    apply_changes(changes, backup, mode="apply")
    assert f.read_text(encoding="utf-8").startswith("import jakarta.servlet")
    assert restore_c_from_backup(backup) == 1
    assert f.read_bytes() == orig


def test_load_backup_restores_via_workdir_meta(tmp_path):
    """load_backup 从 .upgrade-workdir 元数据恢复 workdir，restore 定位正确。"""
    changes, f = _changes(tmp_path)
    orig = f.read_bytes()
    bdir = tmp_path / "bk" / "sub"
    backup = prepare_backup(changes, tmp_path, bdir)
    apply_changes(changes, backup, mode="apply")
    loaded = load_backup(bdir)
    assert loaded.workdir == tmp_path.resolve()
    assert restore_c_from_backup(loaded) == 1
    assert f.read_bytes() == orig


def test_bdir_is_file_raises(tmp_path):
    changes, _ = _changes(tmp_path)
    bfile = tmp_path / "bk"
    bfile.write_text("x", encoding="utf-8")
    with pytest.raises(WriteError):
        prepare_backup(changes, tmp_path, bfile)


def test_symlink_rejected(tmp_path):
    (tmp_path / "real.py").write_text("a", encoding="utf-8")
    try:
        os.symlink(tmp_path / "real.py", tmp_path / "link.py")
    except OSError:
        pytest.skip("无权限创建符号链接")
    changes = [FileChange(str(tmp_path / "link.py"), "a", "b", [])]
    with pytest.raises(WriteError):
        prepare_backup(changes, tmp_path, ".upgrade-backup")
