# UpgradeMate - 旧代码升级检查器

> **状态**：`local-tool` · **行级正则检查清单**，非 AST 迁移工具、非完整升级方案

> 规则驱动的机械迁移检查器：内置 **20 条规则**（Spring Boot 3 ×7 / Python 3 ×9 / MySQL 8 ×4）对旧代码做行级正则匹配替换，生成 unified diff 与风险分级报告。

> ⚠️ **边界说明**：规则引擎是行级正则（`re.subn`），不做 AST/语义分析——注释与字符串字面量中的命中也会被替换，且覆盖不了框架升级中真正的痛点（配置重构、废弃 API 签名变更）。适合作为升级前后的机械检查清单，不能替代完整的迁移方案。

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-77%20passed-brightgreen)](tests/)
[![Stars](https://img.shields.io/github/stars/anyuer678/upgrademate)](https://github.com/anyuer678/upgrademate/stargazers)

## Features

- **Rule-driven**: JSON rule sets with line-level regex matching
- **Risk classification**: high/medium/low risk levels
- **Safe default**: `--dry-run` never writes files
- **Rollback**: `--restore` with SHA256 verification
- **Multi-language**: Built-in springboot3/python3/mysql8 profiles
- **Zero dependencies**: Pure Python standard library

## Quick Start

```bash
python main.py springboot3 --dir samples/ --dry-run   # Check (default, no writes)
python main.py springboot3 --dir samples/ --apply      # Apply (backup then write)
python main.py springboot3 --restore                   # Rollback
python webui.py --port 8765                            # Web UI
```

## License

[MIT](LICENSE)