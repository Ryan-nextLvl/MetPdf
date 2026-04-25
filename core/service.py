"""ConversionService — unified backend used by both CLI and GUI."""

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from core.dispatcher import Dispatcher
from core.exceptions import Any2PDFError


@dataclass
class ConversionResult:
    input_path: Path
    output_path: Path | None
    success: bool
    error: str | None = None


ProgressCallback = Callable[[int, int, ConversionResult], None]
DoneCallback = Callable[[list[ConversionResult]], None]


class ConversionService:
    def __init__(self, output_dir: Path) -> None:
        self._dispatcher = Dispatcher(output_dir)
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def convert_files(
        self,
        files: list[Path],
        on_progress: ProgressCallback | None = None,
        on_done: DoneCallback | None = None,
        *,
        threaded: bool = False,
    ) -> list[ConversionResult]:
        """Convert a list of files. If threaded=True, returns immediately."""
        self._cancel.clear()
        if threaded:
            threading.Thread(
                target=self._run,
                args=(files, on_progress, on_done),
                daemon=True,
            ).start()
            return []
        return self._run(files, on_progress, on_done)

    def _run(
        self,
        files: list[Path],
        on_progress: ProgressCallback | None,
        on_done: DoneCallback | None,
    ) -> list[ConversionResult]:
        results: list[ConversionResult] = []
        for i, f in enumerate(files):
            if self._cancel.is_set():
                break
            try:
                out = self._dispatcher.dispatch(f)
                r = ConversionResult(f, out, success=True)
            except Any2PDFError as exc:
                r = ConversionResult(f, None, success=False, error=str(exc))
            except Exception as exc:
                r = ConversionResult(f, None, success=False, error=f"Erro inesperado: {exc}")
            results.append(r)
            if on_progress:
                on_progress(i + 1, len(files), r)
        if on_done:
            on_done(results)
        return results
