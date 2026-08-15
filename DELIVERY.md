# 交付清单 — 旧代码升级器（UpgradeMate）

## 一、文件清单

```
main.py          CLI 入口：参数、退出码、apply/restore 编排
rules.py         规则加载与静态校验（灾难性回溯拒绝、id 唯一、字段必填）
diff_engine.py   行级匹配替换 + unified diff + 风险分级（high/medium/low）
executor.py      唯一写盘者：备份、原子写、restore、审计日志（符号链接/越界拒绝）
llm_advisor.py   可选 LLM 兜底（只提示不改文件，cfg=None 完全离线）
webui.py         零依赖 Web UI（粘贴代码或选择文件分析，内嵌单页 HTML/JS）
rules/           JSON 规则集（springboot3 / python3 / mysql8）
samples/         演示样例（application.properties / HelloController.java / UserRepository.java）
requirements.txt  无第三方依赖（纯标准库 3.9+）
tests/
  test_rules.py    17 项：规则加载/字段校验/灾难性回溯拒绝/example 一致性
  test_upgrader.py 14 项：diff_engine 匹配替换/风险分级
  test_cli.py      18 项：参数/退出码/apply 备份/restore 回滚/backup 冲突
  test_webui.py     5 项：/api/analyze 路由与响应
  test_llm.py       4 项：LLM 兜底提示不写盘
```

## 二、验证结果（本机 Windows / Python 3.12.3）

- `python -m pytest tests/ -q` → **77 passed**
- CLI dry-run 实测：`python main.py springboot3 --dir samples --dry-run` → 3 文件 7 处替换建议（high=4 javax→jakarta、medium=3 配置迁移），退出码 1（有 high 风险项）
- 全生命周期实测（隔离临时目录）：
  1. dry-run（默认不写文件）→ 退出码 1 ✓
  2. apply（先备份再原子写）→ javax→jakarta 生效 + `upgrade_log.json` 生成 ✓
  3. restore 回滚 → 恢复原始 javax ✓
  4. 复检 dry-run → 回到 high 风险状态 ✓
- Web 端到端：`GET /` → 200；`/api/analyze` 返回文件与风险统计

## 三、接口核对清单（架构设计 §接口，全部通过）

- [x] `load_rules(profile) -> list[Rule]`：id 唯一、必填字段、灾难性回溯静态拒绝
- [x] `process_text(text, rules) -> list[Change]`：行级 `re.subn` 严格命中判定
- [x] `risk_of(change)`：high（编译级）/medium（行为变化）/low（文档/格式化）
- [x] `prepare_backup / apply_changes / restore_c_from_backup`：原子写 + SHA256 审计 + 仅回差异
- [x] 退出码：0 无 high / 1 有 high / 2 参数错误 / 3 规则集不存在 / 4 backup 冲突

## 四、本轮交付（缺陷修复 + 协议统一）

**缺陷修复（关键）**

- `webui.py` HTML 赋值改为 raw 字符串（`HTML = r"""..."""`）：原非 raw 三引号导致 JS 内 `'\n'` 字面量被 Python 转义成真实换行，浏览器报 `Invalid or unexpected token`、分析按钮失效。修复后浏览器实测分析出 diff 正常，77 测试全过。

**打磨**

- 空结果提示清理装饰性 ✓；保留单主题深色开发者设计

**协议**

- LICENSE 统一为 GPL-3.0（Copyright (C) 2026 anyuer678）；pyproject 补声明

## 五、安全行为

- 默认 dry-run 绝不写文件；`--apply` 前先备份（权限尽量 0600）+ `upgrade_log.json`（前后 SHA256）
- 写入「临时文件 + os.replace」原子替换，失败不留半文件
- 符号链接与路径越界（`..`）拒绝；永不删除文件；永不执行生成的代码或构建工具
- LLM 仅 `--llm` 显式开启时调用，结果只提示不写盘

## 六、与文档的偏差

- `match.file`（架构内部映射为 `file_glob`）为路径 glob，缺省匹配全部；`match.regex` 为单行正则（Python `re` 语法）
- Python 3.12 官方 `re` 无 `timeout` 参数，超长行（>100KB）按未命中处理（源头静态防护为主）
- `apply` 后存在 high 风险项时退出码 1（提示人工确认），README 已注明
