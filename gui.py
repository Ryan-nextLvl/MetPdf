"""MetePDF — Desktop GUI powered by customtkinter."""

import os
import platform
import subprocess
import sys
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

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
_WIN_W, _WIN_H = 760, 620
_DEFAULT_OUTPUT = (
    Path(sys.executable).parent / "output"
    if getattr(sys, "frozen", False)
    else Path("output")
)

# ── Palette ──────────────────────────────────────────────────────────────────
_BG       = "#0f0f1a"
_SURFACE  = "#16162a"
_SURFACE2 = "#1e1e36"
_BORDER   = "#2a2a50"
_ACCENT   = "#4fa3e3"
_SUCCESS  = "#2ecc71"
_ERROR    = "#e74c3c"
_WARN     = "#f39c12"
_DIM      = "gray50"


# ─── File row ────────────────────────────────────────────────────────────────

class FileRow(ctk.CTkFrame):
    """One row in the queue: icon | name | size | status | remove."""

    _STATUS_IDLE       = ("Aguardando",  _DIM)
    _STATUS_CONVERTING = ("Convertendo…", _ACCENT)
    _STATUS_OK         = ("✓ Concluído",  _SUCCESS)

    def __init__(self, master, path: Path, on_remove, **kw):
        super().__init__(master, fg_color=_SURFACE2, corner_radius=8, **kw)
        self.path = path
        self.columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text=_ext_icon(path.suffix.lower()), width=30, font=("", 16)).grid(
            row=0, column=0, padx=(10, 4), pady=8)

        ctk.CTkLabel(self, text=path.name, anchor="w", font=("", 13)).grid(
            row=0, column=1, sticky="ew", padx=4)

        ctk.CTkLabel(self, text=_fmt_size(path), text_color=_DIM, font=("", 11),
                     width=64, anchor="e").grid(row=0, column=2, padx=(0, 8))

        self._status = ctk.CTkLabel(
            self, text=self._STATUS_IDLE[0], text_color=self._STATUS_IDLE[1],
            font=("", 11), width=96, anchor="w",
        )
        self._status.grid(row=0, column=3, padx=(0, 6))

        self._remove_btn = ctk.CTkButton(
            self, text="✕", width=26, height=26, fg_color="transparent",
            hover_color="#3a3a5a", text_color=_DIM, font=("", 12),
            command=lambda: on_remove(self),
        )
        self._remove_btn.grid(row=0, column=4, padx=(0, 8))

    # ── State transitions ─────────────────────────────────────────────────────

    def mark_converting(self):
        self._set_status(*self._STATUS_CONVERTING)

    def mark_success(self):
        self.configure(fg_color="#0e2319")
        self._set_status(*self._STATUS_OK)
        self._remove_btn.grid_remove()

    def mark_failed(self, reason: str = ""):
        self.configure(fg_color="#2a0e0e")
        short = (reason[:22] + "…") if len(reason) > 22 else reason
        self._set_status(f"✗ {short}", _ERROR)
        self._remove_btn.grid_remove()

    def reset(self):
        self.configure(fg_color=_SURFACE2)
        self._set_status(*self._STATUS_IDLE)
        self._remove_btn.grid()

    def _set_status(self, text: str, color: str):
        self._status.configure(text=text, text_color=color)


# ─── Main window ─────────────────────────────────────────────────────────────

class App(ctk.CTk if not _HAS_DND else TkinterDnD.Tk):  # type: ignore[misc]
    def __init__(self):
        super().__init__()
        self.title("MetePDF")
        self.geometry(f"{_WIN_W}x{_WIN_H}")
        self.minsize(600, 500)
        self.resizable(True, True)

        self._files: list[Path] = []
        self._rows: dict[Path, FileRow] = {}
        self._output_dir = _DEFAULT_OUTPUT
        self._service: ConversionService | None = None

        # TkinterDnD.Tk is plain Tk and does not accept fg_color
        if isinstance(self, ctk.CTk):
            self.configure(fg_color=_BG)

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

    def _build_header(self):
        bar = ctk.CTkFrame(self, fg_color=_SURFACE, corner_radius=0, height=56)
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)
        bar.grid_propagate(False)

        ctk.CTkLabel(bar, text="MetePDF", font=("", 22, "bold"), text_color=_ACCENT).grid(
            row=0, column=0, padx=20, pady=14, sticky="w")

        ctk.CTkLabel(bar, text="Conversor de arquivos para PDF", font=("", 12),
                     text_color=_DIM).grid(row=0, column=1, sticky="w")

        self._theme_btn = ctk.CTkButton(
            bar, text="☀", width=36, height=36, fg_color="transparent",
            hover_color=_SURFACE2, font=("", 16), command=self._toggle_theme,
        )
        self._theme_btn.grid(row=0, column=2, padx=16)

    def _build_drop_zone(self):
        zone = ctk.CTkFrame(self, fg_color=_SURFACE, corner_radius=12,
                            border_width=2, border_color=_BORDER)
        zone.grid(row=1, column=0, padx=20, pady=(16, 0), sticky="ew")
        zone.columnconfigure((0, 1, 2), weight=1)

        drop_hint = "Arraste arquivos ou pastas aqui" if _HAS_DND else "Selecione arquivos ou pastas"
        ctk.CTkLabel(zone, text=f"📥  {drop_hint}", font=("", 14),
                     text_color="gray60").grid(row=0, column=0, columnspan=3, pady=(18, 6))

        ctk.CTkLabel(zone, text="  ".join(_SUPPORTED), font=("", 10),
                     text_color=_DIM).grid(row=1, column=0, columnspan=3, pady=(0, 12))

        ctk.CTkButton(zone, text="+ Arquivos", command=self._browse_files,
                      width=140, height=34).grid(row=2, column=0, padx=20, pady=(0, 16), sticky="e")

        ctk.CTkButton(zone, text="+ Pasta", command=self._browse_folder, width=140, height=34,
                      fg_color="#2a4a6a", hover_color="#3a5a7a").grid(
            row=2, column=1, padx=4, pady=(0, 16))

        ctk.CTkButton(zone, text="Limpar lista", command=self._clear_files, width=140, height=34,
                      fg_color="#3a2a2a", hover_color="#4a3a3a").grid(
            row=2, column=2, padx=20, pady=(0, 16), sticky="w")

    def _build_file_list(self):
        self._file_scroll = ctk.CTkScrollableFrame(
            self, label_text="Arquivos na fila", label_font=("", 12), fg_color=_BG)
        self._file_scroll.grid(row=2, column=0, padx=20, pady=12, sticky="nsew")
        self._file_scroll.columnconfigure(0, weight=1)

        self._empty_label = ctk.CTkLabel(
            self._file_scroll,
            text="Nenhum arquivo adicionado.\nUse os botões acima ou arraste arquivos.",
            text_color=_DIM, font=("", 12), justify="center",
        )
        self._empty_label.grid(row=0, column=0, pady=28)

    def _build_output_row(self):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=3, column=0, padx=20, pady=(0, 8), sticky="ew")
        row.columnconfigure(1, weight=1)

        ctk.CTkLabel(row, text="Saída:", font=("", 13), width=50, anchor="w").grid(
            row=0, column=0, padx=(0, 8))
        self._out_var = ctk.StringVar(value=str(_DEFAULT_OUTPUT))
        ctk.CTkEntry(row, textvariable=self._out_var, font=("", 12)).grid(
            row=0, column=1, sticky="ew", padx=(0, 8))
        ctk.CTkButton(row, text="Selecionar", width=100, command=self._browse_output).grid(
            row=0, column=2)

    def _build_action_row(self):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=4, column=0, padx=20, pady=(0, 8), sticky="ew")
        row.columnconfigure(0, weight=1)

        self._count_label = ctk.CTkLabel(
            row, text="0 arquivo(s) na fila", font=("", 12), text_color=_DIM)
        self._count_label.grid(row=0, column=0, sticky="w")

        self._cancel_btn = ctk.CTkButton(
            row, text="Cancelar", width=110, height=38, font=("", 13),
            fg_color="#5a2a2a", hover_color="#6a3a3a",
            command=self._cancel_conversion,
        )
        self._cancel_btn.grid(row=0, column=1, padx=(0, 8))
        self._cancel_btn.grid_remove()

        self._convert_btn = ctk.CTkButton(
            row, text="Converter  →", width=160, height=38,
            font=("", 14, "bold"), command=self._start_conversion,
        )
        self._convert_btn.grid(row=0, column=2)

    def _build_progress(self):
        self._progress = ctk.CTkProgressBar(self, height=8, corner_radius=4)
        self._progress.set(0)
        self._progress.grid(row=5, column=0, padx=20, pady=(0, 4), sticky="ew")

        status_row = ctk.CTkFrame(self, fg_color="transparent")
        status_row.grid(row=6, column=0, padx=20, pady=(0, 16), sticky="ew")
        status_row.columnconfigure(0, weight=1)

        self._progress_label = ctk.CTkLabel(
            status_row, text="", font=("", 11), text_color=_DIM)
        self._progress_label.grid(row=0, column=0, sticky="w")

        self._open_folder_btn = ctk.CTkButton(
            status_row, text="📂  Abrir pasta de saída", width=170, height=28,
            font=("", 12), fg_color="#1a3a2a", hover_color="#2a4a3a",
            command=lambda: _open_path(self._output_dir),
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
            file_row.grid(row=len(self._rows), column=0, sticky="ew", padx=4, pady=3)
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
            self._empty_label.grid(row=0, column=0, pady=28)
        self._update_count()

    def _clear_files(self):
        for r in self._rows.values():
            r.destroy()
        self._files.clear()
        self._rows.clear()
        self._empty_label.grid(row=0, column=0, pady=28)
        self._update_count()

    def _update_count(self):
        n = len(self._files)
        self._count_label.configure(text=f"{n} arquivo(s) na fila")

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
        self._progress_label.configure(text="Iniciando…", text_color=_DIM)

        for r in self._rows.values():
            r.reset()

        # Mark the first file as "converting" immediately
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

        # Mark the next file in queue as converting
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
        msg = f"Concluído: {ok}/{total} arquivo(s) convertido(s)."
        self.after(0, self._finish_ui, msg, color, ok > 0)

    def _finish_ui(self, msg: str, color: str, show_folder: bool):
        self._convert_btn.configure(state="normal", text="Converter  →")
        self._cancel_btn.grid_remove()
        self._cancel_btn.configure(state="normal")
        self._progress_label.configure(text=msg, text_color=color)
        self._service = None
        if show_folder:
            self._open_folder_btn.grid()

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _toggle_theme(self):
        mode = ctk.get_appearance_mode()
        new_mode = "light" if mode == "Dark" else "dark"
        ctk.set_appearance_mode(new_mode)
        self._theme_btn.configure(text="🌙" if new_mode == "light" else "☀")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _open_path(path: Path) -> None:
    target = path if path.is_dir() else path.parent
    system = platform.system()
    if system == "Windows":
        os.startfile(str(target))
    elif system == "Darwin":
        subprocess.Popen(["open", str(target)])
    else:
        subprocess.Popen(["xdg-open", str(target)])


def _ext_icon(ext: str) -> str:
    return {
        ".pdf": "📕", ".docx": "📘", ".txt": "📄",
        ".png": "🖼", ".jpg": "🖼", ".jpeg": "🖼",
    }.get(ext, "📎")


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
