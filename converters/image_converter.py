from pathlib import Path

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .base import BaseConverter
from core.exceptions import ConversionError

_PAGE_W, _PAGE_H = A4
_MARGIN = 10 * mm


class ImageConverter(BaseConverter):
    def convert(self, input_path: Path, output_path: Path) -> None:
        self._ensure_output_dir(output_path)
        try:
            img = Image.open(input_path)
            img = img.convert("RGB")
        except Exception as exc:
            raise ConversionError(str(input_path), str(exc)) from exc

        max_w = _PAGE_W - 2 * _MARGIN
        max_h = _PAGE_H - 2 * _MARGIN
        img_w, img_h = img.size
        scale = min(max_w / img_w, max_h / img_h, 1.0)
        draw_w = img_w * scale
        draw_h = img_h * scale
        x = (_PAGE_W - draw_w) / 2
        y = (_PAGE_H - draw_h) / 2

        try:
            c = canvas.Canvas(str(output_path), pagesize=A4)
            c.drawInlineImage(img, x, y, draw_w, draw_h)
            c.save()
        except Exception as exc:
            raise ConversionError(str(input_path), str(exc)) from exc
