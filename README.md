# UpgradeMate 旧代码升级器

规则驱动的跨语言代码升级工具：内置规则集对旧代码做行级正则匹配替换，生成 unified diff 与风险分级报告；`--apply` 前自动备份（SHA256 审计），`--restore` 可回滚；`--llm` 可选调用 LLM 对 high 风险且未覆盖行给出人工处理建议（只提示不改文件）。

> 全文按「开发规范.md」第 8 节交付：用法、规则写作指南、免责。

## 用法

```
python main.py <profile> [--files f... | --dir d] [--dry-run(默认)] [--apply]
                     [--backup-dir .upgrade-backup] [--list-rules] [--json]
                     [--no-llm] [--llm] [--restore [--backup-dir]]
```

| 参数 | 说明 |
| --- | --- |
| `<profile>` | 规则集名称：`springboot3` / `python3` / `mysql8` |
| `--files` / `--dir` | 检查目标（二选一，互斥）；`--dir` 递归收集 |
| `--dry-run`（默认） | 只报告与 diff，绝不写文件 |
| `--apply` | 先备份到 `.upgrade-backup/`（复制原文件 + SHA256 记录）再原子写入 |
| `--backup-dir` | 备份目录（默认 `.upgrade-backup`） |
| `--list-rules` | 仅列出该 profile 的规则，不检查文件 |
| `--json` | 输出 JSON 报告（供 CI/脚本消费） |
| `--no-llm` / `--llm` | 默认纯规则离线；`--llm` 显式开启 LLM 兜底 |
| `--restore` | 从备份恢复，仅回差异文件；不能与 `--apply`/`--list-rules` 同用 |

退出码：`0` 无 high 风险；`1` 存在 high 风险；`2` 参数错误（含 apply 全部写入失败）；`3` 规则集不存在；`4` backup 冲突（备份目录已存在且非空，拒绝覆盖）。

## 示例

```bash
# dry-run 检查（默认）
python main.py springboot3 --dir samples/ --dry-run
# JSON 报告
python main.py springboot3 --dir samples/ --dry-run --json
# 应用升级（先备份再原子写，生成 .upgrade-backup/upgrade_log.json）
python main.py springboot3 --dir samples/ --apply
# 回滚（按 SHA256 只回差异文件）
python main.py springboot3 --restore
# 列出规则
python main.py springboot3 --list-rules
# 指定文件
python main.py python3 --files legacy.py util.py
```

## Web 前端（只读分析）

本地单文件 Web 界面：粘贴/上传代码 → 选择规则集 → 展示风险统计、命中明细与 unified diff。**只做内存 dry-run，绝不写盘、不 apply、不 restore**，数据不出本机。

```bash
python webui.py [--host 127.0.0.1] [--port 8765]
# 浏览器打开 http://127.0.0.1:8765/
```

多文件用 `#! 文件名` 行分隔，或点「选择本地文件」自动填入。

## 安装与测试

无第三方依赖（Python 3.9+ 标准库）。

```bash
python -m pytest tests/ -q     # 全部测试
```

LLM 环境变量（仅 `--llm` 开启时读取，密钥只来自环境变量，永不写盘）：

```
UPM_LLM_API_KEY=<key>        # 或 OPENAI_API_KEY
UPM_LLM_API_BASE=https://api.openai.com/v1   # 可选
UPM_LLM_MODEL=gpt-4o-mini                     # 可选
```

## 规则写作指南

规则为 JSON 数组，文件位于 `rules/<profile>.json`（示例见 `rules/springboot3.json`）：

```json
{
  "id": "s2s3.javax.servlet",
  "profile": "springboot3",
  "priority": "high",
  "match": {"file": "*.java", "regex": "import javax\\.servlet\\."},
  "replace": "import jakarta.servlet.",
  "explain": "Spring Boot 3 将 javax.servlet.* 迁移至 jakarta.servlet.*",
  "example_before": "import javax.servlet.http.HttpServletRequest;",
  "example_after": "import jakarta.servlet.http.HttpServletRequest;"
}
```

- 必填字段：`id` / `profile` / `priority` / `match` / `replace` / `explain` / `example_before` / `example_after`，缺失会加载报错；全库 `id` 必须唯一。
- `priority` ∈ `high | medium | low`。`high`=编译级破坏；`medium`=行为可能变化；`low`=文档/格式化。
- `match.file`（架构内部映射为 `file_glob`）为路径 glob，缺省匹配全部；`match.regex` 为单行正则（Python `re` 语法，JSON 中 `\` 需转义）。
- 替换在**单行**上进行，`re.subn` 返回 `count` 为 0 即视为未命中；请保证 `example_before` 与实际替换结果严格一致（`tests/test_rules.py` 会对每条内置规则做断言）。
- 正则**必须**避免灾难性回溯（如 `(a+)+`、`(a|a)+`、`(a{2,})+`）：加载时静态检查拒绝这类模式，超长行（>100KB）按未命中处理；Python 3.11+ 另保留 `re` 超时兜底（当前 3.12 官方 `re` 无 `timeout` 参数，故以源头静态防护为主）。
- 可选项 `options.count`（替换次数上限）、`options.ignore_case`。

## 安全行为

- **默认 dry-run，绝不写文件**；`--apply` 前先复制原文件到备份目录（权限尽量 0600），记录 `upgrade_log.json`（含前后 SHA256）。
- 写入采用"临时文件 + `os.replace`"原子替换，失败不留半文件。
- `--restore` 按 SHA256 比对，仅还原与备份不一致的文件。
- 永不删除文件；永不执行生成的代码或构建工具。
- LLM 调用仅发生在 `--llm` 显式开启且配置了密钥时，结果只提示不写盘；`cfg=None` 时完全离线。

## 免责声明

本工具按"行级正则替换"语义工作，不解析语言语法，不保证升级后代码可编译/行为不变。所有 `medium/low` 及未覆盖项需人工确认；`high` 项存在时退出码为 1 并提示人工复核。请在使用前备份代码（工具自身也会备份），并在隔离分支上验证。使用即视为接受由此工具产生的任何变更由使用者自行负责。
