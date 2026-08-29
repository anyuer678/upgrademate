"""CLI 端到端行为测试：参数校验、5 档退出码、--json 合法性。"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JAVA = "import javax.servlet.http.HttpServletRequest;\npublic class HelloController {}\n"
CLEAN = "public class Clean {}\n"


def run(tmp, *argv):
    return subprocess.run([sys.executable, "-m", "upgrademate.main", *argv],
                          cwd=tmp, capture_output=True, text=True,
                          encoding="utf-8")


def _src(tmp, name="HelloController.java", content=JAVA):
    d = tmp / "src"
    d.mkdir()
    (d / name).write_text(content, encoding="utf-8")
    return d


def test_no_args_exit_2(tmp_path):
    r = run(tmp_path)
    assert r.returncode == 2


def test_missing_target_exit_2(tmp_path):
    r = run(tmp_path, "springboot3")
    assert r.returncode == 2


def test_files_and_dir_conflict_exit_2(tmp_path):
    r = run(tmp_path, "springboot3", "--files", "a", "--dir", ".")
    assert r.returncode == 2


def test_missing_dir_exit_2(tmp_path):
    r = run(tmp_path, "springboot3", "--dir", "no_such_dir")
    assert r.returncode == 2
    assert "目录不存在" in r.stderr


def test_apply_and_dry_run_conflict_exit_2(tmp_path):
    _src(tmp_path)
    r = run(tmp_path, "springboot3", "--dir", "src", "--apply", "--dry-run")
    assert r.returncode == 2


def test_unknown_profile_exit_3(tmp_path):
    r = run(tmp_path, "nosuchprofile", "--dir", ".")
    assert r.returncode == 3
    assert "不存在" in r.stderr


def test_list_rules_exit_0(tmp_path):
    r = run(tmp_path, "springboot3", "--list-rules")
    assert r.returncode == 0
    assert "s2s3.javax.servlet" in r.stdout
    assert "[high]" in r.stdout


def test_dry_run_high_exit_1(tmp_path):
    _src(tmp_path)
    r = run(tmp_path, "springboot3", "--dir", "src")
    assert r.returncode == 1
    assert "jakarta.servlet" in r.stdout
    assert not (tmp_path / ".upgrade-backup").exists()


def test_dry_run_clean_exit_0(tmp_path):
    _src(tmp_path, "Clean.java", CLEAN)
    r = run(tmp_path, "springboot3", "--dir", "src")
    assert r.returncode == 0


def test_json_output_valid(tmp_path):
    _src(tmp_path)
    r = run(tmp_path, "springboot3", "--dir", "src", "--json")
    assert r.returncode == 1
    data = json.loads(r.stdout)
    assert data["profile"] == "springboot3" and data["mode"] == "dry-run"
    assert data["summary"]["risk"]["high"] >= 1
    assert data["changes"][0]["hits"][0]["after"].strip() == \
        "import jakarta.servlet.http.HttpServletRequest;"


def test_apply_creates_backup_and_log(tmp_path):
    _src(tmp_path)
    orig = (tmp_path / "src" / "HelloController.java").read_bytes()
    r = run(tmp_path, "springboot3", "--dir", "src", "--apply")
    assert r.returncode == 1  # 有 high 仍返回 1
    backup = tmp_path / ".upgrade-backup"
    assert (backup / "src" / "HelloController.java").read_bytes() == orig
    assert json.loads((backup / "upgrade_log.json").read_text(encoding="utf-8"))
    assert (tmp_path / "src" / "HelloController.java").read_text(
        encoding="utf-8").startswith("import jakarta.servlet")


def test_apply_twice_backup_conflict_exit_4(tmp_path):
    _src(tmp_path)
    assert run(tmp_path, "springboot3", "--dir", "src", "--apply").returncode == 1
    r = run(tmp_path, "springboot3", "--dir", "src", "--apply")
    assert r.returncode == 4
    assert "冲突" in r.stderr


def test_restore_roundtrip(tmp_path):
    _src(tmp_path)
    orig = (tmp_path / "src" / "HelloController.java").read_bytes()
    run(tmp_path, "springboot3", "--dir", "src", "--apply")
    r = run(tmp_path, "springboot3", "--restore")
    assert r.returncode == 0
    assert (tmp_path / "src" / "HelloController.java").read_bytes() == orig


def test_restore_without_backup_exit_2(tmp_path):
    r = run(tmp_path, "springboot3", "--restore")
    assert r.returncode == 2


def test_restore_apply_conflict_exit_2(tmp_path):
    r = run(tmp_path, "springboot3", "--restore", "--apply")
    assert r.returncode == 2


def test_list_rules_json(tmp_path):
    r = run(tmp_path, "springboot3", "--list-rules", "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert isinstance(data, list) and any(d["id"] == "s2s3.javax.servlet" for d in data)


def test_apply_json_mode_and_written(tmp_path):
    _src(tmp_path)
    r = run(tmp_path, "springboot3", "--dir", "src", "--apply", "--json", "--backup-dir", "bk")
    data = json.loads(r.stdout)
    assert data["mode"] == "apply" and data["written"] == 1


def test_apply_all_failed_exit_2(tmp_path, monkeypatch):
    from upgrademate import main as m
    _src(tmp_path)
    monkeypatch.chdir(tmp_path)

    def boom(src, dst):
        if "bk" not in str(dst):  # 只让 apply 写入失败，备份写入正常
            raise OSError("simulated replace failure")

    monkeypatch.setattr("os.replace", boom)
    rc = m.main(["springboot3", "--dir", "src", "--apply", "--backup-dir", "bk"])
    assert rc == 2
