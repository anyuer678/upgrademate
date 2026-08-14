# UpgradeMate —— 旧代码升级器

> 规则驱动的跨语言代码升级工具：内置规则集对旧代码做行级正则匹配替换，生成 unified diff 与风险分级报告。

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-77%20passed-brightgreen)](tests/)
[![Deps](https://img.shields.io/badge/deps-zero%20third--party-blueviolet)](requirements.txt)

面向「中小框架升级」垂直场景（Spring Boot 2→3、Python 2→3、MySQL 5→8）：纯 Python 标准库实现，默认 dry-run 绝不写文件。

## 功能特性

| 能力 | 说明 |
|---|---|
| 规则驱动 | JSON 规则集（`rules/*.json`），行级正则匹配 + 替换，`re.subn` 计数严格判定命中 |
| 风险分级 | high（编译级）/ medium（行为变化）/ low（文档/格式化），退出码按风险分档 |
| 安全默认 | 默认 `--dry-run` 绝不写文件；`--apply` 前自动备份（SHA256 审计）再原子写 |
| 可回滚 | `--restore` 按 SHA256 比对，仅还原差异文件 |
| 多语言规则集 | 内置 `springboot3`（javax→jakarta）/ `python3` / `mysql8`，可自行扩展 |
| 可选 LLM 兜底 | `--llm` 对 high 风险未覆盖行给出人工处理建议（只提示不改文件） |
| 两种界面 | CLI / 零依赖 Web UI |

## 快速开始

```bash
# 纯标准库，零第三方依赖（Python 3.9+）
python main.py springboot3 --dir samples/ --dry-run   # 检查（默认，不写文件）
python main.py springboot3 --dir samples/ --apply     # 应用（先备份再原子写）
python main.py springboot3 --restore                  # 回滚（按 SHA256 只回差异）
python main.py springboot3 --list-rules               # 列出规则
python webui.py --port 8765                           # Web UI
```

## 命令参考

| 参数 | 说明 |
|---|---|
| `<profile>` | 规则集名称：`springboot3` / `python3` / `mysql8` |
| `--files f...` / `--dir d` | 检查目标（二选一，互斥）；`--dir` 递归收集 |
| `--dry-run`（默认） | 只报告与 diff，绝不写文件 |
| `--apply` | 先备份到 `.upgrade-backup/`（复制原文件 + SHA256 记录）再原子写入 |
| `--backup-dir` | 备份目录（默认 `.upgrade-backup`） |
| `--json` | 输出 JSON 报告（供 CI/脚本消费） |
| `--no-llm` / `--llm` | 默认纯规则离线；`--llm` 显式开启 LLM 兜底 |
| `--restore` | 从备份恢复，仅回差异文件 |

退出码：`0` 无 high 风险 · `1` 存在 high 风险 · `2` 参数错误 · `3` 规则集不存在 · `4` backup 冲突。

## 规则写作指南

规则为 JSON 数组（示例见 `rules/springboot3.json`）：

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

- 必填字段：`id` / `profile` / `priority` / `match` / `replace` / `explain` / `example_before` / `example_after`；全库 `id` 必须唯一。
- 正则**必须**避免灾难性回溯（如 `(a+)+`）：加载时静态检查拒绝；超长行（>100KB）按未命中处理。
- `tests/test_rules.py` 会对每条内置规则断言 `example_before` → `example_after` 严格一致。

## 安全行为

- 默认 dry-run，绝不写文件；`--apply` 前先复制原文件到备份目录（权限尽量 0600），记录 `upgrade_log.json`（含前后 SHA256）。
- 写入采用「临时文件 + `os.replace`」原子替换，失败不留半文件。
- 符号链接与路径越界（`..`）一律拒绝；永不删除文件；永不执行生成的代码或构建工具。
- LLM 调用仅发生在 `--llm` 显式开启且配置了密钥时，结果只提示不写盘。

## 项目结构

```
main.py          CLI 入口（参数、退出码、apply/restore 编排）
rules.py         规则加载与静态校验（灾难性回溯拒绝）
diff_engine.py   行级匹配替换 + unified diff + 风险分级
executor.py      唯一写盘者：备份、原子写、restore、审计日志
llm_advisor.py   可选 LLM 兜底（只提示不改文件）
webui.py         零依赖 Web UI（粘贴代码或选择文件分析）
rules/           JSON 规则集（springboot3 / python3 / mysql8）
samples/         演示样例
tests/           pytest 测试（77 例，不触网）
```

## 测试

```bash
python -m pytest tests/ -q
```

## 免责声明

本工具按「行级正则替换」语义工作，不解析语言语法，不保证升级后代码可编译/行为不变。所有 `medium/low` 及未覆盖项需人工确认；`high` 项存在时退出码为 1 并提示人工复核。请在使用前备份代码（工具自身也会备份），并在隔离分支上验证。使用即视为接受由此工具产生的任何变更由使用者自行负责。

## License

[GPL-3.0](LICENSE) — Copyright (C) 2026 anyuer678
