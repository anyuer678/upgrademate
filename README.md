# UpgradeMate - 旧代码升级器

> 规则驱动的跨语言代码升级工具：内置规则集对旧代码做行级正则匹配替换，生成 unified diff 与风险分级报告。

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