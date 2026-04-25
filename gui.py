"""MetePDF — Desktop GUI powered by customtkinter."""

import os
import platform
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

# Resolve base dir whether running from source or inside a PyInstaller bundle
_BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
sys.path.insert(0, str(_BASE))

from core.dispatcher import Dispatcher
from core.exceptions import Any2PDFError

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore
    _HAS_DND = True
except ImportError:
    _HAS_DND = False

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

_SUPPORTED = (".txt", ".png", ".jpg", ".jpeg", ".docx", ".pdf")
_WIN_W, _WIN_H = 740, 640

# When bundled as .exe, write output next to the executable, not inside the temp bundle
_DEFAULT_OUTPUT = (Path(sys.executable).parent / "output") if getattr(sys, "frozen", False) else Path("output")


# ─── File row ────────────────────────────────────────────────────────────────

class FileRow(ctk.CTkFrame):
    def __init__(self, master, path: Path, on_remove, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self.path = path
        self._icon = _ext_icon(path.suffix.lower())

        self.columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text=self._icon, width=28, font=("", 16)).grid(row=0, column=0, padx=(4, 0))
        ctk.CTkLabel(self, text=path.name, anchor="w", font=("", 13)).grid(row=0, column=1, sticky="ew", padx=8)
        ctk.CTkLabel(self, text=_fmt_size(path), text_color="gray60", font=("", 11)).grid(row=0, column=2, padx=(0, 6))
        ctk.CTkButton(
            self, text="✕", width=26, height=26, fg_color="transparent",
            hover_color="#3a3a3a", text_color="gray60", font=("", 12),
            command=lambda: on_remove(self),
        ).grid(row=0, column=3, padx=(0, 4))

    def set_status(self, ok: bool, msg: str = ""):
        color = "#2ecc71" if ok else "#e74c3c"
        symbol = "✓" if ok else "✗"
        ctk.CTkLabel(self, text=symbol, text_color=color, font=("", 14, "bold"), width=20).grid(row=0, column=4, padx=(2, 6))


# ─── Log entry ───────────────────────────────────────────────────────────────

class LogEntry(ctk.CTkFrame):
    def __init__(self, master, ok: bool, text: str, output_path: Path | None = None, **kw):
        super().__init__(master, fg_color="#1e1e2e" if ok else "#2a1a1a", corner_radius=6, **kw)
        color = "#2ecc71" if ok else "#e74c3c"
        badge = " OK " if ok else "FAIL"
        ctk.CTkLabel(self, text=badge, fg_color=color, text_color="black",
                     corner_radius=4, font=("", 11, "bold"), width=40).pack(side="left", padx=8, pady=6)
        ctk.CTkLabel(self, text=text, anchor="w", font=("", 12),
                     wraplength=460).pack(side="left", fill="x", expand=True, padx=(0, 4))
        if ok and output_path:
            ctk.CTkButton(
                self, text="📂", width=32, height=28, fg_color="transparent",
                hover_color="#2a3a4a", font=("", 14),
                command=lambda p=output_path: _reveal_file(p),
            ).pack(side="right", padx=(0, 6))


# ─── Main window ─────────────────────────────────────────────────────────────

class App(ctk.CTk if not _HAS_DND else TkinterDnD.Tk):  # type: ignore[misc]
    def __init__(self):
        super().__init__()
        self.title("MetePDF")
        self.geometry(f"{_WIN_W}x{_WIN_H}")
        self.minsize(600, 520)
        self.resizable(True, True)

        self._files: list[Path] = []
        self._rows: list[FileRow] = []
        self._output_dir = _DEFAULT_OUTPUT
        self._converting = False

        self._build_ui()
        if _HAS_DND:
            self._setup_dnd()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self._build_header()
        self._build_drop_zone()
        self._build_file_list()
        self._build_output_row()
        self._build_action_row()
        self._build_progress()
        self._build_log()

    def _build_header(self):
        bar = ctk.CTkFrame(self, fg_color="#161622", corner_radius=0, height=52)
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)

        ctk.CTkLabel(bar, text="MetePDF", font=("", 20, "bold"), text_color="#4fa3e3").grid(
            row=0, column=0, padx=20, pady=12, sticky="w")
        ctk.CTkLabel(bar, text="Converter de arquivos para PDF", font=("", 12), text_color="gray60").grid(
            row=0, column=1, sticky="w")

        self._theme_btn = ctk.CTkButton(
            bar, text="☀", width=36, height=36, fg_color="transparent",
            hover_color="#2a2a3a", font=("", 16), command=self._toggle_theme,
        )
        self._theme_btn.grid(row=0, column=2, padx=16)

    def _build_drop_zone(self):
        zone = ctk.CTkFrame(self, fg_color="#1a1a2e", corner_radius=12, border_width=2, border_color="#2a2a4a")
        zone.grid(row=1, column=0, padx=20, pady=(14, 0), sticky="ew")
        zone.columnconfigure((0, 1, 2), weight=1)

        label_text = "Arraste arquivos aqui  •  ou use os botões" if _HAS_DND else "Adicione arquivos com os botões abaixo"
        ctk.CTkLabel(zone, text="📄  " + label_text, font=("", 13), text_color="gray60").grid(
            row=0, column=0, columnspan=3, pady=(14, 8))

        exts = "  ".join(_SUPPORTED)
        ctk.CTkLabel(zone, text=exts, font=("", 10), text_color="gray50").grid(
            row=1, column=0, columnspan=3, pady=(0, 10))

        ctk.CTkButton(zone, text="+ Arquivos", command=self._browse_files, width=130).grid(
            row=2, column=0, padx=20, pady=(0, 14), sticky="e")
        ctk.CTkButton(zone, text="+ Pasta", command=self._browse_folder, width=130,
                      fg_color="#2a4a6a", hover_color="#3a5a7a").grid(
            row=2, column=1, padx=4, pady=(0, 14))
        ctk.CTkButton(zone, text="Limpar lista", command=self._clear_files, width=130,
                      fg_color="#3a2a2a", hover_color="#4a3a3a").grid(
            row=2, column=2, padx=20, pady=(0, 14), sticky="w")

    def _build_file_list(self):
        self._file_scroll = ctk.CTkScrollableFrame(self, label_text="Arquivos selecionados", label_font=("", 12))
        self._file_scroll.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self._file_scroll.columnconfigure(0, weight=1)
        self._empty_label = ctk.CTkLabel(
            self._file_scroll, text="Nenhum arquivo adicionado ainda.",
            text_color="gray50", font=("", 12),
        )
        self._empty_label.grid(row=0, column=0, pady=20)

    def _build_output_row(self):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=3, column=0, padx=20, pady=(0, 6), sticky="ew")
        row.columnconfigure(1, weight=1)

        ctk.CTkLabel(row, text="Saída:", font=("", 13)).grid(row=0, column=0, padx=(0, 10))
        self._out_var = ctk.StringVar(value=str(_DEFAULT_OUTPUT))
        ctk.CTkEntry(row, textvariable=self._out_var, font=("", 12)).grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ctk.CTkButton(row, text="Selecionar", width=100, command=self._browse_output).grid(row=0, column=2)

    def _build_action_row(self):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=4, column=0, padx=20, pady=(0, 6), sticky="ew")
        row.columnconfigure(0, weight=1)

        self._count_label = ctk.CTkLabel(row, text="0 arquivo(s) na fila", font=("", 12), text_color="gray60")
        self._count_label.grid(row=0, column=0, sticky="w")

        self._convert_btn = ctk.CTkButton(
            row, text="Converter  →", width=160, height=38,
            font=("", 14, "bold"), command=self._start_conversion,
        )
        self._convert_btn.grid(row=0, column=1)

    def _build_progress(self):
        self._progress = ctk.CTkProgressBar(self, height=10, corner_radius=5)
        self._progress.set(0)
        self._progress.grid(row=5, column=0, padx=20, pady=(0, 4), sticky="ew")

        status_row = ctk.CTkFrame(self, fg_color="transparent")
        status_row.grid(row=6, column=0, padx=20, pady=(0, 2), sticky="ew")
        status_row.columnconfigure(0, weight=1)

        self._progress_label = ctk.CTkLabel(status_row, text="", font=("", 11), text_color="gray60")
        self._progress_label.grid(row=0, column=0, sticky="w")

        self._open_folder_btn = ctk.CTkButton(
            status_row, text="📂  Abrir pasta de saída", width=170, height=28,
            font=("", 12), fg_color="#1a3a2a", hover_color="#2a4a3a",
            command=self._open_output_folder,
        )
        self._open_folder_btn.grid(row=0, column=1)
        self._open_folder_btn.grid_remove()

    def _build_log(self):
        self._log_scroll = ctk.CTkScrollableFrame(self, label_text="Resultados", label_font=("", 12), height=130)
        self._log_scroll.grid(row=7, column=0, padx=20, pady=(4, 16), sticky="ew")
        self._log_scroll.columnconfigure(0, weight=1)

    # ── Drag & drop ───────────────────────────────────────────────────────────

    def _setup_dnd(self):
        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event):
        raw = event.data
        # tkinterdnd2 wraps paths with spaces in braces
        paths = self.tk.splitlist(raw)
        self._add_paths([Path(p) for p in paths])

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
            if not p.is_file():
                continue
            if p.suffix.lower() not in _SUPPORTED:
                continue
            if p in self._files:
                continue
            self._files.append(p)
            row = FileRow(self._file_scroll, p, on_remove=self._remove_row)
            row.grid(row=len(self._rows), column=0, sticky="ew", padx=4, pady=2)
            self._rows.append(row)
            added += 1

        if added:
            self._empty_label.grid_remove()
            self._update_count()

    def _remove_row(self, row: FileRow):
        self._files.remove(row.path)
        self._rows.remove(row)
        row.destroy()
        for i, r in enumerate(self._rows):
            r.grid(row=i)
        if not self._files:
            self._empty_label.grid(row=0, column=0, pady=20)
        self._update_count()

    def _clear_files(self):
        for row in self._rows:
            row.destroy()
        self._files.clear()
        self._rows.clear()
        self._empty_label.grid(row=0, column=0, pady=20)
        self._update_count()

    def _update_count(self):
        n = len(self._files)
        self._count_label.configure(text=f"{n} arquivo(s) na fila")

    # ── Conversion ────────────────────────────────────────────────────────────

    def _start_conversion(self):
        if self._converting:
            return
        if not self._files:
            self._flash_label(self._count_label, "Adicione pelo menos um arquivo!", "orange")
            return

        self._output_dir = Path(self._out_var.get())
        self._converting = True
        self._convert_btn.configure(state="disabled", text="Convertendo…")
        self._open_folder_btn.grid_remove()
        self._progress.set(0)
        self._progress_label.configure(text="")
        for widget in self._log_scroll.winfo_children():
            widget.destroy()

        threading.Thread(target=self._run_conversion, daemon=True).start()

    def _run_conversion(self):
        dispatcher = Dispatcher(output_dir=self._output_dir)
        total = len(self._files)
        done = 0

        for i, (path, row) in enumerate(zip(self._files, self._rows)):
            self.after(0, self._progress_label.configure, {"text": f"Convertendo {path.name}… ({i+1}/{total})"})
            try:
                out = dispatcher.dispatch(path)
                self.after(0, row.set_status, True)
                self.after(0, lambda p=path, o=out: self._log(True, f"{p.name}  →  {o}", o))
            except Any2PDFError as exc:
                self.after(0, row.set_status, False, str(exc))
                self.after(0, lambda p=path, e=exc: self._log(False, f"{p.name}  —  {e}"))
            done += 1
            self.after(0, self._progress.set, done / total)

        self.after(0, self._finish_conversion, done, total)

    def _finish_conversion(self, done: int, total: int):
        self._converting = False
        self._convert_btn.configure(state="normal", text="Converter  →")
        self._progress_label.configure(
            text=f"Concluído: {done}/{total} arquivo(s) convertido(s).",
            text_color="#2ecc71" if done == total else "orange",
        )
        if done > 0:
            self._open_folder_btn.grid()

    def _open_output_folder(self):
        _open_path(self._output_dir)

    def _log(self, ok: bool, text: str, output_path: Path | None = None):
        entry = LogEntry(self._log_scroll, ok, text, output_path=output_path)
        entry.grid(row=len(self._log_scroll.winfo_children()), column=0, sticky="ew", padx=4, pady=2)
        self._log_scroll._parent_canvas.yview_moveto(1.0)

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _toggle_theme(self):
        mode = ctk.get_appearance_mode()
        new_mode = "light" if mode == "Dark" else "dark"
        ctk.set_appearance_mode(new_mode)
        self._theme_btn.configure(text="🌙" if new_mode == "light" else "☀")

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _flash_label(label: ctk.CTkLabel, msg: str, color: str):
        original = label.cget("text")
        original_color = label.cget("text_color")
        label.configure(text=msg, text_color=color)
        label.after(2500, lambda: label.configure(text=original, text_color=original_color))


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _open_path(path: Path) -> None:
    """Open a file or folder in the system file manager."""
    target = path if path.is_dir() else path.parent
    system = platform.system()
    if system == "Windows":
        os.startfile(str(target))
    elif system == "Darwin":
        subprocess.Popen(["open", str(target)])
    else:
        subprocess.Popen(["xdg-open", str(target)])


def _reveal_file(path: Path) -> None:
    """Select and highlight a specific file in the file manager."""
    system = platform.system()
    if system == "Windows":
        subprocess.Popen(["explorer", "/select,", str(path)])
    elif system == "Darwin":
        subprocess.Popen(["open", "-R", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path.parent)])


def _ext_icon(ext: str) -> str:
    return {".pdf": "📕", ".docx": "📘", ".txt": "📄", ".png": "🖼", ".jpg": "🖼", ".jpeg": "🖼"}.get(ext, "📎")


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


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
