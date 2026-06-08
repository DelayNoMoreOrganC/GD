#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配置加载（EXE / CLI 共用，不依赖 Flask）"""

import json
import os

from app_paths import get_config_path, init_config_if_missing


def load_config():
    init_config_if_missing()
    path = get_config_path()
    if not os.path.exists(path):
        return _default_config()
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return _merge_defaults(cfg)


def save_config(config):
    with open(get_config_path(), "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def _default_config():
    return {
        "ocr": {"engine": "baidu"},
        "deepseek": {
            "api_key": "",
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-v4-flash",
        },
        "baidu_ocr": {
            "app_id": "",
            "api_key": "",
            "secret_key": "",
            "mode": "basic",
        },
        "mineru": {
            "quality": "ultra",
            "backend": "hybrid-auto-engine",
            "method": "ocr",
            "lang": "ch",
            "force_ocr": True,
            "gpu_device": "0",
            "render_threads": 8,
            "timeout_seconds": 7200,
            "fallback_baidu": False,
            "api_token": "",
            "api_model_version": "vlm",
        },
        "local_ocr": {"max_pages": 0},
        "output": {
            "custom_path": "",
            "docx_only": True,
        },
        "fill": {
            "mode": "textbox",
        },
        "extraction": {
            "mode": "segmented",
        },
    }


def _merge_defaults(cfg):
    d = _default_config()
    for k, v in cfg.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            d[k].update(v)
        else:
            d[k] = v
    return d


def get_ocr_engine(config=None) -> str:
    cfg = config or load_config()
    eng = (cfg.get("ocr") or {}).get("engine", "").strip().lower()
    if eng in ("mineru", "baidu", "mineru_api"):
        return eng
    if cfg.get("mineru", {}).get("enabled"):
        return "mineru"
    return "baidu"


def get_deepseek_config():
    c = load_config().get("deepseek", {})
    return {
        "api_key": c.get("api_key", ""),
        "base_url": c.get("base_url", "https://api.deepseek.com").rstrip("/"),
        "model": c.get("model", "deepseek-v4-flash"),
    }


def get_baidu_config():
    c = load_config().get("baidu_ocr", {})
    return {
        "APP_ID": str(c.get("app_id", "")),
        "API_KEY": c.get("api_key", ""),
        "SECRET_KEY": c.get("secret_key", ""),
        "OCR_MODE": c.get("mode", "basic"),
    }


def parse_llm_output(text):
    field_data = {}
    for line in (text or "").split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            field_data[key.strip()] = value.strip()
    return field_data


def config_is_ready(ocr_engine=None):
    """检查当前 OCR 引擎 + DeepSeek 是否可运行"""
    cfg = load_config()
    engine = ocr_engine or get_ocr_engine(cfg)
    ds = get_deepseek_config()
    if not ds.get("api_key"):
        return False
    if engine == "mineru_api":
        from mineru_api import check_mineru_api_available

        ok, _ = check_mineru_api_available(cfg)
        return ok
    if engine == "mineru":
        from mineru_ocr import check_mineru_available

        ok, _ = check_mineru_available(cfg)
        return ok
    bd = get_baidu_config()
    return bool(bd.get("APP_ID") and bd.get("API_KEY") and bd.get("SECRET_KEY"))


def config_is_ready_v2():
    return config_is_ready(ocr_engine="mineru")


def config_is_ready_v1():
    return config_is_ready(ocr_engine="baidu")


def apply_ocr_engine(
    engine: str,
    mineru_cli_path: str = None,
    max_pages: int = None,
    api_token: str = None,
):
    """GUI 切换 OCR 时写入 config.json（合并写入，不覆盖未改动的 mineru 字段）"""
    cfg = load_config()
    cfg.setdefault("ocr", {})["engine"] = (engine or "baidu").strip().lower()
    mu = cfg.setdefault("mineru", {})
    if mineru_cli_path is not None:
        mu["cli_path"] = mineru_cli_path.strip()
    if api_token is not None:
        from mineru_api import normalize_mineru_api_token

        mu["api_token"] = normalize_mineru_api_token(api_token)
    if max_pages is not None:
        try:
            cfg.setdefault("local_ocr", {})["max_pages"] = int(max_pages)
        except (TypeError, ValueError):
            cfg.setdefault("local_ocr", {})["max_pages"] = 0
    save_config(cfg)
    return cfg


def output_docx_only(config=None) -> bool:
    """V2 默认仅输出 5 份 docx，不生成 zip/pdf/json"""
    cfg = config or load_config()
    return bool((cfg.get("output") or {}).get("docx_only", True))


def get_fill_mode(config=None) -> str:
    """表格填充模式：textbox | atomic"""
    cfg = config or load_config()
    mode = (cfg.get("fill") or {}).get("mode", "textbox").strip().lower()
    return mode if mode in ("textbox", "atomic") else "textbox"


def get_extraction_mode(config=None) -> str:
    """字段提取模式：segmented | legacy"""
    cfg = config or load_config()
    mode = (cfg.get("extraction") or {}).get("mode", "segmented").strip().lower()
    return mode if mode in ("segmented", "legacy") else "segmented"


def config_status_message(ocr_engine=None) -> str:
    """返回当前配置状态简述（供状态栏）"""
    cfg = load_config()
    engine = ocr_engine or get_ocr_engine(cfg)
    ds = get_deepseek_config()
    if not ds.get("api_key"):
        return "待配置 DeepSeek API Key"
    if engine == "mineru_api":
        from mineru_api import check_mineru_api_available

        ok, msg = check_mineru_api_available(cfg)
        if ok:
            return "MinerU API 已连通"
        return f"MinerU API: {msg}"
    if engine == "mineru":
        from mineru_ocr import check_mineru_available

        ok, msg = check_mineru_available(cfg)
        if ok:
            short = msg[:40] + "…" if len(msg) > 40 else msg
            return f"MinerU 就绪 · {short}"
        return f"MinerU: {msg}"
    bd = get_baidu_config()
    if bd.get("APP_ID") and bd.get("API_KEY") and bd.get("SECRET_KEY"):
        return "百度 OCR 已配置"
    return "待配置百度 OCR 密钥"
