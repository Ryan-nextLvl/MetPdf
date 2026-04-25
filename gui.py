"""UniversalPDF — Desktop GUI powered by customtkinter."""

import sys

# Worker mode: the frozen .exe re-runs itself with this flag to convert a
# single DOCX in an isolated process (avoids COM/tkinter deadlock).
# Must be checked before any other import so the child exits fast.
if "--_docx" in sys.argv:
    idx = sys.argv.index("--_docx")
    _in, _out, _err = sys.argv[idx + 1], sys.argv[idx + 2], sys.argv[idx + 3]
    try:
        import pythoncom  # type: ignore
        pythoncom.CoInitialize()
    except ImportError:
        pass
    try:
        from docx2pdf import convert  # type: ignore
        convert(_in, _out)
    except Exception as _exc:
        with open(_err, "w", encoding="utf-8") as _f:
            _f.write(str(_exc))
        sys.exit(1)
    sys.exit(0)

import os
import platform
import subprocess
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image

_BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
sys.path.insert(0, str(_BASE))

from core.service import ConversionResult, ConversionService

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore
    _HAS_DND = True
except ImportError:
    _HAS_DND = False

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

_SUPPORTED = (".txt", ".png", ".jpg", ".jpeg", ".docx", ".pdf")
_WIN_W, _WIN_H = 860, 880
_DEFAULT_OUTPUT = (
    Path(sys.executable).parent / "output"
    if getattr(sys, "frozen", False)
    else Path("output")
)

# ── Palette ──────────────────────────────────────────────────────────────────
_BG       = "#0a0a18"
_SURFACE  = "#12122a"
_SURFACE2 = "#1a1a35"
_BORDER   = "#252548"
_PRIMARY  = "#3b82f6"
_PRIMARY_HOVER = "#2563eb"
_PURPLE   = "#8b5cf6"
_PURPLE_HOVER  = "#7c3aed"
_ACCENT   = "#60a5fa"
_SUCCESS  = "#22c55e"
_SUCCESS_BG = "#0f2a1a"
_ERROR    = "#ef4444"
_ERROR_BG = "#2a0e0e"
_WARN     = "#f59e0b"
_DIM      = "#7a7a9a"
_DIM2     = "#5a5a7a"
_WHITE    = "#f5f5fa"

# ── File-type thumbnail map ─────────────────────────────────────────────────
_THUMB_MAP = {
    ".pdf":  ("📕", "#3a1818"),
    ".docx": ("📘", "#18243a"),
    ".txt":  ("📄", "#2a1a3a"),
    ".png":  ("🖼", "#0f2a1a"),
    ".jpg":  ("🖼", "#0f2a1a"),
    ".jpeg": ("🖼", "#0f2a1a"),
}


# ─── File row ────────────────────────────────────────────────────────────────

class FileRow(ctk.CTkFrame):
    """One row in the queue: thumbnail | name+size | status/badge | remove."""

    def __init__(self, master, path: Path, on_remove, **kw):
        super().__init__(master, fg_color=_SURFACE2, corner_radius=10, **kw)
        self.path = path
        self.columnconfigure(1, weight=1)

        emoji, bg = _THUMB_MAP.get(path.suffix.lower(), ("📎", _SURFACE))
        thumb = ctk.CTkFrame(self, fg_color=bg, corner_radius=10, width=56, height=56)
        thumb.grid(row=0, column=0, padx=12, pady=10)
        thumb.grid_propagate(False)
        ctk.CTkLabel(thumb, text=emoji, font=("", 24)).place(relx=0.5, rely=0.5, anchor="center")

        info = ctk.CTkFrame(self, fg_color="transparent")
        info.grid(row=0, column=1, sticky="ew", padx=4)
        info.columnconfigure(0, weight=1)
        ctk.CTkLabel(info, text=path.name, anchor="w", font=("", 14, "bold"),
                     text_color=_WHITE).grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(info, text=_fmt_size(path), anchor="w", font=("", 11),
                     text_color=_DIM).grid(row=1, column=0, sticky="ew")

        self._status = ctk.CTkLabel(self, text="Aguardando", text_color=_DIM,
                                    font=("", 12), anchor="e", width=110)
        self._status.grid(row=0, column=2, padx=(8, 4))

        self._badge = ctk.CTkFrame(self, fg_color=_SUCCESS_BG, corner_radius=8,
                                   border_width=1, border_color="#1f5a3a")
        ctk.CTkLabel(self._badge, text="✓ Concluído", text_color=_SUCCESS,
                     font=("", 12, "bold")).pack(padx=14, pady=6)

        self._remove_btn = ctk.CTkButton(
            self, text="✕", width=30, height=30, fg_color="transparent",
            hover_color="#3a3a5a", text_color=_DIM, font=("", 14),
            command=lambda: on_remove(self),
        )
        self._remove_btn.grid(row=0, column=4, padx=(4, 12))

    def mark_converting(self):
        self._badge.grid_remove()
        self._status.grid()
        self._status.configure(text="Convertendo…", text_color=_ACCENT)

    def mark_success(self):
        self._status.grid_remove()
        self._badge.grid(row=0, column=2, padx=(8, 4))

    def mark_failed(self, reason: str = ""):
        self._badge.grid_remove()
        self.configure(fg_color=_ERROR_BG)
        short = (reason[:22] + "…") if len(reason) > 22 else reason
        self._status.grid()
        self._status.configure(text=f"✗ {short}", text_color=_ERROR)

    def reset(self):
        self.configure(fg_color=_SURFACE2)
        self._badge.grid_remove()
        self._status.grid()
        self._status.configure(text="Aguardando", text_color=_DIM)


# ─── Main window ─────────────────────────────────────────────────────────────

class App(ctk.CTk if not _HAS_DND else TkinterDnD.Tk):  # type: ignore[misc]
    def __init__(self):
        super().__init__()
        self.title("UniversalPDF")
        self.geometry(f"{_WIN_W}x{_WIN_H}")
        self.minsize(700, 700)
        self.resizable(True, True)

        self._files: list[Path] = []
        self._rows: dict[Path, FileRow] = {}
        self._output_dir = _DEFAULT_OUTPUT
        self._service: ConversionService | None = None
        self._app_icon: ctk.CTkImage | None = None

        if isinstance(self, ctk.CTk):
            self.configure(fg_color=_BG)
        else:
            self.configure(bg=_BG)

        self._load_app_icon()
        self._build_ui()
        if _HAS_DND:
            self._setup_dnd()

    def _load_app_icon(self):
        try:
            img = Image.open(_BASE / "assets" / "icon.png")
            self._app_icon = ctk.CTkImage(light_image=img, dark_image=img, size=(56, 56))
        except Exception:
            self._app_icon = None

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self._build_header()
        self._build_drop_zone()
        self._build_file_list_card()
        self._build_output_card()

    def _build_header(self):
        bar = ctk.CTkFrame(self, fg_color=_BG, corner_radius=0)
        bar.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))
        bar.columnconfigure(1, weight=1)

        if self._app_icon is not None:
            ctk.CTkLabel(bar, image=self._app_icon, text="").grid(
                row=0, column=0, rowspan=2, padx=(0, 14), sticky="w")

        title_row = ctk.CTkFrame(bar, fg_color="transparent")
        title_row.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(title_row, text="Universal", font=("", 30, "bold"),
                     text_color=_WHITE).pack(side="left")
        ctk.CTkLabel(title_row, text="PDF", font=("", 30, "bold"),
                     text_color=_ACCENT).pack(side="left")

        ctk.CTkLabel(bar, text="Conversor de arquivos para PDF", font=("", 13),
                     text_color=_DIM).grid(row=1, column=1, sticky="w")

        self._theme_pill = ctk.CTkFrame(bar, fg_color=_SURFACE, corner_radius=22,
                                        border_width=1, border_color=_BORDER)
        self._theme_pill.grid(row=0, column=2, rowspan=2, sticky="e")

        self._moon_btn = ctk.CTkButton(
            self._theme_pill, text="🌙", width=44, height=36, font=("", 14),
            fg_color=_PRIMARY, hover_color=_PRIMARY_HOVER, corner_radius=18,
            command=lambda: self._set_theme("dark"),
        )
        self._moon_btn.grid(row=0, column=0, padx=(4, 2), pady=4)

        self._sun_btn = ctk.CTkButton(
            self._theme_pill, text="☀", width=44, height=36, font=("", 14),
            fg_color="transparent", hover_color=_SURFACE2, text_color=_DIM,
            corner_radius=18, command=lambda: self._set_theme("light"),
        )
        self._sun_btn.grid(row=0, column=1, padx=(2, 4), pady=4)

    def _build_drop_zone(self):
        zone = ctk.CTkFrame(self, fg_color=_SURFACE, corner_radius=14,
                            border_width=2, border_color=_BORDER)
        zone.grid(row=1, column=0, padx=24, pady=(8, 12), sticky="ew")
        zone.columnconfigure(0, weight=1)

        ctk.CTkLabel(zone, text="☁", font=("", 56), text_color=_ACCENT).grid(
            row=0, column=0, pady=(24, 0))

        drop_hint = "Arraste arquivos ou pastas aqui" if _HAS_DND else "Selecione arquivos ou pastas"
        ctk.CTkLabel(zone, text=drop_hint, font=("", 18, "bold"),
                     text_color=_WHITE).grid(row=1, column=0, pady=(4, 8))

        chips = ctk.CTkFrame(zone, fg_color="transparent")
        chips.grid(row=2, column=0, pady=(0, 18))
        for ext in _SUPPORTED:
            _make_chip(chips, ext).pack(side="left", padx=4)

        btns = ctk.CTkFrame(zone, fg_color="transparent")
        btns.grid(row=3, column=0, pady=(0, 22))

        ctk.CTkButton(btns, text="📄  + Arquivos", command=self._browse_files,
                      width=180, height=42, font=("", 14, "bold"),
                      fg_color=_PRIMARY, hover_color=_PRIMARY_HOVER,
                      corner_radius=10).pack(side="left", padx=8)

        ctk.CTkButton(btns, text="📁  + Pasta", command=self._browse_folder,
                      width=180, height=42, font=("", 14, "bold"),
                      fg_color=_PURPLE, hover_color=_PURPLE_HOVER,
                      corner_radius=10).pack(side="left", padx=8)

        ctk.CTkButton(btns, text="🗑  Limpar lista", command=self._clear_files,
                      width=180, height=42, font=("", 14),
                      fg_color="transparent", hover_color=_SURFACE2,
                      text_color=_WHITE, border_width=1, border_color=_BORDER,
                      corner_radius=10).pack(side="left", padx=8)

    def _build_file_list_card(self):
        card = ctk.CTkFrame(self, fg_color=_SURFACE, corner_radius=14,
                            border_width=1, border_color=_BORDER)
        card.grid(row=2, column=0, padx=24, pady=(0, 12), sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 8))
        header.columnconfigure(1, weight=1)
        ctk.CTkLabel(header, text="📄  Arquivos na fila", font=("", 15, "bold"),
                     text_color=_WHITE).grid(row=0, column=0, sticky="w")

        self._count_pill = ctk.CTkFrame(header, fg_color=_SURFACE2, corner_radius=12)
        self._count_pill.grid(row=0, column=2, sticky="e")
        self._count_pill_label = ctk.CTkLabel(self._count_pill, text="0 arquivos",
                                              font=("", 11), text_color=_DIM)
        self._count_pill_label.pack(padx=12, pady=4)

        self._file_scroll = ctk.CTkScrollableFrame(card, fg_color=_SURFACE,
                                                   scrollbar_button_color=_SURFACE2)
        self._file_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self._file_scroll.columnconfigure(0, weight=1)

        self._empty_label = ctk.CTkLabel(
            self._file_scroll,
            text="Nenhum arquivo adicionado.\nUse os botões acima ou arraste arquivos.",
            text_color=_DIM, font=("", 12), justify="center",
        )
        self._empty_label.grid(row=0, column=0, pady=40)

    def _build_output_card(self):
        card = ctk.CTkFrame(self, fg_color=_SURFACE, corner_radius=14,
                            border_width=1, border_color=_BORDER)
        card.grid(row=3, column=0, padx=24, pady=(0, 20), sticky="ew")
        card.columnconfigure(1, weight=1)

        # Row 0: Saída + path + select
        ctk.CTkLabel(card, text="Saída:", font=("", 13, "bold"),
                     text_color=_ACCENT).grid(row=0, column=0, padx=(18, 8), pady=(16, 8), sticky="w")
        self._out_var = ctk.StringVar(value=str(_DEFAULT_OUTPUT))
        ctk.CTkEntry(card, textvariable=self._out_var, font=("", 12),
                     fg_color=_SURFACE2, border_color=_BORDER, height=36).grid(
            row=0, column=1, sticky="ew", padx=(0, 8), pady=(16, 8))
        ctk.CTkButton(card, text="📁", width=40, height=36, fg_color=_SURFACE2,
                      hover_color=_BORDER, font=("", 14),
                      command=self._browse_output).grid(row=0, column=2, padx=(0, 6), pady=(16, 8))
        ctk.CTkButton(card, text="Selecionar", width=110, height=36,
                      fg_color="transparent", hover_color=_SURFACE2,
                      border_width=1, border_color=_BORDER, text_color=_WHITE,
                      command=self._browse_output).grid(row=0, column=3, padx=(0, 18), pady=(16, 8))

        # Row 1: count + Convert button
        action_row = ctk.CTkFrame(card, fg_color="transparent")
        action_row.grid(row=1, column=0, columnspan=4, sticky="ew", padx=18, pady=(8, 12))
        action_row.columnconfigure(0, weight=1)
        self._count_label = ctk.CTkLabel(action_row, text="0 arquivo(s) na fila",
                                         font=("", 13), text_color=_DIM)
        self._count_label.grid(row=0, column=0, sticky="w")

        self._cancel_btn = ctk.CTkButton(
            action_row, text="Cancelar", width=120, height=44, font=("", 13),
            fg_color=_ERROR, hover_color="#dc2626", corner_radius=10,
            command=self._cancel_conversion,
        )
        self._cancel_btn.grid(row=0, column=1, padx=(0, 8))
        self._cancel_btn.grid_remove()

        self._convert_btn = ctk.CTkButton(
            action_row, text="Converter  →", width=200, height=44,
            font=("", 15, "bold"), fg_color=_PRIMARY, hover_color=_PRIMARY_HOVER,
            corner_radius=10, command=self._start_conversion,
        )
        self._convert_btn.grid(row=0, column=2)

        # Row 2: progress bar
        self._progress = ctk.CTkProgressBar(card, height=6, corner_radius=3,
                                            progress_color=_PRIMARY,
                                            fg_color=_SURFACE2)
        self._progress.set(0)
        self._progress.grid(row=2, column=0, columnspan=4, padx=18, pady=(0, 10), sticky="ew")

        # Row 3: status + open folder
        status_row = ctk.CTkFrame(card, fg_color="transparent")
        status_row.grid(row=3, column=0, columnspan=4, sticky="ew", padx=18, pady=(0, 16))
        status_row.columnconfigure(0, weight=1)

        self._progress_label = ctk.CTkLabel(status_row, text="", font=("", 12),
                                            text_color=_DIM)
        self._progress_label.grid(row=0, column=0, sticky="w")

        self._open_folder_btn = ctk.CTkButton(
            status_row, text="📂  Abrir pasta de saída", width=190, height=36,
            font=("", 12), fg_color="transparent", hover_color=_SURFACE2,
            border_width=1, border_color=_BORDER, text_color=_WHITE,
            corner_radius=10, command=lambda: _open_path(self._output_dir),
        )
        self._open_folder_btn.grid(row=0, column=1)
        self._open_folder_btn.grid_remove()

    # ── Drag & drop ───────────────────────────────────────────────────────────

    def _setup_dnd(self):
        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event):
        self._add_paths([Path(p) for p in self.tk.splitlist(event.data)])

    # ── File management ───────────────────────────────────────────────────────

    def _browse_files(self):
        exts = " ".join(f"*{e}" for e in _SUPPORTED)
        chosen = filedialog.askopenfilenames(
            title="Selecionar arquivos",
            filetypes=[("Suportados", exts), ("Todos", "*.*")],
        )
        self._add_paths([Path(p) for p in chosen])

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Selecionar pasta")
        if folder:
            self._add_paths(list(Path(folder).iterdir()))

    def _browse_output(self):
        folder = filedialog.askdirectory(title="Pasta de saída")
        if folder:
            self._out_var.set(folder)
            self._output_dir = Path(folder)

    def _add_paths(self, paths: list[Path]):
        added = 0
        for p in paths:
            if not p.is_file() or p.suffix.lower() not in _SUPPORTED or p in self._rows:
                continue
            self._files.append(p)
            file_row = FileRow(self._file_scroll, p, on_remove=self._remove_row)
            file_row.grid(row=len(self._rows), column=0, sticky="ew", padx=4, pady=4)
            self._rows[p] = file_row
            added += 1

        if added:
            self._empty_label.grid_remove()
            self._update_count()

    def _remove_row(self, file_row: FileRow):
        self._files.remove(file_row.path)
        del self._rows[file_row.path]
        file_row.destroy()
        for i, r in enumerate(self._rows.values()):
            r.grid(row=i)
        if not self._files:
            self._empty_label.grid(row=0, column=0, pady=40)
        self._update_count()

    def _clear_files(self):
        for r in self._rows.values():
            r.destroy()
        self._files.clear()
        self._rows.clear()
        self._empty_label.grid(row=0, column=0, pady=40)
        self._update_count()

    def _update_count(self):
        n = len(self._files)
        self._count_label.configure(text=f"{n} arquivo(s) na fila")
        self._count_pill_label.configure(text=f"{n} arquivo" if n == 1 else f"{n} arquivos")

    # ── Conversion ────────────────────────────────────────────────────────────

    def _start_conversion(self):
        if not self._files:
            _flash(self._count_label, "Adicione pelo menos um arquivo!", _WARN)
            return

        self._output_dir = Path(self._out_var.get())
        self._convert_btn.configure(state="disabled", text="Convertendo…")
        self._cancel_btn.grid()
        self._open_folder_btn.grid_remove()
        self._progress.set(0)
        self._progress.configure(progress_color=_PRIMARY)
        self._progress_label.configure(text="Iniciando…", text_color=_DIM)

        for r in self._rows.values():
            r.reset()

        if self._files:
            self._rows[self._files[0]].mark_converting()

        self._service = ConversionService(self._output_dir)
        self._service.convert_files(
            self._files,
            on_progress=self._on_progress,
            on_done=self._on_done,
            threaded=True,
        )

    def _cancel_conversion(self):
        if self._service:
            self._service.cancel()
        self._cancel_btn.configure(state="disabled")
        self._progress_label.configure(text="Cancelando…", text_color=_WARN)

    def _on_progress(self, done: int, total: int, result: ConversionResult):
        row = self._rows.get(result.input_path)
        if row:
            if result.success:
                self.after(0, row.mark_success)
            else:
                self.after(0, row.mark_failed, result.error or "")

        if done < total:
            next_row = self._rows.get(self._files[done])
            if next_row:
                self.after(0, next_row.mark_converting)

        self.after(0, self._progress.set, done / total)
        self.after(0, self._progress_label.configure, {
            "text": f"{done}/{total}  —  {result.input_path.name}",
            "text_color": _DIM,
        })

    def _on_done(self, results: list[ConversionResult]):
        ok = sum(1 for r in results if r.success)
        total = len(results)
        color = _SUCCESS if ok == total else (_WARN if ok > 0 else _ERROR)
        msg = f"✓ Concluído: {ok}/{total} arquivo(s) convertido(s)."
        self.after(0, self._finish_ui, msg, color, ok > 0)

    def _finish_ui(self, msg: str, color: str, show_folder: bool):
        self._convert_btn.configure(state="normal", text="Converter  →")
        self._cancel_btn.grid_remove()
        self._cancel_btn.configure(state="normal")
        self._progress_label.configure(text=msg, text_color=color)
        if color == _SUCCESS:
            self._progress.configure(progress_color=_SUCCESS)
        self._service = None
        if show_folder:
            self._open_folder_btn.grid()

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _set_theme(self, mode: str):
        ctk.set_appearance_mode(mode)
        if mode == "dark":
            self._moon_btn.configure(fg_color=_PRIMARY, text_color=_WHITE)
            self._sun_btn.configure(fg_color="transparent", text_color=_DIM)
        else:
            self._sun_btn.configure(fg_color=_PRIMARY, text_color=_WHITE)
            self._moon_btn.configure(fg_color="transparent", text_color=_DIM)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_chip(parent, text: str) -> ctk.CTkFrame:
    chip = ctk.CTkFrame(parent, fg_color=_SURFACE2, corner_radius=10)
    ctk.CTkLabel(chip, text=text, font=("", 11), text_color=_DIM).pack(padx=10, pady=3)
    return chip


def _open_path(path: Path) -> None:
    target = path if path.is_dir() else path.parent
    system = platform.system()
    if system == "Windows":
        os.startfile(str(target))
    elif system == "Darwin":
        subprocess.Popen(["open", str(target)])
    else:
        subprocess.Popen(["xdg-open", str(target)])


def _fmt_size(path: Path) -> str:
    try:
        b = path.stat().st_size
    except OSError:
        return ""
    if b < 1024:
        return f"{b} B"
    if b < 1024 ** 2:
        return f"{b / 1024:.1f} KB"
    return f"{b / 1024 ** 2:.1f} MB"


def _flash(label: ctk.CTkLabel, msg: str, color: str) -> None:
    orig_text = label.cget("text")
    orig_color = label.cget("text_color")
    label.configure(text=msg, text_color=color)
    label.after(2500, lambda: label.configure(text=orig_text, text_color=orig_color))


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
