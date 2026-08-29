"""UpgradeMate 本地 Web 前端：粘贴代码 → 规则分析 → diff 展示。

只读安全边界：仅做内存 dry-run 分析，绝不写盘、不 apply、不 restore。
用法:  python webui.py [--port 8765]   然后浏览器打开 http://127.0.0.1:8765/
"""
import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .diff_engine import process_text, risk_of, unified_diff
from .rules import RuleSchemaError, load_rules

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UpgradeMate · 旧代码升级分析</title>
<style>
  :root { --bg:#0f172a; --card:#1e293b; --line:#334155; --fg:#e2e8f0;
          --mut:#94a3b8; --hi:#f87171; --me:#fbbf24; --lo:#38bdf8; --ok:#34d399; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--fg);
         font:15px/1.6 "Segoe UI","Microsoft YaHei",system-ui,sans-serif; }
  header { padding:20px 28px; border-bottom:1px solid var(--line);
           display:flex; align-items:center; gap:16px; flex-wrap:wrap; }
  h1 { font-size:20px; margin:0; } h1 span { color:var(--ok); }
  .sub { color:var(--mut); font-size:13px; }
  select, button { padding:8px 14px; border-radius:8px; border:1px solid var(--line);
                   background:var(--card); color:var(--fg); font-size:14px; cursor:pointer; }
  button { background:#0ea5e9; border:none; font-weight:600; }
  button:disabled { opacity:.5; cursor:wait; }
  main { max-width:1080px; margin:0 auto; padding:24px 28px 60px; }
  textarea { width:100%; min-height:220px; resize:vertical; background:#0b1220;
             color:var(--fg); border:1px solid var(--line); border-radius:10px;
             padding:14px; font:13px/1.5 Consolas,monospace; }
  .hint { color:var(--mut); font-size:12.5px; margin:8px 2px; }
  .bar { display:flex; gap:10px; align-items:center; margin-top:14px; flex-wrap:wrap; }
  #file-btn { background:var(--card); border:1px dashed var(--line); }
  .cards { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:22px 0; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px 18px; }
  .card b { font-size:26px; display:block; }
  .card small { color:var(--mut); }
  .file { background:var(--card); border:1px solid var(--line); border-radius:12px;
          margin:14px 0; overflow:hidden; }
  .file h3 { margin:0; padding:12px 16px; font-size:15px; background:#16233b;
             display:flex; justify-content:space-between; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  td { padding:7px 10px; border-top:1px solid var(--line); vertical-align:top; }
  td.ln { color:var(--mut); text-align:right; width:44px; user-select:none; }
  code { font:12.5px/1.5 Consolas,monospace; white-space:pre-wrap; word-break:break-all; }
  .del { color:#fca5a5; text-decoration:line-through; }
  .add { color:#86efac; }
  pre.diff { margin:0; padding:12px 16px; font:12.5px/1.5 Consolas,monospace;
             background:#0b1220; overflow-x:auto; }
  .empty { color:var(--mut); text-align:center; padding:40px 0; }
  .pill { font-size:12px; padding:2px 9px; border-radius:99px; background:#16233b; }
  .pill.high { color:var(--hi); } .pill.medium { color:var(--me); } .pill.low { color:var(--lo); }
  #err { display:none; background:#3b0d10; border:1px solid #7f1d1d; color:#fecaca;
         padding:10px 14px; border-radius:10px; margin-top:14px; }
  @media (max-width:640px){ .cards{grid-template-columns:repeat(2,1fr);} }
</style></head><body>
<header>
  <h1>UpgradeMate <span>·</span> 旧代码升级分析</h1>
  <div class="sub">本地只读分析（dry-run），不会修改任何文件 · <a style="color:var(--mut)" href="javascript:void(0)" onclick="fillDemo()">填入示例</a></div>
</header>
<main>
  <textarea id="code" placeholder="// 每行 #! 文件名 开头粘贴一个文件，例如：&#10;#! HelloController.java&#10;import javax.servlet.http.HttpServletRequest;&#10;import java.util.List;&#10;&#10;#! OldClass.java&#10;for (int i = 0; i < 10; i++) { ... }"></textarea>
  <div class="hint">粘贴代码（多个文件用 <code>#! 文件名</code> 分隔），或从磁盘选择文件自动填入。</div>
  <div class="bar">
    <select id="profile">
      <option value="springboot3">Spring Boot 3 (javax→jakarta)</option>
      <option value="python3">Python 3</option>
      <option value="mysql8">MySQL 8</option>
    </select>
    <button id="go" onclick="analyze()">分析</button>
    <input type="file" id="file" multiple hidden onchange="addFiles(event)">
    <button id="file-btn" onclick="document.getElementById('file').click()">选择本地文件</button>
  </div>
  <div id="err"></div>
  <div id="result"></div>
</main>
<script>
const $ = id => document.getElementById(id);
function fillDemo() {
  $('code').value = '#! HelloController.java\n' +
    'import javax.servlet.http.HttpServletRequest;\n' +
    'import javax.servlet.http.HttpServletResponse;\n' +
    'import java.util.List;\n' +
    'public class HelloController {\n' +
    '  public void doGet(HttpServletRequest req, HttpServletResponse resp) {\n' +
    '    List<String> items = new ArrayList<String>();\n' +
    '  }\n' +
    '}';
  analyze();
}
function addFiles(e) {
  const files = [...e.target.files];
  const reads = files.map(f => f.text().then(t => ({ name: f.name, text: t })));
  Promise.all(reads).then(entries => {
    const cur = $('code').value.trim();
    const block = entries.map(x => '#! ' + x.name + '\n' + x.text).join('\n\n');
    $('code').value = cur ? cur + '\n\n' + block : block;
    e.target.value = '';
  });
}
function parseFiles() {
  const files = []; let name = null, buf = [];
  for (const line of $('code').value.split('\n')) {
    if (line.startsWith('#! ')) {
      if (name) files.push({ name, content: buf.join('\n') });
      name = line.slice(3).trim(); buf = [];
    } else buf.push(line);
  }
  if (name) files.push({ name, content: buf.join('\n') });
  return files;
}
async function analyze() {
  const go = $('go'); go.disabled = true; $('err').style.display = 'none';
  const files = parseFiles();
  if (!files.length) { $('err').textContent = '请先粘贴代码（以 #! 文件名 开头）'; $('err').style.display = 'block'; go.disabled = false; return; }
  try {
    const res = await fetch('/api/analyze', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile: $('profile').value, files })
    });
    const data = await res.json();
    if (data.error) { $('err').textContent = data.error; $('err').style.display = 'block'; }
    else render(data);
  } catch (err) { $('err').textContent = '请求失败: ' + err; $('err').style.display = 'block'; }
  finally { go.disabled = false; }
}
function esc(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function render(d) {
  const r = d.summary.risk, total = r.high + r.medium + r.low;
  let html = '<div class="cards">' +
    card(total, '处变更', 'high') + card(r.high, 'high 风险', 'high') +
    card(r.medium, 'medium 风险', 'medium') + card(r.low, 'low 风险', 'low') + '</div>';
  if (!d.changes.length) {
    $('result').innerHTML = html + '<div class="empty">没有发现需要升级的代码</div>';
    return;
  }
  for (const c of d.changes) {
    html += '<div class="file"><h3><span>' + esc(c.path) + '</span><span>';
    const cr = c.risk;
    for (const k of ['high','medium','low'])
      if (cr[k]) html += ' <span class="pill ' + k + '">' + k + '×' + cr[k] + '</span>';
    html += '</span></h3>';
    html += '<table>';
    for (const h of c.hits) {
      html += '<tr><td class="ln">' + h.line + '</td><td>' +
        '<span class="pill ' + h.priority + '">' + esc(h.rule) + '</span> ' + esc(h.explain) + '<br>' +
        '<code><span class="del">' + esc(h.before.trim()) + '</span></code><br>' +
        '<code><span class="add">' + esc(h.after.trim()) + '</span></code></td></tr>';
    }
    html += '</table><pre class="diff">' + esc(c.diff) + '</pre></div>';
  }
  $('result').innerHTML = html;
}
function card(n, label, cls) {
  return '<div class="card"><b class="pill ' + cls + '">' + n + '</b><small>' + label + '</small></div>';
}
</script></body></html>
"""


def analyze(profile: str, files: list) -> dict:
    """内存 dry-run 分析：对每个文本文件应用规则，返回摘要 + 变更 + diff。"""
    rules = load_rules(profile)
    if not rules:
        raise ValueError(f"规则集 '{profile}' 不存在")
    changes = []
    for f in files:
        if not isinstance(f.get("name"), str) or not isinstance(f.get("content"), str):
            raise ValueError("files 每项必须含字符串 name 与 content")
        c = process_text(f["name"], f["content"], rules)
        if c is not None:
            changes.append(c)
    risk = {"high": 0, "medium": 0, "low": 0}
    for c in changes:
        for k, v in risk_of(c).items():
            risk[k] += v
    return {
        "profile": profile,
        "summary": {"files": len(changes), "risk": risk},
        "changes": [{
            "path": c.path, "risk": risk_of(c),
            "hits": [{"line": h.lineno, "rule": h.rule.id, "priority": h.rule.priority,
                      "explain": h.rule.explain, "before": h.before, "after": h.after}
                     for h in c.hits],
            "diff": unified_diff(c.original.splitlines(True),
                                 c.modified.splitlines(True), c.path),
        } for c in changes],
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/":
            self.send_error(404)
            return
        body = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/api/analyze":
            self.send_error(404)
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
            req = json.loads(self.rfile.read(n) or b"{}")
            code, payload = 200, analyze(req.get("profile", "springboot3"), req.get("files", []))
        except (ValueError, RuleSchemaError) as e:
            code, payload = 400, {"error": str(e)}
        except Exception as e:  # 不泄露堆栈，仅给用户可读信息
            code, payload = 500, {"error": f"分析失败: {type(e).__name__}"}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # 安静模式


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="upm-web", description="UpgradeMate 本地 Web 前端（只读分析，不写盘）")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args(argv)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"UpgradeMate Web UI: http://{args.host}:{args.port}/  (Ctrl+C 退出)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
