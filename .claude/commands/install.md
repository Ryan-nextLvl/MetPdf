Install all MetePDF dependencies using `uv`. Follow these steps exactly:

## Step 1 — check if `uv` is installed
Run:
```
uv --version
```
If the command fails (uv not found), install it by running the appropriate command for the current OS:
- **Windows**: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- **Linux/macOS**: `curl -LsSf https://astral.sh/uv/install.sh | sh`

After installing, verify again with `uv --version` and show the version to the user.

## Step 2 — create virtual environment
Run inside the `any2pdf/` directory:
```
uv venv .venv
```
If `.venv` already exists, skip this step and inform the user.

## Step 3 — install dependencies
Run:
```
uv pip install -r requirements.txt --python .venv
```
This will install: Pillow, reportlab, docx2pdf, PyMuPDF, customtkinter, tkinterdnd2.

## Step 4 — show summary
After everything succeeds, print a clear summary with:
- uv version used
- Python version inside the venv
- List of installed packages (run `uv pip list --python .venv`)
- How to run the app:
  - **GUI**: `python gui.py`
  - **CLI**: `python main.py <arquivo>`
- How to activate the venv:
  - Windows: `.venv\Scripts\activate`
  - Linux/macOS: `source .venv/bin/activate`
