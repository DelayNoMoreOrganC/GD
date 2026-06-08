#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
归档流水线 V2
输入：一份案件档案 PDF
输出：填好的 5 份 docx（默认，见 output.docx_only）
"""

import os
import re
import json
import zipfile
import shutil
from datetime import datetime

from field_mapping import get_template_paths, expand_fields_for_template
from template_filler import TemplateFiller
from settings import (
    load_config,
    get_deepseek_config,
    get_ocr_engine,
    get_extraction_mode,
    output_docx_only,
    parse_llm_output,
)
from archive_ocr import extract_pdf_text, get_pdf_page_count
from case_outcome import ensure_outcome_covers_execution, unify_case_outcome_fields
from pdf_text_chunk import build_pdf_chunk_for_llm
from document_segmenter import (
    DOC_TYPE_COMPLAINT,
    DOC_TYPE_CONTRACT,
    DOC_TYPE_DEFAULT,
    DOC_TYPE_EXECUTION,
    DOC_TYPE_JUDGMENT,
    DOC_TYPE_OTHER,
    DocumentSource,
    build_segmented_text,
    validate_sources_for_archive,
)
from field_merger import merge_partial_fields
from field_sanitize import (
    sanitize_all_field_values,
    sanitize_court_case_no,
    parse_court_document_list,
)

try:
    from app_paths import get_outputs_dir, get_prompt_path
except ImportError:

    def get_outputs_dir():
        d = os.path.join(os.path.dirname(__file__), "outputs")
        os.makedirs(d, exist_ok=True)
        return d

    def get_prompt_path():
        return os.path.join(os.path.dirname(__file__), "prompts", "extract_prompt.txt")


def _prompts_dir():
    try:
        from app_paths import get_app_dir

        return os.path.join(get_app_dir(), "prompts")
    except ImportError:
        return os.path.join(os.path.dirname(__file__), "prompts")


def load_prompt_file(filename: str) -> str:
    path = os.path.join(_prompts_dir(), filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        if "文档内容" not in text:
            text = text.rstrip() + "\n\n文档内容：\n"
        return text
    raise FileNotFoundError(f"提示词文件不存在: {path}")


def load_extract_prompt(prompt_path=None):
    path = prompt_path or get_prompt_path()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        if "文档内容" not in text:
            text = text.rstrip() + "\n\n文档内容：\n"
        return text
    raise FileNotFoundError(f"提示词文件不存在: {path}")


def _deepseek_chat(user_content: str, system_content: str) -> dict:
    import requests

    ds = get_deepseek_config()
    if not ds.get("api_key"):
        raise RuntimeError("请在 config.json 中配置 deepseek.api_key")
    headers = {
        "Authorization": f"Bearer {ds['api_key']}",
        "Content-Type": "application/json",
    }
    data = {
        "model": ds["model"],
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0,
    }
    response = requests.post(
        ds["base_url"] + "/chat/completions",
        headers=headers,
        json=data,
        timeout=180,
    )
    result = response.json()
    if "choices" not in result:
        raise RuntimeError(f"DeepSeek API 错误: {result}")
    return parse_llm_output(result["choices"][0]["message"]["content"])


def extract_fields_with_deepseek(pdf_text, prompt_path=None):
    system_content = (
        "你是专业的法律文档分析助手。"
        "结案小结与审（办）结果必须同时写入：①民事判决书主文（谁偿还本金利息、律师费等）；"
        "②执行裁定书/终结本次执行程序要点（执行措施、无财产可供执行、终本等）。"
        "不得仅写判决而忽略执行裁定书。不超过150字。"
    )
    prompt_template = load_extract_prompt(prompt_path)
    cfg = load_config()
    chunk = build_pdf_chunk_for_llm(pdf_text, ocr_engine=get_ocr_engine(cfg))
    return _deepseek_chat(prompt_template + chunk, system_content)


def extract_fields_segmented(segmented, log=print) -> dict:
    """分路提取：判决书 / 执行裁定书 / 委托代理合同"""
    system_content = (
        "你是专业的法律文档分析助手。严格按提示词格式输出字段，不要额外说明。"
        "判决书与执行裁定书分路提取时：判决字段只写裁判主文，执行字段只写执行与终本；"
        "二者将合并为一段连贯的案件办理情况表述。"
    )
    partials = {}

    routes = (
        (DOC_TYPE_JUDGMENT, "extract_judgment.txt", "民事判决书"),
        (DOC_TYPE_EXECUTION, "extract_execution.txt", "执行裁定书"),
        (DOC_TYPE_CONTRACT, "extract_contract.txt", "委托代理合同"),
    )
    for doc_type, prompt_file, label in routes:
        text = segmented.get(doc_type)
        if not text or len(text.strip()) < 30:
            continue
        log(f"       分路提取：{label}（{len(text)} 字）")
        try:
            prompt = load_prompt_file(prompt_file)
            chunk = text[:12000] if len(text) > 12000 else text
            partials[doc_type] = _deepseek_chat(prompt + chunk, system_content)
        except Exception as e:
            log(f"  [WARN] {label} 提取失败: {e}")

    complaint = (
        segmented.get(DOC_TYPE_COMPLAINT)
        or segmented.get(DOC_TYPE_OTHER)
        or segmented.get(DOC_TYPE_DEFAULT)
    )
    if complaint and len(complaint.strip()) >= 30:
        log(f"       分路提取：起诉状/其他（{len(complaint)} 字）")
        try:
            prompt = load_extract_prompt()
            chunk = complaint[:8000]
            partials[DOC_TYPE_COMPLAINT] = _deepseek_chat(prompt + chunk, system_content)
        except Exception as e:
            log(f"  [WARN] 起诉状提取失败: {e}")

    if not partials:
        return {}

    merged = merge_partial_fields(partials)
    log(f"       分路合并 {len(merged)} 个字段")
    return merged


def extract_fields_auto(pdf_text, segmented=None, log=print):
    """根据 config 选择 segmented 或 legacy 提取"""
    mode = get_extraction_mode()
    if mode == "segmented":
        if segmented is None:
            segmented_obj = build_segmented_text(pdf_text=pdf_text)
            segmented = segmented_obj.segments
        if segmented and any(segmented.values()):
            fields = extract_fields_segmented(segmented, log=log)
            if fields:
                return fields
            log("  [WARN] 分路提取无结果，回退 legacy")
    return extract_fields_with_deepseek(pdf_text)


def normalize_fields(raw, pdf_text=""):
    if not raw:
        return {}
    m = dict(raw)
    aliases = {
        "委托人名称": "委托人",
        "委托方": "当事人",
        "立案日期": "收案日期",
        "代理律师": "承办律师",
    }
    for src, dst in aliases.items():
        if src in m and m[src] and (dst not in m or not m.get(dst)):
            m[dst] = m[src]
    if m.get("委托人联系地址及电话") and not m.get("委托人电话"):
        m["委托人电话"] = m["委托人联系地址及电话"]
    from field_mapping import _build_case_project_name

    full_case_name = _build_case_project_name(m)
    if full_case_name:
        m["案件或项目名称"] = full_case_name
    if m.get("案由") and not m.get("案件或项目名称"):
        m["案件或项目名称"] = _build_case_project_name(m)
    elif m.get("案件或项目名称") and not m.get("案由"):
        ay = m["案件或项目名称"]
        if "诉" in ay and "一案" in ay:
            m["案由"] = re.sub(r"^.*?诉.*?的?", "", ay).replace("一案", "").strip() or m.get("案由", "")
    case_no = sanitize_court_case_no(
        m.get("法院收案号") or m.get("案号") or "",
        pdf_text,
    )
    if case_no:
        m["法院收案号"] = case_no
        m["案号"] = case_no
    docs_raw = m.get("法院文件清单") or m.get("法院文书") or ""
    doc_list = parse_court_document_list(str(docs_raw))
    if doc_list:
        m["法院文件清单"] = "、".join(doc_list)
    m = ensure_outcome_covers_execution(m, pdf_text)
    m = unify_case_outcome_fields(m)
    return sanitize_all_field_values(m)


def fill_all_templates(field_data, output_dir, log=print, output_options=None):
    os.makedirs(output_dir, exist_ok=True)
    generated = []
    layout_issues = []
    from output_options import templates_to_fill

    names = templates_to_fill(output_options)
    paths = get_template_paths()
    for name in names:
        template_path = paths.get(name)
        if not template_path or not os.path.exists(template_path):
            log(f"  [SKIP] 模板不存在: {name} → {template_path}")
            continue
        out_path = os.path.join(output_dir, f"{name}.docx")
        mapped = expand_fields_for_template(name, field_data)
        log(f"  [FILL] {name} ({len(mapped)} 字段)")
        filler = TemplateFiller(template_path)
        result = filler.fill_template(mapped, out_path, template_name=name)
        if isinstance(result, tuple):
            _, issues = result
            layout_issues.extend(issues or [])
        generated.append({"template": name, "path": out_path, "filename": f"{name}.docx"})
    return generated, layout_issues


def verify_outputs(output_dir):
    from docx import Document

    issues = []
    for fname in os.listdir(output_dir):
        if not fname.endswith(".docx"):
            continue
        path = os.path.join(output_dir, fname)
        text = ""
        doc = Document(path)
        for t in doc.tables:
            for row in t.rows:
                for c in row.cells:
                    text += c.text
        left = re.findall(r"【([^】]{1,40})】", text)
        if left:
            issues.append(f"{fname}: 残留 {len(left)} 处占位符")
    return issues


def docx_to_pdf(docx_path, pdf_path):
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(os.path.abspath(docx_path))
        doc.SaveAs2(os.path.abspath(pdf_path), FileFormat=17)
        doc.Close(False)
        return os.path.exists(pdf_path)
    finally:
        if word:
            try:
                word.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()


def merge_archive_pdf(docx_files, output_pdf):
    import fitz

    merger = fitz.open()
    for docx in docx_files:
        tmp_pdf = docx.replace(".docx", "_tmp.pdf")
        if docx_to_pdf(docx, tmp_pdf):
            src = fitz.open(tmp_pdf)
            merger.insert_pdf(src)
            src.close()
            try:
                os.remove(tmp_pdf)
            except OSError:
                pass
    if merger.page_count > 0:
        merger.save(output_pdf)
        merger.close()
        return True
    return False


def create_zip(source_dir, zip_path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(source_dir):
            for f in files:
                if f.endswith((".docx", ".pdf", ".json")):
                    full = os.path.join(root, f)
                    arc = os.path.relpath(full, source_dir)
                    zf.write(full, arc)


def _resolve_max_pages(config, pdf_path, max_pages=None):
    total_pages = get_pdf_page_count(pdf_path)
    cfg_mp = config.get("local_ocr", {}).get("max_pages", 0)
    if max_pages is not None:
        use_pages = max_pages
    elif cfg_mp and cfg_mp > 0:
        use_pages = cfg_mp
    else:
        use_pages = total_pages or cfg_mp
    if total_pages > 0 and use_pages > total_pages:
        use_pages = total_pages
    if use_pages <= 0 and total_pages > 0:
        use_pages = total_pages
    config.setdefault("local_ocr", {})["max_pages"] = use_pages
    return use_pages, total_pages


def _derive_case_key(field_data: dict, fallback: str) -> str:
    for key in ("法院收案号", "案号", "案件或项目名称"):
        val = (field_data.get(key) or "").strip()
        if val:
            safe = re.sub(r'[<>:"/\\|?*]', "_", val)[:40]
            return safe
    return fallback


def _finalize_archive(
    work_dir,
    base_name,
    field_data,
    pdf_text,
    generated,
    layout_issues,
    docx_only,
    output_root,
    total_steps,
    log,
    output_options=None,
):
    from output_options import normalize_output_options

    opts = normalize_output_options(output_options)
    issues = verify_outputs(work_dir)
    for i in issues:
        log(f"  [WARN] {i}")

    try:
        from layout_verify import verify_output_layout

        extra = verify_output_layout(work_dir, field_data, log=log)
        for e in extra:
            if e not in layout_issues:
                layout_issues.append(e)
    except Exception as ex:
        log(f"  [WARN] 版式校验跳过: {ex}")

    zip_path = None
    archive_pdf = None

    if docx_only:
        log(f"[4/{total_steps}] 完成：已生成 {len(generated)} 份 docx")
        for g in generated:
            log(f"       · {g['filename']}")
    else:
        log(f"[4/{total_steps}] 校验输出...")
        log(f"[5/{total_steps}] 打包归档...")
        zip_path = os.path.join(work_dir, f"{base_name}_归档资料.zip")
        create_zip(work_dir, zip_path)
        docx_list = [g["path"] for g in generated]
        archive_pdf = os.path.join(work_dir, f"{base_name}_归档资料.pdf")
        if merge_archive_pdf(docx_list, archive_pdf):
            log(f"       合并 PDF: {archive_pdf}")
        else:
            archive_pdf = None
            log("  [WARN] 合并 PDF 失败（需本机安装 Word），仍可使用 ZIP 内 docx")
        for src in (zip_path, archive_pdf):
            if src and os.path.exists(src):
                dest = os.path.join(output_root, os.path.basename(src))
                shutil.copy2(src, dest)

    return {
        "success": True,
        "output_dir": work_dir,
        "zip_path": zip_path,
        "archive_pdf": archive_pdf,
        "generated_files": generated,
        "output_mode": opts["mode"],
        "field_count": len(field_data),
        "fields": field_data,
        "text_length": len(pdf_text),
        "verify_issues": issues,
        "layout_issues": layout_issues,
        "docx_only": docx_only,
    }


def _ocr_engine_label(engine: str) -> str:
    return {
        "mineru": "MinerU 本地",
        "mineru_api": "MinerU API",
        "baidu": "百度 OCR",
    }.get(engine, engine)


def process_archive_sources(
    sources: list,
    output_dir=None,
    prompt_path=None,
    max_pages=None,
    log=print,
    output_options=None,
):
    """多 PDF 分类归档（单案件）"""
    doc_sources = []
    for s in sources:
        if isinstance(s, DocumentSource):
            doc_sources.append(s)
        elif isinstance(s, dict):
            doc_sources.append(
                DocumentSource(
                    path=s.get("path", ""),
                    doc_type=s.get("doc_type") or DOC_TYPE_DEFAULT,
                )
            )

    err = validate_sources_for_archive(doc_sources)
    if err:
        return {"success": False, "error": err}

    config = load_config()
    docx_only = output_docx_only(config)
    output_root = get_outputs_dir()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    first_stem = os.path.splitext(os.path.basename(doc_sources[0].path))[0]
    work_dir = output_dir or os.path.join(output_root, f"{first_stem}_multi_{stamp}")
    os.makedirs(work_dir, exist_ok=True)

    engine = get_ocr_engine(config)
    eng_label = _ocr_engine_label(engine)
    total_steps = 4 if docx_only else 5

    source_texts = {}
    pdf_text_parts = []
    for i, src in enumerate(doc_sources, 1):
        if not os.path.isfile(src.path):
            return {"success": False, "error": f"PDF 不存在: {src.path}"}
        use_pages, total_pages = _resolve_max_pages(config, src.path, max_pages)
        log(
            f"[1/{total_steps}] OCR ({eng_label}) [{i}/{len(doc_sources)}] "
            f"{os.path.basename(src.path)} ({src.doc_type})"
            + (f" 共{total_pages}页" if total_pages else "")
        )
        text, ocr_err = extract_pdf_text(src.path, config, log=log)
        if not text or len(text.strip()) < 20:
            return {"success": False, "error": f"OCR 失败: {src.path} — {ocr_err or '文本过短'}"}
        source_texts[src.doc_type] = source_texts.get(src.doc_type, "") + "\n\n" + text
        pdf_text_parts.append(text)
        log(f"       已提取 {len(text)} 字符")

    pdf_text = "\n\n".join(pdf_text_parts)
    segmented = build_segmented_text(source_texts=source_texts).segments

    log(f"[2/{total_steps}] DeepSeek 分路提取字段...")
    try:
        raw_fields = extract_fields_auto(pdf_text, segmented=segmented, log=log)
    except Exception as e:
        return {"success": False, "error": f"字段提取失败: {e}"}
    field_data = normalize_fields(raw_fields, pdf_text)
    if not field_data:
        return {"success": False, "error": "未提取到任何字段"}
    log(f"       共 {len(field_data)} 个字段")

    if not docx_only:
        meta_path = os.path.join(work_dir, "extracted_fields.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(field_data, f, ensure_ascii=False, indent=2)

    from output_options import templates_to_fill, mode_label, normalize_output_options

    opts = normalize_output_options(output_options)
    fill_names = templates_to_fill(opts)
    log(f"[3/{total_steps}] 填充模板（{mode_label(opts['mode'])}，{len(fill_names)} 份）...")
    generated, layout_issues = fill_all_templates(
        field_data, work_dir, log=log, output_options=opts
    )
    if not generated:
        return {"success": False, "error": "未能生成任何文书"}

    base_name = _derive_case_key(field_data, first_stem)
    return _finalize_archive(
        work_dir,
        base_name,
        field_data,
        pdf_text,
        generated,
        layout_issues,
        docx_only,
        output_root,
        total_steps,
        log,
        output_options=opts,
    )


def process_archive(
    pdf_path,
    output_dir=None,
    prompt_path=None,
    max_pages=None,
    log=print,
    output_options=None,
):
    """一键归档：PDF → 5 份 docx（output.docx_only=true 时无 zip/pdf/json）"""
    if not os.path.exists(pdf_path):
        return {"success": False, "error": f"PDF 不存在: {pdf_path}"}

    config = load_config()
    docx_only = output_docx_only(config)
    output_root = get_outputs_dir()
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = output_dir or os.path.join(output_root, f"{base_name}_{stamp}")
    os.makedirs(work_dir, exist_ok=True)
    use_pages, total_pages = _resolve_max_pages(config, pdf_path, max_pages)

    engine = get_ocr_engine(config)
    eng_label = _ocr_engine_label(engine)
    total_steps = 4 if docx_only else 5
    log(
        f"[1/{total_steps}] 提取 PDF 文本 ({eng_label}): {pdf_path}"
        + (f"（共 {total_pages} 页，解析 {use_pages} 页）" if total_pages else "")
    )
    pdf_text, ocr_err = extract_pdf_text(pdf_path, config, log=log)
    if not pdf_text or len(pdf_text.strip()) < 100:
        return {"success": False, "error": f"PDF 文本提取失败: {ocr_err or '文本过短'}"}
    log(f"       已提取 {len(pdf_text)} 字符")

    segmented_obj = build_segmented_text(pdf_text=pdf_text)
    log(f"[2/{total_steps}] DeepSeek 提取字段（{get_extraction_mode()}）...")
    try:
        raw_fields = extract_fields_auto(
            pdf_text, segmented=segmented_obj.segments, log=log
        )
    except Exception as e:
        return {"success": False, "error": f"字段提取失败: {e}"}
    field_data = normalize_fields(raw_fields, pdf_text)
    if not field_data:
        return {"success": False, "error": "未提取到任何字段"}
    log(f"       共 {len(field_data)} 个字段")

    if not docx_only:
        meta_path = os.path.join(work_dir, "extracted_fields.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(field_data, f, ensure_ascii=False, indent=2)
        log(f"       字段缓存 → {meta_path}")

    from output_options import templates_to_fill, mode_label, normalize_output_options

    opts = normalize_output_options(output_options)
    fill_names = templates_to_fill(opts)
    log(f"[3/{total_steps}] 填充模板（{mode_label(opts['mode'])}，{len(fill_names)} 份）...")
    generated, layout_issues = fill_all_templates(
        field_data, work_dir, log=log, output_options=opts
    )
    if not generated:
        return {"success": False, "error": "未能生成任何文书（请检查 templates/bundled 下 .doc 模板）"}

    return _finalize_archive(
        work_dir,
        base_name,
        field_data,
        pdf_text,
        generated,
        layout_issues,
        docx_only,
        output_root,
        total_steps,
        log,
        output_options=opts,
    )
