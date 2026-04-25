from abc import ABC, abstractmethod
from pathlib import Path


class BaseConverter(ABC):
    @abstractmethod
    def convert(self, input_path: Path, output_path: Path) -> None:
        """Convert input_path to a PDF at output_path."""

    def _ensure_output_dir(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
