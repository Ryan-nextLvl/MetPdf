"""
MetePDF — convert files to PDF from the command line.

Usage examples:
    python main.py document.docx
    python main.py input/photo.jpg --output output/
    python main.py input/ --recursive
    python main.py file1.txt file2.png --output results/
"""

import argparse
import logging
import sys
from pathlib import Path

from core.service import ConversionResult, ConversionService
from utils.file_utils import collect_input_files

_DEFAULT_OUTPUT = Path("output")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="metepdf",
        description="Convert TXT, images, DOCX, and PDF files into PDF.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Supported extensions: .txt .png .jpg .jpeg .docx .pdf",
    )
    parser.add_argument("inputs", nargs="+", type=Path, metavar="FILE_OR_DIR",
                        help="One or more files or directories to convert.")
    parser.add_argument("-o", "--output", type=Path, default=_DEFAULT_OUTPUT, metavar="DIR",
                        help=f"Output directory (default: {_DEFAULT_OUTPUT}).")
    parser.add_argument("-r", "--recursive", action="store_true",
                        help="Recurse into directories.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose logging.")
    return parser


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )


def _on_progress(done: int, total: int, result: ConversionResult) -> None:
    if result.success:
        print(f"  [OK]   {result.input_path.name}  →  {result.output_path}")
    else:
        print(f"  [FAIL] {result.input_path.name}  —  {result.error}", file=sys.stderr)


def main() -> int:
    args = _build_parser().parse_args()
    _configure_logging(args.verbose)

    files = collect_input_files(args.inputs, recursive=args.recursive)
    if not files:
        print("Nenhum arquivo encontrado.", file=sys.stderr)
        return 1

    service = ConversionService(args.output)
    results = service.convert_files(files, on_progress=_on_progress)

    ok = sum(1 for r in results if r.success)
    failed = len(results) - ok
    print(f"\nConcluído: {ok} convertido(s), {failed} falha(s).")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
