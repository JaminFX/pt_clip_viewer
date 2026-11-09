# ====================================================================
# [修改日志 / Modification Log]
# 修改时间: 2026-06-02
# 修复项目:
#   1. 开启 Windows 进程级高 DPI 适配（解决高分屏窗口发虚、边缘毛刺问题）
#   2. 升级安全级组件拦截重绘器 -> 统一重写并净化字族为【Microsoft YaHei UI】
#   3. 完美剥离并清洗 CustomTkinter 底层向原生 Tkinter 传递的显式字族设定
#
# v3.8 新增 / 修复:
#   1. 智能合并：复制轨道或添加到分组时，自动检测相连时间码并提示/自动合并
#   2. 设置选项：可选"每次提示"或"自动合并不再提示"
#   3. 编辑模式展开后滚动到顶部（原为底部）
#   4. "重做"按钮改为"回撤"
#   5. 关于页开发信息修正（移除 Gemini）
#
# v3.9 新增 / 修复:
#   1. 智能合并偏好持久化：用 .ini 配置文件保存，关闭重开均生效
#   2. 新增「⚙ 设置」窗口：含智能合并开关，封装 exe 后同样有效
#   3. 关于页新增拖拽安装说明（tkinterdnd2 安装方法）
#   4. 编辑模式分组有内容时「删除选中行」「清空」按钮高亮显示
#   5. 轨道列表过多时增加鼠标滚轮滚动支持（原本只能拖动细滚动条）
#   6. 修复 logo.ico 图标路径：打包成 exe 后能正确找到并应用图标；
#      同时让所有子窗口（关于/设置/提示框）都应用同一图标
#   7. 修复小窗口（关于/设置/智能合并提示）打开时先闪现默认位置
#      再跳到居中位置的问题：改为先隐藏窗口，定位完成后再显示
#   8. 新增「Reading 空隙」识别（独立提示、独立开关）：添加/复制含 "Reading"
#      的轨道时，若相邻两段之间的空隙，其起止时间码与其他轨道（不限名称）
#      的一个片段、或几个首尾相连的片段合起来完全一致，说明这段被截去
#      放进了那条轨道，提示是否合并。先提示"首尾相连"，再提示"空隙填补"
#   9. 默认打开编辑模式；点击「添加当前轨道」填入内容时自动勾选该分组
#  10. 提亮浅蓝色提示/说明文字（TEXT2/TEXT3），设置图标换为 Lucide 矢量图标
#
# 🛠️ 本工具由 Claude (Anthropic) 倾力开发 | 💡 创意概念来自 JaminFX
# ====================================================================

import os
import sys
import ctypes
from pt_platform import IS_MAC, UI_FONT, CODE_FONT, MODIFIER, UNDO_HINT, config_path, legacy_config_path, wheel_units

# 🛡️ 注入1：Windows 高分屏抗锯齿清晰化开启
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

if sys.platform == "win32":
    # 🛡️ 注入2：解耦级组件字族剥离与动态重绘机制
    try:
        import tkinter as _vfr_tk
    
        def _vfr_smart_patch_font(font_attr, target_family="Microsoft YaHei UI"):
            if not font_attr:
                return (target_family, 10)
            if isinstance(font_attr, (tuple, list)):
                font_list = list(font_attr)
                if len(font_list) > 0:
                    font_list[0] = target_family
                return tuple(font_list)
            if isinstance(font_attr, str):
                parts = font_attr.split()
                if parts:
                    parts[0] = target_family
                    return " ".join(parts)
            return font_attr

        _vfr_intercept_widgets = ['Label', 'Button', 'Entry', 'Text', 'Checkbutton', 'Radiobutton', 'Listbox', 'Spinbox']
        for _vfr_w_name in _vfr_intercept_widgets:
            if hasattr(_vfr_tk, _vfr_w_name):
                _vfr_orig_widget = getattr(_vfr_tk, _vfr_w_name)
                class _VFR_PatchedWidget(_vfr_orig_widget):
                    def __init__(self, master=None, cnf=None, **kw):
                        if cnf is None: cnf = {}
                        for k in list(cnf.keys()): kw[k] = cnf[k]
                        if 'font' in kw:
                            kw['font'] = _vfr_smart_patch_font(kw['font'])
                        super().__init__(master, cnf={}, **kw)
                
                    def configure(self, cnf=None, **kw):
                        if cnf is None: cnf = {}
                        for k in list(cnf.keys()): kw[k] = cnf[k]
                        if 'font' in kw:
                            kw['font'] = _vfr_smart_patch_font(kw['font'])
                        return super().configure(cnf={}, **kw)
                    config = configure
                setattr(_vfr_tk, _vfr_w_name, _VFR_PatchedWidget)

        _vfr_orig_Tk = _vfr_tk.Tk
        class _VFR_PatchedTk(_vfr_orig_Tk):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.option_add("*Font", ("Microsoft YaHei UI", 10))
        _vfr_tk.Tk = _VFR_PatchedTk
    except Exception:
        pass

# ==================== 应用正文 ===================
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT Clip Viewer v3.9
===================
概念：JaminFX
开发：Claude (Anthropic)
"""

import os
import re
import sys
import tkinter as tk
import configparser
from tkinter import filedialog, ttk, messagebox
from pathlib import Path
from edl_parser import parse_edl, MAX_EDL_BYTES
from ui_widgets import ActionButton, apply_dark_inputs, ASSETS, draw_checkbox, VisibleScrollbar

# ── 核心修复：开启 Windows 硬件级高 DPI 感知，彻底解决字体模糊 ─────────────────
if sys.platform == "win32":
    import ctypes
    try:
        # Windows 8.1 及以上支持
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            # 兼容老版本 Windows
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
            
    # 隐藏 Windows 控制台黑框
    ctypes.windll.user32.ShowWindow(
        ctypes.windll.kernel32.GetConsoleWindow(), 0
    )

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

# Lucide vector icons and license are stored in assets/.

# ── 版本 ─────────────────────────────────────────────────────────────────────
APP_NAME    = "PT Clip Viewer"
APP_VERSION = "v3.9.10"

# ── 核心字体修复（完美适配界面像素对齐，防止笔画粗细不均） ───────────────────────
# 经测试，使用 "Microsoft YaHei UI" 替代 "Microsoft YaHei"，能完美解决 Windows 界面渲染时笔画变粗变形的问题
FONT_UI_LG   = (UI_FONT, 12, "bold")
FONT_UI_BOLD = (UI_FONT, 10, "bold")
FONT_UI_REG  = (UI_FONT, 10)
FONT_UI_SM   = (UI_FONT, 9)
FONT_CODE    = (CODE_FONT, 10)  # 时间码和对齐表格首选 Consolas，高 DPI 下边缘表现极稳
FONT_CODE_SM = (CODE_FONT, 9)

# ── 颜色 ─────────────────────────────────────────────────────────────────────
BG      = "#0b1120"
BG2     = "#111827"
BG3     = "#1a2336"
BG4     = "#1e2d47"
BORDER  = "#243044"
ACCENT  = "#38bdf8"
ACCENT2 = "#087ea4"
GREEN   = "#22c55e"
AMBER   = "#f59e0b"
RED     = "#ef4444"
TEXT    = "#e8f4ff"
TEXT2   = "#a8c6e2"
TEXT3   = "#7f9fc0"

TRACK_COLORS = [
    "#38bdf8", "#34d399", "#f59e0b", "#f472b6",
    "#818cf8", "#a3e635", "#fb923c", "#e879f9",
]

class GapFill:
    """
    其他轨道的片段索引。判断时间段 (a, b) 能否被填满：
    · 恰好有一个片段 开始=a 结束=b；或
    · 有几个首尾相连的片段，从 a 开始一路接到 b（例如回答轨道被切成 3 小段）。
    """
    def __init__(self, tracks_clips):
        self._next = {}
        for clips in tracks_clips:
            for c in clips:
                self._next.setdefault(c["start"], set()).add(c["end"])

    def __bool__(self):
        return bool(self._next)

    def __contains__(self, key):
        a, b = key
        seen, stack = set(), [a]
        while stack:
            cur = stack.pop()
            for nxt in self._next.get(cur, ()):
                if nxt == b:
                    return True
                if nxt not in seen and len(seen) < 5000:   # 上限：防止异常数据拖慢
                    seen.add(nxt)
                    stack.append(nxt)
        return False


# ── 解析 ─────────────────────────────────────────────────────────────────────

def smpte_compact(tc: str) -> str:
    return tc


# ── 配置文件（持久化设置）────────────────────────────────────────────────────────

def _get_config_path() -> Path:
    return config_path()


def _get_icon_path() -> Path:
    """
    返回 logo.ico 路径，依次尝试以下位置：
      1. PyInstaller 打包内部资源目录 (sys._MEIPASS，onedir 模式下为 _internal 文件夹)
      2. exe 所在目录（手动放置 / Nuitka 打包场景）
      3. 脚本所在目录（未打包，直接运行 .py 时）
    找到第一个存在的文件就返回；都不存在则返回最后一个候选路径（供上层判断 exists() 失败后跳过）。
    """
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "logo.ico")
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).parent / "logo.ico")
    else:
        candidates.append(Path(__file__).parent / "logo.ico")
    for c in candidates:
        if c.exists():
            return c
    return candidates[-1]


def apply_icon(win):
    """给任意窗口（Tk 或 Toplevel）尝试应用 logo.ico，找不到则静默跳过。"""
    try:
        icon_path = _get_icon_path()
        if icon_path.exists():
            if not IS_MAC:
                win.iconbitmap(str(icon_path))
    except Exception:
        pass


def load_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    p = _get_config_path()
    if not p.exists():
        p = legacy_config_path()
    if p.exists():
        try:
            cfg.read(str(p), encoding="utf-8")
        except Exception:
            pass
    if "settings" not in cfg:
        cfg["settings"] = {}
    return cfg


def save_config(cfg: configparser.ConfigParser):
    try:
        path = _get_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            cfg.write(f)
    except Exception:
        pass


# ── 关于对话框 ────────────────────────────────────────────────────────────────

def show_about(parent):
    win = tk.Toplevel(parent)
    win.withdraw()          # 先隐藏，避免定位前的窗口闪现
    apply_icon(win)
    win.title(f"关于 {APP_NAME}")
    win.configure(bg=BG2)
    win.resizable(False, False)

    win.update_idletasks()
    w, h = 460, 560
    px = parent.winfo_x() + (parent.winfo_width()  - w) // 2
    py = parent.winfo_y() + (parent.winfo_height() - h) // 2
    win.geometry(f"{w}x{h}+{px}+{py}")

    tk.Frame(win, bg=ACCENT, height=4).pack(fill="x")

    # 可滚动容器
    canvas = tk.Canvas(win, bg=BG2, highlightthickness=0)
    sb = VisibleScrollbar(win, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    body = tk.Frame(canvas, bg=BG2)
    canvas_win = canvas.create_window((0, 0), window=body, anchor="nw")

    def _on_body_configure(e):
        canvas.configure(scrollregion=canvas.bbox("all"))
    def _on_canvas_configure(e):
        canvas.itemconfig(canvas_win, width=e.width)
    body.bind("<Configure>", _on_body_configure)
    canvas.bind("<Configure>", _on_canvas_configure)
    canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(wheel_units(e), "units"))
    body.bind("<MouseWheel>", lambda e: canvas.yview_scroll(wheel_units(e), "units"))

    inner = tk.Frame(body, bg=BG2)
    inner.pack(fill="both", expand=True, padx=30, pady=24)

    tk.Label(inner, text="🎬", bg=BG2, font=("", 36)).pack()
    tk.Label(inner, text=APP_NAME, bg=BG2, fg=TEXT, font=FONT_UI_LG).pack(pady=(4, 0))
    tk.Label(inner, text=APP_VERSION, bg=BG2, fg=ACCENT, font=FONT_CODE).pack(pady=(0, 18))

    tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", pady=(0, 18))

    for label, value, color in [
        ("概念 / 出品",  "JaminFX",              AMBER),
        ("开发",        "Claude (Anthropic)",    TEXT2),
        ("用途",        "Pro Tools 片段时间提取", TEXT2),
        ("格式支持",    "SMPTE 时间码 · 中文 EDL", TEXT2),
    ]:
        row = tk.Frame(inner, bg=BG2)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=label, bg=BG2, fg=TEXT3, font=FONT_UI_REG, width=10, anchor="e").pack(side="left")
        tk.Label(row, text=value, bg=BG2, fg=color, font=FONT_UI_BOLD, anchor="w").pack(side="left", padx=(10, 0))

    tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", pady=(18, 14))

    tk.Label(inner, text="专为音频后期工作流设计\n从 Pro Tools 导出文件中快速提取片段时间",
             bg=BG2, fg=TEXT3, font=FONT_UI_SM, justify="center").pack()

    # ── 拖拽功能安装说明 ──────────────────────────────────────────────────────
    tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", pady=(18, 0))

    dnd_hdr = tk.Frame(inner, bg="#112030")
    dnd_hdr.pack(fill="x", pady=(0, 0))
    tk.Label(dnd_hdr, text="📦  拖拽功能安装说明", bg="#112030", fg=AMBER,
             font=FONT_UI_BOLD, anchor="w").pack(anchor="w", padx=12, pady=(10, 4))

    dnd_body = tk.Frame(inner, bg="#0d1a28")
    dnd_body.pack(fill="x")

    dnd_text = (
        "首次打开软件若提示不支持拖拽，按以下步骤安装：\n\n"
        "1.  按 Win + R，输入 cmd，回车打开命令提示符\n\n"
        "2.  粘贴以下命令并回车：\n"
    )
    tk.Label(dnd_body, text=dnd_text, bg="#0d1a28", fg=TEXT2, font=FONT_UI_SM,
             justify="left", anchor="w", wraplength=380).pack(anchor="w", padx=14, pady=(10, 0))

    # 命令框（可复制）
    cmd_frame = tk.Frame(dnd_body, bg="#0a1520", bd=0)
    cmd_frame.pack(fill="x", padx=14, pady=(2, 6))
    cmd_entry = tk.Entry(cmd_frame, bg="#0a1520", fg=ACCENT, font=FONT_CODE,
                         relief="flat", readonlybackground="#0a1520",
                         insertbackground=ACCENT)
    cmd_entry.insert(0, "pip install tkinterdnd2")
    cmd_entry.config(state="readonly")
    cmd_entry.pack(fill="x", padx=8, pady=6)

    dnd_text2 = (
        "3.  等安装完毕后，重新运行脚本即可。\n\n"
        "如提示「pip 不是内部命令」，说明 Python 未加入\n"
        "环境变量，改用以下命令："
    )
    tk.Label(dnd_body, text=dnd_text2, bg="#0d1a28", fg=TEXT2, font=FONT_UI_SM,
             justify="left", anchor="w", wraplength=380).pack(anchor="w", padx=14, pady=(0, 0))

    cmd_frame2 = tk.Frame(dnd_body, bg="#0a1520", bd=0)
    cmd_frame2.pack(fill="x", padx=14, pady=(2, 12))
    cmd_entry2 = tk.Entry(cmd_frame2, bg="#0a1520", fg=ACCENT, font=FONT_CODE,
                          relief="flat", readonlybackground="#0a1520",
                          insertbackground=ACCENT)
    cmd_entry2.insert(0, "python -m pip install tkinterdnd2")
    cmd_entry2.config(state="readonly")
    cmd_entry2.pack(fill="x", padx=8, pady=6)

    ActionButton(inner, text="关闭", command=win.destroy, bg=ACCENT2, fg="white",
              relief="flat", font=FONT_UI_BOLD, padx=24, pady=6,
              cursor="hand2").pack(pady=(18, 4))

    win.deiconify()         # 位置/内容都就绪后再显示，避免闪现
    win.grab_set()


# ── 主应用 ────────────────────────────────────────────────────────────────────

class App(TkinterDnD.Tk if DND_AVAILABLE else tk.Tk):
    def __init__(self, open_dialog=True):
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.minsize(960, 600)
        self.configure(bg=BG)
        apply_dark_inputs(self)

        apply_icon(self)

        self.tracks       = []
        self.view_idx     = None
        self.selected_set = set()
        self._edit_mode   = False

        # 加载持久化配置
        self._cfg = load_config()
        ask_val = self._cfg["settings"].get("smart_merge_ask", "true").lower() != "false"
        self._smart_merge_ask = tk.BooleanVar(value=ask_val)

        # "Reading 空隙" 检测：True=每次弹窗提示，False=自动合并不再提示
        reading_ask_val = self._cfg["settings"].get("reading_merge_ask", "true").lower() != "false"
        self._reading_merge_ask = tk.BooleanVar(value=reading_ask_val)

        self._icon_settings_btn   = tk.PhotoImage(file=str(ASSETS / "settings.png"))
        self._icon_settings_title = tk.PhotoImage(file=str(ASSETS / "settings.png"))

        self._build_ui()
        self._toggle_edit_mode()      # 默认打开编辑模式
        self.bind(f"<{MODIFIER}-o>", lambda e: self.load_file())
        if IS_MAC:
            self.createcommand("tk::mac::Quit", self.destroy)
            menu = tk.Menu(self)
            file_menu = tk.Menu(menu, tearoff=False)
            file_menu.add_command(label="打开…", accelerator="Command+O", command=self.load_file)
            file_menu.add_separator()
            file_menu.add_command(label="关闭窗口", accelerator="Command+W", command=self.destroy)
            menu.add_cascade(label="文件", menu=file_menu)
            self.configure(menu=menu)
            self.bind("<Command-w>", lambda e: self.destroy())
        if open_dialog:
            self.after(100, self.load_file)

    # ── 界面构建 ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        topbar = tk.Frame(self, bg=BG2)
        topbar.pack(fill="x")
        inner = tk.Frame(topbar, bg=BG2)
        inner.pack(fill="x", padx=14, pady=8)

        ActionButton(inner, text="📂  打开文件", command=self.load_file, bg=ACCENT2, fg="white", relief="flat", font=FONT_UI_BOLD, padx=14, pady=5, cursor="hand2").pack(side="left")

        self.file_label = tk.Label(inner, text="未选择文件", bg=BG2, fg=TEXT2, font=FONT_UI_REG)
        self.file_label.pack(side="left", padx=14)

        ActionButton(inner, text="ℹ  关于", command=lambda: show_about(self), bg=BG3, fg=TEXT2, relief="flat", font=FONT_UI_REG, padx=10, pady=5, cursor="hand2").pack(side="right")

        ActionButton(inner, text=" 设置", image=self._icon_settings_btn, compound="left", command=self._show_settings, bg=BG3, fg=TEXT2, relief="flat", font=FONT_UI_REG, padx=10, pady=5, cursor="hand2").pack(side="right", padx=(0, 6))

        self.edit_mode_btn = ActionButton(inner, text="编辑模式", command=self._toggle_edit_mode, bg=BG4, fg=TEXT2, relief="flat", font=FONT_UI_REG, padx=10, pady=5, cursor="hand2")
        self.edit_mode_btn.pack(side="right", padx=(0, 8))

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        hint = "⬇  将 .txt 文件拖拽到此处" if DND_AVAILABLE else "（安装 tkinterdnd2 可启用拖拽）"
        self.drop_zone = tk.Label(self, text=hint, bg="#131f33", fg=TEXT2, font=FONT_UI_REG, pady=8)
        self.drop_zone.pack(fill="x", padx=14, pady=(10, 0))

        if DND_AVAILABLE:
            self.drop_zone.drop_target_register(DND_FILES)
            self.drop_zone.dnd_bind("<<Drop>>", self._on_drop)
            self.drop_zone.dnd_bind("<<DragEnter>>", lambda e: self.drop_zone.config(bg="#0c2a4a", fg=ACCENT))
            self.drop_zone.dnd_bind("<<DragLeave>>", lambda e: self.drop_zone.config(bg=BG3, fg=TEXT2))

        self._body = tk.Frame(self, bg=BG)
        self._body.pack(fill="both", expand=True, padx=14, pady=10)
        body = self._body

        # ── 左侧：轨道列表 ──
        left = tk.Frame(body, bg=BG2, width=220)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        left_hdr = tk.Frame(left, bg=BG3)
        left_hdr.pack(fill="x")
        tk.Label(left_hdr, text="轨道列表", bg=BG3, fg=TEXT2, font=FONT_UI_BOLD).pack(side="left", padx=12, pady=8)
        self.sel_count_lbl = tk.Label(left_hdr, text="", bg=BG3, fg=AMBER, font=FONT_UI_SM)
        self.sel_count_lbl.pack(side="right", padx=8)

        sel_bar = tk.Frame(left, bg=BG2)
        sel_bar.pack(fill="x", padx=8, pady=(6, 2))
        ActionButton(sel_bar, text="全选", command=self._select_all, bg=BG4, fg=TEXT2, relief="flat", font=FONT_UI_SM, padx=8, pady=2, cursor="hand2").pack(side="left", padx=(0, 4))
        ActionButton(sel_bar, text="全不选", command=self._deselect_all, bg=BG4, fg=TEXT2, relief="flat", font=FONT_UI_SM, padx=8, pady=2, cursor="hand2").pack(side="left")

        tk.Frame(left, bg=BORDER, height=1).pack(fill="x", padx=8, pady=4)

        self.track_canvas = tk.Canvas(left, bg=BG2, highlightthickness=0)
        tsb = VisibleScrollbar(left, orient="vertical", command=self.track_canvas.yview)
        self.track_canvas.configure(yscrollcommand=tsb.set)
        self.track_canvas.pack(side="left", fill="both", expand=True)
        tsb.pack(side="right", fill="y")

        self.track_list_frame = tk.Frame(self.track_canvas, bg=BG2)
        self._canvas_win = self.track_canvas.create_window((0, 0), window=self.track_list_frame, anchor="nw")
        self.track_list_frame.bind("<Configure>", lambda e: self.track_canvas.configure(scrollregion=self.track_canvas.bbox("all")))
        self.track_canvas.bind("<Configure>", lambda e: self.track_canvas.itemconfig(self._canvas_win, width=e.width))

        def _track_wheel(event):
            self.track_canvas.yview_scroll(wheel_units(event), "units")
        self._track_wheel_handler = _track_wheel
        self.track_canvas.bind("<MouseWheel>", _track_wheel)
        self.track_list_frame.bind("<MouseWheel>", _track_wheel)

        # ── 右侧：片段表格 ──
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        ctrl = tk.Frame(right, bg=BG)
        ctrl.pack(fill="x", pady=(0, 8))

        self.cur_track_lbl = tk.Label(ctrl, text="请在左侧选择轨道", bg=BG, fg=TEXT2, font=FONT_UI_BOLD)
        self.cur_track_lbl.pack(side="left")

        self.cur_count_lbl = tk.Label(ctrl, text="", bg=BG, fg=TEXT3, font=FONT_UI_REG)
        self.cur_count_lbl.pack(side="left", padx=10)

        btns = tk.Frame(ctrl, bg=BG)
        btns.pack(side="right")

        self.copy_single_btn = ActionButton(btns, text="📋 复制当前轨道", command=self._copy_single, bg="#087ea4", fg="white", relief="flat", font=FONT_UI_BOLD, padx=10, pady=4, cursor="hand2", state="disabled")
        self.copy_single_btn.pack(side="left", padx=(0, 6))

        self.copy_sel_btn = ActionButton(btns, text="📋 合并所选轨道", command=self._copy_selected, bg=ACCENT2, fg="white", relief="flat", font=FONT_UI_BOLD, padx=10, pady=4, cursor="hand2", state="disabled")
        self.copy_sel_btn.pack(side="left", padx=(0, 6))

        self.copy_all_btn = ActionButton(btns, text="📋 合并全部", command=self._copy_all, bg="#0d9488", fg="white", relief="flat", font=FONT_UI_BOLD, padx=10, pady=4, cursor="hand2", state="disabled")
        self.copy_all_btn.pack(side="left")

        tree_wrap = tk.Frame(right, bg=BG)
        tree_wrap.pack(fill="both", expand=True)

        style = ttk.Style()
        style.theme_use("clam")
        for orientation in ("Vertical", "Horizontal"):
            style.configure(f"{orientation}.TScrollbar", background="#7899ba", troughcolor="#101a2a",
                            bordercolor="#4c6c8c", arrowcolor="#e3f3ff", lightcolor="#7899ba",
                            darkcolor="#7899ba", gripcount=0, arrowsize=15, width=15)
            style.map(f"{orientation}.TScrollbar", background=[("disabled", "#31475f"), ("pressed", "#38bdf8"), ("active", "#b4d9f6")],
                      arrowcolor=[("disabled", "#7891aa"), ("active", "white")])
        style.configure("Clip.Treeview", background=BG2, foreground=TEXT, rowheight=30, fieldbackground=BG2, borderwidth=0, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER, font=FONT_UI_REG)
        style.configure("Clip.Treeview.Heading", background=BG3, foreground=TEXT2, font=FONT_UI_BOLD, relief="flat")
        style.map("Clip.Treeview", background=[("selected", ACCENT2)], foreground=[("selected", "white")])

        cols = ("序号", "片段名称", "开始时间 (SMPTE)", "结束时间 (SMPTE)", "时长")
        self.tree = ttk.Treeview(tree_wrap, columns=cols, show="headings", style="Clip.Treeview")
        for col, w, anc in [
            ("序号",             50,  "center"),
            ("片段名称",         220, "w"),
            ("开始时间 (SMPTE)", 155, "center"),
            ("结束时间 (SMPTE)", 155, "center"),
            ("时长",             130, "center"),
        ]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor=anc)

        self.tree.tag_configure("odd",  background=BG2)
        self.tree.tag_configure("even", background="#152030")

        clip_sb = VisibleScrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=clip_sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        clip_sb.pack(side="right", fill="y")

        prev_wrap = tk.Frame(right, bg=BG)
        prev_wrap.pack(fill="x", pady=(8, 0))

        tk.Label(prev_wrap, text="复制预览：", bg=BG, fg=TEXT3, font=FONT_UI_SM).pack(anchor="w")

        self.preview = tk.Text(prev_wrap, height=4, bg=BG2, fg="#38bdf8", font=FONT_CODE, relief="flat", state="disabled")
        self.preview.pack(fill="x")

        self._drawer = tk.Frame(self._body, bg=BG2, width=360)
        self._drawer.pack_propagate(False)
        self._build_edit_drawer()

        self.status_lbl = tk.Label(self, text="请打开或拖入 Pro Tools 导出的文本文件", bg=BG2, fg=TEXT2, font=FONT_UI_SM, anchor="w")
        self.status_lbl.pack(fill="x", side="bottom", padx=14, pady=6)

    # ── 文件加载 ─────────────────────────────────────────────────────────────

    def _on_drop(self, event):
        files = self.tk.splitlist(event.data)      # 正确处理带空格的路径与多文件拖拽
        if not files:
            return
        path = files[0]
        if len(files) > 1:
            self._set_status("ℹ  一次只能导入一个文件，已读取第一个")
        self.drop_zone.config(bg=BG3, fg=TEXT2)
        self._load_path(path)

    def load_file(self):
        path = filedialog.askopenfilename(
            title="选择 Pro Tools 导出文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if path:
            self._load_path(path)

    def _load_path(self, path: str):
        try:
            tracks = parse_edl(path)
        except ValueError as error:
            self._set_status(f"❌ {error}")
            return
        except OSError:
            self._set_status("❌ 无法读取文件，请确认文件仍存在并且有读取权限")
            return
        if not tracks:
            self._set_status("❌ 未解析到任何轨道，请检查文件格式")
            return

        self.tracks       = tracks
        self.view_idx     = None
        self.selected_set = set(range(len(tracks)))

        total = sum(len(t["clips"]) for t in tracks)
        self.file_label.config(text=Path(path).name, fg=TEXT)
        self._set_status(f"✅  {Path(path).name}  ·  {len(tracks)} 条轨道  ·  共 {total} 个片段")
        self.copy_all_btn.config(state="normal")
        self._build_track_list()
        self._select_view(0)
        self._update_sel_label()

    # ── 轨道列表构建 ─────────────────────────────────────────────────────────

    def _build_track_list(self):
        for w in self.track_list_frame.winfo_children():
            w.destroy()
        self.track_row_widgets = []

        for i, track in enumerate(self.tracks):
            color   = TRACK_COLORS[i % len(TRACK_COLORS)]
            n_clips = len(track["clips"])

            outer = tk.Frame(self.track_list_frame, bg=BG2, cursor="hand2")
            outer.pack(fill="x", padx=6, pady=2)

            tk.Frame(outer, bg=color, width=4).pack(side="left", fill="y")

            chk_var = tk.BooleanVar(value=True)
            chk = tk.Canvas(outer, width=18, height=18, bg=BG2, highlightthickness=0, cursor="hand2")
            chk.pack(side="left", padx=(6, 2), pady=8)
            self._draw_checkbox(chk, True, color)
            chk.bind("<Button-1>", lambda e, idx=i, v=chk_var, c=chk, col=color: self._click_checkbox(idx, v, c, col))

            inner = tk.Frame(outer, bg=BG2)
            inner.pack(side="left", fill="both", expand=True, padx=(4, 8), pady=6)

            name_lbl = tk.Label(inner, text=track["track_name"], bg=BG2, fg=TEXT, font=FONT_UI_REG, anchor="w", wraplength=130, justify="left")
            name_lbl.pack(anchor="w")

            cnt_lbl = tk.Label(inner, text=f"{n_clips} 个片段", bg=BG2, fg=color, font=FONT_UI_SM)
            cnt_lbl.pack(anchor="w")

            for widget in (outer, inner, name_lbl, cnt_lbl):
                widget.bind("<Button-1>", lambda e, idx=i: self._select_view(idx))

            self.track_row_widgets.append((outer, chk_var, color, chk, inner, name_lbl, cnt_lbl))

        self._refresh_track_highlight()

        # 让鼠标悬停在任意一行上都能滚动整个轨道列表
        def _bind_wheel_recursive(widget):
            try:
                widget.bind("<MouseWheel>", self._track_wheel_handler)
            except tk.TclError:
                pass
            for child in widget.winfo_children():
                _bind_wheel_recursive(child)
        _bind_wheel_recursive(self.track_list_frame)

    def _draw_checkbox(self, canvas, checked, color):
        draw_checkbox(canvas, checked, color)

    def _click_checkbox(self, idx, var, canvas, color):
        new_val = not var.get()
        var.set(new_val)
        self._draw_checkbox(canvas, new_val, color)
        if new_val:
            self.selected_set.add(idx)
        else:
            self.selected_set.discard(idx)
        self._update_sel_label()
        self._update_copy_sel_btn()

    def _select_all(self):
        self.selected_set = set(range(len(self.tracks)))
        for i, (_, chk_var, color, chk, *_) in enumerate(self.track_row_widgets):
            chk_var.set(True)
            self._draw_checkbox(chk, True, color)
        self._update_sel_label()
        self._update_copy_sel_btn()

    def _deselect_all(self):
        self.selected_set.clear()
        for i, (_, chk_var, color, chk, *_) in enumerate(self.track_row_widgets):
            chk_var.set(False)
            self._draw_checkbox(chk, False, color)
        self._update_sel_label()
        self._update_copy_sel_btn()

    def _update_sel_label(self):
        n = len(self.selected_set)
        self.sel_count_lbl.config(text=f"已选 {n}" if n else "", fg=AMBER if n else TEXT3)

    def _update_copy_sel_btn(self):
        n = len(self.selected_set)
        if n >= 2:
            self.copy_sel_btn.config(state="normal", text=f"📋 合并所选（{n}）")
        elif n == 1:
            self.copy_sel_btn.config(state="normal", text="📋 复制所选（1）")
        else:
            self.copy_sel_btn.config(state="disabled", text="📋 合并所选轨道")

    def _select_view(self, idx: int):
        self.view_idx = idx
        self._refresh_track_highlight()

        track = self.tracks[idx]
        color = TRACK_COLORS[idx % len(TRACK_COLORS)]

        self.cur_track_lbl.config(text=f"轨道：{track['track_name']}", fg=color)
        self.cur_count_lbl.config(text=f"{len(track['clips'])} 个片段")
        self.copy_single_btn.config(state="normal")
        self._update_copy_sel_btn()

        self.tree.delete(*self.tree.get_children())
        for n, clip in enumerate(track["clips"], 1):
            tag = "odd" if n % 2 else "even"
            self.tree.insert("", "end", values=(
                n, clip["name"], clip["start"], clip["end"], clip["duration"]
            ), tags=(tag,))

        self._update_preview(track["clips"])

    def _refresh_track_highlight(self):
        for i, (outer, chk_var, color, chk, inner, name_lbl, cnt_lbl) in enumerate(self.track_row_widgets):
            is_view = (i == self.view_idx)
            bg = "#162336" if is_view else BG2
            for w in (outer, inner, name_lbl, cnt_lbl):
                try:
                    w.config(bg=bg)
                except tk.TclError:
                    pass
            try:
                chk.config(bg=bg)
            except tk.TclError:
                pass

    # ── 预览 ─────────────────────────────────────────────────────────────────

    def _update_preview(self, clips):
        lines = [f"{smpte_compact(c['start'])}-{smpte_compact(c['end'])}" for c in clips]
        self._set_preview("\n".join(lines))

    def _set_preview(self, text: str):
        self.preview.config(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)
        self.preview.config(state="disabled")

    # ── 复制 ─────────────────────────────────────────────────────────────────

    def _clips_to_text(self, clips_list: list) -> str:
        seen  = set()
        items = []
        for c in clips_list:
            key = (c["start"], c["end"])
            if key not in seen:
                seen.add(key)
                items.append(key)
        items.sort()
        return "\n".join(f"{smpte_compact(s)}-{smpte_compact(e)}" for s, e in items)

    # ── 智能合并 ─────────────────────────────────────────────────────────────

    def _tc_to_frames(self, tc: str) -> int:
        """将 HH:MM:SS:FF 转换为帧数（用于比较相邻关系，帧率无关，仅用于精确字符串匹配）"""
        # 返回一个可比较的整数，HH*3600*100 + MM*3600 + SS*100 + FF
        parts = tc.split(":")
        if len(parts) != 4:
            return -1
        try:
            hh, mm, ss, ff = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
            return hh * 10000000 + mm * 100000 + ss * 1000 + ff
        except ValueError:
            return -1

    def _smart_merge_lines(self, lines: list, bridges=frozenset(), adjacent: bool = True) -> list:
        """
        检测并合并相连时间码行。
        bridges: {(空隙起点, 空隙终点), ...}——这些空隙已被其他轨道的片段精确填补，
                 视同相连一并合并（Reading 轨道被截去一段放进别的轨道的情况）。
        输入: ["HH:MM:SS:FF-HH:MM:SS:FF", ...]
        输出: 合并后的行列表
        """
        parsed = []
        for line in lines:
            parts = line.split("-")
            if len(parts) == 2:
                parsed.append((parts[0].strip(), parts[1].strip(), line))
            else:
                parsed.append((None, None, line))

        merged = []
        i = 0
        while i < len(parsed):
            s, e, orig = parsed[i]
            if s is None:
                merged.append(orig)
                i += 1
                continue
            # 尝试合并相邻
            j = i + 1
            cur_s, cur_e = s, e
            while j < len(parsed):
                ns, ne, _ = parsed[j]
                if ns is not None and ((adjacent and ns == cur_e) or (cur_e, ns) in bridges):
                    cur_e = ne
                    j += 1
                else:
                    break
            merged.append(f"{cur_s}-{cur_e}")
            i = j
        return merged

    def _bridge_ranges(self, track_idx):
        """
        仅当该轨道名含 Reading 时，返回其他轨道的片段索引（GapFill），
        用来判断空隙是否被别的轨道精确填满；否则返回空集合（不做空隙检测）。
        """
        if track_idx is None or not (0 <= track_idx < len(self.tracks)):
            return frozenset()
        if "reading" not in self.tracks[track_idx]["track_name"].lower():
            return frozenset()
        others = [t["clips"] for i, t in enumerate(self.tracks) if i != track_idx]
        return GapFill(others)

    def _count_merge_points(self, lines: list, bridges=frozenset()):
        """返回 (首尾直接相连的处数, 空隙被其他轨道填补的处数)"""
        adj = bri = 0
        for i in range(len(lines) - 1):
            a = lines[i].split("-")
            b = lines[i + 1].split("-")
            if len(a) == 2 and len(b) == 2:
                ea, sb = a[1].strip(), b[0].strip()
                if ea == sb:
                    adj += 1
                elif (ea, sb) in bridges:
                    bri += 1
        return adj, bri

    def _maybe_merge_lines(self, lines: list, bridges=frozenset()) -> list:
        """
        两步检测，各自独立提示、独立设置：
        ① 首尾直接相连 → 「智能合并」提示
        ② 空隙被其他轨道填补（仅 Reading 轨道）→ 「Reading 空隙」提示
        """
        adj, _ = self._count_merge_points(lines)
        if adj:
            if not self._smart_merge_ask.get() or self._show_merge_dialog("adjacent", adj) == "merge":
                lines = self._smart_merge_lines(lines)

        _, bri = self._count_merge_points(lines, bridges)
        if bri:
            if not self._reading_merge_ask.get() or self._show_merge_dialog("gap", bri) == "merge":
                lines = self._smart_merge_lines(lines, bridges, adjacent=False)
        return lines

    def _show_merge_dialog(self, kind: str = "adjacent", n: int = 0) -> str:
        """
        弹出合并提示框。kind: "adjacent"=首尾相连；"gap"=Reading 空隙被其他轨道填补
        返回 "merge" 或 "keep"
        """
        if kind == "gap":
            title, head = "检测到 Reading 空隙", "🎙  检测到 Reading 空隙"
            desc = (f"检测到 {n} 处空隙，其时间码与其他轨道的片段\n"
                    f"（或首尾相连的几个片段）完全一致，\n"
                    f"多半是被截取放进了那条轨道。\n\n"
                    f"是否将空隙两侧合并为一段连续时间？")
            ask_var, cfg_key = self._reading_merge_ask, "reading_merge_ask"
            chk_text, ok_text = "以后遇到此情况自动合并，不再提示", "✅  合并空隙"
        else:
            title, head = "检测到相连时间段", "🔗  检测到相连时间段"
            desc = (f"检测到 {n} 处片段首尾相连的时间码。\n\n"
                    f"是否将它们智能合并为一段连续时间？")
            ask_var, cfg_key = self._smart_merge_ask, "smart_merge_ask"
            chk_text, ok_text = "以后遇到相连时自动合并，不再提示", "✅  智能合并"

        win = tk.Toplevel(self)
        win.withdraw()          # 先隐藏，避免定位前的窗口闪现
        apply_icon(win)
        win.title(title)
        win.configure(bg=BG2)
        win.resizable(False, False)

        tk.Frame(win, bg=AMBER, height=4).pack(fill="x")
        body = tk.Frame(win, bg=BG2, padx=24, pady=18)
        body.pack(fill="both", expand=True)

        tk.Label(body, text=head, bg=BG2, fg=AMBER, font=FONT_UI_BOLD).pack(anchor="w")
        tk.Label(body, text=desc, bg=BG2, fg=TEXT2, font=FONT_UI_REG,
                 justify="left").pack(anchor="w", pady=(8, 12))

        setting_row = tk.Frame(body, bg=BG2)
        setting_row.pack(anchor="w", pady=(0, 14))
        tk.Checkbutton(setting_row, text=chk_text, variable=ask_var,
                       onvalue=False, offvalue=True,
                       bg=BG2, fg=TEXT2, selectcolor=BG4,
                       activebackground=BG2, activeforeground=TEXT,
                       font=FONT_UI_SM, cursor="hand2").pack(side="left")

        result = tk.StringVar(value="keep")
        btn_row = tk.Frame(body, bg=BG2)
        btn_row.pack(fill="x")

        def finish(choice):
            result.set(choice)
            self._cfg["settings"][cfg_key] = str(ask_var.get())
            save_config(self._cfg)
            win.destroy()

        ActionButton(btn_row, text=ok_text, command=lambda: finish("merge"),
                  bg=GREEN, fg="white", relief="flat", font=FONT_UI_BOLD,
                  padx=14, pady=6, cursor="hand2").pack(side="left")
        ActionButton(btn_row, text="保持原样", command=lambda: finish("keep"),
                  bg=BG4, fg=TEXT2, relief="flat", font=FONT_UI_REG,
                  padx=14, pady=6, cursor="hand2").pack(side="left", padx=(10, 0))

        # 窗口大小按内容自适应，避免按钮被裁掉
        win.update_idletasks()
        w, h = max(400, win.winfo_reqwidth()), win.winfo_reqheight()
        px = self.winfo_x() + (self.winfo_width()  - w) // 2
        py = self.winfo_y() + (self.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{px}+{py}")
        win.deiconify()         # 位置/内容都就绪后再显示，避免闪现
        win.grab_set()
        win.wait_window()
        return result.get()

    # ── 设置窗口 ─────────────────────────────────────────────────────────────

    def _show_settings(self):
        win = tk.Toplevel(self)
        win.withdraw()          # 先隐藏，避免定位前的窗口闪现
        apply_icon(win)
        win.title("设置")
        win.configure(bg=BG2)
        win.resizable(False, False)

        tk.Frame(win, bg=ACCENT, height=4).pack(fill="x")
        body = tk.Frame(win, bg=BG2, padx=24, pady=20)
        body.pack(fill="both", expand=True)

        tk.Label(body, text=" 设置", image=self._icon_settings_title, compound="left",
                 bg=BG2, fg=TEXT, font=FONT_UI_BOLD).pack(anchor="w")
        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=(10, 14))

        def section(title, var, ask_text):
            """一个设置板块：标题 + 「每次提示 / 自动合并」单选"""
            sec = tk.Frame(body, bg=BG2)
            sec.pack(fill="x")
            tk.Label(sec, text=title, bg=BG2, fg=AMBER, font=FONT_UI_BOLD).pack(anchor="w")
            opt = tk.Frame(sec, bg=BG2)
            opt.pack(anchor="w", pady=(6, 0))
            for text, val, pady in ((ask_text, True, 0), ("自动合并，不再提示", False, (4, 0))):
                tk.Radiobutton(opt, text=text, variable=var, value=val,
                               bg=BG2, fg=TEXT2, selectcolor=BG4,
                               activebackground=BG2, activeforeground=TEXT,
                               font=FONT_UI_REG, cursor="hand2").pack(anchor="w", pady=pady)

        section("智能合并（首尾相连的时间码）", self._smart_merge_ask,
                "检测到相连时间段时弹窗提示")
        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=(14, 12))
        section("Reading 空隙检测（空隙被其他轨道填补）", self._reading_merge_ask,
                "检测到 Reading 空隙被其他轨道填补时弹窗提示")
        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=(16, 12))

        def _save_and_close():
            self._cfg["settings"]["smart_merge_ask"]   = str(self._smart_merge_ask.get())
            self._cfg["settings"]["reading_merge_ask"] = str(self._reading_merge_ask.get())
            save_config(self._cfg)
            win.destroy()

        btns = tk.Frame(body, bg=BG2)
        btns.pack(fill="x")
        ActionButton(btns, text="保存并关闭", command=_save_and_close,
                  bg=ACCENT2, fg="white", relief="flat",
                  font=FONT_UI_BOLD, padx=20, pady=5,
                  cursor="hand2").pack(side="left")
        ActionButton(btns, text="取消", command=win.destroy,
                  bg=BG4, fg=TEXT2, relief="flat",
                  font=FONT_UI_REG, padx=14, pady=5,
                  cursor="hand2").pack(side="left", padx=(10, 0))

        # 窗口大小按内容自适应，避免按钮被裁掉
        win.update_idletasks()
        w, h = max(420, win.winfo_reqwidth()), win.winfo_reqheight()
        px = self.winfo_x() + (self.winfo_width()  - w) // 2
        py = self.winfo_y() + (self.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{px}+{py}")
        win.deiconify()         # 位置/内容都就绪后再显示，避免闪现
        win.grab_set()

    def _copy_single(self):
        if self.view_idx is None:
            return
        clips = self.tracks[self.view_idx]["clips"]
        lines = [f"{smpte_compact(c['start'])}-{smpte_compact(c['end'])}" for c in clips]
        lines = self._maybe_merge_lines(lines, self._bridge_ranges(self.view_idx))
        text  = "\n".join(lines)
        self._set_preview(text)
        self._do_copy(text, self.copy_single_btn, "📋 复制当前轨道", "#087ea4")

    def _copy_selected(self):
        if not self.selected_set:
            return
        all_clips = []
        for idx in sorted(self.selected_set):
            all_clips.extend(self.tracks[idx]["clips"])
        text = self._clips_to_text(all_clips)
        self._set_preview(text)
        n = len(self.selected_set)
        orig = f"📋 合并所选（{n}）" if n >= 2 else "📋 复制所选（1）"
        self._do_copy(text, self.copy_sel_btn, orig, ACCENT2)

    def _copy_all(self):
        all_clips = []
        for t in self.tracks:
            all_clips.extend(t["clips"])
        text = self._clips_to_text(all_clips)
        self._set_preview(text)
        self._do_copy(text, self.copy_all_btn, "📋 合并全部", "#0d9488")

    def _do_copy(self, text: str, btn: ActionButton, orig: str, orig_bg: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        btn.config(text="✅  已复制！", bg="#16a34a")
        self.after(1500, lambda: btn.config(text=orig, bg=orig_bg))

    def _set_status(self, msg: str):
        self.status_lbl.config(text=msg)

    # ── 编辑模式 ─────────────────────────────────────────────────────────────

    _DEFAULT_SLOT_NAMES = [("朗诵", True), ("补录", False), ("回答问题", False)]

    def _build_edit_drawer(self):
        drawer = self._drawer

        hdr = tk.Frame(drawer, bg=BG3)
        hdr.pack(fill="x")
        tk.Label(hdr, text="编辑模式", bg=BG3, fg=AMBER, font=FONT_UI_BOLD).pack(side="left", padx=12, pady=8)
        tk.Label(hdr, text="勾选分组参与复制", bg=BG3, fg=TEXT3, font=FONT_UI_SM).pack(side="left")

        tk.Frame(drawer, bg=BORDER, height=1).pack(fill="x")

        scroll_wrap = tk.Frame(drawer, bg=BG2)
        scroll_wrap.pack(fill="both", expand=True)

        self._slot_canvas = tk.Canvas(scroll_wrap, bg=BG2, highlightthickness=0)
        slot_sb = VisibleScrollbar(scroll_wrap, orient="vertical", command=self._slot_canvas.yview)
        self._slot_canvas.configure(yscrollcommand=slot_sb.set)
        slot_sb.pack(side="right", fill="y")
        self._slot_canvas.pack(side="left", fill="both", expand=True)

        self._slots_frame = tk.Frame(self._slot_canvas, bg=BG2)
        self._slot_win = self._slot_canvas.create_window((0, 0), window=self._slots_frame, anchor="nw")

        self._slots_frame.bind("<Configure>", lambda e: self._slot_canvas.configure(scrollregion=self._slot_canvas.bbox("all")))
        self._slot_canvas.bind("<Configure>", lambda e: self._slot_canvas.itemconfig(self._slot_win, width=e.width))

        def _on_wheel(e):
            self._slot_canvas.yview_scroll(wheel_units(e), "units")
        self._wheel_handler = _on_wheel
        self._slot_canvas.bind("<MouseWheel>", _on_wheel)
        self._slots_frame.bind("<MouseWheel>", _on_wheel)

        self._slots = []
        self._slot_widgets = []

        for name, enabled in self._DEFAULT_SLOT_NAMES:
            self._add_slot(default_name=name, default_enabled=enabled, scroll_to="top")

        bottom = tk.Frame(drawer, bg=BG3)
        bottom.pack(fill="x", side="bottom")
        tk.Frame(bottom, bg=BORDER, height=1).pack(fill="x")

        btn_row = tk.Frame(bottom, bg=BG3)
        btn_row.pack(fill="x", padx=10, pady=8)

        ActionButton(btn_row, text="＋ 添加分组", command=self._add_slot, bg=BG4, fg=TEXT2, relief="flat", font=FONT_UI_REG, padx=10, pady=4, cursor="hand2").pack(side="left")

        self._edit_copy_btn = ActionButton(btn_row, text="📋 复制勾选分组", command=self._edit_copy_all, bg=AMBER, fg=BG, relief="flat", font=FONT_UI_BOLD, padx=10, pady=4, cursor="hand2")
        self._edit_copy_btn.pack(side="right")

        self.bind(f"<{MODIFIER}-z>", self._global_undo)
        self.bind("<Command-Shift-Z>" if IS_MAC else "<Control-y>", self._global_redo)

    def _bind_mousewheel(self, widget):
        try:
            widget.bind("<MouseWheel>", self._wheel_handler)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._bind_mousewheel(child)

    def _add_slot(self, default_name: str = "", default_enabled: bool = True, scroll_to: str = "bottom"):
        idx = len(self._slots)
        data = {
            "label":   tk.StringVar(value=default_name),
            "enabled": tk.BooleanVar(value=default_enabled),
            "clips":   [],
            "undo":    [],
            "redo":    [],
        }
        self._slots.append(data)

        color = TRACK_COLORS[idx % len(TRACK_COLORS)]

        slot_frame = tk.Frame(self._slots_frame, bg=BG3, relief="flat", bd=0)
        slot_frame.pack(fill="x", padx=8, pady=(8, 0))

        tk.Frame(slot_frame, bg=color, width=4).pack(side="left", fill="y")

        inner = tk.Frame(slot_frame, bg=BG3)
        inner.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        title_row = tk.Frame(inner, bg=BG3)
        title_row.pack(fill="x")

        enabled_canvas = tk.Canvas(title_row, width=18, height=18, bg=BG3, highlightthickness=0, cursor="hand2")
        enabled_canvas.pack(side="left", padx=(0, 6))
        self._draw_slot_checkbox(enabled_canvas, default_enabled, color)

        def _toggle_enabled(ev, d=data, cv=enabled_canvas, c=color):
            d["enabled"].set(not d["enabled"].get())
            self._draw_slot_checkbox(cv, d["enabled"].get(), c)
            self._refresh_slot_dim(d, inner)

        enabled_canvas.bind("<Button-1>", _toggle_enabled)
        data["_cv"], data["_color"], data["_inner"] = enabled_canvas, color, inner

        if not default_enabled:
            self.after(10, lambda d=data, i=inner: self._refresh_slot_dim(d, i))

        tk.Label(title_row, text="分组名：", bg=BG3, fg=TEXT3, font=FONT_UI_SM).pack(side="left")

        name_entry = tk.Entry(title_row, textvariable=data["label"], bg=BG4, fg=TEXT, insertbackground=TEXT, relief="flat", font=FONT_UI_REG, width=10)
        name_entry.pack(side="left", padx=(2, 4), ipady=3)

        del_btn = ActionButton(title_row, text="✕", command=lambda f=slot_frame, d=data: self._remove_slot(f, d), bg=BG3, fg=TEXT3, relief="flat", font=FONT_UI_REG, padx=4, pady=0, cursor="hand2")
        del_btn.pack(side="right")

        clips_frame = tk.Frame(inner, bg=BG3)
        clips_frame.pack(fill="x", pady=(6, 0))

        clips_listbox = tk.Listbox(clips_frame, bg=BG4, fg=ACCENT, selectbackground="#1e3a5f", font=FONT_CODE_SM, relief="flat", height=3, activestyle="none", selectmode="extended")
        clips_listbox.pack(fill="x")

        _drag = {"y": 0, "h": 3}

        def _drag_start(e, lb=clips_listbox, d=_drag):
            d["y"] = e.y_root
            d["h"] = lb.cget("height")

        def _drag_move(e, lb=clips_listbox, d=_drag):
            line_px = lb.winfo_height() / max(lb.cget("height"), 1)
            if line_px <= 0:
                line_px = 16
            delta_lines = int((e.y_root - d["y"]) / line_px)
            new_h = max(2, min(20, d["h"] + delta_lines))
            lb.config(height=new_h)
            self._slots_frame.update_idletasks()
            self._slot_canvas.configure(scrollregion=self._slot_canvas.bbox("all"))

        resize_bar_cv = tk.Canvas(clips_frame, bg="#1e3a5f", height=8, highlightthickness=0, cursor="sb_v_double_arrow")
        resize_bar_cv.pack(fill="x", pady=(1, 0))

        def _draw_grip_lines(e=None, cv=resize_bar_cv):
            cv.delete("all")
            w = cv.winfo_width()
            mid = cv.winfo_height() // 2
            for dy in (-2, 2):
                cv.create_line(w//2 - 20, mid+dy, w//2 + 20, mid+dy, fill="#4a7aaa", width=1)

        resize_bar_cv.bind("<Configure>",    _draw_grip_lines)
        resize_bar_cv.bind("<ButtonPress-1>", _drag_start)
        resize_bar_cv.bind("<B1-Motion>",     _drag_move)
        resize_bar_cv.bind("<MouseWheel>",    self._wheel_handler)

        act_row = tk.Frame(inner, bg=BG3)
        act_row.pack(fill="x", pady=(4, 0))

        add_btn = ActionButton(act_row, text="＋ 添加轨道", command=lambda d=data, lb=clips_listbox: self._slot_add_current(d, lb), bg=color, fg=BG, relief="flat", font=FONT_UI_BOLD, padx=8, pady=3, cursor="hand2")
        add_btn.pack(side="left")

        del_line_btn = ActionButton(act_row, text="删除选中", command=lambda d=data, lb=clips_listbox: self._slot_del_selected(d, lb), bg=BG4, fg=TEXT3, relief="flat", font=FONT_UI_SM, padx=8, pady=3, cursor="hand2", state="disabled")
        del_line_btn.pack(side="left", padx=(6, 0))

        clr_btn = ActionButton(act_row, text="清空", command=lambda d=data, lb=clips_listbox: self._slot_clear(d, lb), bg=BG4, fg=TEXT3, relief="flat", font=FONT_UI_SM, padx=8, pady=3, cursor="hand2", state="disabled")
        clr_btn.pack(side="right")

        ur_row = tk.Frame(inner, bg=BG3)
        ur_row.pack(fill="x", pady=(3, 0))

        undo_btn = ActionButton(ur_row, text="↩ 撤销", command=lambda d=data, lb=clips_listbox: self._slot_undo(d, lb), bg=BG4, fg=TEXT2, relief="flat", font=FONT_UI_SM, padx=8, pady=2, cursor="hand2", state="disabled")
        undo_btn.pack(side="left")

        redo_btn = ActionButton(ur_row, text="↪ 回撤", command=lambda d=data, lb=clips_listbox: self._slot_redo(d, lb), bg=BG4, fg=TEXT2, relief="flat", font=FONT_UI_SM, padx=8, pady=2, cursor="hand2", state="disabled")
        redo_btn.pack(side="left", padx=(6, 0))

        tk.Label(ur_row, text=UNDO_HINT, bg=BG3, fg=TEXT3, font=FONT_UI_SM).pack(side="left", padx=(8, 0))

        w_entry = {
            "frame":        slot_frame,
            "inner":        inner,
            "listbox":      clips_listbox,
            "data":         data,
            "add_btn":      add_btn,
            "undo_btn":     undo_btn,
            "redo_btn":     redo_btn,
            "del_line_btn": del_line_btn,
            "clr_btn":      clr_btn,
        }
        self._slot_widgets.append(w_entry)

        self._bind_mousewheel(slot_frame)

        self._slots_frame.update_idletasks()
        self._slot_canvas.configure(scrollregion=self._slot_canvas.bbox("all"))
        self._slot_canvas.yview_moveto(0.0 if scroll_to == "top" else 1.0)

    def _refresh_slot_action_btns(self, data: dict):
        """根据分组是否有内容，高亮或置灰「删除选中行」和「清空」按钮。"""
        has_items = bool(data.get("clips"))
        for we in self._slot_widgets:
            if we["data"] is not data:
                continue
            if has_items:
                we["del_line_btn"].config(state="normal",  bg="#7f1d1d", fg="#fca5a5")
                we["clr_btn"].config(     state="normal",  bg="#7f1d1d", fg="#fca5a5")
            else:
                we["del_line_btn"].config(state="disabled", bg=BG4, fg=TEXT3)
                we["clr_btn"].config(     state="disabled", bg=BG4, fg=TEXT3)
            break

    def _draw_slot_checkbox(self, canvas, checked: bool, color: str):
        draw_checkbox(canvas, checked, color)

    def _refresh_slot_dim(self, data, inner):
        enabled = data["enabled"].get()
        dim_bg  = BG3  if enabled else "#141e2e"
        try:
            inner.config(bg=dim_bg)
            for w in inner.winfo_children():
                try:
                    w.config(bg=dim_bg)
                except tk.TclError:
                    pass
        except tk.TclError:
            pass

    def _remove_slot(self, frame, data):
        if len(self._slots) <= 1:
            messagebox.showinfo("提示", "至少保留一个分组", parent=self)
            return
        self._slots.remove(data)
        self._slot_widgets = [w for w in self._slot_widgets if w["data"] is not data]
        frame.destroy()
        self._slots_frame.update_idletasks()
        self._slot_canvas.configure(scrollregion=self._slot_canvas.bbox("all"))

    # ── 撤销/重做辅助 ────────────────────────────────────────────────────────

    def _slot_snapshot(self, data):
        data["undo"].append(list(data["clips"]))
        data["redo"].clear()
        if len(data["undo"]) > 50:
            data["undo"].pop(0)
        self._slot_refresh_ur_buttons(data)

    def _slot_refresh_ur_buttons(self, data):
        for w in self._slot_widgets:
            if w["data"] is not data:
                continue
            w["undo_btn"].config(state="normal" if data["undo"] else "disabled", fg=TEXT if data["undo"] else TEXT3)
            w["redo_btn"].config(state="normal" if data["redo"] else "disabled", fg=TEXT if data["redo"] else TEXT3)
            break

    def _slot_restore(self, data, listbox, snapshot):
        data["clips"] = list(snapshot)
        listbox.delete(0, "end")
        for line in data["clips"]:
            listbox.insert("end", line)

    def _slot_undo(self, data, listbox):
        if not data["undo"]:
            return
        data["redo"].append(list(data["clips"]))
        snapshot = data["undo"].pop()
        self._slot_restore(data, listbox, snapshot)
        self._slot_refresh_ur_buttons(data)
        self._set_status("↩  已撤销上一步操作")
        self._refresh_slot_action_btns(data)

    def _slot_redo(self, data, listbox):
        if not data["redo"]:
            return
        data["undo"].append(list(data["clips"]))
        snapshot = data["redo"].pop()
        self._slot_restore(data, listbox, snapshot)
        self._slot_refresh_ur_buttons(data)
        self._set_status("↪  已重做操作")
        self._refresh_slot_action_btns(data)

    def _slot_add_current(self, data, listbox):
        if self.view_idx is None:
            messagebox.showinfo("提示", "请先在左侧点击选择一条轨道", parent=self)
            return
        clips = self.tracks[self.view_idx]["clips"]
        new_lines = []
        for c in clips:
            line = f"{smpte_compact(c['start'])}-{smpte_compact(c['end'])}"
            if line not in data["clips"]:
                new_lines.append(line)
        if not new_lines:
            self._set_status("⚠  所有片段已在该分组中，无需重复添加")
            return
        # 将已有片段 + 新片段合并后做智能合并检测
        combined = list(data["clips"]) + new_lines
        merged   = self._maybe_merge_lines(combined, self._bridge_ranges(self.view_idx))
        if merged == combined:
            # 无合并，只追加新行
            self._slot_snapshot(data)
            for line in new_lines:
                data["clips"].append(line)
                listbox.insert("end", line)
        else:
            # 有合并，整体替换
            self._slot_snapshot(data)
            data["clips"] = merged
            listbox.delete(0, "end")
            for line in data["clips"]:
                listbox.insert("end", line)
        self._slot_set_enabled(data)      # 填充内容后自动勾选该分组
        self._set_status(f"✅  已添加 {len(new_lines)} 条片段到分组「{data['label'].get() or '(未命名)'}」")
        self._refresh_slot_action_btns(data)

    def _slot_set_enabled(self, data):
        """把分组设为勾选状态（已勾选则不动）。"""
        if data["enabled"].get() or "_cv" not in data:
            return
        data["enabled"].set(True)
        self._draw_slot_checkbox(data["_cv"], True, data["_color"])
        self._refresh_slot_dim(data, data["_inner"])

    def _slot_del_selected(self, data, listbox):
        sel = listbox.curselection()
        if not sel:
            return
        self._slot_snapshot(data)
        for i in reversed(sel):
            line = listbox.get(i)
            listbox.delete(i)
            if line in data["clips"]:
                data["clips"].remove(line)
        self._set_status(f"🗑  已删除 {len(sel)} 条片段")
        self._refresh_slot_action_btns(data)

    def _slot_clear(self, data, listbox):
        if not data["clips"]:
            return
        self._slot_snapshot(data)
        data["clips"].clear()
        listbox.delete(0, "end")
        self._set_status("🗑  已清空分组")
        self._refresh_slot_action_btns(data)

    def _edit_copy_all(self):
        parts = []
        skipped = 0
        for slot in self._slots:
            if not slot["enabled"].get():
                skipped += 1
                continue
            label = slot["label"].get().strip()
            clips = slot["clips"]
            if not label and not clips:
                continue
            if label:
                parts.append(f"{label}：")
            parts.extend(clips)

        if not parts:
            if skipped:
                messagebox.showinfo("提示", f"所有分组均未勾选激活，或勾选的分组没有内容。\n（已跳过 {skipped} 个未激活分组）", parent=self)
            else:
                messagebox.showinfo("提示", "没有任何内容可复制，请先添加片段", parent=self)
            return

        text = "\n".join(parts)
        self.clipboard_clear()
        self.clipboard_append(text)
        self._edit_copy_btn.config(text="✅  已复制！", bg="#16a34a", fg="white")
        self.after(1500, lambda: self._edit_copy_btn.config(text="📋 复制勾选分组", bg=AMBER, fg=BG))
        active = sum(1 for s in self._slots if s["enabled"].get())
        self._set_status(f"✅  已复制 {active} 个激活分组的内容到剪贴板")

    def _global_undo(self, event=None):
        if not self._edit_mode:
            return
        for w in reversed(self._slot_widgets):
            if w["data"]["undo"]:
                self._slot_undo(w["data"], w["listbox"])
                return

    def _global_redo(self, event=None):
        if not self._edit_mode:
            return
        for w in reversed(self._slot_widgets):
            if w["data"]["redo"]:
                self._slot_redo(w["data"], w["listbox"])
                return

    def _toggle_edit_mode(self):
        self._edit_mode = not self._edit_mode
        if self._edit_mode:
            self._drawer.pack(side="right", fill="y", padx=(10, 0))
            self.edit_mode_btn.config(bg=AMBER, fg=BG, text="✕  关闭编辑")
        else:
            self._drawer.pack_forget()
            self.edit_mode_btn.config(bg=BG4, fg=TEXT2, text="编辑模式")


# ── 入口 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--ui-preview":
        from ui_validation import run_visual_checks
        run_visual_checks(App, sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == "--smoke-test":
        import tempfile
        app = App(open_dialog=False)
        try:
            if not DND_AVAILABLE:
                raise RuntimeError("TkDnD was not bundled")
            with tempfile.TemporaryDirectory() as tmp:
                sample = Path(tmp) / "测试轨道.txt"
                sample.write_text("TRACK NAME: Reading 测试\n1 1 片段一  00:00:01:00 00:00:02:00 00:00:01:00\n", encoding="utf-8")
                app._load_path(str(sample))
                app.update()
                if not (len(app.tracks) == 1):
                    raise RuntimeError('Release validation failed')
                if not (app.tracks[0]["track_name"] == "Reading 测试"):
                    raise RuntimeError('Release validation failed')
                app.clipboard_clear()
                app.clipboard_append("PT Clip Viewer 测试")
                app.update()
                if not (app.clipboard_get() == "PT Clip Viewer 测试"):
                    raise RuntimeError('Release validation failed')
                Path(sys.argv[2]).write_text("OK\n", encoding="utf-8")
        finally:
            app.destroy()
    else:
        app = App()
        app.mainloop()
