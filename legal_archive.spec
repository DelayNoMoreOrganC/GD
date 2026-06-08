# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — 案件档案一键归档 EXE

import os
import sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
root = os.path.abspath(SPECPATH)
sys.path.insert(0, root)
from app_version import V3_VERSION

_exe_name = f"案件档案归档{V3_VERSION}"

datas = [
    (os.path.join(root, "config.json.example"), "."),
    (os.path.join(root, "config.json.v2.example"), "."),
    (os.path.join(root, "config.target-pc.example.json"), "."),
    (os.path.join(root, "MINERU_V2_SETUP.md"), "."),
    (os.path.join(root, "OCR_PACKAGING.md"), "."),
    (os.path.join(root, "DEPLOY_V2.md"), "."),
    (os.path.join(root, "prompts"), "prompts"),
    (os.path.join(root, "templates", "bundled"), os.path.join("templates", "bundled")),
    (os.path.join(root, "templates", "manifests"), os.path.join("templates", "manifests")),
]

hiddenimports = [
    "win32com",
    "win32com.client",
    "pythoncom",
    "fitz",
    "docx",
    "aip",
    "requests",
    "delivery_list_filler",
    "field_sanitize",
    "case_outcome",
    "archive_pipeline",
    "template_filler",
    "field_mapping",
    "table_layout_optimizer",
    "template_manifest",
    "manifest_word_fill",
    "word_placeholder_fill",
    "word_atomic_fill",
    "post_fill_cleanup",
    "fill_cell_format",
    "mineru_ocr",
    "archive_ocr",
    "gui_settings_dialog",
    "gui_theme",
    "lian_approval_fill",
    "mineru_api",
    "output_options",
    "batch_processor",
    "document_segmenter",
    "textbox_fill",
    "settings",
    "app_paths",
    "layout_verify",
    "pdf_text_chunk",
    "app_version",
]
hiddenimports += collect_submodules("aip")
try:
    hiddenimports += collect_submodules("chardet")
except Exception:
    hiddenimports.append("chardet")

a = Analysis(
    ["legal_archive_gui.py"],
    pathex=[root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "flask", "werkzeug", "jinja2",
        "torch", "torchvision", "torchaudio", "transformers", "accelerate",
        "scipy", "pandas", "numpy.testing", "pytest", "nltk", "cv2", "av",
        "sqlalchemy", "fastapi", "starlette", "uvicorn", "httpx", "huggingface_hub",
        "onnxruntime", "sklearn", "matplotlib", "IPython", "notebook",
        "tensorflow", "keras", "openai", "anthropic", "gradio", "streamlit",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=_exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
