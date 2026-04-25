import platform
import subprocess
from pathlib import Path

from .base import BaseConverter
from core.exceptions import ConversionError

_IS_WINDOWS = platform.system() == "Windows"


class DocxConverter(BaseConverter):
    def convert(self, input_path: Path, output_path: Path) -> None:
        self._ensure_output_dir(output_path)
        # docx2pdf wraps LibreOffice on Linux/macOS and Word COM on Windows.
        # Import lazily to surface a clean error if the package is missing.
        try:
            from docx2pdf import convert  # type: ignore
        except ImportError as exc:
            raise ConversionError(
                str(input_path),
                "docx2pdf is not installed. Run: pip install docx2pdf",
            ) from exc

        if _IS_WINDOWS:
            self._convert_windows(convert, input_path, output_path)
        else:
            self._convert_unix(convert, input_path, output_path)

    @staticmethod
    def _convert_windows(convert_fn, input_path: Path, output_path: Path) -> None:
        # COM automation (Word) requires CoInitialize on the calling thread.
        # Without this, Word's STA apartment tries to marshal calls through the
        # main thread's message pump, deadlocking against tkinter's event loop.
        try:
            import pythoncom  # type: ignore
            pythoncom.CoInitialize()
        except ImportError:
            pass
        try:
            convert_fn(str(input_path), str(output_path))
        except Exception as exc:
            raise ConversionError(str(input_path), str(exc)) from exc
        finally:
            try:
                import pythoncom  # type: ignore
                pythoncom.CoUninitialize()
            except ImportError:
                pass

    @staticmethod
    def _convert_unix(convert_fn, input_path: Path, output_path: Path) -> None:
        # On Unix docx2pdf outputs to a directory, not a file path.
        try:
            convert_fn(str(input_path), str(output_path.parent))
            generated = output_path.parent / (input_path.stem + ".pdf")
            if generated != output_path and generated.exists():
                generated.rename(output_path)
        except Exception as exc:
            raise ConversionError(str(input_path), str(exc)) from exc
