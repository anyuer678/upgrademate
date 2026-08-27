# UpgradeMate 鈥斺€?鏃т唬鐮佸崌绾у櫒

> 瑙勫垯椹卞姩鐨勮法璇█浠ｇ爜鍗囩骇宸ュ叿锛氬唴缃鍒欓泦瀵规棫浠ｇ爜鍋氳绾ф鍒欏尮閰嶆浛鎹紝鐢熸垚 unified diff 涓庨闄╁垎绾ф姤鍛娿€?

[![Stars](https://img.shields.io/github/stars/anyuer678/upgrademate)][![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-77%20passed-brightgreen)](tests/)
[![Deps](https://img.shields.io/badge/deps-zero%20third--party-blueviolet)](requirements.txt)

闈㈠悜銆屼腑灏忔鏋跺崌绾с€嶅瀭鐩村満鏅紙Spring Boot 2鈫?銆丳ython 2鈫?銆丮ySQL 5鈫?锛夛細绾?Python 鏍囧噯搴撳疄鐜帮紝榛樿 dry-run 缁濅笉鍐欐枃浠躲€?

## 鍔熻兘鐗规€?

| 鑳藉姏 | 璇存槑 |
|---|---|
| 瑙勫垯椹卞姩 | JSON 瑙勫垯闆嗭紙`rules/*.json`锛夛紝琛岀骇姝ｅ垯鍖归厤 + 鏇挎崲锛宍re.subn` 璁℃暟涓ユ牸鍒ゅ畾鍛戒腑 |
| 椋庨櫓鍒嗙骇 | high锛堢紪璇戠骇锛? medium锛堣涓哄彉鍖栵級/ low锛堟枃妗?鏍煎紡鍖栵級锛岄€€鍑虹爜鎸夐闄╁垎妗?|
| 瀹夊叏榛樿 | 榛樿 `--dry-run` 缁濅笉鍐欐枃浠讹紱`--apply` 鍓嶈嚜鍔ㄥ浠斤紙SHA256 瀹¤锛夊啀鍘熷瓙鍐?|
| 鍙洖婊?| `--restore` 鎸?SHA256 姣斿锛屼粎杩樺師宸紓鏂囦欢 |
| 澶氳瑷€瑙勫垯闆?| 鍐呯疆 `springboot3`锛坖avax鈫抝akarta锛? `python3` / `mysql8`锛屽彲鑷鎵╁睍 |
| 鍙€?LLM 鍏滃簳 | `--llm` 瀵?high 椋庨櫓鏈鐩栬缁欏嚭浜哄伐澶勭悊寤鸿锛堝彧鎻愮ず涓嶆敼鏂囦欢锛?|
| 涓ょ鐣岄潰 | CLI / 闆朵緷璧?Web UI |

## 蹇€熷紑濮?

```bash
# 绾爣鍑嗗簱锛岄浂绗笁鏂逛緷璧栵紙Python 3.9+锛?
python main.py springboot3 --dir samples/ --dry-run   # 妫€鏌ワ紙榛樿锛屼笉鍐欐枃浠讹級
python main.py springboot3 --dir samples/ --apply     # 搴旂敤锛堝厛澶囦唤鍐嶅師瀛愬啓锛?
python main.py springboot3 --restore                  # 鍥炴粴锛堟寜 SHA256 鍙洖宸紓锛?
python main.py springboot3 --list-rules               # 鍒楀嚭瑙勫垯
python webui.py --port 8765                           # Web UI
```

## 鍛戒护鍙傝€?

| 鍙傛暟 | 璇存槑 |
|---|---|
| `<profile>` | 瑙勫垯闆嗗悕绉帮細`springboot3` / `python3` / `mysql8` |
| `--files f...` / `--dir d` | 妫€鏌ョ洰鏍囷紙浜岄€変竴锛屼簰鏂ワ級锛沗--dir` 閫掑綊鏀堕泦 |
| `--dry-run`锛堥粯璁わ級 | 鍙姤鍛婁笌 diff锛岀粷涓嶅啓鏂囦欢 |
| `--apply` | 鍏堝浠藉埌 `.upgrade-backup/`锛堝鍒跺師鏂囦欢 + SHA256 璁板綍锛夊啀鍘熷瓙鍐欏叆 |
| `--backup-dir` | 澶囦唤鐩綍锛堥粯璁?`.upgrade-backup`锛?|
| `--json` | 杈撳嚭 JSON 鎶ュ憡锛堜緵 CI/鑴氭湰娑堣垂锛?|
| `--no-llm` / `--llm` | 榛樿绾鍒欑绾匡紱`--llm` 鏄惧紡寮€鍚?LLM 鍏滃簳 |
| `--restore` | 浠庡浠芥仮澶嶏紝浠呭洖宸紓鏂囦欢 |

閫€鍑虹爜锛歚0` 鏃?high 椋庨櫓 路 `1` 瀛樺湪 high 椋庨櫓 路 `2` 鍙傛暟閿欒 路 `3` 瑙勫垯闆嗕笉瀛樺湪 路 `4` backup 鍐茬獊銆?

## 瑙勫垯鍐欎綔鎸囧崡

瑙勫垯涓?JSON 鏁扮粍锛堢ず渚嬭 `rules/springboot3.json`锛夛細

```json
{
  "id": "s2s3.javax.servlet",
  "profile": "springboot3",
  "priority": "high",
  "match": {"file": "*.java", "regex": "import javax\\.servlet\\."},
  "replace": "import jakarta.servlet.",
  "explain": "Spring Boot 3 灏?javax.servlet.* 杩佺Щ鑷?jakarta.servlet.*",
  "example_before": "import javax.servlet.http.HttpServletRequest;",
  "example_after": "import jakarta.servlet.http.HttpServletRequest;"
}
```

- 蹇呭～瀛楁锛歚id` / `profile` / `priority` / `match` / `replace` / `explain` / `example_before` / `example_after`锛涘叏搴?`id` 蹇呴』鍞竴銆?
- 姝ｅ垯**蹇呴』**閬垮厤鐏鹃毦鎬у洖婧紙濡?`(a+)+`锛夛細鍔犺浇鏃堕潤鎬佹鏌ユ嫆缁濓紱瓒呴暱琛岋紙>100KB锛夋寜鏈懡涓鐞嗐€?
- `tests/test_rules.py` 浼氬姣忔潯鍐呯疆瑙勫垯鏂█ `example_before` 鈫?`example_after` 涓ユ牸涓€鑷淬€?

## 瀹夊叏琛屼负

- 榛樿 dry-run锛岀粷涓嶅啓鏂囦欢锛沗--apply` 鍓嶅厛澶嶅埗鍘熸枃浠跺埌澶囦唤鐩綍锛堟潈闄愬敖閲?0600锛夛紝璁板綍 `upgrade_log.json`锛堝惈鍓嶅悗 SHA256锛夈€?
- 鍐欏叆閲囩敤銆屼复鏃舵枃浠?+ `os.replace`銆嶅師瀛愭浛鎹紝澶辫触涓嶇暀鍗婃枃浠躲€?
- 绗﹀彿閾炬帴涓庤矾寰勮秺鐣岋紙`..`锛変竴寰嬫嫆缁濓紱姘镐笉鍒犻櫎鏂囦欢锛涙案涓嶆墽琛岀敓鎴愮殑浠ｇ爜鎴栨瀯寤哄伐鍏枫€?
- LLM 璋冪敤浠呭彂鐢熷湪 `--llm` 鏄惧紡寮€鍚笖閰嶇疆浜嗗瘑閽ユ椂锛岀粨鏋滃彧鎻愮ず涓嶅啓鐩樸€?

## 椤圭洰缁撴瀯

```
main.py          CLI 鍏ュ彛锛堝弬鏁般€侀€€鍑虹爜銆乤pply/restore 缂栨帓锛?
rules.py         瑙勫垯鍔犺浇涓庨潤鎬佹牎楠岋紙鐏鹃毦鎬у洖婧嫆缁濓級
diff_engine.py   琛岀骇鍖归厤鏇挎崲 + unified diff + 椋庨櫓鍒嗙骇
executor.py      鍞竴鍐欑洏鑰咃細澶囦唤銆佸師瀛愬啓銆乺estore銆佸璁℃棩蹇?
llm_advisor.py   鍙€?LLM 鍏滃簳锛堝彧鎻愮ず涓嶆敼鏂囦欢锛?
webui.py         闆朵緷璧?Web UI锛堢矘璐翠唬鐮佹垨閫夋嫨鏂囦欢鍒嗘瀽锛?
rules/           JSON 瑙勫垯闆嗭紙springboot3 / python3 / mysql8锛?
samples/         婕旂ず鏍蜂緥
tests/           pytest 娴嬭瘯锛?7 渚嬶紝涓嶈Е缃戯級
```

## 娴嬭瘯

```bash
python -m pytest tests/ -q
```

## 鍏嶈矗澹版槑

鏈伐鍏锋寜銆岃绾ф鍒欐浛鎹€嶈涔夊伐浣滐紝涓嶈В鏋愯瑷€璇硶锛屼笉淇濊瘉鍗囩骇鍚庝唬鐮佸彲缂栬瘧/琛屼负涓嶅彉銆傛墍鏈?`medium/low` 鍙婃湭瑕嗙洊椤归渶浜哄伐纭锛沗high` 椤瑰瓨鍦ㄦ椂閫€鍑虹爜涓?1 骞舵彁绀轰汉宸ュ鏍搞€傝鍦ㄤ娇鐢ㄥ墠澶囦唤浠ｇ爜锛堝伐鍏疯嚜韬篃浼氬浠斤級锛屽苟鍦ㄩ殧绂诲垎鏀笂楠岃瘉銆備娇鐢ㄥ嵆瑙嗕负鎺ュ彈鐢辨宸ュ叿浜х敓鐨勪换浣曞彉鏇寸敱浣跨敤鑰呰嚜琛岃礋璐ｃ€?

## License

[GPL-3.0](LICENSE) 鈥?Copyright (C) 2026 anyuer678
