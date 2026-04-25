import platform
import subprocess
import sys
import tempfile
from pathlib import Path

from .base import BaseConverter
from core.exceptions import ConversionError

_IS_WINDOWS = platform.system() == "Windows"
_TIMEOUT = 120  # seconds before giving up on Word


def _exe_cmd() -> list[str]:
    """Return the command prefix to spawn a conversion worker process."""
    if getattr(sys, "frozen", False):
        # Frozen .exe re-runs itself with --_docx flag
        return [sys.executable]
    # Source: run via gui.py which handles --_docx at the top
    gui_py = Path(__file__).resolve().parent.parent / "gui.py"
    return [sys.executable, str(gui_py)]


class DocxConverter(BaseConverter):
    def convert(self, input_path: Path, output_path: Path) -> None:
        self._ensure_output_dir(output_path)
        try:
            import docx2pdf  # noqa: F401 — verify it's installed
        except ImportError as exc:
            raise ConversionError(
                str(input_path),
                "docx2pdf não está instalado. Execute: pip install docx2pdf",
            ) from exc

        if _IS_WINDOWS:
            self._convert_windows(input_path, output_path)
        else:
            self._convert_unix(input_path, output_path)

    @staticmethod
    def _convert_windows(input_path: Path, output_path: Path) -> None:
        # Run conversion in a completely separate process to avoid
        # Word COM (STA) deadlocking against tkinter's message loop.
        with tempfile.NamedTemporaryFile(
            suffix=".txt", delete=False, mode="w"
        ) as tf:
            error_path = tf.name

        cmd = _exe_cmd() + [
            "--_docx",
            str(input_path.resolve()),
            str(output_path.resolve()),
            error_path,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, timeout=_TIMEOUT)
        except subprocess.TimeoutExpired:
            subprocess.run(
                ["taskkill", "/f", "/im", "WINWORD.EXE"], capture_output=True
            )
            raise ConversionError(
                str(input_path),
                f"Timeout: Word não respondeu após {_TIMEOUT}s",
            )

        error_msg = ""
        try:
            with open(error_path, encoding="utf-8") as f:
                error_msg = f.read().strip()
        except OSError:
            pass

        if result.returncode != 0:
            raise ConversionError(
                str(input_path),
                error_msg or f"Falha na conversão (código {result.returncode})",
            )

    @staticmethod
    def _convert_unix(input_path: Path, output_path: Path) -> None:
        try:
            from docx2pdf import convert  # type: ignore
            convert(str(input_path), str(output_path.parent))
            generated = output_path.parent / (input_path.stem + ".pdf")
            if generated != output_path and generated.exists():
                generated.rename(output_path)
        except Exception as exc:
            raise ConversionError(str(input_path), str(exc)) from exc
