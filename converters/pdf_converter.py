import shutil
from pathlib import Path

import fitz  # PyMuPDF

from .base import BaseConverter
from core.exceptions import ConversionError


class PdfConverter(BaseConverter):
    def convert(self, input_path: Path, output_path: Path) -> None:
        self._ensure_output_dir(output_path)
        self._validate(input_path)
        try:
            shutil.copy2(input_path, output_path)
        except OSError as exc:
            raise ConversionError(str(input_path), str(exc)) from exc

    @staticmethod
    def _validate(input_path: Path) -> None:
        try:
            doc = fitz.open(str(input_path))
            if doc.is_encrypted:
                raise ConversionError(str(input_path), "PDF is encrypted/password-protected")
            page_count = doc.page_count
            doc.close()
            if page_count == 0:
                raise ConversionError(str(input_path), "PDF has no pages")
        except ConversionError:
            raise
        except Exception as exc:
            raise ConversionError(str(input_path), f"Invalid or corrupt PDF: {exc}") from exc
