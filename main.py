"""
Any2PDF — convert files to PDF from the command line.

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

from core.dispatcher import Dispatcher
from core.exceptions import Any2PDFError
from utils.file_utils import collect_input_files

_DEFAULT_OUTPUT = Path("output")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="any2pdf",
        description="Convert TXT, images, DOCX, and PDF files into PDF.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Supported extensions: .txt .png .jpg .jpeg .docx .pdf",
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        metavar="FILE_OR_DIR",
        help="One or more files or directories to convert.",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        metavar="DIR",
        help=f"Output directory (default: {_DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Recurse into directories.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    return parser


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    _configure_logging(args.verbose)

    logger = logging.getLogger(__name__)
    dispatcher = Dispatcher(output_dir=args.output)
    files = collect_input_files(args.inputs, recursive=args.recursive)

    if not files:
        logger.error("No input files found.")
        return 1

    success, failed = 0, 0
    for file in files:
        try:
            out = dispatcher.dispatch(file)
            print(f"  [OK]  {file}  →  {out}")
            success += 1
        except Any2PDFError as exc:
            print(f"  [FAIL]  {file}  —  {exc}", file=sys.stderr)
            logger.debug("", exc_info=True)
            failed += 1

    print(f"\nDone: {success} converted, {failed} failed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
