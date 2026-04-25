# MetePDF

Convert TXT, images (PNG/JPG), DOCX, and PDF files to PDF from the command line.

## Installation

### Recommended — using `uv` (fastest)

If you have Claude Code open inside this project, just run:
```
/install
```
The custom command installs `uv` automatically if needed, creates the virtualenv, and installs all dependencies.

### Manual — uv

```bash
# Install uv (once)
# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv + install
uv venv .venv
uv pip install -r requirements.txt --python .venv

# Activate
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate
```

### Manual — pip (fallback)

```bash
pip install -r requirements.txt
```

> **Windows + DOCX:** `docx2pdf` requires Microsoft Word to be installed.  
> **Linux/macOS + DOCX:** Install LibreOffice (`sudo apt install libreoffice` or `brew install libreoffice`).

## Usage

```bash
# Single file
python main.py document.docx

# Multiple files
python main.py file1.txt file2.png file3.jpg

# Entire directory
python main.py input/

# Recursive directory scan
python main.py input/ --recursive

# Custom output directory
python main.py input/ --output results/

# Verbose logging
python main.py input/ --verbose
```

## Project structure

```
any2pdf/
├── main.py                  # CLI entry point
├── requirements.txt
├── converters/
│   ├── base.py              # Abstract BaseConverter
│   ├── txt_converter.py     # TXT → PDF via reportlab
│   ├── image_converter.py   # PNG/JPG → PDF via Pillow + reportlab
│   ├── docx_converter.py    # DOCX → PDF via docx2pdf
│   └── pdf_converter.py     # PDF → validate + copy via PyMuPDF
├── core/
│   ├── dispatcher.py        # Routes files to the right converter
│   └── exceptions.py        # Custom exception hierarchy
├── utils/
│   └── file_utils.py        # Path helpers
├── input/                   # Drop source files here
└── output/                  # PDFs land here
```

## Supported formats

| Extension | Strategy |
|-----------|----------|
| `.txt` | reportlab — preserves line breaks, A4 layout |
| `.png` `.jpg` `.jpeg` | Pillow + reportlab — centred, aspect-ratio preserved |
| `.docx` | docx2pdf (Word on Windows, LibreOffice on Unix) |
| `.pdf` | PyMuPDF validation + file copy |

## Adding a new converter

1. Create `converters/my_format_converter.py` extending `BaseConverter`.
2. Implement `convert(self, input_path, output_path)`.
3. Register the extension in `core/dispatcher.py` inside `_REGISTRY`.
