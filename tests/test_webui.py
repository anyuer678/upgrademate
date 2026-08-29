"""webui 本地前端测试：只读 dry-run 分析接口。"""
import json
import threading
import urllib.error
import urllib.request

import pytest

from upgrademate.webui import Handler, ThreadingHTTPServer


@pytest.fixture
def url():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def _post(url, payload):
    req = urllib.request.Request(url + "/api/analyze",
                                 data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def test_analyze_finds_javax(url):
    st, data = _post(url, {"profile": "springboot3", "files": [
        {"name": "A.java", "content": "import javax.servlet.http.HttpServletRequest;\n"}]})
    assert st == 200
    assert data["summary"]["files"] == 1 and data["summary"]["risk"]["high"] > 0
    assert data["changes"][0]["hits"][0]["line"] == 1
    assert "jakarta" in data["changes"][0]["diff"]


def test_analyze_no_change_empty(url):
    st, data = _post(url, {"profile": "springboot3", "files": [
        {"name": "A.java", "content": "import jakarta.servlet.http.HttpServletRequest;\n"}]})
    assert st == 200 and data["changes"] == []


def test_unknown_profile_400(url):
    req = urllib.request.Request(url + "/api/analyze",
                                 data=json.dumps({"profile": "nope", "files": []}).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with pytest.raises(urllib.error.HTTPError) as ei:
        urllib.request.urlopen(req)
    assert ei.value.code == 400


def test_index_page_served(url):
    with urllib.request.urlopen(url + "/") as r:
        body = r.read().decode("utf-8")
    assert r.status == 200 and "UpgradeMate" in body


def test_analyze_is_readonly(tmp_path, url, monkeypatch):
    monkeypatch.chdir(tmp_path)
    st, data = _post(url, {"profile": "springboot3", "files": [
        {"name": "A.java", "content": "import javax.servlet.http.HttpServletRequest;\n"}]})
    assert st == 200 and data["changes"]
    assert list(tmp_path.iterdir()) == []  # 分析绝不写盘
