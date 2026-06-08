# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — 案件档案归档 V1.3.6

import os
import sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
root = os.path.abspath(SPECPATH)
sys.path.insert(0, root)
from app_version import V1_VERSION

_exe_name = f"案件档案归档{V1_VERSION}"

datas = [
    (os.path.join(root, "config.v1.example.json"), "config.json.example"),
    (os.path.join(root, "prompts"), "prompts"),
    (os.path.join(root, "templates", "bundled"), os.path.join("templates", "bundled")),
    (os.path.join(root, "templates", "manifests"), os.path.join("templates", "manifests")),
    (os.path.join(root, "EXE_README.md"), "."),
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
    "archive_ocr",
    "gui_settings_dialog",
    "mineru_ocr",
    "pdf_text_chunk",
    "app_version",
]
hiddenimports += collect_submodules("aip")
try:
    hiddenimports += collect_submodules("chardet")
except Exception:
    hiddenimports.append("chardet")

a = Analysis(
    ["legal_archive_gui_v1.py"],
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
