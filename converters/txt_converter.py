from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from .base import BaseConverter
from core.exceptions import ConversionError

_MARGIN = 20 * mm
_FONT_SIZE = 10
_LINE_SPACING = 4


class TxtConverter(BaseConverter):
    def convert(self, input_path: Path, output_path: Path) -> None:
        self._ensure_output_dir(output_path)
        try:
            text = input_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise ConversionError(str(input_path), str(exc)) from exc

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=_MARGIN,
            rightMargin=_MARGIN,
            topMargin=_MARGIN,
            bottomMargin=_MARGIN,
        )
        styles = getSampleStyleSheet()
        body_style = styles["BodyText"]
        body_style.fontSize = _FONT_SIZE
        body_style.leading = _FONT_SIZE + _LINE_SPACING

        story = []
        for line in text.splitlines():
            story.append(Paragraph(line or "&nbsp;", body_style))
            story.append(Spacer(1, 1))

        try:
            doc.build(story)
        except Exception as exc:
            raise ConversionError(str(input_path), str(exc)) from exc
