"""LLM 兜底：对 high 风险未覆盖行生成人工提示，永不写盘。"""
import json
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMConfig:
    api_base: str
    api_key: str
    model: str


@dataclass
class Advice:
    file: str
    snippet: str
    reason: str
    confidence: str


def _call_llm(cfg: LLMConfig, prompt: str) -> str | None:
    payload = {"model": cfg.model,
               "messages": [{"role": "user", "content": prompt}], "max_tokens": 200}
    req = urllib.request.Request(
        cfg.api_base.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {cfg.api_key}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except Exception:
        return None  # 网络/响应异常一律容错为离线


def advise(files_with_target: list, cfg: LLMConfig | None) -> list:
    """cfg=None 返回 []，纯离线可用；只查 high 风险且规则未覆盖的行。"""
    if cfg is None:
        return []
    out = []
    for c in files_with_target:
        lines = c.original.splitlines()
        hit = {h.lineno for h in c.hits}
        missed = [(i, l) for i, l in enumerate(lines, 1)
                  if i not in hit and l.strip()][:40]
        if not missed:
            continue
        body = "\n".join(f"{i}|{l}" for i, l in missed)
        text = _call_llm(cfg, f"以下 {c.path} 中这些行未被升级规则覆盖，指出最需要人工确认的最多3处。"
                         f"每行输出格式：行号|代码片段|原因|置信度(high/medium/low)。\n{body}")
        if not text:
            continue
        for line in text.splitlines():
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4 and parts[0].isdigit():
                out.append(Advice(c.path, parts[1], parts[2],
                                  parts[3] if parts[3] in ("high", "medium", "low") else "medium"))
    return out
