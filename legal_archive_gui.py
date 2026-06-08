#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""案件档案一键归档 — 百度 OCR / MinerU 可切换"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app_paths import ensure_app_dirs, get_app_dir, get_config_path, init_config_if_missing
from settings import (
    apply_ocr_engine,
    config_is_ready,
    config_status_message,
    get_ocr_engine,
    load_config,
)
from archive_pipeline import process_archive, process_archive_sources
from batch_processor import process_batch
from document_segmenter import (
    DOC_TYPE_DEFAULT,
    DOC_TYPE_LABELS,
    DocumentSource,
)
from output_options import (
    ALL_TEMPLATES,
    OUTPUT_MODE_ALL,
    OUTPUT_MODE_SELECT,
)
from gui_settings_dialog import open_settings_dialog
from gui_theme import (
    C,
    Card,
    ChipRadio,
    HeroHeader,
    RoundedButton,
    ScrollPanel,
    SectionTitle,
    SegmentedControl,
    StatusBar,
    apply_ttk_combobox_style,
    fit_window,
    styled_entry,
    ui_fonts,
)

from app_version import V3_VERSION as APP_VERSION


class ArchiveApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"案件归档 {APP_VERSION}")
        self.configure(bg=C["bg"])

        ensure_app_dirs()
        init_config_if_missing()

        cfg = load_config()
        self.pdf_path = tk.StringVar()  # CLI 兼容
        self.max_pages = tk.IntVar(
            value=cfg.get("local_ocr", {}).get("max_pages", 0) or 0
        )
        self.ocr_engine = tk.StringVar(value=get_ocr_engine(cfg))
        self.mineru_cli_path = tk.StringVar(
            value=(cfg.get("mineru") or {}).get("cli_path", "")
        )
        self._running = False
        self._cancel_batch = False
        self._log_win = None
        self._log_text = None
        self.upload_mode = tk.StringVar(value="case")
        self.multi_files = []  # 个案归档：{path, doc_type}
        self.output_mode = tk.StringVar(value=OUTPUT_MODE_ALL)
        self.template_vars = {name: tk.BooleanVar(value=True) for name in ALL_TEMPLATES}

        self._fonts = ui_fonts(self)
        apply_ttk_combobox_style(self)

        self._main = tk.Frame(self, bg=C["bg"])
        self._main.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        self._build()
        self._on_engine_changed(initial=True)
        self._refresh_status()
        self._fit_window()

    def _fit_window(self):
        fit_window(self, content=self._main)

    def _shell_card(self, parent, pady=(0, 10)):
        card = Card(parent, colors=C, pady=pady, padx=0, autopack=True, fill=tk.X)
        return card.body

    def _build(self):
        root = self._main

        HeroHeader(
            root,
            "案件归档",
            "全选/自选 docx  ·  OCR 可切换",
            APP_VERSION,
            colors=C,
            fonts=self._fonts,
            compact=True,
        ).pack(fill=tk.X)

        # 双栏主体
        body = tk.Frame(root, bg=C["bg"])
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=1, uniform="col")
        body.columnconfigure(1, weight=1, uniform="col")
        body.rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=C["bg"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right = tk.Frame(body, bg=C["bg"])
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # ── 左栏：上传 + OCR ──
        upload = self._shell_card(left)
        SectionTitle(upload, "📤", "上传方式", colors=C, fonts=self._fonts).pack(anchor="w")
        mode_row = tk.Frame(upload, bg=C["card"])
        mode_row.pack(fill=tk.X, pady=(8, 0))
        ChipRadio(
            mode_row,
            (("case", "个案"), ("batch", "批量")),
            self.upload_mode,
            command=self._on_upload_mode_changed,
            colors=C,
            fonts=self._fonts,
        ).pack(fill=tk.X)

        self.upload_detail = tk.Frame(upload, bg=C["card"])
        self.upload_detail.pack(fill=tk.X, pady=(8, 0))
        self._build_case_upload(self.upload_detail)
        self._build_batch_upload(self.upload_detail)
        self._on_upload_mode_changed()

        ocr = self._shell_card(left, pady=(0, 0))
        SectionTitle(ocr, "🔍", "OCR 方案", colors=C, fonts=self._fonts).pack(anchor="w")
        self._ocr_seg = SegmentedControl(
            ocr,
            (
                ("mineru_api", "🌐  MinerU API"),
                ("baidu", "☁️  百度 OCR"),
                ("mineru", "🖥️  MinerU 本地"),
            ),
            self.ocr_engine,
            command=lambda: self._on_engine_changed(),
            colors=C,
            fonts=self._fonts,
            vertical=True,
        )
        self._ocr_seg.pack(fill=tk.X, pady=(8, 0))

        self.mineru_path_frame = tk.Frame(ocr, bg=C["card"])
        tk.Label(
            self.mineru_path_frame,
            text="MinerU 路径（可选）",
            font=self._fonts["cap"],
            fg=C["secondary"],
            bg=C["card"],
        ).pack(anchor="w", pady=(8, 4))
        path_wrap, _, path_inner = styled_entry(
            self.mineru_path_frame, self.mineru_cli_path, colors=C, fonts=self._fonts
        )
        path_wrap.pack(fill=tk.X)
        browse_btn = RoundedButton(
            path_inner,
            text="浏览",
            command=self._browse_mineru,
            style="soft",
            fonts=self._fonts,
        )
        browse_btn.pack(side=tk.RIGHT, padx=(6, 0))
        browse_btn.configure(width=64)

        orow = tk.Frame(ocr, bg=C["card"])
        orow.pack(fill=tk.X, pady=(8, 0))
        tk.Label(orow, text="解析页数", font=self._fonts["cap"], fg=C["secondary"], bg=C["card"]).pack(
            side=tk.LEFT
        )
        spin_fr = tk.Frame(orow, bg=C["input"], highlightbackground=C["border"], highlightthickness=1)
        spin_fr.pack(side=tk.RIGHT)
        tk.Spinbox(
            spin_fr,
            from_=0,
            to=999,
            textvariable=self.max_pages,
            width=4,
            font=self._fonts["body"],
            relief=tk.FLAT,
            bg=C["input"],
            bd=0,
        ).pack(padx=10, pady=4)
        self.ocr_hint = tk.Label(
            ocr,
            text="",
            font=self._fonts["cap"],
            fg=C["tertiary"],
            bg=C["card"],
            wraplength=280,
            justify="left",
        )
        self.ocr_hint.pack(anchor="w", pady=(6, 0))

        # ── 右栏：输出 + 操作 ──
        out_card = self._shell_card(right)
        SectionTitle(out_card, "📄", "输出项目", colors=C, fonts=self._fonts).pack(anchor="w")
        om = tk.Frame(out_card, bg=C["card"])
        om.pack(fill=tk.X, pady=(8, 0))
        for val, label in (
            (OUTPUT_MODE_ALL, "全选（5 份 docx）"),
            (OUTPUT_MODE_SELECT, "自选 docx"),
        ):
            tk.Radiobutton(
                om,
                text=label,
                variable=self.output_mode,
                value=val,
                font=self._fonts["cap"],
                bg=C["card"],
                fg=C["text"],
                activebackground=C["accent_soft"],
                activeforeground=C["accent"],
                selectcolor=C["accent_soft"],
                command=self._on_output_mode_changed,
            ).pack(anchor="w", pady=1)

        self.template_pick_frame = tk.Frame(
            out_card, bg=C["input"], highlightbackground=C["border"], highlightthickness=1
        )
        tpf = tk.Frame(self.template_pick_frame, bg=C["input"])
        tpf.pack(fill=tk.X, padx=10, pady=8)
        self._template_cb_widgets = []
        for i, name in enumerate(ALL_TEMPLATES):
            cb = tk.Checkbutton(
                tpf,
                text=name,
                variable=self.template_vars[name],
                font=self._fonts["cap"],
                bg=C["input"],
                fg=C["text"],
                activebackground=C["input"],
                selectcolor=C["accent_soft"],
            )
            cb.grid(row=i // 2, column=i % 2, sticky="w", padx=4, pady=2)
            self._template_cb_widgets.append(cb)
        self._on_output_mode_changed()

        side = tk.Frame(right, bg=C["bg"])
        side.pack(fill=tk.X, pady=(10, 0))

        self.run_btn = RoundedButton(
            side, "✨  开始归档", self._start, style="primary", fonts=self._fonts
        )
        self.run_btn.pack(fill=tk.X, pady=(0, 8))

        self.status_var = tk.StringVar(value="🟢  就绪")
        StatusBar(side, self.status_var, colors=C, fonts=self._fonts).pack(fill=tk.X, pady=(0, 8))

        for label, cmd, style in (
            ("📂  打开输出文件夹", self._open_outputs, "soft"),
            ("⚙️  详细设置", self._open_settings, "secondary"),
            ("📘  MinerU 说明", self._open_mineru_doc, "secondary"),
        ):
            btn = RoundedButton(side, text=label, command=cmd, style=style, fonts=self._fonts)
            btn.pack(fill=tk.X, pady=(0, 6))

        tk.Label(
            root,
            text=f"📍 {get_app_dir()}",
            font=(self._fonts["cap"][0], 8),
            fg=C["tertiary"],
            bg=C["bg"],
            wraplength=640,
            justify="left",
        ).pack(fill=tk.X, pady=(10, 0))

    def _on_output_mode_changed(self):
        mode = self.output_mode.get()
        if mode == OUTPUT_MODE_SELECT:
            self.template_pick_frame.pack(fill=tk.X, pady=(10, 0))
        else:
            self.template_pick_frame.pack_forget()
        self._fit_window()

    def _get_output_options(self):
        selected = [n for n in ALL_TEMPLATES if self.template_vars[n].get()]
        mode = self.output_mode.get()
        if mode == OUTPUT_MODE_SELECT and not selected:
            return None
        return {"mode": mode, "templates": selected}

    def _build_case_upload(self, parent):
        self.case_frame = tk.Frame(parent, bg=C["card"])
        tk.Label(
            self.case_frame,
            text="同一案件可添加 1 个或多个 PDF；默认按综合文档解析",
            font=self._fonts["cap"],
            fg=C["secondary"],
            bg=C["card"],
            wraplength=420,
            justify="left",
        ).pack(anchor="w")
        hdr = tk.Frame(self.case_frame, bg=C["card"])
        hdr.pack(fill=tk.X, pady=(10, 0))
        tk.Label(hdr, text="PDF 列表", font=self._fonts["cap"], fg=C["secondary"], bg=C["card"]).pack(
            side=tk.LEFT
        )
        add_btn = RoundedButton(
            hdr,
            text="＋  添加 PDF",
            command=self._add_case_pdf,
            style="soft",
            fonts=self._fonts,
        )
        add_btn.pack(side=tk.RIGHT)
        add_btn.configure(width=110)
        self.multi_list_panel = ScrollPanel(self.case_frame, height=96, colors=C)
        self.multi_list_panel.pack(fill=tk.X, pady=(6, 0))
        self.multi_list_frame = self.multi_list_panel.inner

    def _build_batch_upload(self, parent):
        self.batch_frame = tk.Frame(parent, bg=C["card"])
        tk.Label(
            self.batch_frame,
            text="每个案件 1 个 PDF，分别生成至 batch_时间戳 子目录",
            font=self._fonts["cap"],
            fg=C["secondary"],
            bg=C["card"],
        ).pack(anchor="w")
        brow = tk.Frame(self.batch_frame, bg=C["card"])
        brow.pack(fill=tk.X, pady=(10, 0))
        for label, cmd in (("选多个 PDF", self._pick_batch_pdfs), ("选文件夹", self._pick_batch_folder)):
            btn = RoundedButton(brow, text=label, command=cmd, style="soft", fonts=self._fonts)
            btn.pack(side=tk.LEFT, padx=(0, 8))
            btn.configure(width=108)
        self.batch_files_var = tk.StringVar(value="未选择")
        tk.Label(
            self.batch_frame,
            textvariable=self.batch_files_var,
            font=self._fonts["cap"],
            fg=C["tertiary"],
            bg=C["card"],
            wraplength=420,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))
        self.batch_paths = []
        self.batch_list_panel = ScrollPanel(self.batch_frame, height=96, colors=C)
        self.batch_list_panel.pack(fill=tk.X, pady=(6, 0))
        self.batch_queue_frame = self.batch_list_panel.inner

    def _on_upload_mode_changed(self):
        mode = self.upload_mode.get()
        for fr in (self.case_frame, self.batch_frame):
            fr.pack_forget()
        if mode == "case":
            self.case_frame.pack(fill=tk.X)
        else:
            self.batch_frame.pack(fill=tk.X)
        self._fit_window()

    def _refresh_multi_list(self):
        for w in self.multi_list_frame.winfo_children():
            w.destroy()
        for i, item in enumerate(self.multi_files):
            row = tk.Frame(
                self.multi_list_frame,
                bg=C["input"],
                highlightbackground=C["border"],
                highlightthickness=1,
            )
            row.pack(fill=tk.X, pady=2, padx=2)
            inner = tk.Frame(row, bg=C["input"])
            inner.pack(fill=tk.X, padx=10, pady=8)
            name = os.path.basename(item["path"])
            tk.Label(
                inner,
                text=name[:32] + ("…" if len(name) > 32 else ""),
                font=self._fonts["cap"],
                fg=C["text"],
                bg=C["input"],
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)
            var = tk.StringVar(value=DOC_TYPE_LABELS.get(item["doc_type"], item["doc_type"]))
            cb = ttk.Combobox(
                inner,
                textvariable=var,
                values=list(DOC_TYPE_LABELS.values()),
                width=14,
                state="readonly",
                font=self._fonts["cap"],
                style="Archive.TCombobox",
            )
            cb.pack(side=tk.LEFT, padx=(8, 4))
            label_to_key = {v: k for k, v in DOC_TYPE_LABELS.items()}
            cb.bind(
                "<<ComboboxSelected>>",
                lambda e, idx=i, v=var, m=label_to_key: self._set_multi_type(
                    idx, m.get(v.get(), DOC_TYPE_DEFAULT)
                ),
            )
            rm = RoundedButton(
                inner,
                text="移除",
                command=lambda idx=i: self._remove_multi_pdf(idx),
                style="danger_soft",
                fonts=self._fonts,
            )
            rm.pack(side=tk.RIGHT)
            rm.configure(width=56)
        self._fit_window()

    def _set_multi_type(self, idx, doc_type):
        if 0 <= idx < len(self.multi_files):
            self.multi_files[idx]["doc_type"] = doc_type

    def _remove_multi_pdf(self, idx):
        if 0 <= idx < len(self.multi_files):
            self.multi_files.pop(idx)
            self._refresh_multi_list()

    def _add_case_pdf(self):
        paths = filedialog.askopenfilenames(title="选择案件 PDF", filetypes=[("PDF", "*.pdf")])
        for p in paths:
            if not p:
                continue
            self.multi_files.append({"path": p, "doc_type": DOC_TYPE_DEFAULT})
        self._refresh_multi_list()
        if self.multi_files:
            self.status_var.set(f"📄  个案已选 {len(self.multi_files)} 个 PDF")
            if len(self.multi_files) == 1:
                try:
                    from archive_ocr import get_pdf_page_count

                    n = get_pdf_page_count(self.multi_files[0]["path"])
                    if n > 0:
                        self.max_pages.set(n)
                except Exception:
                    pass

    def _pick_batch_pdfs(self):
        paths = filedialog.askopenfilenames(title="批量选择 PDF", filetypes=[("PDF", "*.pdf")])
        if paths:
            for p in paths:
                if p and p not in self.batch_paths:
                    self.batch_paths.append(p)
            self._update_batch_count()
            self._refresh_batch_queue()

    def _pick_batch_folder(self):
        folder = filedialog.askdirectory(title="选择含 PDF 的文件夹")
        if folder:
            pdfs = []
            for root, _, files in os.walk(folder):
                for f in files:
                    if f.lower().endswith(".pdf"):
                        pdfs.append(os.path.join(root, f))
            pdfs.sort()
            self.batch_paths = pdfs
            self._update_batch_count()
            self._refresh_batch_queue()

    def _update_batch_count(self):
        n = len(self.batch_paths)
        self.batch_files_var.set(f"已选 {n} 个 PDF" if n else "未选择")

    def _remove_batch_pdf(self, idx):
        if 0 <= idx < len(self.batch_paths):
            self.batch_paths.pop(idx)
            self._update_batch_count()
            self._refresh_batch_queue()

    def _refresh_batch_queue(self):
        for w in self.batch_queue_frame.winfo_children():
            w.destroy()
        if not self.batch_paths:
            self._fit_window()
            return
        for i, p in enumerate(self.batch_paths):
            row = tk.Frame(
                self.batch_queue_frame,
                bg=C["input"],
                highlightbackground=C["border"],
                highlightthickness=1,
            )
            row.pack(fill=tk.X, pady=2, padx=2)
            inner = tk.Frame(row, bg=C["input"])
            inner.pack(fill=tk.X, padx=10, pady=8)
            name = os.path.basename(p)
            tk.Label(
                inner,
                text=f"{i + 1}. {name[:40]}{'…' if len(name) > 40 else ''}",
                font=self._fonts["cap"],
                fg=C["text"],
                bg=C["input"],
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)
            rm = RoundedButton(
                inner,
                text="移除",
                command=lambda idx=i: self._remove_batch_pdf(idx),
                style="danger_soft",
                fonts=self._fonts,
            )
            rm.pack(side=tk.RIGHT)
            rm.configure(width=56)
        self._fit_window()

    def _select_engine(self, engine: str):
        self.ocr_engine.set(engine)
        self._on_engine_changed()

    def _on_engine_changed(self, initial=False):
        eng = self.ocr_engine.get()
        if eng == "mineru":
            self.mineru_path_frame.pack(fill=tk.X, pady=(0, 0))
            self.ocr_hint.configure(
                text="💡 本机 MinerU + GPU；首次较慢，可填 mineru.exe 全路径"
            )
        else:
            self.mineru_path_frame.pack_forget()
            if eng == "mineru_api":
                self.ocr_hint.configure(
                    text="💡 MinerU 云端精准解析（mineru.net）；Token 见 config 或桌面 token 文件"
                )
            else:
                self.ocr_hint.configure(
                    text="💡 百度云 OCR；0=全部页。注意每日 API 额度"
                )
        if not initial:
            apply_ocr_engine(
                eng,
                mineru_cli_path=self.mineru_cli_path.get(),
                max_pages=self._safe_max_pages(),
            )
            self._refresh_status()
        self._fit_window()

    def _browse_mineru(self):
        p = filedialog.askopenfilename(
            title="选择 mineru.exe",
            filetypes=[("mineru", "mineru.exe"), ("可执行文件", "*.exe")],
        )
        if p:
            self.mineru_cli_path.set(p)
            apply_ocr_engine(
                self.ocr_engine.get(),
                mineru_cli_path=p,
                max_pages=self._safe_max_pages(),
            )
            self._refresh_status()

    def _safe_max_pages(self) -> int:
        try:
            return int(self.max_pages.get())
        except (TypeError, ValueError, tk.TclError):
            return 0

    def _persist_prefs(self):
        apply_ocr_engine(
            self.ocr_engine.get(),
            mineru_cli_path=self.mineru_cli_path.get(),
            max_pages=self._safe_max_pages(),
        )

    def _refresh_status(self):
        msg = config_status_message(self.ocr_engine.get())
        if config_is_ready(self.ocr_engine.get()):
            self.status_var.set(f"🟢  {msg}")
        else:
            self.status_var.set(f"🟠  {msg}")

    def _open_log_window(self):
        if self._log_win and self._log_win.winfo_exists():
            self._log_text.configure(state=tk.NORMAL)
            self._log_text.delete("1.0", tk.END)
            self._log_text.configure(state=tk.DISABLED)
            self._log_win.deiconify()
            self._log_win.lift()
            return
        win = tk.Toplevel(self)
        win.title("运行日志")
        win.configure(bg=C["bg"])
        win.transient(self)
        win.protocol("WM_DELETE_WINDOW", lambda: None)
        tk.Label(
            win,
            text="⏳  正在归档，请稍候…",
            font=self._fonts["body"],
            fg=C["secondary"],
            bg=C["bg"],
            padx=16,
            pady=10,
        ).pack(anchor="w")
        inner = tk.Frame(win, bg=C["card"], highlightbackground=C["border"], highlightthickness=1)
        inner.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))
        scroll = ttk.Scrollbar(inner)
        text = tk.Text(
            inner,
            height=14,
            font=self._fonts["log"],
            bg=C["input"],
            fg=C["text"],
            relief=tk.FLAT,
            wrap=tk.WORD,
            padx=10,
            pady=10,
            state=tk.DISABLED,
            yscrollcommand=scroll.set,
        )
        scroll.config(command=text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._log_win = win
        self._log_text = text
        fit_window(win, min_w=480, min_h=320)

    def _close_log_window(self):
        if self._log_win and self._log_win.winfo_exists():
            self._log_win.destroy()
        self._log_win = None
        self._log_text = None

    def _log(self, msg):
        if self._log_text is None:
            return
        self._log_text.configure(state=tk.NORMAL)
        self._log_text.insert(tk.END, msg + "\n")
        self._log_text.see(tk.END)
        self._log_text.configure(state=tk.DISABLED)
        if self._log_win and self._log_win.winfo_exists():
            self._log_win.update_idletasks()

    def _open_outputs(self):
        out = os.path.join(get_app_dir(), "outputs")
        os.makedirs(out, exist_ok=True)
        os.startfile(out)

    def _open_settings(self):
        def _on_settings_saved(cfg):
            self.ocr_engine.set(get_ocr_engine(cfg))
            self._on_engine_changed(initial=True)
            self._refresh_status()

        open_settings_dialog(
            self,
            C,
            self._fonts,
            on_saved=_on_settings_saved,
        )

    def _open_mineru_doc(self):
        for doc in (
            os.path.join(get_app_dir(), "MINERU_V2_SETUP.md"),
            os.path.join(os.path.dirname(__file__), "MINERU_V2_SETUP.md"),
            os.path.join(get_app_dir(), "OCR_PACKAGING.md"),
        ):
            if os.path.isfile(doc):
                os.startfile(doc)
                return
        messagebox.showinfo("说明", "请查看 MINERU_V2_SETUP.md / OCR_PACKAGING.md")

    def _start(self):
        if self._running:
            return
        mode = self.upload_mode.get()
        try:
            self._persist_prefs()
        except Exception as e:
            messagebox.showerror("配置保存失败", f"无法写入 config.json：{e}\n{get_config_path()}")
            return
        eng = self.ocr_engine.get()
        if not config_is_ready(eng):
            labels = {
                "baidu": "百度 OCR",
                "mineru": "MinerU 本地",
                "mineru_api": "MinerU API",
            }
            hint = labels.get(eng, eng)
            detail = config_status_message(eng)
            messagebox.showerror(
                "设置未完成",
                f"当前方案：{hint}\n{detail}\n\n"
                f"请在「详细设置」中填写并点击「保存」。\n配置文件：{get_config_path()}",
            )
            return

        if mode == "case":
            if not self.multi_files:
                messagebox.showerror("提示", "请添加至少一个 PDF")
                return
            out_opts = self._get_output_options()
            if out_opts is None:
                messagebox.showerror("提示", "请至少勾选一份输出文书")
                return
            if len(self.multi_files) == 1:
                pdf = self.multi_files[0]["path"]
                if not os.path.isfile(pdf):
                    messagebox.showerror("提示", "PDF 文件无效")
                    return
                self._run_worker(
                    lambda: process_archive(
                        pdf,
                        max_pages=self._safe_max_pages(),
                        log=self._log,
                        output_options=out_opts,
                    )
                )
            else:
                types = {f["doc_type"] for f in self.multi_files}
                only_default = types <= {DOC_TYPE_DEFAULT}
                if not only_default and "judgment" not in types and "execution" not in types:
                    messagebox.showerror(
                        "提示",
                        "多文件个案至少需要一份判决书或执行裁定书，"
                        "或将全部文件设为「默认（综合文档）」",
                    )
                    return
                sources = [
                    DocumentSource(path=f["path"], doc_type=f["doc_type"])
                    for f in self.multi_files
                ]
                self._run_worker(
                    lambda: process_archive_sources(
                        sources,
                        max_pages=self._safe_max_pages(),
                        log=self._log,
                        output_options=out_opts,
                    )
                )
        else:
            if not self.batch_paths:
                messagebox.showerror("提示", "请选择批量 PDF 或文件夹")
                return
            out_opts = self._get_output_options()
            if out_opts is None:
                messagebox.showerror("提示", "请至少勾选一份输出文书")
                return
            self._cancel_batch = False
            self._run_worker(self._run_batch)

    def _run_worker(self, fn):
        self._running = True
        self.run_btn.set_state(False)
        labels = {
            "mineru": "MinerU 本地解析",
            "mineru_api": "MinerU API 解析",
            "baidu": "百度 OCR",
        }
        label = labels.get(self.ocr_engine.get(), "OCR")
        self.status_var.set(f"⏳  {label}…")
        self._open_log_window()

        def worker():
            try:
                r = fn()
                self.after(0, lambda: self._on_done(r))
            except Exception as e:
                self.after(0, lambda: self._on_done({"success": False, "error": str(e)}))

        threading.Thread(target=worker, daemon=True).start()

    def _run_batch(self):
        out_opts = self._get_output_options()
        if out_opts is None:
            return {"success": False, "error": "请至少勾选一份输出文书"}
        return process_batch(
            self.batch_paths,
            max_pages=self._safe_max_pages(),
            log=self._log,
            cancel_check=lambda: self._cancel_batch,
            output_options=out_opts,
        )

    def _on_done(self, result):
        self._running = False
        self.run_btn.set_state(True)
        self._refresh_status()
        if result.get("batch_root"):
            ok = result.get("ok_count", 0)
            total = result.get("total", 0)
            if result.get("success"):
                self.status_var.set(f"✅  批量完成 {ok}/{total}")
                self._log(f"\n🎉 批量归档 {ok}/{total}")
                self._close_log_window()
                if messagebox.askyesno("完成", f"批量完成 {ok}/{total}，打开批次文件夹？"):
                    os.startfile(result["batch_root"])
            else:
                self.status_var.set("❌  批量失败")
                self._close_log_window()
                messagebox.showerror("失败", "所有案件均处理失败")
            return
        if result.get("success"):
            self.status_var.set("✅  归档完成")
            n = len(result.get("generated_files") or [])
            layout_n = len(result.get("layout_issues") or [])
            self._log(f"\n🎉 已生成 {n} 份 docx")
            if layout_n:
                self._log(f"⚠ 版式待核对 {layout_n} 项")
            self._close_log_window()
            if messagebox.askyesno("完成", f"已生成 {n} 份 docx，打开输出文件夹？"):
                os.startfile(result["output_dir"])
        else:
            self.status_var.set("❌  失败")
            self._log(f"\n❌ {result.get('error')}")
            self._close_log_window()
            messagebox.showerror("失败", result.get("error", "未知错误"))


def run_cli(pdf_path, max_pages=0):
    ensure_app_dirs()
    init_config_if_missing()
    if not config_is_ready():
        print("[FAIL] 请在 config.json 或 GUI 中配置 OCR 与 DeepSeek")
        sys.exit(1)
    if not os.path.isfile(pdf_path):
        print(f"[FAIL] PDF 不存在: {pdf_path}")
        sys.exit(1)
    result = process_archive(pdf_path, max_pages=max_pages, log=print)
    if result.get("success"):
        print("\n[OK] 归档完成")
        print(f"  输出: {result['output_dir']}")
        return 0
    print(f"\n[FAIL] {result.get('error')}")
    return 1


def main():
    ArchiveApp().mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        pages = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        sys.exit(run_cli(sys.argv[1], pages))
    main()
