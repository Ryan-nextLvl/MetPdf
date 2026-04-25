import logging
from pathlib import Path

from core.exceptions import InputFileNotFoundError, UnsupportedFormatError
from utils.file_utils import build_output_path

logger = logging.getLogger(__name__)


def _registry() -> dict:
    # Imported lazily to break the circular chain:
    # converters -> core.__init__ -> dispatcher -> converters (circular!)
    from converters import DocxConverter, ImageConverter, PdfConverter, TxtConverter
    return {
        ".txt":  TxtConverter,
        ".png":  ImageConverter,
        ".jpg":  ImageConverter,
        ".jpeg": ImageConverter,
        ".docx": DocxConverter,
        ".pdf":  PdfConverter,
    }


class Dispatcher:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def dispatch(self, input_path: Path) -> Path:
        if not input_path.exists():
            raise InputFileNotFoundError(str(input_path))

        ext = input_path.suffix.lower()
        reg = _registry()
        converter_cls = reg.get(ext)
        if converter_cls is None:
            raise UnsupportedFormatError(ext)

        output_path = build_output_path(input_path, self.output_dir)
        logger.info("Converting '%s' → '%s' using %s",
                    input_path.name, output_path.name, converter_cls.__name__)
        converter_cls().convert(input_path, output_path)
        logger.info("Done: '%s'", output_path)
        return output_path

    @staticmethod
    def supported_extensions() -> list[str]:
        return sorted(_registry().keys())
